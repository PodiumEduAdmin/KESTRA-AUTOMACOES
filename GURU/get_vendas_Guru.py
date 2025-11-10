import requests
from io import StringIO
import json
import os
from datetime import datetime as dt
import uuid
import dotenv
import time
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
import base64
from typing import Optional, Dict, Any, List
from CLASSES.pipe_class import PipedriveAPI

dotenv.load_dotenv("../.env")

TOKEN_GURU = os.getenv("TOKEN_GURU")

# --- 3. FUNÇÃO DE REQUISIÇÃO GENÉRICA (Usada pelo 'digitalmanager.guru') ---
# MANTEMOS esta função aqui, pois ela é diferente da 'pipe_api'
def Get_Vendas_Guru(
    url: str,
    method: str = "GET",
    query_params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    data: Optional[Any] = None
) -> requests.Response:
    """
    Faz uma requisição HTTP usando a biblioteca 'requests', baseada na configuração
    de um nó HTTP Request do n8n.
    """

    # Configuração de Parâmetros de Consulta
    params_to_use = query_params if query_params is not None else {}

    # Configuração de Cabeçalhos
    headers_to_use = headers if headers is not None else {}
    # Se estiver enviando dados JSON, é bom definir o Content-Type
    if method in ["POST", "PUT", "PATCH"] and data and not headers_to_use.get("Content-Type"):
        headers_to_use["Content-Type"] = "application/json"

    # Serializa o corpo (body) se for um dicionário e o método não for GET/DELETE
    body_data = data
    if isinstance(data, dict) and method in ["POST", "PUT", "PATCH"]:
        body_data = json.dumps(data)
    
    # Variável para armazenar o objeto de resposta para uso no bloco except
    response = None 

    try:
        response = requests.request(
            method=method,
            url=url,
            params=params_to_use,
            headers=headers_to_use,
            data=body_data,
            timeout=30  # Define um timeout para evitar que a requisição trave
        )

        # Levanta um erro HTTP se a resposta não for 2xx
        response.raise_for_status()

        return response

    except requests.exceptions.HTTPError as errh:
        print(f"Erro HTTP: {errh}")
        if response is not None:
            # Tenta extrair o corpo da resposta para mais detalhes sobre o erro 422
            print(f"URL da Requisição: {response.url}")
            print(f"Status Code: {response.status_code}")
            try:
                # Tenta ler o corpo como JSON
                error_details = response.json()
                print(f"Detalhes do Erro (JSON): {json.dumps(error_details, indent=2)}")
            except requests.exceptions.JSONDecodeError:
                # Se não for JSON, imprime o texto bruto
                print(f"Detalhes do Erro (Texto Bruto): {response.text[:500]}...")
        
        # Levanta a exceção para interromper o fluxo
        raise
    except requests.exceptions.ConnectionError as errc:
        print(f"Erro de Conexão: {errc}")
        raise
    except requests.exceptions.Timeout as errt:
        print(f"Timeout de Requisição: {errt}")
        raise
    except requests.exceptions.RequestException as err:
        print(f"Ocorreu um erro inesperado: {err}")
        raise
