# Iniciar el proyecto

## De cero:
docker compose build --no-cache

docker compose up -d db ollama

docker compose run --rm extractor

docker compose exec db mysql -u reports_user -preports_pass -D reports -e \t
  "SELECT id, empresa, procesado, LENGTH(resumen) as resumen_length FROM reports;"

ls -lh shared/faiss_index/

docker compose run --rm processor python query_faiss.py stats

ocker compose run --rm processor python query_faiss.py query "resultados financieros"

## Ejecutar queries sobre empresas

docker compose run --rm processor python main.py

docker compose run --rm processor python query_faiss.py search

docker compose run --rm processor python query_faiss.py stats

docker compose run --rm processor python regenerate_summaries.py