# Iniciar el proyecto

## De cero:
docker compose up --build

#### Descargar modelo y verificar
docker exec -it tfg-ollama-1 ollama pull qwen2.5:14b
docker compose exec ollama ollama list

## Extractor
docker compose --profile manual run --rm extractor

## Processor
docker compose run --rm processor python main.py

#### Ejecutar queries sobre empresas
docker compose run --rm processor python query_faiss.py search

#### Generar de nuevo resúmenes texto
docker compose run --rm processor python regenerate_summaries.py


-----------------------------------------------------------------------------------
# Comandos extra:

#### Mirar la bbdd 
docker compose exec db mysql -u reports_user -preports_pass -D reports -e "SELECT id, empresa, procesado, LENGTH(resumen) as resumen_length FROM reports;"

#### Cambiar el estado del report de procesado a no procesado
docker compose exec db mysql -u reports_user -preports_pass -D reports -e "UPDATE reports SET procesado = 0 WHERE id = 1;"

#### Borrar el resumen que tenía
docker compose exec db mysql -u reports_user -preports_pass -D reports -e "UPDATE reports SET resumen = '' WHERE id = 1;"

#### Mirar indices
ls -lh shared/faiss_index/

#### Borrar faiss
Remove-Item -Recurse -Force .\shared\faiss_index\*