import os
from langchain_google_vertexai import ChatVertexAI
import dotenv

dotenv.load_dotenv()
# Substitua pelos seus dados do Google Cloud
PROJECT_ID = "gen-lang-client-0238034750"
LOCATION = "us-central1"# Exemplo: us-central1, europe-west4, etc.

# 1. Inicialize o modelo de chat do Vertex AI
try:
    llm_vertex = ChatVertexAI(
        model="gemini-2.5-flash",
        project=PROJECT_ID,
        location=LOCATION,
        temperature=0.0,
        max_output_tokens=2048
    )

    print(f"✅ Modelo Gemini no Vertex AI ({LOCATION}) inicializado com sucesso.")

    # 2. Exemplo de uso
    response = llm_vertex.invoke("Explique o conceito de chunking em LLMs em uma frase.")

    print(f"\nResposta do Vertex AI: {response.content}")

except Exception as e:
    print(f"❌ Erro ao inicializar o Vertex AI: Certifique-se de que as credenciais (ADC) estão configuradas e as bibliotecas instaladas. Erro: {e}")