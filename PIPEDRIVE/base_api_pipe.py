import requests
import json
from typing import Optional, Dict, Any

# A função pipe_api foi corrigida para usar o parâmetro 'json' 
# na chamada requests.request(), garantindo o Content-Type correto
# e a serialização de dados para o Pipedrive.
def pipe_api(
    url: str,
    method: str = "GET",
    query_params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
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
    
    # 1. Determina como enviar os dados: usa 'json' se for um dicionário em POST/PUT/PATCH
    json_payload = data if isinstance(data, dict) and method in ["POST", "PUT", "PATCH"] else None
    
    # 2. Se for JSON, não passamos nada para 'data'; caso contrário, passamos o 'data' original
    body_data = None if json_payload else data 
    
    response = None 
    try:
        response = requests.request(
            method=method,
            url=url,
            params=query_params,
            headers=headers,
            data=body_data, 
            json=json_payload, # Usando o parâmetro 'json' para serialização automática
            timeout=30
        )

        # Levanta um erro HTTP se a resposta não for 2xx (status 400, 500, etc.)
        response.raise_for_status()

        return response

    except requests.exceptions.HTTPError as errh:
        print(f"Erro HTTP: {errh}")
        if response is not None:
            print(f"URL da Requisição: {response.url}")
            print(f"Status Code: {response.status_code}")
            try:
                # Tenta ler o corpo como JSON para detalhes do erro 400 (Bad Request)
                error_details = response.json()
                print(f"Detalhes do Erro (JSON): {json.dumps(error_details, indent=2)}")
            except requests.exceptions.JSONDecodeError:
                print(f"Detalhes do Erro (Texto Bruto): {response.text[:500]}...")
        
        # Re-lança a exceção para que o fluxo de trabalho (Kestra) saiba que houve falha
        raise
    except requests.exceptions.RequestException as err:
        print(f"Ocorreu um erro na requisição: {err}")
        raise