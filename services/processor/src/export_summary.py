"""
Utilidad para exportar resúmenes de la base de datos a archivos
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mysql.connector
from config import MYSQL_HOST, MYSQL_PORT, MYSQL_DB, MYSQL_USER, MYSQL_PASSWORD


def export_summary(report_id: int, output_file: str = None):
    """
    Exporta el resumen de un reporte a un archivo .txt
    
    Args:
        report_id: ID del reporte a exportar
        output_file: Ruta del archivo de salida (opcional)
    """
    try:
        # Conectar a MySQL
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DB,
            charset='utf8mb4'
        )
        cur = conn.cursor()
        
        # Obtener resumen y empresa
        cur.execute(
            "SELECT empresa, resumen FROM reports WHERE id = %s",
            (report_id,)
        )
        result = cur.fetchone()
        
        if not result:
            print(f"❌ No se encontró el reporte con ID {report_id}")
            return False
        
        empresa, resumen = result
        
        if not resumen or len(resumen.strip()) < 50:
            print(f"⚠️  El reporte {report_id} no tiene resumen generado")
            return False
        
        # Generar nombre de archivo si no se proporciona
        if not output_file:
            # Limpiar nombre de empresa para usar en archivo
            empresa_clean = empresa.replace(' ', '_').replace('/', '_')
            output_file = f"resumen_{empresa_clean}_id{report_id}.txt"
        
        # Guardar en archivo con UTF-8
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"RESUMEN EJECUTIVO - {empresa}\n")
            f.write("="*80 + "\n\n")
            f.write(resumen)
            f.write("\n\n" + "="*80 + "\n")
            f.write(f"Reporte ID: {report_id}\n")
        
        print(f"✅ Resumen exportado correctamente")
        print(f"📄 Archivo: {output_file}")
        
        cur.close()
        conn.close()
        
        return True
        
    except mysql.connector.Error as e:
        print(f"❌ Error de MySQL: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def export_all_summaries(output_dir: str = "summaries"):
    """
    Exporta todos los resúmenes disponibles a archivos individuales
    
    Args:
        output_dir: Directorio donde guardar los archivos
    """
    try:
        # Crear directorio si no existe
        os.makedirs(output_dir, exist_ok=True)
        
        # Conectar a MySQL
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DB,
            charset='utf8mb4'
        )
        cur = conn.cursor()
        
        # Obtener todos los reportes con resumen
        cur.execute("""
            SELECT id, empresa, resumen 
            FROM reports 
            WHERE resumen IS NOT NULL AND resumen != ''
            ORDER BY id
        """)
        
        results = cur.fetchall()
        
        if not results:
            print("⚠️  No hay resúmenes disponibles para exportar")
            return False
        
        print(f"📋 Encontrados {len(results)} resumen(es) para exportar\n")
        
        exported = 0
        for report_id, empresa, resumen in results:
            if len(resumen.strip()) < 50:
                print(f"⚠️  Reporte {report_id} - {empresa}: resumen demasiado corto, omitiendo")
                continue
            
            # Limpiar nombre de empresa
            empresa_clean = empresa.replace(' ', '_').replace('/', '_')
            output_file = os.path.join(output_dir, f"resumen_{empresa_clean}_id{report_id}.txt")
            
            # Guardar archivo
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"RESUMEN EJECUTIVO - {empresa}\n")
                f.write("="*80 + "\n\n")
                f.write(resumen)
                f.write("\n\n" + "="*80 + "\n")
                f.write(f"Reporte ID: {report_id}\n")
            
            print(f"✅ {empresa} (ID: {report_id}) → {output_file}")
            exported += 1
        
        cur.close()
        conn.close()
        
        print(f"\n🎉 {exported} resumen(es) exportado(s) correctamente")
        print(f"📁 Directorio: {output_dir}/")
        
        return True
        
    except mysql.connector.Error as e:
        print(f"❌ Error de MySQL: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Función principal con CLI"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Exportar resúmenes de reportes a archivos .txt'
    )
    parser.add_argument(
        'command',
        choices=['export', 'export-all'],
        help='Comando a ejecutar'
    )
    parser.add_argument(
        '--id',
        type=int,
        help='ID del reporte a exportar (para comando export)'
    )
    parser.add_argument(
        '--output',
        help='Archivo de salida (para comando export)'
    )
    parser.add_argument(
        '--dir',
        default='summaries',
        help='Directorio de salida (para comando export-all)'
    )
    
    args = parser.parse_args()
    
    if args.command == 'export':
        if not args.id:
            print("❌ Debes especificar --id para el comando export")
            print("Ejemplo: python export_summary.py export --id 1")
            return
        
        export_summary(args.id, args.output)
    
    elif args.command == 'export-all':
        export_all_summaries(args.dir)


if __name__ == "__main__":
    main()