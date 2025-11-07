# Importa apenas o necessário, e a função base da API
import os
import requests
from typing import Optional, Dict, Any
# Usamos o import relativo, assumindo que os arquivos estão no mesmo diretório
# Se estiver usando Kestra/módulos, pode precisar ajustar para 'from .pipedrive_api_util import pipe_api'
from base_api_pipe import pipe_api
import datetime as dt
import dotenv

dotenv.load_dotenv()
# --- CONFIGURAÇÕES DE AUTENTICAÇÃO ---
# É recomendável obter o API_KEY de variáveis de ambiente (os.environ.get) 
# ou de um mecanismo de segredos do Kestra.
# Substitua pelo seu token real.
# 🚨 CHAVE UNIFICADA: Usando a chave que funcionou no pipedrive_persons.py 🚨
API_KEY = os.getenv('API_KEY')

# Configuração de Cabeçalhos: 'x-api-token' conforme sua imagem de autenticação.
cabecalhos_personalizados = {
    'x-api-token': API_KEY,
    'Accept': 'application/json' 
}


def add_person(person_name: str, email: str,empresa: str,
    data_aprov: str) -> requests.Response:
    """
    Cria uma nova pessoa (Person) no Pipedrive.

    Args:
        person_name: O nome da pessoa.
        email: O endereço de e-mail principal da pessoa.

    Returns:
        O objeto Response da requisição.
    """
    
    # 🚨 CORREÇÃO DEFINITIVA 🚨
    # Pipedrive V2 exige: 
    # 1. Chave no plural ('emails').
    # 2. Array de OBJETOS (o que exige 'value', 'primary', etc.)
    # 1. Mapeamento de Campos Customizados (usando os IDs fornecidos)
    custom_fields_data = {
        # [CS] NOME BARBEARIA
        "2b6fde1ae96d7e4400c8f59373e684fcb3b3a2fb": empresa,
        # [CS] DATA ENTRADA
        "9554a7487f4200c3ea68ff94ffa3e88fe8e19b38": data_aprov
    }

    novo_contato_payload = {
        "name": person_name,
        
        # Estrutura Correta (Chave Plural + Array de Objetos)
        "emails": [
            {
                "value": email,
                "primary": True,  # Booleano
                "label": "work"   # Label válido
            }
        ],
        # Se precisar adicionar telefone, use a chave 'phones' com a mesma estrutura:
        # "phones": [
        #    {
        #        "value": "999999999",
        #        "primary": True,
        #        "label": "mobile"
        #    }
        # ]
    }
    
    url_criar_pessoa = "https://api.pipedrive.com/api/v2/persons" 
    
    print(f"Tentando criar pessoa: {person_name} com email: {email}")

    response_post = pipe_api(
        url=url_criar_pessoa,
        method="POST",
        data=novo_contato_payload, # Dicionário de payload
        headers=cabecalhos_personalizados 
    )
    
    print("Pessoa criada com sucesso.")
    return response_post

def get_fields():
    URL_FIELDS="https://api.pipedrive.com/v1/personFields"
    # OBS: data agora contém a combinação de campos padrão e customizados (hashes)

    response_get = pipe_api(
        url=URL_FIELDS,
        method="GET",
        headers=cabecalhos_personalizados 
    )
    return response_get

# --- EXECUTAR TESTE ---
if __name__ == '__main__':

    # fields=get_fields()
    # dados_feald = fields.json()   
    # data_field=dados_feald.get('data')
    # for item in data_field:
    #     if '[CS]' in item.get('name'):
    #         print(f"NOME: {item.get('name')} - ID: {item.get('key')}")
    try:
        # Tenta executar a função corrigida
        person_response = add_person('Teste API Kestra 2', 'teste.kestra2@emailteste.com.br','barba brava',dt.date.today().strftime('%Y-%m-%d'))
        
        # Extrai os dados criados
        dados_pessoa = person_response.json()
        person_id = dados_pessoa.get('data', {}).get('id')
        
        print(f"\nStatus: {person_response.status_code}")
        print(f"Nova Pessoa Criada: ID={person_id}")
        
    except Exception as e:
        print(f"\nFalha ao executar a criação da pessoa: {e}")