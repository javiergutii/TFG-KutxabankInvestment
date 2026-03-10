# Iniciar el proyecto

## De cero:
docker compose build --no-cache

docker compose up -d

Comprobar si están levantados: docker compose ps
Una vez levantados: docker compose exec ollama ollama pull qwen2.5:7b

docker compose exec db mysql -u reports_user -preports_pass -D reports -e "SELECT id, empresa, procesado, LENGTH(resumen) as resumen_length FROM reports;"

ls -lh shared/faiss_index/


## Ejecutar queries sobre empresas

docker compose run --rm processor python main.py

docker compose run --rm processor python query_faiss.py search

## Resúmenes del texto
docker compose run --rm processor python regenerate_summaries.py

#### Borrar el resumen que tenía
docker compose exec db mysql -u reports_user -preports_pass -D reports -e "UPDATE reports SET resumen = '' WHERE id = 1;"

#### Borrar faiss
Remove-Item -Recurse -Force .\shared\faiss_index\*


#### Exportarlo a un txt
##### Específico:
docker compose run --rm processor python export_summary.py export --id 2 --output /app/exports/resumen_id2.txt

#### Cambiar el estado del report de procesado a no procesado
docker compose exec db mysql -u reports_user -preports_pass -D reports -e "UPDATE reports SET procesado = 0 WHERE id = 1;"
