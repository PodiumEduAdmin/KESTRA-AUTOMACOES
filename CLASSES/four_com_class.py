import requests
import os
import dotenv
from typing import Optional, Dict, Any
import json

class FourComAPI:
    """
    Classe para interagir com a API da 4com, gerenciando a autenticação
    e encapsulando métodos para GET, POST, PUT, etc.
    """
# O 'self' é a referência à própria instância da classe (o objeto que está sendo criado)
    def __init__(self, api_token: str, base_url: str = "https://api.api4com.com/"):
        # Atributos (Dados da Instância)
        self.api_token = api_token
        self.base_url = base_url
        
        # Configuração da Sessão (Melhora performance e gerencia headers)
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"{self.api_token}"
        })

    def _request_api(
        self,
        endpoint: str,
        method: str = "GET",
        query_params: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None # 'data' é o payload (dicionário) para POST/PUT
    ) -> Dict[str, Any]:
        """
        Função genérica para fazer requisições à API da 4com.

        Args:
            endpoint: Exemplo: 'calls', 'api/v1/calls'.
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
    def list_calls(self,query):

        endpoint = f"api/v1/calls"

        return self._request_api(
            endpoint=endpoint,
            method="GET",
            query_params=query
        )
