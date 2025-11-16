from CLASSES.notion_class import NotiondriveAPI
import os
import json

notion_token = os.environ['NOTION_TOKEN']
api_notion = NotiondriveAPI(notion_token)

database_id="2853bbf5-b1e1-80d8-8485-eec426ca8de6"
data_source_id='2853bbf5-b1e1-8024-bd2e-000b87023880'

depoimentos=api_notion.database_Retrieve(database_id)


page=api_notion.page_props(page_id="28c3bbf5b1e180c58badd5abd6f2780c")

page.json()

depoimentos.json()


datasource=api_notion.database_props(data_source_id)
datasource.json()

list_dep=api_notion.list_datasource(data_source_id)

list_dep.json()

payload_faturamento_apenas = {
  "filter": {
    "property": 'Link',
    "url": {
        "is_not_empty": True
    }
  }
}

# 1. Chamada à API
response = api_notion.query_datasource(data_source_id, payload_faturamento_apenas)
results = response.json().get("results", [])

depoimentos_finais = []
for page in results:
    # try:
    cidade = page['properties'].get('Cidade').get('place').get('name') if page['properties'].get('Cidade').get('place') is not None else None,

    depoimentos_finais.append(
        {
          "NOME": (page['properties'].get('Nome').get('title')[0].get('plain_text')) if (page['properties'].get('Nome').get('title')[0].get('plain_text')) else "",
          "CIDADE": page['properties'].get('Cidade').get('place').get('name') if page['properties'].get('Cidade').get('place') is not None else None,
          "FATURAMENTO_INICIAL":(page['properties'].get('Fat. Inicial').get('number')) if (page['properties'].get('Fat. Atual').get('number')) else "",
          "FATURAMENTO_ATUAL":(page['properties'].get('Fat. Atual').get('number')) if (page['properties'].get('Fat. Atual').get('number')) else "",
          "ASSINANTES":(page['properties'].get('Assinantes').get('number')) if (page['properties'].get('Fat. Atual').get('number')) else "",
          "TEXTO":str([item.get('text').get('content') for item in page['properties'].get('Texto').get('rich_text')]) if str([item.get('text').get('content') for item in page['properties'].get('Texto').get('rich_text')]) else "",
          "Link":(page['properties'].get('Link').get('url')) if (page['properties'].get('Link').get('url')) else ""
      })
        
    # except:
    #   continue

datasource.json()