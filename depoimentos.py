from CLASSES.notion_class import NotiondriveAPI
import os
import json

notion_token = os.environ['NOTION_TOKEN']
api_notion = NotiondriveAPI(notion_token)

database_id="2853bbf5-b1e1-80d8-8485-eec426ca8de6"
data_source_id='2853bbf5-b1e1-8024-bd2e-000b87023880'

depoimentos=api_notion.database_Retrieve(database_id)


page=api_notion.page_props(page_id="28c3bbf5b1e180c58badd5abd6f2780c")

page.json()

depoimentos.json()


datasource=api_notion.database_props(data_source_id)
datasource.json()

list_dep=api_notion.list_datasource(data_source_id)

list_dep.json()

payload_faturamento_apenas = {
  "filter": {
    "property": 'Link',
    "url": {
        "is_not_empty": True
    }
  }
}

# 1. Chamada à API
response = api_notion.query_datasource(data_source_id, payload_faturamento_apenas)
results = response.json().get("results", [])

depoimentos_finais = []
for page in results:
    # try:
    cidade = page['properties'].get('Cidade').get('place').get('name') if page['properties'].get('Cidade').get('place') is not None else None,

    depoimentos_finais.append(
        {
          "NOME": page['properties'].get('Nome').get('title')[0].get('plain_text') if page['properties'].get('Nome').get('title')[0] else None,
          "CIDADE": page['properties'].get('Cidade').get('place').get('name') if page['properties'].get('Cidade').get('place') else None,
          "FATURAMENTO_INICIAL":page['properties'].get('Fat. Inicial').get('number') if page['properties'].get('Fat. Atual') else None,
          "FATURAMENTO_ATUAL":(page['properties'].get('Fat. Atual').get('number')) if (page['properties'].get('Fat. Atual').get('number')) else "",
          "ASSINANTES":(page['properties'].get('Assinantes').get('number')) if (page['properties'].get('Fat. Atual').get('number')) else "",
          "TEXTO":str([item.get('text').get('content') for item in page['properties'].get('Texto').get('rich_text')]) if str([item.get('text').get('content') for item in page['properties'].get('Texto').get('rich_text')]) else "",
          "Link":(page['properties'].get('Link').get('url')) if (page['properties'].get('Link').get('url')) else ""
      })
        
    # except:
    #   continue

datasource.json()


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
dotenv.load_dotenv("./.env")
api_key = os.getenv('GOOGLE_API')
apikey_pipe = os.getenv("API_KEY")
notion_token = os.getenv("NOTION_TOKEN")
# apikey_pipe = os.environ["apikey_pipe"]
# notion_token = os.environ['NOTION_TOKEN']
api_notion = NotiondriveAPI(notion_token)
api_pipedrive = PipedriveAPI(apikey_pipe)
# os.environ["GOOGLE_API_KEY"] = api_key

# Inicialização do Modelo
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-pro",
    temperature=0,
    max_tokens=None, # Deixa o LLM decidir o melhor
    timeout=None,    # Deixa o LLM decidir o melhor
    max_retries=2,
)

# Inicialização do Modelo
llm_basic = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
    max_tokens=None, # Deixa o LLM decidir o melhor
    timeout=None,    # Deixa o LLM decidir o melhor
    max_retries=2,
)

url = "https://fs6.api4com.com/recordings/podium.api4com.com/1039@podium.api4com.com/d5901b49-2655-4cf0-86f1-118345b08c5a.mp3"

r = requests.get(url)

if r.status_code == 200:
    
  audio_bytes = r.content 
  audio_mime_type = "audio/mpeg" 
  encoded_audio = base64.b64encode(audio_bytes).decode("utf-8")
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

print("⏳ 1/3: Enviando áudio para transcrição completa...")
response_transcription = llm_basic.invoke([transcription_message])
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
    
    response_summary = llm_basic.invoke(summary_prompt)
    summarized_chunks.append(response_summary.content)

# 3. ANÁLISE FINAL (CONCATENAÇÃO DOS RESUMOS + PROMPT ESTRUTURADO)

# O modelo fará a análise final em cima deste texto reduzido
concatenated_summary = "\n---\n".join(summarized_chunks)