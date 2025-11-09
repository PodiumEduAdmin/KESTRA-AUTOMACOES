from kestra import Kestra
import os

# say = os.environ['SAY'] + "He  # Se a saída for 'Hello from teste.py', isso estaria errado.

# Para manter o exemplo da imagem, supondo que você queria concatenar com 'Hello'
say = os.environ['SAY'] + " there!" 
# O valor de SAY será 'Hello from teste.py'
# say final será 'Hello from teste.py there!'

# Se você quiser que o segundo script também produza um output, use a mesma estrutura:
Kestra.outputs({"final_message": say})
