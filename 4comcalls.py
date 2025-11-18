from CLASSES.four_com_class import FourComAPI
import requests
import json
import datetime as dt
from typing import Optional, Dict, Any, List
import pandas as pd

data_hora_atual=dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

api_com = FourComAPI("npHImQxqpv8n6zleKryZ21BzJYCy4izyi4HQhpAg1f1UgTWRpxgIwbEPA8pEdVVV")

# O objeto que será codificado
filter_object = {
  "where": {
    "ended_at": {
      "gte": "2025-11-17T00:00:00Z",
      "lt": f"{data_hora_atual}"
    }
  }
}

filter_string = json.dumps(filter_object)


query = {
    "page": 1,
    "filter": json.dumps(filter_object)
}
chamadas = api_com.list_calls(query)
totalPageCount = chamadas.json().get('meta').get('totalPageCount')


len(chamadas.json().get('data'))

dados=chamadas.json()

calls = []
p=1
for p in range(totalPageCount+1):
  
  p_=1
  calls.append(api_com.list_calls(query))

todos_os_dados: List[Dict[str, Any]] = []
current_page = 1 # Sempre começa na página 1
total_pages = None
while current_page is not None:
    print(f"\n--- ⏳ Buscando Página: {current_page} ---")
    
    # Monta a query: usamos o valor de current_page. O valor deve ser um inteiro,
    # mas a string 'page' na URL deve ter seu valor.
    # Corrigi a sintaxe do query: 'page' deve ser a chave, e current_page o valor (inteiro).
    query = {
        "page": current_page, 
        "filter": json.dumps(filter_object)
    }

    try:
        # 1. Faz a requisição
        response_get = api_com.list_calls(query)
        response_get.raise_for_status() # Lança exceção para status 4xx/5xx
        response_data = response_get.json()
        
        # 2. Extrai os dados e a meta
        meta = response_data.get('meta', {})
        dados_da_pagina = response_data.get('data', [])

        # 3. Processa os dados
        if dados_da_pagina:
            todos_os_dados.extend(dados_da_pagina)
            print(f"✅ Página {current_page} coletada. Total de registros: {len(todos_os_dados)}")
        else:
            print(f"Página {current_page} retornou sem dados.")
            
        # 4. Atualiza a condição de loop (Lógica de Paginação)
        # O valor para a próxima iteração é o nextPage retornado pela API.
        # Se nextPage não for retornado ou for None, o loop PARA.
        current_page = meta.get('nextPage') 
        total_pages = meta.get('totalPageCount')
        
        if current_page is not None:
             print(f"Próxima Página: {current_page}. Total de Páginas: {total_pages}")
        else:
             print("Fim da Paginação. 'nextPage' não foi retornado.")


    except requests.exceptions.RequestException as e:
        print(f"❌ Erro na Requisição da Página {current_page}: {e}")
        break # Sai do loop em caso de erro fatal

print(f"\n=====================================")
print(f"Finalizado. Total de {len(todos_os_dados)} registros coletados.")
print(f"=====================================")

# 3. CRIAÇÃO DO DATAFRAME
if todos_os_dados:
    df = pd.DataFrame(todos_os_dados)
    print("\n--- DataFrame Criado com Sucesso! ---")
    print(f"Número final de linhas: {len(df)}")
    print("Primeiras 5 linhas do DataFrame:")
    print(df.head())
else:
    print("\nNenhum dado foi coletado para criar o DataFrame.")
# 3. CRIAÇÃO DO 

len(df.query("duration>=300"))
filtro_nome = df['first_name'].str.contains('suportepodium', case=False, na=False)

df.query("@df['first_name'].str.contains('suportepodium', case=False, na=False)")

