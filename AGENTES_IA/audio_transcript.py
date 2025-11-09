import os
import dotenv
import base64
import requests
import re
from langchain.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.exceptions import OutputParserException # Importar para melhor tratamento de erros

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

url = "https://podium.3c.plus/api/v1/calls/690e2499e2568a660041dd85/recording"
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
            {"type": "text", "text": "Transcreva o áudio de maneira completa e fiel, informanto a minutágem e identificando os locutores com 🟢SDR e 🟣CLIENTE"},
            {
                "type": "media",
                "data": encoded_audio,
                "mime_type": audio_mime_type,
            },
        ]
    )

    # 5. Invoca o modelo para a transcrição
    try:
        print("⏳ Enviando para o Gemini para transcrição...")
        response = llm.invoke([message])
        
        # 6. Imprime a transcrição
        print("\n--- Transcrição do Áudio ---")
        print(f"{response.content}")
        print("----------------------------\n")

    except OutputParserException as e:
        print(f"❌ Erro de Transcrição/LangChain: {e}")
    except Exception as e:
        print(f"❌ Ocorreu um erro ao invocar o modelo: {e}")

else:
    # Caso a requisição HTTP falhe
    print(f"❌ Erro ao baixar o áudio. Status Code: {r.status_code}")