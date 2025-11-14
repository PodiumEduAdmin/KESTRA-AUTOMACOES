import os
import dotenv
import base64
import requests
import re
from langchain.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.exceptions import OutputParserException 
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
# Importar para melhor tratamento de erros
from kestra import Kestra
from CLASSES.notion_class import NotiondriveAPI
from CLASSES.pipe_class import PipedriveAPI
import datetime as dt
import json

# --- Configurações Iniciais ---
# dotenv.load_dotenv("./.env")
# api_key = os.getenv('GOOGLE_API')

# notion_token = os.getenv("NOTION_TOKEN")
notion_token = os.environ['NOTION_TOKEN']
api_notion = NotiondriveAPI(notion_token)

# os.environ["GOOGLE_API_KEY"] = api_key

# Inicialização do Modelo
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
    max_tokens=None, # Deixa o LLM decidir o melhor
    timeout=None,    # Deixa o LLM decidir o melhor
    max_retries=2,
)

# url = "https://podium.3c.plus/api/v1/calls/6915e4e5ecc4600c8b673031/recording"

url = os.environ['URL']

# --- Funções Auxiliares para Chunking ---

def split_text_into_chunks(text, max_chars=1950):
    """Divide um texto longo em chunks com limite de caracteres."""
    if not text:
        return []
    
    # Tenta quebrar por frases ou linhas para manter coerência
    sentences = re.split(r'([.!?])\s+', text)
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        if len(current_chunk) + len(sentence) < max_chars:
            current_chunk += sentence
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence
    
    if current_chunk:
        chunks.append(current_chunk.strip())
        
    # Garante que sempre terá 10 partes, mesmo que vazias, para o schema Notion
    while len(chunks) < 10:
        chunks.append("")
        
    return chunks[:10] # Retorna no máximo 10 partes

def get_safe_str(data_dict, key, default="N/A"):
    """Extrai um valor do dicionário, tratando listas e sets como strings seguras."""
    value = data_dict.get(key, default)
    
    if isinstance(value, (list, set)):
        # Junta listas/sets em uma string com quebra de linha
        return "\n".join(map(str, value))
    
    # Adiciona um tratamento específico para o padrao_comportamental que usa emojis
    if key == "padrao_comportamental":
        # Remove emojis de cor e o caractere '#'
        return str(value).replace("🔵", "").replace("🔴", "").replace("🟡", "").replace("🟢", "").replace("#", "").strip()

    return str(value)


# --- INÍCIO DO FLUXO PRINCIPAL ---
r = requests.get(url)

