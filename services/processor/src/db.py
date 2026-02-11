import mysql.connector
from typing import List, Dict, Optional
import time
from datetime import datetime

from config import MYSQL_HOST, MYSQL_PORT, MYSQL_DB, MYSQL_USER, MYSQL_PASSWORD


def mysql_conn(db: str | None = None):
    """Crear conexión a MySQL"""
    return mysql.connector.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=db or MYSQL_DB,
    )


def wait_for_mysql(max_tries=30, sleep_s=2):
    """Esperar a que MySQL esté disponible"""
    for i in range(max_tries):
        try:
            c = mysql_conn()
            c.close()
            print("[processor] MySQL OK")
            return
        except Exception as e:
            print(f"[processor] esperando MySQL... ({i+1}/{max_tries}) {e}")
            time.sleep(sleep_s)
    raise SystemExit("MySQL no arrancó a tiempo")


def get_unprocessed_reports(limit: int = 10) -> List[Dict]:
    """
    Obtener reportes no procesados de la base de datos.
    
    Args:
        limit: Número máximo de reportes a obtener
        
    Returns:
        Lista de diccionarios con los datos de los reportes
    """
    conn = mysql_conn()
    cur = conn.cursor(dictionary=True)
    
    try:
        cur.execute(
            """
            SELECT id, empresa, url, texto_transcrito, fecha, fetched_at
            FROM reports
            WHERE procesado = 0
            ORDER BY fetched_at ASC
            LIMIT %s
            """,
            (limit,)
        )
        
        reports = cur.fetchall()
        print(f"[processor] Encontrados {len(reports)} reportes sin procesar")
        return reports
        
    finally:
        cur.close()
        conn.close()


def mark_as_processed(report_id: int, success: bool = True):
    """
    Marcar un reporte como procesado.
    
    Args:
        report_id: ID del reporte
        success: Si el procesamiento fue exitoso
    """
    conn = mysql_conn()
    cur = conn.cursor()
    
    try:
        # Si fue exitoso, marcar como procesado
        # Si falló, mantener procesado=0 para reintentarlo
        if success:
            cur.execute(
                """
                UPDATE reports
                SET procesado = 1
                WHERE id = %s
                """,
                (report_id,)
            )
            conn.commit()
            print(f"[processor] Reporte {report_id} marcado como procesado ✅")
        else:
            print(f"[processor] Reporte {report_id} NO marcado (falló procesamiento) ❌")
            
    finally:
        cur.close()
        conn.close()


def update_report_summary(report_id: int, resumen: str):
    """
    Actualizar el resumen de un reporte.
    
    Args:
        report_id: ID del reporte
        resumen: Texto del resumen generado
    """
    conn = mysql_conn()
    cur = conn.cursor()
    
    try:
        cur.execute(
            """
            UPDATE reports
            SET resumen = %s
            WHERE id = %s
            """,
            (resumen, report_id)
        )
        conn.commit()
        print(f"[processor] Resumen actualizado para reporte {report_id} ✅")
        
    finally:
        cur.close()
        conn.close()


def get_report_by_id(report_id: int) -> Optional[Dict]:
    """
    Obtener un reporte específico por ID.
    
    Args:
        report_id: ID del reporte
        
    Returns:
        Diccionario con los datos del reporte o None si no existe
    """
    conn = mysql_conn()
    cur = conn.cursor(dictionary=True)
    
    try:
        cur.execute(
            """
            SELECT id, empresa, url, texto_transcrito, fecha, fetched_at, procesado, resumen
            FROM reports
            WHERE id = %s
            """,
            (report_id,)
        )
        
        report = cur.fetchone()
        return report
        
    finally:
        cur.close()
        conn.close()


def get_all_processed_reports() -> List[Dict]:
    """
    Obtener todos los reportes procesados.
    
    Returns:
        Lista de reportes procesados
    """
    conn = mysql_conn()
    cur = conn.cursor(dictionary=True)
    
    try:
        cur.execute(
            """
            SELECT id, empresa, url, fecha, fetched_at
            FROM reports
            WHERE procesado = 1
            ORDER BY fetched_at DESC
            """
        )
        
        reports = cur.fetchall()
        return reports
        
    finally:
        cur.close()
        conn.close()


def get_processing_stats() -> Dict:
    """
    Obtener estadísticas de procesamiento.
    
    Returns:
        Diccionario con estadísticas
    """
    conn = mysql_conn()
    cur = conn.cursor(dictionary=True)
    
    try:
        cur.execute(
            """
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN procesado = 1 THEN 1 ELSE 0 END) as procesados,
                SUM(CASE WHEN procesado = 0 THEN 1 ELSE 0 END) as pendientes
            FROM reports
            """
        )
        
        stats = cur.fetchone()
        return stats
        
    finally:
        cur.close()
        conn.close()


def get_unprocessed_report_by_empresa(empresa: str) -> Optional[Dict]:
    """
    Obtener el reporte no procesado de una empresa específica.
    
    Args:
        empresa: Nombre de la empresa
        
    Returns:
        Diccionario con los datos del reporte o None si no existe
    """
    conn = mysql_conn()
    cur = conn.cursor(dictionary=True)
    
    try:
        cur.execute(
            """
            SELECT id, empresa, url, texto_transcrito, fecha, fetched_at
            FROM reports
            WHERE empresa = %s AND procesado = 0
            ORDER BY fetched_at DESC
            LIMIT 1
            """,
            (empresa,)
        )
        
        report = cur.fetchone()
        if report:
            print(f"[processor] Encontrado reporte sin procesar para {empresa} (ID: {report['id']})")
        else:
            print(f"[processor] No hay reportes sin procesar para {empresa}")
        return report
        
    finally:
        cur.close()
        conn.close()