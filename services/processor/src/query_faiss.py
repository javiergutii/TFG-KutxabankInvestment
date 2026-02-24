#!/usr/bin/env python3
"""
Script de utilidad para buscar en el índice FAISS y hacer preguntas con RAG
CON FILTRO AUTOMÁTICO POR EMPRESA Y COMPARACIONES MULTI-EMPRESA
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from faiss_manager import FAISSManager
from summarizer import OllamaSummarizer


def print_separator(char='=', length=80):
    print(char * length)


def show_stats():
    """Mostrar estadísticas del índice"""
    print_separator()
    print("📊 ESTADÍSTICAS DEL ÍNDICE FAISS")
    print_separator()

    manager = FAISSManager()
    stats = manager.get_stats()

    print(f"\n📦 Total de vectores: {stats['total_vectors']}")
    print(f"📏 Dimensión: {stats['dimension']}")
    print(f"🏢 Empresas indexadas: {stats['num_empresas']}")
    print(f"🤖 Modelo: {stats['embedding_model']}")

    print(f"\n📋 Empresas:")
    for empresa in stats['empresas']:
        chunks = stats['chunks_por_empresa'].get(empresa, 0)
        print(f"   • {empresa}: {chunks} chunks")
    print()


def search_interactive():
    """Modo interactivo de búsqueda con RAG y filtro automático"""
    print_separator()
    print("🔍 BÚSQUEDA INTERACTIVA CON RAG")
    print_separator()
    print("\nEscribe 'exit' para salir\n")

    manager = FAISSManager()
    summarizer = OllamaSummarizer()

    while True:
        try:
            query = input("🔍 Pregunta: ").strip()

            if query.lower() in ['exit', 'quit', 'salir']:
                print("\n👋 ¡Hasta luego!")
                break

            if not query:
                continue
            
            # 🆕 AUTO-DETECTAR EMPRESA en la pregunta
            empresas_disponibles = manager.get_all_empresas()
            empresas_mencionadas = []
            for empresa in empresas_disponibles:
                if empresa.lower() in query.lower():
                    empresas_mencionadas.append(empresa)
            
            # Solo filtrar si menciona UNA empresa (no comparaciones)
            if len(empresas_mencionadas) == 1:
                empresa_filter = empresas_mencionadas[0]
                print(f"🔍 Filtrando automáticamente por: {empresa_filter}")
            elif len(empresas_mencionadas) > 1:
                empresa_filter = None
                print(f"🔍 Comparación detectada: {', '.join(empresas_mencionadas)} → buscando en ambas")
            else:
                empresa_filter = None
            
            # Traducir términos financieros clave ES → EN
            translations = {
                'ingresos': 'revenue',
                'beneficios': 'profit',
                'deuda': 'debt',
                'trimestre': 'quarter',
                'semestre': 'half',
                'dividendo': 'dividend',
                'acciones': 'shares',
                'crecimiento': 'growth',
                'resultados': 'results',
                'ventas': 'sales',
                'facturación': 'revenue',
                'ganancias': 'earnings',
                'pérdidas': 'losses',
                'margen': 'margin',
                'capex': 'capex',
                'ebitda': 'ebitda',
                'flujo': 'cash flow',
                'caja': 'cash',
                'apalancamiento': 'leverage',
                'latinoamérica': 'latin america',
                'países': 'countries',
                'vendido': 'sold sale',
                'venta': 'sale',
                'comprado': 'acquired',
                'adquisición': 'acquisition',
            }
            query_en = query.lower()
            for es, en in translations.items():
                query_en = query_en.replace(es, en)

            # Buscar con ambas queries y combinar
            print("\n🔎 Buscando en índice FAISS...")
            
            # 🆕 Si es comparación, asegurar chunks de ambas empresas
            if empresas_mencionadas and len(empresas_mencionadas) > 1:
                # Buscar chunks de cada empresa por separado para garantizar mezcla
                all_results = []
                for empresa in empresas_mencionadas:
                    results_empresa_es = manager.search(query, k=10, filter_empresa=empresa)
                    results_empresa_en = manager.search(query_en, k=10, filter_empresa=empresa)
                    
                    # Combinar y eliminar duplicados de esta empresa
                    seen_empresa = set()
                    results_empresa = []
                    for r in results_empresa_es + results_empresa_en:
                        pos = r[0].get('index_position')
                        if pos not in seen_empresa:
                            seen_empresa.add(pos)
                            results_empresa.append(r)
                    
                    # Tomar top 5 de ESTA empresa (garantiza diversidad)
                    results_empresa = sorted(results_empresa, key=lambda x: x[1], reverse=True)[:5]
                    all_results.extend(results_empresa)
                
                # Ya tenemos 5 de cada empresa, no hace falta reducir más
                results = all_results
            else:
                # Búsqueda normal (una empresa o sin filtro)
                results_es = manager.search(query, k=7, filter_empresa=empresa_filter)
                results_en = manager.search(query_en, k=7, filter_empresa=empresa_filter)
                
                # Combinar evitando duplicados
                seen = set()
                results = []
                for r in results_es + results_en:
                    pos = r[0].get('index_position')
                    if pos not in seen:
                        seen.add(pos)
                        results.append(r)
                results = sorted(results, key=lambda x: x[1], reverse=True)[:10]

            if not results:
                print("❌ No se encontraron resultados\n")
                continue

            # Mostrar resultados
            print(f"\n✅ Encontrados {len(results)} resultados:\n")

            context_chunks = []
            for i, (meta, score) in enumerate(results, 1):
                print(f"--- Resultado {i} (similitud: {score:.3f}) ---")
                print(f"🏢 Empresa: {meta['empresa']}")
                print(f"📅 Fecha: {meta.get('fecha', 'N/A')}")
                print(f"📄 Chunk: {meta['chunk_index'] + 1}/{meta['total_chunks']}")
                print(f"💬 Texto: {meta['text'][:200]}...")
                print()
                context_chunks.append(meta['text'])

            # Generar respuesta con Ollama
            print("🤖 Generando respuesta con Ollama...")
            answer = summarizer.generate_answer(
                question=query,
                context_chunks=context_chunks,
                empresa=results[0][0].get('empresa') if results else None,
                max_tokens=800
            )

            if answer:
                print(f"\n💡 RESPUESTA:")
                print(f"{answer}\n")
            else:
                print("\n⚠️  No se pudo generar respuesta con Ollama")
                print("💡 Pero aquí tienes los fragmentos relevantes encontrados arriba\n")

            print_separator('-')
            print()

        except KeyboardInterrupt:
            print("\n\n👋 ¡Hasta luego!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")


def search_once(query: str, k: int = 10):
    """Realizar una única búsqueda"""
    print_separator()
    print(f"🔍 BÚSQUEDA: {query}")
    print_separator()

    manager = FAISSManager()
    
    # Auto-detectar empresa
    empresas_disponibles = manager.get_all_empresas()
    empresas_mencionadas = []
    for empresa in empresas_disponibles:
        if empresa.lower() in query.lower():
            empresas_mencionadas.append(empresa)
    
    # Solo filtrar si menciona UNA empresa
    if len(empresas_mencionadas) == 1:
        empresa_filter = empresas_mencionadas[0]
        print(f"🔍 Filtrando por: {empresa_filter}")
    elif len(empresas_mencionadas) > 1:
        empresa_filter = None
        print(f"🔍 Comparación: {', '.join(empresas_mencionadas)} → sin filtro")
    else:
        empresa_filter = None
    
    results = manager.search(query, k=k, filter_empresa=empresa_filter)

    if not results:
        print("\n❌ No se encontraron resultados")
        return

    print(f"\n✅ Encontrados {len(results)} resultados:\n")

    for i, (meta, score) in enumerate(results, 1):
        print(f"--- Resultado {i} (similitud: {score:.3f}) ---")
        print(f"🏢 Empresa: {meta['empresa']}")
        print(f"📅 Fecha: {meta.get('fecha', 'N/A')}")
        print(f"🔗 URL: {meta.get('url', 'N/A')}")
        print(f"📄 Chunk: {meta['chunk_index'] + 1}/{meta['total_chunks']}")
        print(f"\n💬 Texto:")
        print(f"{meta['text']}\n")


def main():
    if len(sys.argv) < 2:
        print("""
╔═══════════════════════════════════════════════════════════════╗
║                   FAISS Search Utility                        ║
║       CON FILTRO AUTOMÁTICO Y COMPARACIÓN MULTI-EMPRESA       ║
╚═══════════════════════════════════════════════════════════════╝

Uso:
  python query_faiss.py stats              - Mostrar estadísticas
  python query_faiss.py search             - Búsqueda interactiva
  python query_faiss.py query "texto"      - Búsqueda única

Ejemplos:
  python query_faiss.py stats
  python query_faiss.py search
  python query_faiss.py query "¿Cuáles fueron los ingresos de Telefónica?"
  
🆕 FILTRO AUTOMÁTICO:
  - Una empresa → filtra solo esa empresa
  - Dos+ empresas → busca en ambas por separado y mezcla resultados
  - Sin empresa → busca en todas
        """)
        return

    command = sys.argv[1].lower()

    if command == 'stats':
        show_stats()
    elif command == 'search':
        search_interactive()
    elif command == 'query' and len(sys.argv) > 2:
        query = ' '.join(sys.argv[2:])
        search_once(query)
    else:
        print("❌ Comando no reconocido. Usa: stats, search, o query \"texto\"")


if __name__ == "__main__":
    main()