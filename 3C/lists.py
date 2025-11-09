import requests
import dotenv
import os
import time # Adicionado para pausar entre requisições (boa prática)
from typing import Dict, List, Any

dotenv.load_dotenv(
    "../.env"
)
manager_token=os.getenv("TOKEN_3C")
BASE_URL=f"https://podium.3c.plus/api/v1/calls?api_token={manager_token}&simple_paginate=true&per_page=1000"

# --- Função Auxiliar: Conversão de Tempo ---
def time_to_seconds(time_str: str) -> int:
    """Converte uma string de tempo 'HH:MM:SS' para segundos."""
    try:
        # Divide a string em horas, minutos e segundos
        h, m, s = map(int, time_str.split(':'))
        return h * 3600 + m * 60 + s
    except ValueError:
        # Retorna 0 em caso de formato inválido
        return 0
    
# Parâmetros de filtro e limites (data, por exemplo)
# A API 3C Plus geralmente usa 'params' para filtros na URL
filters = {
    "startDate": "2025-10-07 00:00:00",
    "endDate": "2025-10-07 23:59:59",
    "page": 1, # Adicionamos o parâmetro 'page' inicial
}
all_filtered_calls: List[Dict[str, Any]] = [] # Lista para armazenar APENAS chamadas filtradas
current_page = 1
total_pages = 1 
MIN_CALL_SECONDS = 300 # 5 minutos * 60 segundos/min = 300 segundos

print(f"Iniciando coleta e filtragem de dados para chamadas > 5 min e com agente...")

# --- Loop de Paginação ---
while current_page <= total_pages:
    
    filters['page'] = current_page 
    
    print(f"Buscando e filtrando Página {current_page} / {total_pages}...")
    
    r = requests.get(BASE_URL, params=filters)

    if r.status_code != 200:
        print(f"❌ Erro na requisição (Status: {r.status_code}) na página {current_page}. Encerrando.")
        break
        
    try:
        item = r.json()
    except requests.exceptions.JSONDecodeError:
        print("❌ Erro ao decodificar JSON. Encerrando.")
        break

    # 1. Extrai os dados e informações de paginação
    data = item.get('data', [])
    pagination_info = item.get('meta', {}).get("pagination", {})
    total_pages = pagination_info.get('total_pages', 0)
    
    # 2. Loop de FILTRAGEM
    for call in data:
        # A API tem 'speaking_time' e 'speaking_with_agent_time'. 
        # Vou usar 'speaking_time' que parece ser o tempo total de fala na chamada.
        speaking_time_seconds = time_to_seconds(call.get('speaking_time', '00:00:00'))
        
        # Condições de filtro:
        # a) deve ter agente (has_agent == True)
        # b) tempo de chamada (speaking_time) > 5 minutos (300 segundos)
        if call.get('has_agent', False) and speaking_time_seconds > MIN_CALL_SECONDS:
            all_filtered_calls.append(call)
    
    print(f"  -> {len(data)} itens processados. Total filtrado acumulado: {len(all_filtered_calls)}")

    # 3. Prepara para a próxima iteração
    current_page += 1
    
    # Pausa entre requisições
    if current_page <= total_pages:
         time.sleep(0.5) 
    
# --- Fim do Processamento ---
print(f"\n✅ Paginação e filtragem finalizadas.")
print(f"Total de chamadas coletadas e filtradas (com agente e > 5 min): {len(all_filtered_calls)}")