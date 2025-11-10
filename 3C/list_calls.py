import requests
import dotenv
import os
import time
import json
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse, parse_qs, urlunparse, urlencode # Importado para manipulação segura de URL

# Importa o cliente Kestra para gerenciamento de outputs
from kestra import Kestra 

dotenv.load_dotenv(
    "../.env"
)

# --- Configurações e Variáveis ---
manager_token = os.getenv("TOKEN_3C")
# Base URL original, sem nenhum parâmetro de query
INITIAL_BASE_URL = "https://podium.3c.plus/api/v1/calls"

# Parâmetros de filtro e paginação - Usados na PRIMEIRA requisição
filters: Dict[str, Any] = {
    "api_token": manager_token, 
    "simple_paginate": "true",
    "per_page": 1000,
    
    # Filtro de data:
    "startDate": "2025-11-07 08:00:00",
    "endDate": "2025-11-07 22:00:00",
}
MIN_CALL_SECONDS = 300 # 5 minutos * 60 segundos/min = 300 segundos

# --- Variáveis de Execução ---
all_filtered_calls: List[Dict[str, Any]] = []
# next_url armazena a URL COMPLETA para a próxima requisição
next_url: Optional[str] = INITIAL_BASE_URL
requests_count = 0
total_calls_processed = 0
total_pages = "???"

# --- Função Auxiliar: Conversão de Tempo ---
def time_to_seconds(time_str: str) -> int:
    """Converte uma string de tempo 'HH:MM:SS' para segundos."""
    try:
        h, m, s = map(int, time_str.split(':'))
        return h * 3600 + m * 60 + s
    except ValueError:
        return 0

# --- Função de Correção: Garantir que o Token esteja na URL ---
def ensure_token_in_url(url: str, token: str) -> str:
    """Garante que o parâmetro 'api_token' esteja presente na URL, se estiver faltando."""
    
    # 1. Parseia a URL
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    
    # 2. Adiciona o token se não estiver presente
    if 'api_token' not in query_params:
        query_params['api_token'] = [token]
        
        # 3. Reconstrói a query string
        new_query = urlencode(query_params, doseq=True)
        
        # 4. Reconstrói a URL completa
        return urlunparse(parsed_url._replace(query=new_query))
        
    return url # Token já estava presente


# --- Loop de Paginação (usando 'next_url') ---
print(f"Iniciando coleta e filtragem de dados para chamadas > 5 min e com agente...")

while next_url:
    requests_count += 1
    
    # Define a URL e os parâmetros para a requisição
    if requests_count == 1:
        # PRIMEIRA REQUISIÇÃO: Usa a URL base e todos os filtros via 'params'
        url_to_request = INITIAL_BASE_URL
        params_to_use = filters
    else:
        # REQUISIÇÕES SUBSEQUENTES: 
        # 1. Usa a URL 'next' e a corrige (adicionando o token)
        # 2. NÃO PASSA PARÂMETROS ADICIONAIS no 'params'
        url_to_request = ensure_token_in_url(next_url, manager_token)
        params_to_use = None # O token e a paginação já estão na url_to_request

    print(f"Buscando e filtrando Request #{requests_count}. Total de Páginas: {total_pages}")
    # Nota: Não logamos a URL completa, para não expor o token no log.
    
    # 1. Faz a Requisição
    r = requests.get(url_to_request, params=params_to_use)

    if r.status_code != 200:
        print(f"❌ Erro na requisição (Status: {r.status_code}) na URL: {url_to_request}. Encerrando.")
        break
        
    try:
        item = r.json()
    except requests.exceptions.JSONDecodeError:
        print("❌ Erro ao decodificar JSON. Encerrando.")
        print(f"Conteúdo da resposta: {r.text[:200]}...")
        break

    # 2. Extrai os dados e informações de paginação
    data = item.get('data', [])
    pagination_info = item.get('meta', {}).get("pagination", {})
    
    # Atualiza as variáveis de controle
    total_pages = pagination_info.get('total_pages', total_pages)
    current_page = pagination_info.get('current_page', 0)
    
    # 3. Atualiza o next_url (será None se for a última página)
    # Este é o link FORNECIDO PELA API, que será corrigido no topo do loop (se necessário)
    next_link = pagination_info.get('links', {}).get('next')
    next_url = next_link
    
    # 4. Loop de FILTRAGEM
    for call in data:
        speaking_time_seconds = time_to_seconds(call.get('speaking_time', '00:00:00'))
        
        # Filtros: deve ter agente E tempo de chamada > 5 minutos
        if call.get('has_agent', False) and speaking_time_seconds > MIN_CALL_SECONDS:
            all_filtered_calls.append(call)
            
    total_calls_processed += len(data)
    
    print(f"  -> {len(data)} itens processados. Pág {current_page} de {total_pages}. Filtrados acumulados: {len(all_filtered_calls)}")

    # 5. Pausa entre requisições (somente se houver próxima página)
    if next_url:
         time.sleep(0.5) 
    
# --- Fim do Processamento e Exportação ---
print(f"\n✅ Paginação e filtragem finalizadas.")
print(f"Total de chamadas processadas: {total_calls_processed}")
print(f"Total de chamadas coletadas e filtradas (com agente e > 5 min): {len(all_filtered_calls)}")


# Define o nome do arquivo de saída
OUTPUT_FILENAME = "filtered_3c_calls.json"

# Salva o resultado no sistema de arquivos local
with open(OUTPUT_FILENAME, 'w') as f:
    json.dump(all_filtered_calls, f, indent=2)

print(f"Arquivo de saída '{OUTPUT_FILENAME}' salvo com sucesso.")

# Envia o arquivo para o Internal Storage do Kestra e cria um output para o Flow
# Kestra.outputs espera um dicionário. A chave 'uri' será usada para referenciar o arquivo.
# Kestra.outputs({
#     "filtered_calls_uri": Kestra.store_file(OUTPUT_FILENAME),
#     "total_filtered_count": len(all_filtered_calls)
# })

print(f"Output 'filtered_calls_uri' e 'total_filtered_count' enviados para o Kestra.")