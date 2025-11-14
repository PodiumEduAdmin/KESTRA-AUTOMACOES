import requests
import json
from typing import Optional, Dict, Any

# A função pipe_api foi corrigida para usar o parâmetro 'json' 
# na chamada requests.request(), garantindo o Content-Type correto
# e a serialização de dados para o Pipedrive.

class PipedriveAPI:
    """
    Classe para interagir com a API do Pipedrive, gerenciando a autenticação
    e encapsulando métodos para GET, POST, PUT, etc.
    """
# O 'self' é a referência à própria instância da classe (o objeto que está sendo criado)
    def __init__(self, api_token: str, base_url: str = "https://api.pipedrive.com/"):
        # Atributos (Dados da Instância)
        self.api_token = api_token
        self.base_url = base_url
        
        # Configuração da Sessão (Melhora performance e gerencia headers)
        self.session = requests.Session()
        self.session.params = {'api_token': self.api_token}
        self.session.headers.update({
            'x-api-token': self.api_token,
            'Accept': 'application/json' 
        })

    def _request_api(
        self,
        endpoint: str,
        method: str = "GET",
        query_params: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None # 'data' é o payload (dicionário) para POST/PUT
    ) -> requests.Response:
        """
        Faz uma requisição HTTP para a API do Pipedrive, tratando a autenticação
        e a serialização JSON.

        Args:
            url: O URL de destino.
            method: O método HTTP (GET, POST, PUT, DELETE).
            query_params: Parâmetros de consulta (incluindo o api_token, se preferir).
            headers: Cabeçalhos da requisição (geralmente contém 'x-api-token').
            data: O corpo (payload) da requisição como um dicionário Python.

        Returns:
            Um objeto requests.Response.
        """
        full_url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        params_to_use = query_params
        # 2. Usa 'json' para serialização automática em POST/PUT/PATCH
        json_payload = data if isinstance(data, dict) and method in ["POST", "PUT", "PATCH"] else None
        
        try:
            response = requests.request(
                method=method,
                url=full_url,
                # Usa os headers da sessão (sem o 'x-api-token' redundante)
                headers=self.session.headers,
                params=params_to_use,
                json=json_payload, 
                data=None, # Garante que 'data' não entre em conflito com 'json'
                timeout=30
            )

            response.raise_for_status()
            return response

        # ... (O bloco try/except de tratamento de erros está bom, mas omisso aqui por brevidade) ...
        except requests.exceptions.RequestException as err:
            print(f"Ocorreu um erro na requisição: {err}")
            raise

    def get_deal(
        self,
        person_id: int
    ) -> requests.Response:
        """
        Busca os negócios (Deal) no Pipedrive.

        Args:
            person_id: ID da Pessoa a ser vinculada ao Negócio (obrigatório).

        Returns:
            O objeto Response da requisição.
        """

        # 2. Monta o payload do Negócio (enviando customizados na raiz)
        payload = {
            # Campos Padrão
            "person_id": person_id
        }
        
        endpoint = "api/v2/deals"

        response_get = self._request_api(
            endpoint=endpoint,
            method="GET",
            query_params=payload
        )
        
        print("Negócio encontrado")
        return response_get
    
    def search_persons(
        self,
        term: str,
        fields: str
    ) -> requests.Response:
        """
        Busca um pessea (Person) no Pipedrive.

        Args:
            person_id: ID da Pessoa a ser vinculada ao Negócio (obrigatório).
                term: Texto para buscar a pessoa, pode usar custom_fields,email,notes,phone,name.
            fields: Especificar qual field está sendo usada para o filtro.

        Returns:
            O objeto Response da requisição.
        """

        # 2. Monta o payload do Negócio (enviando customizados na raiz)
        payload = {
            # Campos Padrão
            "term": f"{term}",
            "fields": f"{fields}"
        }
        
        endpoint = "api/v2/persons/search"

        
        response_post = self._request_api(
            endpoint=endpoint,
            method="GET",
            query_params=payload
        )
        
        print("Pessoa encontrada")
        return response_post
    
    def create_deal(
        self,
        person_id: int, 
        person_name: str,
        empresa: str,
        data_aprov: str,
        oferta: str,
        doc: str,
        funil: str
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
            "title": f"[{funil}] {person_name}",
            "person_id": person_id,
            "stage_id": 58,      
            "status": "open",    
            
            # Campos Customizados de Negócio (enviados na raiz)
            "custom_fields": custom_fields_data
        }
        
        endpoint = "api/v2/deals" # Endpoint de criação

        print(f"Tentando criar Negócio para Pessoa ID: {person_id} com Título: {novo_deal_payload['title']}")
        
        response_post = self._request_api(
            endpoint=endpoint,
            method="POST",
            data=novo_deal_payload
        )
        
        print("Negócio criado com sucesso.")
        return response_post

    def add_person(self,person_name: str, email: str,empresa: str,
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
        
        endpoint = "api/v2/persons" 
        
        print(f"Tentando criar pessoa: {person_name} com email: {email}")

        response_post = self._request_api(
            endpoint=endpoint,
            method="POST",
            data=novo_contato_payload # Dicionário de payload
        )
        
        print("Pessoa criada com sucesso.")
        return response_post

    def get_fields(self):
        endpoint="v1/personFields"
        # OBS: data agora contém a combinação de campos padrão e customizados (hashes)

        response_get = self._request_api(
            endpoint=endpoint,
            method="GET"
        )
        return response_get
    
    def post_notes(self, payload):
        """
        Cria uma nova nota no Pipedrive vinculada a um deal, pessoa ou organização.

        Args:
            payload (dict): O corpo da requisição, ex: {"content": "...", "deal_id": 123}.

        Returns:
            O objeto Response da requisição.
        """
        endpoint = "v1/notes"

        response_post = self._request_api(
            endpoint=endpoint,
            method="POST",
            # 🎯 CORREÇÃO AQUI: Passar o payload no argumento 'data' 🎯
            data=payload 
        )
        
        # ⚠️ Sugestão: Adicionar um print para confirmar ⚠️
        print(f"Nota criada com sucesso.")
        return response_post
