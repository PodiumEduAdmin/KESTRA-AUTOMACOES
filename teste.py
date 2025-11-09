from kestra import Kestra

# Defina a variável que você quer passar
output_value = "Hello from teste.py"

# Envie um dicionário com o nome da chave (ex: 'hello_message')
Kestra.outputs({"hello_message": output_value})