if r.status_code == 200:
    
    audio_bytes = r.content 
    audio_mime_type = "audio/mpeg" 

    print("✅ Áudio baixado para a memória. Iniciando codificação...")
    encoded_audio = base64.b64encode(audio_bytes).decode("utf-8")
    
    # 1. TRANSCRIÇÃO (AUDIO -> TEXTO COMPLETO)
    
    # Mensagem de solicitação de transcrição (sem análise ainda)
    transcription_message = HumanMessage(
        content=[
            {
                "type": "text", 
                "text": "Transcreva o áudio de maneira completa e fiel, informando os minuto expecífico do diálogo e também identificando os locutores com 🟢SDR e 🟣CLIENTE, adicione quebra de linha entre as conversas dos locutores para manter organizado."
            },
            {
                "type": "media",
                "data": encoded_audio,
                "mime_type": audio_mime_type,
            },
        ]
    )
    
    try:
        print("⏳ 1/3: Enviando áudio para transcrição completa...")
        response_transcription = llm.invoke([transcription_message])
        full_transcript = response_transcription.content
        print("✅ 1/3: Transcrição concluída. Quebrando em chunks para análise...")

        # Quebra a transcrição completa em chunks de 2000 caracteres
        chunks = split_text_into_chunks(full_transcript, max_chars=2000)
        
        # 2. SUMARIZAÇÃO EM CHUNKS (Redução do Contexto)
        summarized_chunks = []
        
        # System Message para forçar um resumo conciso de cada chunk
        system_summary_msg = SystemMessage("Você é um assistente que recebe partes de uma transcrição de ligação. Sua única tarefa é fazer um resumo MUITO CONCISO e objetivo (máximo 100 palavras) sobre o que foi discutido nesta parte da conversa. Não adicione contexto externo, apenas resuma.")

        for i, chunk in enumerate(chunks):
            if not chunk: continue
            
            print(f"⏳ Processando Chunk {i+1}/{len(chunks)}...")
            summary_prompt = [
                system_summary_msg,
                HumanMessage(f"RESUMA: {chunk}")
            ]
            
            response_summary = llm.invoke(summary_prompt)
            summarized_chunks.append(response_summary.content)

        # 3. ANÁLISE FINAL (CONCATENAÇÃO DOS RESUMOS + PROMPT ESTRUTURADO)
        
        # O modelo fará a análise final em cima deste texto reduzido
        concatenated_summary = "\n---\n".join(summarized_chunks)
        
        # Adicione a transcrição completa quebrada em partes ao prompt para garantir que a IA possa acessá-la
        # e preencher as 10 partes do Notion (Embora seja mais seguro extrair estas partes do 'full_transcript'
        # e preencher no JSON final).

        system_msg = SystemMessage("""
        Você é uma IA especialista em análise de ligações de pré-vendas. Sua missão é avaliar a performance do SDR com base em critérios do método NEPQ e atribuir uma nota objetiva de 1 a 5 para cada etapa, considerando clareza, profundidade, adequação e impacto da fala.
        IMPORTANTE:
        - Use exemplos reais ditos pelo lead como parâmetro da eficácia.
        - Deixa claro na resposta o que o lead falou de forma espontanea e o que foi induzido pelo pré-vendedor
        - Entender para todos os critérios avaliados o mesmo problema, construindo uma linha lógica de avaliação (os critérios fazendo parte de um mesmo script de pré-vendas)

        QUEBRE ESTA TRANSCRIÇÃO EM "10" PARTES SE NECESSÁRIO, RELATIVAMENTE IGUAIS POR FAVOR, CADA PARTE NÃO PODE PASSAR DE 2000 LETRA, PRECISO INCLUIR ESTA INFORMAÇÃO NO NOTION E ESTÁ ESTOURANDO O LIMITE DE 2000 LETRAS.

        FORMATO DE RESPOSTA (OBRIGATÓRIO)

        Para cada um dos critérios abaixo, responda com:
        1.	🎯 Nota (de 1 a 5);
        2. Minutagem;
        3.	💬 Trecho da fala revelando o problema **(LITERAL COM NO MÁXIMO 30 PALAVRAS) - SEMPRE identificar o LEAD e o SDR incluindo a Minutagem da fala**.
        4.  Qual a lista de problemas ou desafios identificados?
        5.	💬 Trecho da fala revelando os desdobramento do problema identificado **(LITERAL COM NO MÁXIMO 30 PALAVRAS) - SEMPRE identificar o LEAD e o SDR incluindo a Minutagem da fala**. ( caso não tenha uma pergunta de desdobramento sobre algum dos problemas identificados, fale que não houve desdobramento do especificamente do problema.
        6.  Qual o aprofundamento dos problemas segundo a provocação do SDR
        7.	📌 Feedback brutalmente direto sobre a qualidade analisada
        8.	🛠 Sugestão prática de melhoria (se nota < 5)

        1. INVESTIGAÇÃO: CRIOU CLAREZA DA DOR E ENTENDEU A FUNDO O PROBLEMA.

        Objetivo: Avaliar se o SDR levantou um problema real e relevante da barbearia — mesmo que o lead não tenha percebido isso de imediato. - e aprofundou nesse problema.

        Critérios para nota:
        •	Nota 4 ou 5: O SDR conduziu perguntas que revelaram uma dor clara (ex: instabilidade no faturamento, agenda vazia, dependência do dono, equipe desmotivada). + aprofundou nessa dor identificada.
        •	Nota 3: O SDR fez perguntas mas NÃO se aprofundou de forma natural com perguntas inteligentes e investigativas, após saber da dor.
        •	Nota 1 ou 2: Fez perguntas genéricas ou aceitou somente a resposta superficial do cliente na abertura de ligação. (não fez nenhuma pergunta que entendesse os desdobramentos do problema identificado. 
        •	Nota 0: Ausência de investigação de problema e aprofundamento. 

        OBRIGATÓRIO: A dor real precisa ser a falada pelo cliente APENAS depois da pergunta provocativa do SDR, e não problemas soltos ao longo da ligação.

        Exemplos esperados:
        "Qual o maior problema que você vê no seu dia a dia que acontece pelo fato de você não ter um sistema? "
        “O que você já tentou fazer pra resolver isso?”
        “E por que isso ainda não foi resolvido?”

        2. DESCOBERTA DO SONHO (gatilho do ‘gap’ entre dor e desejo)

        Objetivo: Avaliar se o SDR entendeu quais os sonhos que o lead possui e o que solucionar os desafios citados traria para a sua barbearia 

        FORMATO DE RESPOSTA (OBRIGATÓRIO)

        Para cada um dos critérios abaixo, responda com: 
        1.	🎯 Nota (de 1 a 5);
        2. Minutagem;
        3.	💬 Trecho da fala revelando o sonho **(LITERAL COM NO MÁXIMO 30 PALAVRAS) - SEMPRE identificar o LEAD e o SDR incluindo a Minutagem da fala**. (se não tiver investigado isso, mencionar que não perguntou na ligação)
        4.  Qual a lista dos sonhos ou conquistas identificados? (se não tiver investigado isso, mencionar que não perguntou na ligação)
        5.	💬 Trecho da fala revelando os desdobramento do sonho identificados **(LITERAL COM NO MÁXIMO 30 PALAVRAS) - SEMPRE identificar o LEAD e o SDR incluindo a Minutagem da fala**. (se não tiver investigado isso, mencionar que não perguntou na ligação)
        6.  Qual o aprofundamento dos das conquistas que o lead terá resolvendo seus problemas e desafios citados dentro dos próximos 6 a 12 meses (se não tiver investigado isso, mencionar que não perguntou na ligação)
        7.	📌 Feedback brutalmente direto sobre a qualidade analisada
        8.	🛠 Sugestão prática de melhoria (se nota < 5)

        Critérios para nota:
        •	Nota 4 ou 5: O SDR conduziu perguntas que revelaram o sonhos . + aprofundou no que a resolução desses problemas traria para sua barbearia e sua vida pessoal dentro de 6 a 12 meses
        •	Nota 3: O SDR fez perguntas de sonho mas NÃO se aprofundou no que a resolução dos problemas citados traria para a sua vida e a sua barbearia dentro de 6 a 12 meses 
        •	Nota 1 ou 2: Fez perguntas genéricas de sonhos, aceito de forma rasa o que ele busca para o futuro da sua barbearia 
        •	Nota 0: Ausência de investigação de realizações de sonho

        OBRIGATÓRIO: Entender se a resolução estivesse resolvido como que seria a barbearia e a vida pessoal do lead dentro dos próximos 6 a 12 meses 

        Exemplos de pergunta:

        “E pensando no futuro... como você imagina sua barbearia ideal nos próximos 12 meses?
        Menos operação? Mais equipe? Mais estabilidade?”
        “Hoje o que mais te impede de chegar nesse cenário?”

        3. DESPERTE O INTERESSE DO CLIENTE ATENDENDO A DOR REAL: (mostre que nossa solução serve na medida do seu problema.)

        Objetivo: É sobre responder uma dor real com uma solução específica presente no produto!
        O lead precisa sentir: “Isso resolve exatamente o que estou passando.”

        Identifique qual foi a dor real expressa pelo cliente (ex: “agenda vazia”, “trabalhar fora”, “equipe sem vendas”).

        Verifique se houve uma explicação objetiva do modelo ou sistema, com termos como: recorrência, fidelização, aumento de ticket, ocupação, etc.

        FORMATO DE RESPOSTA (OBRIGATÓRIO)

        Para cada um dos critérios abaixo, responda com: 
        1.	🎯 Nota (de 1 a 5);
        2. Minutagem;
        3. Trecho da fala que sita o problema real do lead indagado pelo SDR **(LITERAL COM NO MÁXIMO 30 PALAVRAS) - SEMPRE identificar o LEAD e o SDR incluindo a Minutagem da fala**. (se não tiver investigado isso, mencionar que não perguntou na ligação)
        4.	💬 Trecho da fala revelando a explicação do SDR sobre um entregável do produto ou estratégico **(LITERAL COM NO MÁXIMO 30 PALAVRAS) - SEMPRE identificar o LEAD e o SDR incluindo a Minutagem da fala**. (se não tiver investigado isso, mencionar que não perguntou na ligação)
        5.	💬 Trecho da fala revelando os desdobramento do entregável ou estrategia **(LITERAL COM NO MÁXIMO 30 PALAVRAS) - SEMPRE identificar o LEAD e o SDR incluindo a Minutagem da fala**. (se não tiver investigado isso, mencionar que não perguntou na ligação)
        6.	📌 Feedback brutalmente direto sobre a qualidade analisada
        7.	🛠 Sugestão prática de melhoria (se nota < 5)


        Critérios para nota:
        •	Nota 4 ou 5: O SDR explicou de forma clara de completa algum entregavel e também envolveu a dor do cliente na explicação dando o gancho pra a venda da consultoria 
        •	Nota 3: O SDR fez perguntas explicou algum entregavel mais não envolveu a dor do cliente durante a explicacão
        •	Nota 1 ou 2: conduziu de forma errada vendendo a consultoria e nao explicando entregavel do produto ou estrategia
        •	Nota 0: Ausência de investigação de explicação de entregavel ou estrategia 

        OBRIGATÓRIO:  Entender se o Sdr explicou de forma clara algum entregável ou estratégia que solucione aquele problema que o lead mencionou na ligação.

        Exemplo de comportamento: 

        “Ah sim, seu desafio de lotar a agenda é exatamente o que vai possibilitar você crescer mais rápido e finalmente sair do operacional, né? Deixa eu te falar: o modelo de assinatura funciona exatamente nesses casos. A gente aumenta muito rápido a taxa de ocupação e consegue faturar 3x mais com o mesmo cliente. Sem precisar de novos clientes, você já consegue atingir esse objetivo. E é exatamente isso que você vai ver na Consultoria com o nosso Especialista.”

        4. PROMOVEU A ESCASSEZ NA AGENDA DO ESPECIALISTA

        Objetivo: Avaliar se o SDR vendeu com autoridade, personalização e escassez a reunião.

        FORMATO DE RESPOSTA (OBRIGATÓRIO)

        Para cada um dos critérios abaixo, responda com: 
        1.	🎯 Nota (de 1 a 5) ;
        2. Minutagem;
        3.	💬 Trecho da fala do SDR oferecendo a reunião com escassez e direto na dor do cliente **(LITERAL COM NO MÁXIMO 30 PALAVRAS) - SEMPRE identificar o LEAD e o SDR incluindo a Minutagem da fala**. (se não tiver investigado isso, mencionar que não perguntou na ligação)
        4.	📌 Feedback brutalmente direto sobre a qualidade analisada
        5.	🛠 Sugestão prática de melhoria (se nota < 5)

        Critérios para nota:
        •	Nota 4 ou 5: O SDR ofereceu a reunião com base as dores vinculando soluções para resolver as dores de forma personalizada, sendo escasso com os horários do especialista e trazendo urgência para o agendamento. 
        •	Nota 3: O SDR somente ofereceu os horários disponíveis sem oferecer a reunião como um meio de solução para os problemas do cliente e sem criar urgência para o agendamento.
        •	Nota 1 ou 2: O SDR apenas passou horários listados sem gerar nenhum valor. 
        •	Nota 0: Ausência de oferta de horários para a reunião com o especialista.

        OBRIGATÓRIO: Gerar valor ao oferecer a reunião e personalizar as soluções com base na dor.

        Exemplos de venda da reunião:

        “Esse horário foi liberado porque vimos que sua barbearia tem estrutura e já tem equipe — é esse tipo de perfil que nosso especialista prioriza.”
        “Acho que já ficou claro que tem um espaço entre onde você está e onde quer chegar.
        O que a gente faz aqui é justamente montar um plano pra reduzir esse gap.
        Esse plano é apresentado numa reunião 100% personalizada, que dura cerca de 1 hora, onde mostramos como barbearias como a sua estão aumentando a taxa de ocupação, engajando o time e saindo do operacional com segurança.
        Faz sentido reservar esse horário contigo?”

        5 - PERFIL MKT (CAMPO NO PIPEDRIVE)

        Você é um analista especialista em vendas e marketing B2B. Sua função é analisar uma transcrição de ligação de prospecção feita por um SDR e gerar um feedback direto e resumido sobre a qualidade do lead, com base nos critérios abaixo.

        A resposta deve ser o mais objetiva e curta possível, sem perder clareza — utilize bullet points e frases curtas, evitando repetições e redundâncias.

        Condense ao máximo o texto, sem linhas vazias ou muitos emojis. - a ideia é ser sucinto.

        ⸻

        📋 ANÁLISE DE LEAD — PERFIL DO AVATAR
        1.	Conhece o produto ou o Lincohn?
        * [Sim/Não/Parcialmente]
        * [Breve observação se necessário]
        2.	Faturamento mensal estimado:
        * [Valor ou “não identificado”]
        3.	Tamanho da equipe:
        * [Número de barbeiros ou “não citado”]
        4.	Principal queixa/dificuldade:
        * [Aqui pode lista as dificuldades, a ideia é entender a demanda]
        5.	Gerou agendamento?
        * [Sim/Não] 
        * [Observação se necessário]
        6.	Motivo para desqualificação (se houver):
        * [Sim/Não + motivo claro em poucas palavras]

        6 - PERFIL COMPORTAMENTAL

        Com base na transcrição, defina qual o perfil comportamental do meu cliente

        Deixei claro os motivos e as transcrições chaves (com minutagem) que utilizou para o julgamento.

        Siga o método DISC

        ----

        EXEMPLO DE MODELO DE RESPOSTAS
        ➡️ Padrão Comportamental 🔴#DOMINANTE#

        ➡️ Explicação dos Motivos:

        ➡️ Erros e Acertos que o atendente cometeu na ligação: 

        ➡️ Orientações práticas e contextualizadas para o Consultor que fará a Reunião:

        ➡️ Trechos utilizados:

        ---

        CRITÉRIOS

        🔴 1. Cliente Dominante
        Foco: Resultados rápidos.
        Comportamento: Objetivo, direto, impaciente, competitivo
        O que ele valoriza: Eficiência, agilidade, liderança.
        Como atender: Vá direto ao ponto, mostre ganhos concretos e impacto. Evite enrolação.

        Exemplo de abordagem:
        “Com essa solução, você vai conseguir reduzir em 30% os custos logo no primeiro mês.”

        🟡 2. Cliente Influente
        Foco: Relacionamento e entusiasmo.
        Comportamento: Comunicativo, emocional, expressivo, impulsivo.
        O que ele valoriza: Conexão, experiências, inovação.
        Como atender: Seja carismático, use histórias, gere entusiasmo. Use elementos visuais e envolventes.

        Exemplo de abordagem:
        “Temos clientes parecidos com você que estão amando a experiência com nosso serviço!”

        🟢 3. Cliente Estável
        Foco: Segurança e confiança.
        Comportamento: Calmo, amigável, paciente, avesso a riscos.
        O que ele valoriza: Segurança, apoio, continuidade.
        Como atender: Mostre que ele será bem acompanhado. Seja gentil, escute bastante e evite pressão.

        Exemplo de abordagem:
        “Vamos acompanhar você de perto nessa transição, e sempre terá nosso suporte.”

        🔵 4. Cliente Conforme
        Foco: Informação e lógica.
        Comportamento: Racional, detalhista, questionador, exigente.
        O que ele valoriza: Precisão, dados, controle.
        Como atender: Traga números, comparativos, provas. Esteja preparado para perguntas técnicas.

        Exemplo de abordagem:
        “Veja esse relatório com os dados de performance dos últimos 3 meses.”

        7 - TEMPERATURA

        PROMPT – TREINAMENTO DE AGENTE DE IA PARA CLASSIFICAR A TEMPERATURA DE LEADS (CASH BARBER)

        Você é um agente de inteligência responsável por analisar interações comerciais com leads interessados no produto Cash Barber — um sistema de agendamento e gestão desenvolvido exclusivamente para barbearias que operam no modelo de assinatura.

        Sua tarefa é identificar a temperatura do lead (Frio, Morno, Quente ou Cliente Pronto) com base em falas, comportamentos e no nível de consciência comercial do prospect.

        ⸻

        📘 SOBRE O PRODUTO CASH BARBER

        O Cash Barber é a única solução do mercado feita 100% para barbearias por assinatura. Ele oferece:
        •	Precificação inteligente de planos recorrentes
        •	Controle de frequência dos assinantes
        •	Indicadores de performance por barbeiro
        •	Integração entre agendamento e cobrança
        •	Aplicativo personalizado da barbearia
        •	Consultoria estratégica e eventos presenciais de treinamento

        Big Idea: “Pare de achar. Comece a decidir.”

        ⸻

        🧠 METODOLOGIAS USADAS

        NEPQ – Neuro Emotional Persuasion Questioning
        Utilizamos NEPQ para identificar o quanto o lead sente a dor, deseja a mudança e percebe urgência. Fazemos isso através de perguntas que investigam o estado atual, o estado desejado e o impacto de não mudar.

        Níveis de Consciência – Eugene Schwartz
        Schwartz definiu os 5 estágios de consciência de um comprador:
        1.	Inconsciente
        2.	Consciente do problema
        3.	Consciente da solução
        4.	Consciente do produto
        5.	Totalmente consciente (pronto para comprar)

        Você irá cruzar o comportamento do lead com esse modelo de consciência.

        ⸻

        🔥 DEFINIÇÃO DAS TEMPERATURAS

        1. Lead FRIO
        * Nível de consciência: Inconsciente ou só consciente do problema
        * Comportamento: Minimiza problemas, acredita que o sistema atual é suficiente, respostas vagas
        * Desejo oculto: Ter uma barbearia que funcione sem saber o que está travando

        Exemplos:
        “A gente já usa um sistema e tá tranquilo.”
        “Assinatura é legal, mas ainda não aplicamos de verdade.”

        ⸻

        2. Lead MORNO
        * Nível de consciência: Consciente da solução
        * Comportamento: Reconhece limitações, está em busca de alternativas, mas indeciso ou sem critério
        * Desejo oculto: Tomar uma decisão com segurança

        Exemplos:
        “Já testei alguns sistemas, mas ainda não encontrei um ideal.”
        “Tô vendo umas opções mais voltadas pra assinatura.”

        ⸻

        3. Lead QUENTE
        * Nível de consciência: Consciente do produto (não precisa ser o Cash Barber ainda)
        * Comportamento: Tem urgência, frustração com o atual, busca solução definitiva com critério
        * Desejo oculto: Resolver com quem realmente sabe entregar resultado

        Exemplos:
        “Já usei dois sistemas e nenhum deu conta da recorrência.”
        “Quero resolver isso ainda esse mês.”

        ⸻

        4. PRONTO PRA COMPRAR (Fora da régua comercial ativa)
        * Nível de consciência: Totalmente consciente
        * Comportamento: Já conhece o Cash Barber, foi indicado ou está voltando, confia e quer ativar
        * Desejo: Começar com quem ele já confia

        Exemplos:
        “Me indicaram vocês, quero saber como começar.”
        “Vi os conteúdos, já decidi, só falta ativar.”

        ⸻

        ✅ SUA TAREFA (OBRIGATÓRIA)

        Dado um trecho de conversa ou ligação, você deve classificar a temperatura do lead e justificar sua decisão.

        Sua resposta deve conter obrigatoriamente:
        1.	Temperatura do lead: FRIO, MORNO, QUENTE ou PRONTO PRA COMPRAR
        2.	Motivo da classificação: Comportamento observado + nível de consciência + urgência percebida
        3.	Citações exatas do lead (mínimo 1, idealmente 2 ou 3), que justifiquem sua decisão
        4.	Minutagem da conversa para cada citação (ex: 01:42, 03:10 etc.)
        5.	(Opcional) Observações úteis para o Closer

        ⸻

        🧪 EXEMPLO DE RESPOSTA

        Temperatura: %QUENTE% (OBRIGATÓRIO ESTAR ENTRE %)
        Motivo: O lead demonstrou frustração com o sistema atual, testou outras soluções e quer resolver com urgência. Está no estágio consciente do produto.
        Citações:
        [01:45] “Já testei dois sistemas, mas nenhum deu conta da recorrência.”
        [03:10] “Tô com 200 assinantes, mas o sistema atual me trava, quero trocar ainda esse mês.”
        Observação: Ideal conduzir diagnóstico visual para reforçar segurança e fechar.""")

        # print("⏳ Enviando para o Gemini para transcrição...")
        # response = llm.invoke([message])
        print("⏳ 2/3: Enviando resumos e prompt estruturado para análise final (JSON)...")
        messages = [
                system_msg,
                HumanMessage(f"""
            Segue o áudio na íntegra para análise e extração de trechos (use-o como sua fonte primária, ignorando o resumo se houver divergência):
            
            # TRANSCRIÇÃO COMPLETA PARA ANÁLISE:
            {full_transcript}
            
            Por favor, realize as análises solicitadas e devolva as informações EXATAMENTE no formato JSON Schema fornecido. **OBS IMPORTANTE: essas informações serão inseridas no Notion, preciso que o conteúdo dos blocos não exceda 2000 letras, e inclua qubras de linhas entre os diálogos para melhorar a leitura***.
            """)
            ]
        # response_analise = llm.invoke(messages)
        # 6. Imprime a transcrição
        # print("\n--- Transcrição do Áudio ---")
        # print(f"Transcrição: {response.content}, Análise: {response_analise.content}")

        mensagem_schema={
        "type": "object",
        "properties": {
            "1. INVESTIGAÇÃO": {
            "type": "object",
            "description": "Análise da etapa de Investigação (Clareza da Dor e Aprofundamento do Problema).",
            "properties": {
                "nota": {
                "type": "number",
                "description": "Nota objetiva de 1 a 5."
                },
                "minutagem": {
                "type": "string",
                "description": "Minutagem relevante para esta seção (ex: 01:20)."
                },
                "trecho_problema": {
                "type": "string",
                "description": "Trecho da fala revelando o problema (literal com no mínimo 30 palavras)."
                },
                "lista_de_problemas": {
                "type": "array",
                "items": {
                    "type": "string"
                },
                "description": "Lista de problemas ou desafios identificados."
                },
                "trecho_desdobramento_problema": {
                "type": "string",
                "description": "Trecho da fala revelando os desdobramentos do problema identificado (literal com no mínimo 30 palavras)."
                },
                "aprofundamento_problemas_sdr": {
                "type": "string",
                "description": "Qual o aprofundamento dos problemas segundo a provocação do SDR."
                },
                "feedback_direto": {
                "type": "string",
                "description": "Feedback brutalmente direto sobre a qualidade analisada."
                },
                "sugestao_melhoria": {
                "type": "string",
                "description": "Sugestão prática de melhoria (se nota < 5)."
                }
            },
            "required": [
                "nota",
                "minutagem",
                "trecho_problema",
                "lista_de_problemas",
                "trecho_desdobramento_problema",
                "aprofundamento_problemas_sdr",
                "feedback_direto",
                "sugestao_melhoria"
            ]
            },
            "2. DESCOBERTA": {
            "type": "object",
            "description": "Análise da etapa de Descoberta do Sonho (Gatilho do Gap).",
            "properties": {
                "nota": {
                "type": "number",
                "description": "Nota objetiva de 1 a 5."
                },
                "minutagem": {
                "type": "string",
                "description": "Minutagem relevante para esta seção (ex: 03:45)."
                },
                "trecho_sonho": {
                "type": "string",
                "description": "Trecho da fala revelando o sonho (literal com no mínimo 30 palavras)."
                },
                "lista_dos_sonhos": {
                "type": "array",
                "items": {
                    "type": "string"
                },
                "description": "Lista dos sonhos ou conquistas identificados."
                },
                "trecho_desdobramento_sonho": {
                "type": "string",
                "description": "Trecho da fala revelando os desdobramentos do sonho identificados (literal com no mínimo 30 palavras)."
                },
                "aprofundamento_conquistas": {
                "type": "string",
                "description": "Qual o aprofundamento das conquistas que o lead terá resolvendo seus problemas."
                },
                "feedback_direto": {
                "type": "string",
                "description": "Feedback brutalmente direto sobre a qualidade analisada."
                },
                "sugestao_melhoria": {
                "type": "string",
                "description": "Sugestão prática de melhoria (se nota < 5)."
                }
            },
            "required": [
                "nota",
                "minutagem",
                "trecho_sonho",
                "lista_dos_sonhos",
                "trecho_desdobramento_sonho",
                "aprofundamento_conquistas",
                "feedback_direto",
                "sugestao_melhoria"
            ]
            },
            "3. DESPERTE O INTERESSE": {
            "type": "object",
            "description": "Análise da etapa de Despertar o Interesse (Solução para a Dor Real).",
            "properties": {
                "nota": {
                "type": "number",
                "description": "Nota objetiva de 1 a 5."
                },
                "minutagem": {
                "type": "string",
                "description": "Minutagem relevante para esta seção (ex: 05:15)."
                },
                "trecho_problema_citado_sdr": {
                "type": "string",
                "description": "Trecho da fala que sita o problema real do lead indagado pelo SDR (literal com no mínimo 30 palavras)."
                },
                "trecho_explicacao_entregavel": {
                "type": "string",
                "description": "Trecho da fala revelando a explicação do SDR sobre um entregável do produto ou estratégico (literal com no mínimo 30 palavras)."
                },
                "trecho_desdobramento_entregavel": {
                "type": "string",
                "description": "Trecho da fala revelando os desdobramentos do entregável ou estratégia (literal com no mínimo 30 palavras)."
                },
                "feedback_direto": {
                "type": "string",
                "description": "Feedback brutalmente direto sobre a qualidade analisada."
                },
                "sugestao_melhoria": {
                "type": "string",
                "description": "Sugestão prática de melhoria (se nota < 5)."
                }
            },
            "required": [
                "nota",
                "minutagem",
                "trecho_problema_citado_sdr",
                "trecho_explicacao_entregavel",
                "trecho_desdobramento_entregavel",
                "feedback_direto",
                "sugestao_melhoria"
            ]
            },
            "4. PROMOVEU A ESCASSEZ": {
            "type": "object",
            "description": "Análise da etapa de Promoção da Escassez na Agenda.",
            "properties": {
                "nota": {
                "type": "number",
                "description": "Nota objetiva de 1 a 5."
                },
                "minutagem": {
                "type": "string",
                "description": "Minutagem relevante para esta seção (ex: 07:00)."
                },
                "trecho_oferta_escassez": {
                "type": "string",
                "description": "Trecho da fala do SDR oferecendo a reunião com escassez (literal com no mínimo 30 palavras)."
                },
                "feedback_direto": {
                "type": "string",
                "description": "Feedback brutalmente direto sobre a qualidade analisada."
                },
                "sugestao_melhoria": {
                "type": "string",
                "description": "Sugestão prática de melhoria (se nota < 5)."
                }
            },
            "required": [
                "nota",
                "minutagem",
                "trecho_oferta_escassez",
                "feedback_direto",
                "sugestao_melhoria"
            ]
            },
            "5. PERFIL MKT (CAMPO NO PIPEDRIVE)": {
            "type": "object",
            "description": "Análise de qualificação do Lead para o Pipedrive.",
            "properties": {
                "conhece_produto_ou_lincohn": {
                "type": "string",
                "enum": [
                    "Sim",
                    "Não",
                    "Parcialmente"
                ]
                },
                "observacao_conhecimento": {
                "type": "string"
                },
                "faturamento_mensal_estimado": {
                "type": "string",
                "description": "Valor ou 'não identificado'."
                },
                "tamanho_da_equipe": {
                "type": "string",
                "description": "Número de barbeiros ou 'não citado'."
                },
                "principal_queixa_dificuldade": {
                "type": "array",
                "items": {
                    "type": "string"
                }
                },
                "gerou_agendamento": {
                "type": "string",
                "enum": [
                    "Sim",
                    "Não"
                ]
                },
                "observacao_agendamento": {
                "type": "string"
                },
                "motivo_desqualificacao": {
                "type": "string",
                "description": "Sim/Não + motivo claro em poucas palavras."
                }
            },
            "required": [
                "conhece_produto_ou_lincohn",
                "faturamento_mensal_estimado",
                "tamanho_da_equipe",
                "principal_queixa_dificuldade",
                "gerou_agendamento",
                "motivo_desqualificacao"
            ]
            },
            "6. PERFIL COMPORTAMENTAL": {
            "type": "object",
            "description": "Análise do Perfil Comportamental (DISC).",
            "properties": {
                "padrao_comportamental": {
                "type": "string",
                "enum": [
                    "🔴DOMINANTE",
                    "🟡INFLUENTE",
                    "🟢ESTÁVEL",
                    "🔵CONFORME",
                    "MISTO"
                ]
                },
                "explicacao_motivos": {
                "type": "string"
                },
                "erros_acertos_atendente": {
                "type": "string"
                },
                "orientacoes_praticas_closer": {
                "type": "string"
                },
                "trechos_utilizados": {
                "type": "array",
                "items": {
                    "type": "string"
                },
                "description": "Trechos chaves com minutagem utilizados para o julgamento."
                }
            },
            "required": [
                "padrao_comportamental",
                "explicacao_motivos",
                "erros_acertos_atendente",
                "orientacoes_praticas_closer",
                "trechos_utilizados"
            ]
            },
            "7. TEMPERATURA": {
            "type": "object",
            "description": "Análise da Temperatura do Lead.",
            "properties": {
                "temperatura_do_lead": {
                "type": "string",
                "pattern": "^%(FRIO|MORNO|QUENTE|PRONTO PRA COMPRAR)%$",
                "description": "Temperatura do lead (FRIO, MORNO, QUENTE ou PRONTO PRA COMPRAR), OBRIGATÓRIO estar entre %."
                },
                "motivo_da_classificacao": {
                "type": "string",
                "description": "Comportamento observado + nível de consciência + urgência percebida."
                },
                "citacoes": {
                "type": "array",
                "items": {
                    "type": "string"
                },
                "description": "Citações exatas do lead (mínimo 1) que justifiquem a decisão."
                },
                "observacao_closer": {
                "type": "string",
                "description": "(Opcional) Observações úteis para o Closer."
                }
            },
            "required": [
                "temperatura_do_lead",
                "motivo_da_classificacao",
                "citacoes"
            ]
            },
            "TRANSCRIÇÃO_COMPLETA_PARTE_1": {
            "type": "string",
            "description": "Primeira parte da transcrição completa da conversa."
            },
            "TRANSCRIÇÃO_COMPLETA_PARTE_2": {
            "type": "string",
            "description": "Segunda parte da transcrição completa da conversa."
            },
            "TRANSCRIÇÃO_COMPLETA_PARTE_3": {
            "type": "string",
            "description": "Terceira parte da transcrição completa da conversa."
            },
            "TRANSCRIÇÃO_COMPLETA_PARTE_4": {
            "type": "string",
            "description": "Terceira parte da transcrição completa da conversa."
            },
            "TRANSCRIÇÃO_COMPLETA_PARTE_5": {
            "type": "string",
            "description": "Terceira parte da transcrição completa da conversa."
            },
            "TRANSCRIÇÃO_COMPLETA_PARTE_6": {
            "type": "string",
            "description": "Terceira parte da transcrição completa da conversa."
            },
            "TRANSCRIÇÃO_COMPLETA_PARTE_7": {
            "type": "string",
            "description": "Terceira parte da transcrição completa da conversa."
            },
            "TRANSCRIÇÃO_COMPLETA_PARTE_8": {
            "type": "string",
            "description": "Terceira parte da transcrição completa da conversa."
            },
            "TRANSCRIÇÃO_COMPLETA_PARTE_9": {
            "type": "string",
            "description": "Terceira parte da transcrição completa da conversa."
            },
            "TRANSCRIÇÃO_COMPLETA_PARTE_10": {
            "type": "string",
            "description": "Terceira parte da transcrição completa da conversa."
            },
            "TRANSCRIÇÃO_COMPLETA_PARTE_11": {
            "type": "string",
            "description": "Terceira parte da transcrição completa da conversa."
            },
            "TRANSCRIÇÃO_COMPLETA_PARTE_12": {
            "type": "string",
            "description": "Terceira parte da transcrição completa da conversa."
            },
            "TRANSCRIÇÃO_COMPLETA_PARTE_13": {
            "type": "string",
            "description": "Terceira parte da transcrição completa da conversa."
            },
            "TRANSCRIÇÃO_COMPLETA_PARTE_14": {
            "type": "string",
            "description": "Terceira parte da transcrição completa da conversa."
            },
            "TRANSCRIÇÃO_COMPLETA_PARTE_15": {
            "type": "string",
            "description": "Terceira parte da transcrição completa da conversa."
            }           
        },
        "required": [
            "1. INVESTIGAÇÃO",
            "2. DESCOBERTA",
            "3. DESPERTE O INTERESSE",
            "4. PROMOVEU A ESCASSEZ",
            "5. PERFIL MKT (CAMPO NO PIPEDRIVE)",
            "6. PERFIL COMPORTAMENTAL",
            "7. TEMPERATURA",
            "TRANSCRIÇÃO_COMPLETA_PARTE_1",
            "TRANSCRIÇÃO_COMPLETA_PARTE_2",
            "TRANSCRIÇÃO_COMPLETA_PARTE_3",
            "TRANSCRIÇÃO_COMPLETA_PARTE_4",
            "TRANSCRIÇÃO_COMPLETA_PARTE_5",
            "TRANSCRIÇÃO_COMPLETA_PARTE_6",
            "TRANSCRIÇÃO_COMPLETA_PARTE_7",
            "TRANSCRIÇÃO_COMPLETA_PARTE_8",
            "TRANSCRIÇÃO_COMPLETA_PARTE_9",
            "TRANSCRIÇÃO_COMPLETA_PARTE_10",
            "TRANSCRIÇÃO_COMPLETA_PARTE_11",
            "TRANSCRIÇÃO_COMPLETA_PARTE_12",
            "TRANSCRIÇÃO_COMPLETA_PARTE_13",
            "TRANSCRIÇÃO_COMPLETA_PARTE_14",
            "TRANSCRIÇÃO_COMPLETA_PARTE_15"
        ]
        }

        agent = create_agent(
        llm,
        tools=[],
        response_format=ToolStrategy(mensagem_schema)
    )

        result = agent.invoke({
                    "messages": [
                        {"role": "user", "content": f"Realize a análise NEPQ completa e extraia todas as informações no JSON Schema fornecido. A transcrição completa é: {full_transcript}, Não esqueça de quebrar a transcrição em 15 partes conforme especificado no schema, não use Notas quebradas com ','. Sempre identificar os locutores e a minutágem nos diálogos, use quebra de linhas entre os diálogos para facilitar a leitura."}
                    ]
                })
        
        # Kestra.outputs({"response": result["structured_response"]})
   
        # --- VARIAVEIS DE PROPRIEDADES PRINCIPAIS ---
        cliente = os.environ['cliente'] 
        SDR=os.environ['SDR']
        Data_Make=dt.datetime.now().date().strftime('%Y-%m-%d') 
        id_pipedrive=os.environ['id_pipedrive']
        Link_da_Ligação= url
        Link_PIPEDRIVE=f"https://podiumeducacai.pipedrive.com/deal/{id_pipedrive}"
        Faturamento=os.environ['Faturamento']
        Campanha=os.environ['Campanha']

        # CORREÇÃO 1: Tratar temperatura e perfil comportamental como string de forma segura
        Tempertura_IA = str(result["structured_response"]["7. TEMPERATURA"]["temperatura_do_lead"]).replace("%", "").strip() 
        Disc_IA = str(result["structured_response"]["6. PERFIL COMPORTAMENTAL"]["padrao_comportamental"]).replace("🔵", "").replace("#", "").strip()

        # NO SEU CÓDIGO PYTHON (Onde as variáveis são preenchidas)

        def get_safe_str(data_dict, key, default="N/A"):
            """Extrai um valor do dicionário, tratando listas e sets como strings seguras."""
            value = data_dict.get(key, default)
            
            if isinstance(value, (list, set)):
                # Junta listas/sets em uma string com quebra de linha
                return "\n".join(map(str, value))
            
            # Adiciona um tratamento específico para o padrao_comportamental que usa emojis
            if key == "padrao_comportamental":
                return str(value).replace("🔵", "").replace("🔴", "").replace("🟡", "").replace("🟢", "").replace("#", "").strip()

            return str(value)

        # --- VARIAVEIS DE NOTAS (DEIXE COMO FLOAT) ---
        nota_investigacao = float(result["structured_response"]["1. INVESTIGAÇÃO"]["nota"]) 
        nota_descoberta = float(result["structured_response"]["2. DESCOBERTA"]["nota"]) 
        nota_interesse = float(result["structured_response"]["3. DESPERTE O INTERESSE"]["nota"]) 
        nota_escassez = float(result["structured_response"]["4. PROMOVEU A ESCASSEZ"]["nota"]) 

        # --- VARIAVEIS DE PERFIL MKT ---
        mkt_data = result["structured_response"]["5. PERFIL MKT (CAMPO NO PIPEDRIVE)"]

        conhece_produto_ou_lincohn = get_safe_str(mkt_data, "observacao_conhecimento", mkt_data.get("conhece_produto_ou_lincohn"))
        faturamento_mensal_estimado = get_safe_str(mkt_data, "faturamento_mensal_estimado")
        tamanho_da_equipe = get_safe_str(mkt_data, "tamanho_da_equipe")
        principal_queixa_dificuldade = get_safe_str(mkt_data, "principal_queixa_dificuldade")
        gerou_agendamento = get_safe_str(mkt_data, "observacao_agendamento", mkt_data.get("gerou_agendamento"))
        motivo_desqualificacao = get_safe_str(mkt_data, "motivo_desqualificacao")

        # --- VARIAVEIS DE PERFIL COMPORTAMENTAL ---
        perfil_data = result["structured_response"]["6. PERFIL COMPORTAMENTAL"]

        padrao_comportamental_valor = get_safe_str(perfil_data, "padrao_comportamental") # Usa a função que limpa emojis
        explicacao_motivos = get_safe_str(perfil_data, "explicacao_motivos")
        erros_acertos_atendente = get_safe_str(perfil_data, "erros_acertos_atendente")
        orientacoes_praticas_closer = get_safe_str(perfil_data, "orientacoes_praticas_closer")

        # --- VARIAVEIS DE INVESTIGAÇÃO ---
        inv_data = result["structured_response"]["1. INVESTIGAÇÃO"]

        minutagem_investigacao = get_safe_str(inv_data, "minutagem")
        trecho_problema = get_safe_str(inv_data, "trecho_problema")
        lista_de_problemas = get_safe_str(inv_data, "lista_de_problemas")
        trecho_desdobramento_problema = get_safe_str(inv_data, "trecho_desdobramento_problema")
        aprofundamento_problemas_sdr = get_safe_str(inv_data, "aprofundamento_problemas_sdr")
        feedback_direto_investigacao = get_safe_str(inv_data, "feedback_direto")
        sugestao_melhoria_investigacao = get_safe_str(inv_data, "sugestao_melhoria")
        # --- VARIAVEIS DE DESCOBERTA DO SONHO ---
        dsc_data = result["structured_response"]["2. DESCOBERTA"]

        minutagem_descoberta = str(dsc_data.get("minutagem", "N/A"))
        trecho_sonho = str(dsc_data.get("trecho_sonho", "N/A"))
        lista_dos_sonhos = get_safe_str(dsc_data, "lista_dos_sonhos")
        trecho_desdobramento_sonho = str(dsc_data.get("trecho_desdobramento_sonho", "N/A"))
        aprofundamento_conquistas = str(dsc_data.get("aprofundamento_conquistas", "N/A"))
        feedback_direto_descoberta = str(dsc_data.get("feedback_direto", "N/A"))
        sugestao_melhoria_descoberta = str(dsc_data.get("sugestao_melhoria", "N/A"))

        # --- VARIAVEIS DE DESPERTE O INTERESSE ---
        int_data = result["structured_response"]["3. DESPERTE O INTERESSE"]

        minutagem_interesse = str(int_data.get("minutagem", "N/A"))
        trecho_problema_citado_sdr = str(int_data.get("trecho_problema_citado_sdr", "N/A"))
        trecho_explicacao_entregavel = str(int_data.get("trecho_explicacao_entregavel", "N/A"))
        trecho_desdobramento_entregavel = str(int_data.get("trecho_desdobramento_entregavel", "N/A"))
        feedback_direto_interesse = str(int_data.get("feedback_direto", "N/A"))
        sugestao_melhoria_interesse = str(int_data.get("sugestao_melhoria", "N/A"))


        # --- VARIAVEIS DE ESCASSEZ ---
        esc_data = result["structured_response"]["4. PROMOVEU A ESCASSEZ"]

        minutagem_escassez = str(esc_data.get("minutagem", "N/A"))
        trecho_oferta_escassez = str(esc_data.get("trecho_oferta_escassez", "N/A"))
        feedback_direto_escassez = str(esc_data.get("feedback_direto", "N/A"))
        sugestao_melhoria_escassez = str(esc_data.get("sugestao_melhoria", "N/A"))

        # --- VARIAVEIS DE TRANSCRIÇÃO ---
        transcricao_parte_1 = str(result["structured_response"].get("TRANSCRIÇÃO_COMPLETA_PARTE_1", "N/A"))
        transcricao_parte_2 = str(result["structured_response"].get("TRANSCRIÇÃO_COMPLETA_PARTE_2", "N/A"))
        transcricao_parte_3 = str(result["structured_response"].get("TRANSCRIÇÃO_COMPLETA_PARTE_3", "N/A"))
        transcricao_parte_4 = str(result["structured_response"].get("TRANSCRIÇÃO_COMPLETA_PARTE_4", "N/A"))
        transcricao_parte_5 = str(result["structured_response"].get("TRANSCRIÇÃO_COMPLETA_PARTE_5", "N/A"))
        transcricao_parte_6 = str(result["structured_response"].get("TRANSCRIÇÃO_COMPLETA_PARTE_6", "N/A"))
        transcricao_parte_7 = str(result["structured_response"].get("TRANSCRIÇÃO_COMPLETA_PARTE_7", "N/A"))
        transcricao_parte_8 = str(result["structured_response"].get("TRANSCRIÇÃO_COMPLETA_PARTE_8", "N/A"))
        transcricao_parte_9 = str(result["structured_response"].get("TRANSCRIÇÃO_COMPLETA_PARTE_9", "N/A"))
        transcricao_parte_10 = str(result["structured_response"].get("TRANSCRIÇÃO_COMPLETA_PARTE_10", "N/A"))
        transcricao_parte_11 = str(result["structured_response"].get("TRANSCRIÇÃO_COMPLETA_PARTE_11", "N/A"))
        transcricao_parte_12 = str(result["structured_response"].get("TRANSCRIÇÃO_COMPLETA_PARTE_12", "N/A"))
        transcricao_parte_13 = str(result["structured_response"].get("TRANSCRIÇÃO_COMPLETA_PARTE_13", "N/A"))
        transcricao_parte_14 = str(result["structured_response"].get("TRANSCRIÇÃO_COMPLETA_PARTE_14", "N/A"))
        transcricao_parte_15 = str(result["structured_response"].get("TRANSCRIÇÃO_COMPLETA_PARTE_15", "N/A"))

        page_payload={
            "parent": {
                # O ID do database deve ser o data_source_id (2693bbf5-b1e1-8108-b2fb-000bde2e95b5) 
                # do JSON que você forneceu, mas page_id também funciona se for o ID da página mãe.
                # Vou manter 'page_id' pois é o que você estava usando para o parent:
                'data_source_id': '2693bbf5-b1e1-8108-b2fb-000bde2e95b5'
            },
            "properties": {
                "Cliente": {
                    "title": [
                        {
                            "text": {
                                "content": cliente.strip() # Usando f-string format aqui
                            }
                        }
                    ]
                },
                "Tempertura IA": {
                    "select": {
                        "name": Tempertura_IA.strip()
                    }
                },
                "SDR": {
                    "rich_text": [
                        {
                            "text": {
                                "content": SDR.strip()
                            }
                        }
                    ]
                },
                "Data Make": {
                    "date": {
                        "start": Data_Make.strip() 
                    }
                },
                "Faturamento": {
                    "select": {
                        "name": Faturamento.strip()
                    }
                },
                "Campanha": {
                    "select": {
                        "name": Campanha.strip()
                    }
                },
                "# Disc IA": {
                    "select": {
                        "name": Disc_IA.strip()
                    }
                },
                "Link da Ligação": {
                    "url": Link_da_Ligação.strip()
                },
                "Link PIPEDRIVE": {
                    # Certifique-se de que o id_pipedrive seja uma string válida
                    "url": f"https://podiumeducacai.pipedrive.com/deal/{id_pipedrive.strip()}"
                },
                
                # 🛑 CORRIGIDO: Nomes de propriedades EXATOS (retirados do JSON de resposta)
                # 🛑 CORRIGIDO: Remoção das chaves extras {} em torno da variável number
                "C1.APROFUNDAMENTO NA DOR": { 
                    "number": nota_investigacao 
                },
                "C2.DESCOBERTA DO SONHO": {
                    "number": nota_descoberta 
                },
                "C3.DESPERTE O INTERESSE DO CLIENTE ATENDENDO A DOR REAL": {
                    "number": nota_interesse 
                },
                "C4.PROMOVEU A ESCASSEZ NA AGENDA DO ESPECIALISTA": {
                    "number": nota_escassez 
                }
            },
                        "children": [
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": "📋 ANÁLISE DE LEAD — PERFIL DO AVATAR"
                                }
                            }
                        ]
                    }
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": f"1. Conhece o produto ou o Lincohn?\n{conhece_produto_ou_lincohn}\n\n2. Faturamento mensal estimado:\n{faturamento_mensal_estimado}\n\n3. Tamanho da equipe:\n{tamanho_da_equipe}\n\n4. Principal queixa/dificuldade:\n{principal_queixa_dificuldade}\n\n5. Gerou agendamento?\n{gerou_agendamento}\n\n6. Motivo para desqualificação (se houver):\n{motivo_desqualificacao}"
                                }
                            }
                        ]
                    }
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": f"➡️ Padrão Comportamental -> {padrao_comportamental_valor}\n\n➡️ Explicação dos Motivos: {explicacao_motivos}"
                                }
                            }
                        ]
                    }
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": f"➡️ Erros e Acertos que o atendente cometeu na ligação: {erros_acertos_atendente}"
                                }
                            }
                        ]
                    }
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": f"➡️ Orientações práticas e contextualizadas para o Consultor que fará a Reunião: {orientacoes_praticas_closer}"
                                }
                            }
                        ]
                    }
                },
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": "INVESTIGAÇÃO: CRIOU CLAREZA DA DOR E ENTENDEU A FUNDO O PROBLEMA."
                                }
                            }
                        ]
                    }
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": f"1. 🎯 Nota: {nota_investigacao}\n\n2. 🕒 Minutagem: {minutagem_investigacao}\n\n3. 💬 Trecho da fala revelando o problema: \n{trecho_problema}\n\n4. 💬 Qual a lista de problemas ou desafios identificados?\n{lista_de_problemas}"
                                }
                            }
                        ]
                    }
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": f"5. 💬 Trecho da fala revelando os desdobramento do problema identificado:\n{trecho_desdobramento_problema}\n\n6. 💬 Qual o aprofundamento dos problemas segundo a provocação do SDR:\n{aprofundamento_problemas_sdr}\n\n7. 📌 Feedback brutalmente direto sobre a qualidade analisada:\n{feedback_direto_investigacao}\n\n8. 🛠 Sugestão prática de melhoria (se nota < 5):\n{sugestao_melhoria_investigacao}\n"
                                }
                            }
                        ]
                    }
                },

                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                                "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": "DESCOBERTA DO SONHO (gatilho do ‘gap’ entre dor e desejo)"
                                }
                            }
                        ]
                    }
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": f"1. 🎯 Nota: {nota_descoberta}\n\n2. 🕒 Minutagem: {minutagem_descoberta}\n\n2. 💬 Trecho da fala revelando o sonho:\n{trecho_sonho}\n\n3. 💬 Qual a lista dos sonhos ou conquistas identificados?\n{lista_dos_sonhos}\n"
                                }
                            }
                        ]
                    }
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": f"4. 💬 Trecho da fala revelando os desdobramento do sonho identificados:\n{trecho_desdobramento_sonho}\n\n5. 💬 Qual o aprofundamento dos das conquistas que o lead terá resolvendo seus problemas e desafios citados dentro dos próximos 6 a 12 meses:\n{aprofundamento_conquistas}\n\n6. 📌 Feedback brutalmente direto sobre a qualidade\n{feedback_direto_descoberta}\n\n7. 🛠 Sugestão prática de melhoria (se nota < 5):\n{sugestao_melhoria_descoberta}\n"
                                }
                            }
                        ]
                    }
                },                
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": "DESPERTE O INTERESSE DO CLIENTE ATENDENDO A DOR REAL: (mostre que nossa solução serve na medida do seu problema.)"
                                }
                            }
                        ]
                    }
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": f"1. 🎯 Nota: {nota_interesse}\n\n2. 🕒 Minutagem: {minutagem_interesse}\n\n3. Trecho da fala que sita o problema real do lead indagado pelo SDR:\n{trecho_problema_citado_sdr}\n\n4. 💬 Trecho da fala revelando a explicação do SDR sobre um entregável do produto ou estratégico:\n{trecho_explicacao_entregavel}\n"
                                }
                            }
                        ]
                    }
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": f"5. 💬 Trecho da fala revelando os desdobramento do entregável ou estrategia: {trecho_desdobramento_entregavel}\n\n6. 📌 Feedback brutalmente direto sobre a qualidade analisada: {feedback_direto_interesse}\n\n7. 🛠 Sugestão prática de melhoria (se nota < 5): {sugestao_melhoria_interesse}\n"
                                }
                            }
                        ]
                    }
                },
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": "PROMOVEU A ESCASSEZ NA AGENDA DO ESPECIALISTA"
                                }
                            }
                        ]
                    }
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": f"1. 🎯 Nota: {nota_escassez}\n\n2. 🕒 Minutagem: {minutagem_escassez}\n\n3. 💬 Trecho da fala do SDR oferecendo a reunião com escassez e direto na dor do cliente:\n{trecho_oferta_escassez}\n"
                                }
                            }
                        ]
                    }
                },

                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": f"4. 📌 Feedback brutalmente direto sobre a qualidade analisada: {feedback_direto_escassez}\n\n5. 🛠 Sugestão prática de melhoria (se nota < 5) {sugestao_melhoria_escassez}\n"
                                }
                            }
                        ]
                    }
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                                "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": "🔥🧊🔥🧊🔥🧊🔥🧊"
                                }
                            }
                        ]
                    }
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": f"{transcricao_parte_1}"
                                }
                            }
                        ]
                    }
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": f"{transcricao_parte_2}"
                                }
                            }
                        ]
                    }
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": f"{transcricao_parte_3}"
                                }
                            }
                        ]
                    }
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": f"{transcricao_parte_4}"
                                }
                            }
                        ]
                    }
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": f"{transcricao_parte_5}"
                                }
                            }
                        ]
                    }
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": f"{transcricao_parte_6}"
                                }
                            }
                        ]
                    }
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": f"{transcricao_parte_7}"
                                }
                            }
                        ]
                    }
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": f"{transcricao_parte_8}"
                                }
                            }
                        ]
                    }
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": f"{transcricao_parte_9}"
                                }
                            }
                        ]
                    }
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": f"{transcricao_parte_10}"
                                }
                            }
                        ]
                    }
                },
                                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": f"{transcricao_parte_11}"
                                }
                            }
                        ]
                    }
                },
                                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": f"{transcricao_parte_12}"
                                }
                            }
                        ]
                    }
                },
                                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": f"{transcricao_parte_13}"
                                }
                            }
                        ]
                    }
                },
                                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": f"{transcricao_parte_14}"
                                }
                            }
                        ]
                    }
                },
                                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": f"{transcricao_parte_15}"
                                }
                            }
                        ]
                    }
                }
            ]
        }

        api_notion.create_page(page_payload)
        Kestra.outputs({"response": result["structured_response"]})

        print("Enviado para o Notion")

        print("----------------------------\n")

    except OutputParserException as e:
        print(f"❌ Erro de Transcrição/LangChain: {e}")
    except Exception as e:
        print(f"❌ Ocorreu um erro ao invocar o modelo: {e}")

else:
    # Caso a requisição HTTP falhe
    print(f"❌ Erro ao baixar o áudio. Status Code: {r.status_code}")


