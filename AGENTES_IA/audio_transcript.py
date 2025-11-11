import os
import dotenv
import base64
import requests
import re
from langchain.messages import HumanMessage,SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.exceptions import OutputParserException 
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
# Importar para melhor tratamento de erros
from kestra import Kestra

# dotenv.load_dotenv("../.env")
# api_key=os.getenv('GOOGLE_API')

# # Configuração da API Key (boa prática)
# os.environ["GOOGLE_API_KEY"] = api_key

# Inicialização do Modelo
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
)

# url = os.environ['URL']
url = os.environ['URL']

r = requests.get(url)

# 2. Verifique o status da resposta
if r.status_code == 200:
    
    # O conteúdo do áudio (em bytes) está aqui. Não salvamos em disco!
    audio_bytes = r.content 
    
    # O Content-Type do cabeçalho era 'audio/mpeg' (MP3)
    audio_mime_type = "audio/mpeg" 

    print("✅ Áudio baixado para a memória (não salvo em disco). Iniciando codificação...")
    
    # 3. Codifica os bytes diretamente da memória para Base64
    # Note que usamos 'audio_bytes' em vez de abrir um arquivo.
    encoded_audio = base64.b64encode(audio_bytes).decode("utf-8")
    
    # 4. Prepara a mensagem para o Gemini
    message = HumanMessage(
        content=[
            {"type": "text", "text": "Transcreva o áudio de maneira completa e fiel, informanto a minutágem e identificando os locutores com 🟢SDR e 🟣CLIENTE. Também aplique a análise conforme as regras do negócio"
            },
            {
                "type": "media",
                "data": encoded_audio,
                "mime_type": audio_mime_type,
            },
        ]
    )

    # 5. Invoca o modelo para a transcrição
    try:
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
        3.	💬 Trecho da fala revelando o problema (literal com no mínimo 30 palavras) - identificando o LEAD e o SDR + a Minutagem da fala.
        4.  Qual a lista de problemas ou desafios identificados?
        5.	💬 Trecho da fala revelando os desdobramento do problema identificado (literal com no mínimo 30 palavras) - identificando o LEAD e o SDR + a Minutagem da fala. ( caso não tenha uma pergunta de desdobramento sobre algum dos problemas identificados, fale que não houve desdobramento do especificamente do problema.
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
        3.	💬 Trecho da fala revelando o sonho (literal com no mínimo 30 palavras) - identificando o LEAD e o SDR + a Minutagem da fala. (se não tiver investigado isso, mencionar que não perguntou na ligação)
        4.  Qual a lista dos sonhos ou conquistas identificados? (se não tiver investigado isso, mencionar que não perguntou na ligação)
        5.	💬 Trecho da fala revelando os desdobramento do sonho identificados (literal com no mínimo 30 palavras) - identificando o LEAD e o SDR + a Minutagem da fala. (se não tiver investigado isso, mencionar que não perguntou na ligação)
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
        3. Trecho da fala que sita o problema real do lead indagado pelo SDR (literal com no mínimo 30 palavras) - identificando o LEAD e o SDR + a Minutagem da fala. (se não tiver investigado isso, mencionar que não perguntou na ligação)
        4.	💬 Trecho da fala revelando a explicação do SDR sobre um entregável do produto ou estratégico  (literal com no mínimo 30 palavras) - identificando o LEAD e o SDR + a Minutagem da fala. (se não tiver investigado isso, mencionar que não perguntou na ligação)
        5.	💬 Trecho da fala revelando os desdobramento do entregável ou estrategia (literal com no mínimo 30 palavras) - identificando o LEAD e o SDR + a Minutagem da fala. (se não tiver investigado isso, mencionar que não perguntou na ligação)
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
        3.	💬 Trecho da fala do SDR oferecendo a reunião com escassez e direto na dor do cliente (literal com no mínimo 30 palavras) - identificando o LEAD e o SDR + a Minutagem da fala. (se não tiver investigado isso, mencionar que não perguntou na ligação)
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

        print("⏳ Enviando para o Gemini para transcrição...")
        response = llm.invoke([message])
        messages = [
                system_msg,
                HumanMessage(f"Segue a transcição do Áudio do SDR, por favor realize as análises solicitdas e devolva as informações em formato json.As informações serão incluídas no Notion, preciso que análise que exederem 2000 letras sejam qubradas em partes, a transcrição do áudio deve ser quebrada em 10 partes. **TRANSCRIÇÃO**: {response.content}")
            ]
        response_analise = llm.invoke(messages)
        # 6. Imprime a transcrição
        print("\n--- Transcrição do Áudio ---")
        print(f"Transcrição: {response.content}, Análise: {response_analise.content}")

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
            "TRANSCRIÇÃO_COMPLETA_PARTE_10"
        ]
        }

        agent = create_agent(
        llm,
        tools=[],
        response_format=ToolStrategy(mensagem_schema)
    )

        result = agent.invoke({

        "messages": [{"role": "user", 
                      "content": f"Extract info: Transcrição: {response.content}, Análise: {response_analise.content}"}]
    })
        
        Kestra.outputs({"response": result["structured_response"]})
        print("----------------------------\n")

    except OutputParserException as e:
        print(f"❌ Erro de Transcrição/LangChain: {e}")
    except Exception as e:
        print(f"❌ Ocorreu um erro ao invocar o modelo: {e}")

else:
    # Caso a requisição HTTP falhe
    print(f"❌ Erro ao baixar o áudio. Status Code: {r.status_code}")