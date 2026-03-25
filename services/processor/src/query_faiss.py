#!/usr/bin/env python3
"""
Script de utilidad para buscar en el índice FAISS y hacer preguntas con RAG
CON FILTRO AUTOMÁTICO POR EMPRESA Y COMPARACIONES MULTI-EMPRESA
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from faiss_manager import FAISSManager
from summarizer import GroqSummarizer
from db import mysql_conn


def get_transcript(empresa: str) -> tuple:
    """Obtiene la transcripción completa de una empresa desde MySQL."""
    conn = mysql_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT texto_transcrito FROM reports
            WHERE empresa = %s AND procesado = 1
            ORDER BY fecha DESC
            LIMIT 1
            """,
            (empresa,)
        )
        result = cur.fetchone()
        return result[0] if result else None
    finally:
        cur.close()
        conn.close()


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
    """Modo interactivo de búsqueda con transcripción completa"""
    print_separator()
    print("🔍 BÚSQUEDA INTERACTIVA — TRANSCRIPCIÓN COMPLETA")
    print_separator()
    print("\nEscribe 'exit' para salir\n")

    manager = FAISSManager()
    summarizer = GroqSummarizer()

    while True:
        try:
            query = input("Pregunta: ").strip()

            if query.lower() in ['exit', 'quit', 'salir']:
                print("\n👋 ¡Hasta luego!")
                break

            if not query:
                continue

            # Auto-detectar empresa en la pregunta
            empresas_disponibles = manager.get_all_empresas()
            empresas_mencionadas = [e for e in empresas_disponibles if e.lower() in query.lower()]

            if len(empresas_mencionadas) == 1:
                empresa = empresas_mencionadas[0]
                print(f"🏢 Empresa detectada: {empresa}")
            elif len(empresas_mencionadas) > 1:
                print(f"⚠️  Varias empresas detectadas: {', '.join(empresas_mencionadas)}")
                print(f"   Usando la primera: {empresas_mencionadas[0]}")
                empresa = empresas_mencionadas[0]
            elif empresas_disponibles:
                empresa = empresas_disponibles[0]
                print(f"🏢 Usando empresa por defecto: {empresa}")
            else:
                print("❌ No hay empresas procesadas en la base de datos")
                continue

            # Obtener transcripción completa de MySQL
            print(f"📄 Cargando transcripción de {empresa}...")
            transcript = get_transcript(empresa)

            if not transcript:
                print(f"❌ No se encontró transcripción para {empresa}\n")
                continue

            print(f"   ✅ {len(transcript.split())} palabras cargadas")

            # Generar respuesta con la transcripción completa
            print("🤖 Generando respuesta con Groq...")
            answer = summarizer.generate_answer(
                question=query,
                transcript=transcript,
                empresa=empresa,
            )

            if answer:
                print(f"\n💡 RESPUESTA:")
                print(f"{answer}\n")
            else:
                print("\n⚠️  No se pudo generar respuesta\n")

            print_separator('-')
            print()

        except KeyboardInterrupt:
            print("\n\n👋 ¡Hasta luego!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")


def search_once(query: str):
    """Realizar una única consulta con transcripción completa"""
    print_separator()
    print(f"🔍 CONSULTA: {query}")
    print_separator()

    manager = FAISSManager()
    summarizer = GroqSummarizer()

    empresas_disponibles = manager.get_all_empresas()
    empresas_mencionadas = [e for e in empresas_disponibles if e.lower() in query.lower()]

    if len(empresas_mencionadas) >= 1:
        empresa = empresas_mencionadas[0]
        print(f"🏢 Empresa detectada: {empresa}")
    elif empresas_disponibles:
        empresa = empresas_disponibles[0]
        print(f"🏢 Usando empresa por defecto: {empresa}")
    else:
        print("❌ No hay empresas procesadas en la base de datos")
        return

    print(f"📄 Cargando transcripción de {empresa}...")
    transcript = get_transcript(empresa)

    if not transcript:
        print(f"❌ No se encontró transcripción para {empresa}")
        return

    print(f"   ✅ {len(transcript.split())} palabras cargadas")
    print("🤖 Generando respuesta con Groq...")

    answer = summarizer.generate_answer(
        question=query,
        transcript=transcript,
        empresa=empresa,
    )

    if answer:
        print(f"\n💡 RESPUESTA:")
        print(f"{answer}\n")
    else:
        print("\n⚠️  No se pudo generar respuesta")


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