# --- EXECUTAR TESTE ---
if __name__ == '__main__':
    # Este bloco simula a criação de um Negócio após a Pessoa ter sido criada
        
    # --- Bloco de Teste do digitalmanager.guru (Mantido) ---
    API_URL = "https://digitalmanager.guru/api/v2/transactions"
    # parametros_de_consulta = {
    #     'ordered_at_ini': '2025-11-01',
    #     'ordered_at_end': '2025-11-10',
    #     'status[]': 'approved',
    #     'cursor':
    # }
    cabecalhos_personalizados_guru = {
        'Authorization': f'Bearer {TOKEN_GURU}',
        'Accept': 'application/json' 
    }
    print(f"Fazendo requisição GET para: {API_URL}")

    next_cursor = 1
    pagina_atual = 1

    todos_os_dados: List[Dict[str, Any]] = []

    while next_cursor:
        parametros_de_consulta = {
        'ordered_at_ini': '2025-11-01',
        'ordered_at_end': '2025-11-10',
        'status[]': 'approved',
        'cursor' : f'{next_cursor}'
    }
        try:
            response_get = Get_Vendas_Guru(
                url=API_URL,
                method="GET",
                query_params=parametros_de_consulta,
                headers=cabecalhos_personalizados_guru
            )
            print("\n--- Resposta da Requisição GET (Guru) ---")
            print(f"Status Code: {response_get.status_code}")
            next_cursor=response_get.json().get('next_cursor')
    # Adiciona os dados da página à lista principal
            dados_da_pagina = response_get.json().get('data', [])
            if dados_da_pagina:
                todos_os_dados.extend(dados_da_pagina)
                print(f"Página {pagina_atual} coletada. Total de registros: {len(todos_os_dados)}")
            else:
                print(f"Página {pagina_atual} retornou sem dados.")
            pagina_atual += 1
        except Exception as e:
            print(f"\nFalha na execução do teste 'digitalmanager.guru': {e}")

    # 3. CRIAÇÃO DO DATAFRAME
    if todos_os_dados:
        df = pd.DataFrame(todos_os_dados)
        print("\n--- DataFrame Criado com Sucesso! ---")
        print(f"Número final de linhas: {len(df)}")
        print("Primeiras 5 linhas do DataFrame:")
        print(df.head())
    else:
        print("\nNenhum dado foi coletado para criar o DataFrame.")

    import numpy as np
    # 1. Função Lambda para extrair o valor 'cycle'
    # 1. Função Lambda para extrair o valor 'cycle'
    df['cycle_extraido'] = df['invoice'].apply(
        # Verifica se 'x' é um dicionário; se for, tenta pegar 'cycle'. Se não for, retorna NaN.
        lambda x: x.get('cycle') if isinstance(x, dict) else np.nan
    )

    cilo1=df.query("cycle_extraido==1")

    cilo1['oferta'] = cilo1['product'].apply(
        # Verifica se 'x' é um dicionário; se for, tenta pegar 'cycle'. Se não for, retorna NaN.
        lambda x: x['offer'].get('name') if isinstance(x, dict) else np.nan
    )

    cilo1['oferta']=cilo1['oferta'].str.upper()
    cilo1=cilo1.query("~oferta.str.contains('LETÍCIA')")
    cilo1=cilo1.query("~oferta.str.contains('RENOVAÇÃO')")
    cilo1=cilo1.query("~oferta.str.contains('MIGRAÇÃO')")
    cilo1=cilo1.query("~oferta.str.contains('DOWNGRADE')")
    cilo1=cilo1.query("~oferta.str.contains('REGULARIZAÇÃO')")
    cilo1=cilo1.query("oferta.str.contains('CASH') or oferta.str.contains('SHELBY') or oferta.str.contains('PASS')")

    cilo1['contact_email'] = cilo1['contact'].apply(
        # Verifica se 'x' é um dicionário; se for, tenta pegar 'cycle'. Se não for, retorna NaN.
        lambda x: x.get('email') if isinstance(x, dict) else np.nan
    )

    cilo1['contact_name'] = cilo1['contact'].apply(
        # Verifica se 'x' é um dicionário; se for, tenta pegar 'cycle'. Se não for, retorna NaN.
        lambda x: x.get('name') if isinstance(x, dict) else np.nan
    )

    cilo1['contact_phone_number'] = cilo1['contact'].apply(
        # Verifica se 'x' é um dicionário; se for, tenta pegar 'cycle'. Se não for, retorna NaN.
        lambda x: x.get('phone_number') if isinstance(x, dict) else np.nan
    )

    cilo1['contact_doc'] = cilo1['contact'].apply(
        # Verifica se 'x' é um dicionário; se for, tenta pegar 'cycle'. Se não for, retorna NaN.
        lambda x: x.get('doc') if isinstance(x, dict) else np.nan
    )
    API_KEY = os.getenv('API_KEY')
    api = PipedriveAPI(api_token=API_KEY)
    
    for i,tab in cilo1.iterrows():
        person=api.search_persons(tab['contact_email'],"email")
        id=person.json().get('data').get('items')[0].get('item').get('id')

        deals=api.get_deal(id)
        # data = deals.json().get('data')[0].get('add_time')
        # data_obj = dt.strptime(data, '%Y-%m-%dT%H:%M:%SZ').date().strftime('%Y-%m-%d')

        for j,item in enumerate(deals.json().get('data')):
            cilo1.loc[i,f'ID_Pipedrive{j}'] = item.get('id')
            cilo1.loc[i,f'Title_Pipedrive{j}'] = item.get('title')
            cilo1.loc[i,f'Data_Pipedrive{j}'] =  dt.strptime(item.get('add_time'), '%Y-%m-%dT%H:%M:%SZ').date().strftime('%Y-%m-%d')

cilo1.columns
cilo1.to_excel(r"vendas_guru.xlsx",index=False)