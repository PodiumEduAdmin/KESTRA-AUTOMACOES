import requests
import os
import dotenv
from typing import Optional, Dict, Any
import json

# --- Configuração de Variáveis ---
dotenv.load_dotenv("../.env")

notion_token = os.getenv("NOTION_TOKEN")
# O ID pode ser de uma página comum ou de um database, 
# mas o endpoint é para buscar as propriedades dessa página.
# page_id = "26b3bbf5b1e18196b1ddc3bfb5b7cb19"

class NotiondriveAPI:
    """
    Classe para interagir com a API do Pipedrive, gerenciando a autenticação
    e encapsulando métodos para GET, POST, PUT, etc.
    """
    NOTION_VERSION ="2025-09-03"

# O 'self' é a referência à própria instância da classe (o objeto que está sendo criado)
    def __init__(self, api_token: str, base_url: str = "https://api.notion.com/"):
        # Atributos (Dados da Instância)
        self.api_token = api_token
        self.base_url = base_url
        
        # Configuração da Sessão (Melhora performance e gerencia headers)
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_token}",
            "Notion-Version": self.NOTION_VERSION.strip()
        })

    def _request_api(
        self,
        endpoint: str,
        method: str = "GET",
        query_params: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None # 'data' é o payload (dicionário) para POST/PUT
    ) -> Dict[str, Any]:
        """
        Função genérica para fazer requisições à API do Notion.

        Args:
            endpoint: Exemplo: 'pages', 'databases/{id}/query'.
            method: Método HTTP (GET, POST, PATCH, DELETE).
            query_params: Parâmetros de consulta (opcional).
            data: Dicionário Python contendo o corpo da requisição (payload).
        
        Returns:
            O corpo da resposta JSON decodificado (Dict[str, Any]).
        """

        full_url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"

        params_to_use = query_params
        # 2. Usa 'json' para serialização automática em POST/PUT/PATCH
        json_payload = data if isinstance(data, dict) and method in ["POST", "PUT", "PATCH"] else None
        
        try:
            response = self.session.request(
                method=method,
                url=full_url,
                params=query_params,
                json=data, 
                timeout=60
            )

            response.raise_for_status()
            return response

        except requests.exceptions.HTTPError as errh:
            print(f"Erro HTTP: {errh}")
            # Tenta mostrar detalhes do erro
            try:
                error_details = response.json()
                print(f"Detalhes da API (JSON): {json.dumps(error_details, indent=2)}")
            except json.JSONDecodeError:
                print(f"Detalhes (Texto Bruto): {response.text[:200]}...")
            raise # Re-lança a exceção para interromper o fluxo
            
        except requests.exceptions.RequestException as err:
            print(f"Ocorreu um erro na requisição: {err}")
            raise

    def page_props(self,
                   page_id):

        endpoint = f"v1/pages/{page_id.lstrip('/')}"

        return self._request_api(
            endpoint=endpoint,
            method="GET"
        )
  
    def create_page(self, page_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cria uma nova página ou um item de banco de dados.
        O payload deve conter 'parent', 'properties' e, opcionalmente, 'children'.
        """
        endpoint = "v1/pages"
        
        return self._request_api(
            endpoint=endpoint,
            method="POST",
            data=page_payload # O payload (seu corpo do curl)
        )
    
    def database_props(
            self,
            data_source_id,
            method="GET"
            ):
        
        endpoint =f"v1/data_sources/{data_source_id.lstrip('/')}"
        return self._request_api(
            endpoint=endpoint,
            method="GET",
        )
    
    def database_Retrieve(
            self,
            database_id,
            method="GET"
            ):
        
        endpoint =f"v1/databases/{database_id.lstrip('/')}"
        return self._request_api(
            endpoint=endpoint,
            method="GET",
        )
    
    def page_update(
            self,
            page_id,
            page_payload: Dict[str, Any]
            ):
        
        endpoint = f"v1/pages/{page_id.lstrip('/')}"
        return self._request_api(
            endpoint=endpoint,
            method="PATCH",
            data=page_payload
        )
    
    def append_children(
            self,
            page_id: str,
            children_payload: Dict[str, Any]
            ):
        
        # Endpoint para adicionar blocos à página (visto que o page_id atua como block_id)
        endpoint = f"v1/blocks/{page_id.lstrip('/')}/children"
        
        # O payload deve ser um dicionário com a chave "children": [...]
        return self._request_api(
            endpoint=endpoint,
            method="PATCH", 
            data=children_payload
        )