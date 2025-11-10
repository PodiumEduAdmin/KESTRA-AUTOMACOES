import pandas as pd
import requests
from io import StringIO
import json
import os
import datetime as dt
import uuid
import dotenv
import time
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
import base64
from typing import Optional, Dict, Any, List
from CLASSES.pipe_class import PipedriveAPI

dotenv.load_dotenv()
# --- 2. CONFIGURAÇÕES GOOGLE SHEETS ---

# Substitua pelo ID da sua planilha (está na URL)
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')

# Caminho para o seu arquivo JSON de credenciais
SERVICE_ACCOUNT_FILE = 'credentials.json'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

def ler_dados_planilha(range_name,plan_id):
    """Lê um intervalo da planilha e retorna um DataFrame do Pandas."""
    try:
        result = sheet.values().get(
            spreadsheetId=plan_id,
            range=range_name
        ).execute()

        values = result.get('values', [])
        
        if not values:
            return pd.DataFrame() # Retorna um DataFrame vazio se não houver dados
        
        # Converte para DataFrame: primeira linha como cabeçalho
        header = values[0]
        data = values[1:]
        df = pd.DataFrame(data, columns=header)
        return df

    except Exception as e:
        print(f"Erro ao ler o intervalo '{range_name}': {e}")
        return pd.DataFrame()
    
try:
    # Cria as credenciais usando o arquivo JSON da Conta de Serviço
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)

    # Constrói o serviço da API
    service = build('sheets', 'v4', credentials=creds)
    sheet = service.spreadsheets()
    print("Conexão com a Google Sheets API estabelecida com sucesso!")

except Exception as e:
    print(f"ERRO DE AUTENTICAÇÃO. Verifique o caminho do JSON e as permissões: {e}")
    exit() # Interrompe o script se a conexão falhar


def fazer_requisicao_n8n_style(
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


# --- 5. EXECUÇÃO PRINCIPAL (ORQUESTRADOR) ---
if __name__ == '__main__':
    
    print("-" * 40)
    print("Iniciando processo de sincronia com Pipedrive...")

    # --- Configuração Pipedrive ---
    API_KEY = os.getenv("API_KEY")
    # Este cabeçalho será passado para as funções importadas

    # --- Leitura do Google Sheets ---
    INTERVALO_LEITURA = "erros!A1:G"
    base = ler_dados_planilha(INTERVALO_LEITURA, SPREADSHEET_ID)
    print(f"Encontradas {len(base)} linhas para processar na planilha.")
    # base=base[1:]

    # --- Processamento em Lote (Linha por Linha) ---
    for linha, tab in base.iterrows():
        print(f"\n--- Processando Linha {linha}: {tab['email contato']} ---")
        tab['data aprovacao'] = pd.to_datetime(tab['data aprovacao'],dayfirst=True).strftime('%Y-%m-%d')
        # Variáveis para armazenar dados da pessoa
        id_person = None
        name_person = None
        
        # 1. BUSCAR A PESSOA NO PIPEDRIVE
# 1. BUSCAR A PESSOA NO PIPEDRIVE
        try:
            search_term = tab['email contato']
            
            API_KEY = os.getenv('API_KEY')
            api = PipedriveAPI(api_token=API_KEY)
            
            dados_pipedrive=api.search_persons(search_term,"email")
            dados_pipedrive = dados_pipedrive.json()
            
            # --- ESTA É A PARTE CORRIGIDA ---
            items = dados_pipedrive.get('data', {}).get('items', [])
            
            # Verifica se a lista 'items' não está vazia
            if items:
                # Se não estiver vazia, pega os dados
                item_data = items[0].get('item', {})
                id_person = item_data.get('id')
                name_person = item_data.get('name')
                print(f"Pessoa encontrada: {name_person} (ID: {id_person})")
            else:
                # Se estiver vazia, 'id_person' continua None
                # e o script saberá que precisa criar a pessoa
                pass 
            # --- FIM DA CORREÇÃO ---

        except Exception as e:
            print(f"Falha ao BUSCAR pessoa '{search_term}': {e}")
            # Continua para a próxima linha
            continue

        # 2. CRIAR PESSOA (Se não foi encontrada)
        try:
            if not id_person:
                person_name = tab['nome contato']
                person_email = tab['email contato']
                empresa = "empresa"
                data_aprov=dt.date.today().strftime('%Y-%m-%d')

                print(f"Pessoa não encontrada. Criando nova pessoa: {person_name}")
                
                person_data=api.add_person(person_name,person_email,empresa,empresa)
                # Chama a função importada de 'add_person.py'
                
                person_data = person_data.json().get('data', {})
                id_person = person_data.get('id')
                name_person = person_data.get('name')
                barbearia=person_data.get('custom_fields')[0]
                
                if not id_person:
                    print("!! Falha crítica ao criar a pessoa. Pulando esta linha.")
                    continue # Pula para o próximo loop
                
                print(f"Pessoa criada com sucesso: {name_person} (ID: {id_person})")
            
            # 3. CRIAR O NEGÓCIO (DEAL)
            # Se chegamos aqui, temos um 'id_person' (seja novo ou existente)
            
            # Coleta os dados para o Negócio (Deal) da planilha
            # ATENÇÃO: Estou assumindo o nome da coluna '[CS] NOME BARBEARIA'
            empresa = barbearia
            data_aprov = tab['data aprovacao']
            oferta = tab['nome oferta']
            doc = int(tab['doc contato'])
            funil = ""
            
            print(f"Criando/atualizando Negócio (Deal) para {name_person}...")
            
            # Chama a função importada de 'add_deal.py'
            deal_response = api.create_deal(
                person_id=id_person,
                person_name=name_person,
                empresa=empresa,
                data_aprov=data_aprov,
                oferta=oferta,
                doc=doc,
                funil = funil
            )
            
            deal_id = deal_response.json().get('data', {}).get('id')
            print(f"✅ Negócio (Deal) criado/atualizado com sucesso! ID: {deal_id}")

        except Exception as e:
            print(f"!! Erro ao processar Negócio para '{tab['email contato']}': {e}")
            # Continua para a próxima linha
            continue
    
    print("\n--- Processo Concluído ---")