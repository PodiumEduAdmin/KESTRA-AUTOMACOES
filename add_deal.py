# Importa apenas o necessário, e a função base da API
import os
import requests
from typing import Optional, Dict, Any
# Usamos o import relativo, assumindo que os arquivos estão no mesmo diretório
# Se estiver usando Kestra/módulos, pode precisar ajustar para 'from .pipedrive_api_util import pipe_api'
from base_api_pipe import pipe_api # Corrigido o import para 'pipedrive_api_util'
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

def create_deal(
    person_id: int, 
    person_name: str,
    empresa: str,
    data_aprov: str,
    oferta: str,
    doc: str
) -> requests.Response:
    """
    Cria um novo Negócio (Deal) no Pipedrive com campos customizados preenchidos.

    Args:
        person_id: ID da Pessoa a ser vinculada ao Negócio (obrigatório).
        person_name: Nome da Pessoa, usado para compor o título.
        empresa: Valor para o campo customizado '[CS] NOME BARBEARIA'.
        data_aprov: Valor para o campo customizado '[CS] DATA ENTRADA SHELBY'.
        oferta: Valor para o campo customizado '[CS] OFERTA'.
        doc: Valor para o campo customizado '[CS] DOCUMENTO'.

    Returns:
        O objeto Response da requisição.
    """
    
    # 1. Mapeamento de Campos Customizados (usando os IDs fornecidos)
    custom_fields_data = {
        # [CS] NOME BARBEARIA
        "d15bfd1071385745cb1a2eabf8fefde79c06a1b0": empresa,
        # [CS] DATA ENTRADA SHELBY
        "dc2445ac578667511b6311df3bcdf5b91a6e5ac1": data_aprov,
        # [CS] OFERTA
        "236783b3d46e872a2d54b2a33d70e0d212ff88b1": oferta,
        # [CS] DOCUMENTO
        "e4e8411ddcb81913570c8beab551c2db9616baaa": doc,
    }

    # 2. Monta o payload do Negócio (enviando customizados na raiz)
    novo_deal_payload = {
        # Campos Padrão
        "title": f"[IMPLEMENTAÇÃO] {person_name}",
        "person_id": person_id,
        "stage_id": 58,      
        "status": "open",    
        
        # Campos Customizados de Negócio (enviados na raiz)
        "custom_fields": custom_fields_data
    }
    
    url_criar_deal = "https://api.pipedrive.com/api/v2/deals" # Endpoint de criação

    print(f"Tentando criar Negócio para Pessoa ID: {person_id} com Título: {novo_deal_payload['title']}")
    
    response_post = pipe_api(
        url=url_criar_deal,
        method="POST",
        data=novo_deal_payload, 
        headers=cabecalhos_personalizados 
    )
    
    print("Negócio criado com sucesso.")
    return response_post


# --- EXECUTAR TESTE ---
if __name__ == '__main__':
    # Este bloco simula a criação de um Negócio após a Pessoa ter sido criada
    
    # Simula dados necessários
    TEST_PERSON_ID = 39186 
    TEST_PERSON_NAME = "Teste Kestra Deal"
    TEST_EMPRESA = "Barbearia Kestra Flow"
    TEST_DATA_APROV = "2025-10-25"
    TEST_OFERTA = "Oferta Completa"
    TEST_DOC = 987654321

    print(f"--- Simulação de Criação de Negócio ---")

    try:
        # Tenta executar a função corrigida
        deal_response = create_deal(
            person_id=TEST_PERSON_ID,
            person_name=TEST_PERSON_NAME,
            empresa=TEST_EMPRESA,
            data_aprov=TEST_DATA_APROV,
            oferta=TEST_OFERTA,
            doc=TEST_DOC
        )
        
        # Extrai os dados criados
        dados_deal = deal_response.json()
        deal_id = dados_deal.get('data', {}).get('id')
        
        print(f"\nStatus: {deal_response.status_code}")
        print(f"Novo Negócio Criado: ID={deal_id}")
        print(f"Verifique o Pipedrive para confirmação dos campos customizados.")
        
    except Exception as e:
        print(f"\nFalha ao executar a criação do Negócio: {e}")