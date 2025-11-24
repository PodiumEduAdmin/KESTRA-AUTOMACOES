import requests
from io import StringIO
import json
import os
from datetime import datetime as dt
import uuid
import dotenv
import time
# A maioria dos imports não está sendo usada no trecho, mas são mantidos por contexto
from typing import Optional, Dict, Any, List 
from CLASSES.pipe_class import PipedriveAPI 

# --- CONFIGURAÇÃO ---
dotenv.load_dotenv("../.env")

# api_key do Google não é usada no trecho, mas mantida
api_key = os.getenv('GOOGLE_API')
apikey_pipe = os.getenv("API_KEY")

# Assumindo que PipedriveAPI está corretamente implementada para fazer requisições
api_pipedrive = PipedriveAPI(apikey_pipe)

# Data de corte para buscar atividades
DATA_INICIO = '2025-11-21T00:00:00Z' 
LIMITE_POR_PAGINA = 50 # O Pipedrive geralmente usa um limite padrão

# --- INICIALIZAÇÃO DA PAGINAÇÃO ---
todos_dados = []
current_cursor = None
tem_mais_paginas = True

print(f"Iniciando busca de atividades atualizadas desde {DATA_INICIO}...")

# --- LOOP DE PAGINAÇÃO ---
while tem_mais_paginas:
    # 1. Parâmetros base da requisição
    params = {
        'updated_since': DATA_INICIO,
        'limit': LIMITE_POR_PAGINA # Adicionando limite explícito
    }

    # 2. Adiciona o cursor à requisição, se existir
    if current_cursor:
        params['cursor'] = current_cursor

    print(f"Buscando página com cursor: {current_cursor if current_cursor else 'INÍCIO'}")
    
    # Faz a requisição, assumindo que api_pipedrive é um objeto de requests
    # CORREÇÃO: Usamos o método get_activities() ou um método que você tenha implementado
    try:
        # Se a sua classe PipedriveAPI for chamada como uma função:
        response_data = api_pipedrive.get_activities(params)
        # Se a sua classe PipedriveAPI tiver um método específico para atividades:
        # response_data = api_pipedrive.get_activities(params) 
        
        # Assumindo que a chamada retorna o JSON diretamente (ou um objeto com método .json())
        data = response_data if isinstance(response_data, dict) else response_data.json()

    except requests.exceptions.RequestException as e:
        print(f"❌ Erro na requisição Pipedrive: {e}")
        break # Sai do loop em caso de erro

    # 3. Processa os dados da página atual
    if data.get('data'):
        todos_dados.extend(data['data'])
    
    # 4. Extrai o novo cursor e decide se continua
    additional_data = data.get('additional_data', {})
    next_cursor = additional_data.get('next_cursor')
    
    if next_cursor:
        current_cursor = next_cursor
        print(f"Encontrado próximo cursor. Total de itens coletados: {len(todos_dados)}")
        # Pausa para evitar atingir limites de taxa (Rate Limit) da API
        time.sleep(1) 
    else:
        tem_mais_paginas = False # Termina o loop

print("\n-------------------------------------------")
print(f"✅ Paginação concluída. Total de itens coletados: {len(todos_dados)}")
print("-------------------------------------------")

# --- PROCESSAMENTO E IMPRESSÃO DOS DADOS COLETADOS (CORRIGIDO) ---
# O loop de impressão foi movido para fora do loop de paginação
if todos_dados:
    for item in todos_dados:
        if item.get('type')=="meeting":
            print("_______________________")
            # Usando .get() para acessar as chaves com um valor padrão em caso de KeyError
            print(f"Assunto: {item.get('subject', 'N/A')}")
            print(f"Tipo: {item.get('type', 'N/A')}")
            print(f"Hora criação: {item.get('add_time', 'N/A')}")
            print(f"Hora da Atualização: {item.get('update_time', 'N/A')}")
            print(f"ID da Negociação: {item.get('deal_id', 'N/A')}")
            print("_______________________")
else:
    print("Nenhuma atividade encontrada ou ocorreu um erro durante a busca.")