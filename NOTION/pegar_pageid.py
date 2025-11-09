import requests
import os
import dotenv

# --- Configuração de Variáveis ---
dotenv.load_dotenv("../.env")

notion_token = os.getenv("NOTION_TOKEN")
# O ID pode ser de uma página comum ou de um database, 
# mas o endpoint é para buscar as propriedades dessa página.
page_id = "26b3bbf5b1e18196b1ddc3bfb5b7cb19" 

# CORREÇÃO: Endpoint para BUSCAR PROPRIEDADES DE UMA PÁGINA (GET)
# Para buscar uma página, o endpoint é /pages/{id}
url = f"https://api.notion.com/v1/pages/{page_id}"

# 1. Defina os HEADERS (Obrigatórios)
headers = {
    "Authorization": f"Bearer {notion_token}",
    "Notion-Version": "2025-09-03", 
    # Content-Type é opcional para GET
}

# Não é necessário payload para requisições GET simples
# payload = {} 

# 2. Faça a requisição (Para buscar uma página, use GET)
print(f"Buscando propriedades da Página ID: {page_id}...")
try:
    # CORREÇÃO: Método GET é usado para buscar as propriedades de uma página
    response = requests.get(url, headers=headers)
    
    # 3. Verifique a resposta
    if response.status_code == 200:
        data = response.json()
        
        print("✅ Requisição bem-sucedida ao Notion!")
        
        # O resultado é um objeto, não um array. Vamos imprimir o título ou nome.
        # A forma de acessar o título depende do tipo de página.
        # Para páginas de database, o título está dentro de 'properties'.
        title_property = data.get('properties', {}).get('title', {})
        
        page_title = "Título Não Encontrado"
        if title_property.get('type') == 'title':
            # Tenta extrair o texto da propriedade 'title'
            page_title = title_property.get('title', [{}])[0].get('plain_text', page_title)

        print(f"Título da Página (ou Database): {page_title}")
        print(f"Tipo do Objeto: {data.get('object')}")


    else:
        # Se houver outro erro (401, 404, etc.)
        error_details = response.json()
        print(f"❌ Erro HTTP: Status {response.status_code}")
        print(f"Código do erro: {error_details.get('code')}")
        print(f"Mensagem: {error_details.get('message')}")

except requests.exceptions.RequestException as e:
    print(f"❌ Ocorreu um erro na conexão: {e}")
except Exception as e:
    print(f"❌ Ocorreu um erro inesperado: {e}")