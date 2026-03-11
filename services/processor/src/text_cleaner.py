import re
from typing import List


def clean_text(text: str) -> str:
    """
    Limpia el texto transcrito eliminando ruido y normalizando.
    
    Args:
        text: Texto a limpiar
        
    Returns:
        Texto limpio
    """
    if not text:
        return ""
    
    # Eliminar URLs
    text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
    
    # Eliminar emails
    text = re.sub(r'\S+@\S+', '', text)
    
    # Eliminar caracteres especiales excesivos (mantener puntuación básica)
    text = re.sub(r'[^\w\s.,;:!?¿¡\-áéíóúñüÁÉÍÓÚÑÜ]', ' ', text)
    
    # Normalizar espacios múltiples
    text = re.sub(r'\s+', ' ', text)
    
    # Normalizar saltos de línea excesivos
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Eliminar espacios al inicio y final
    text = text.strip()

    # Mirar a ver si se pueden quitar los stopwords
    
    return text


def split_into_chunks(text: str, chunk_size: int = None, overlap: int = None) -> List[str]:
    """
    Divide el texto en chunks de tamaño aproximado.
    
    Args:
        text: Texto a dividir
        chunk_size: Tamaño del chunk en palabras (None = usar config)
        overlap: Número de palabras de solapamiento entre chunks (None = usar config)
        
    Returns:
        Lista de chunks
    """
    # Importar config solo si no se proporcionan parámetros
    if chunk_size is None or overlap is None:
        try:
            from config import CHUNK_SIZE, CHUNK_OVERLAP
            chunk_size = chunk_size or int(CHUNK_SIZE)
            overlap = overlap or int(CHUNK_OVERLAP)
        except ImportError:
            # Fallback a valores por defecto si no hay config
            chunk_size = chunk_size or 200
            overlap = overlap or 100
    
    if not text:
        return []
    
    # Dividir en palabras
    words = text.split()
    
    if len(words) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(words):
        # Tomar chunk_size palabras
        end = start + chunk_size
        chunk_words = words[start:end]
        
        # Unir palabras en texto
        chunk_text = ' '.join(chunk_words)
        chunks.append(chunk_text)
        
        # Avanzar con overlap
        start = end - overlap
        
        # Si quedan menos palabras que el overlap, tomar el resto
        if start + chunk_size >= len(words) and end < len(words):
            start = len(words) - chunk_size if len(words) > chunk_size else 0
    
    return chunks

def split_into_sentences(text: str) -> List[str]:
    """
    Divide el texto en oraciones (útil para análisis más fino).
    
    Args:
        text: Texto a dividir
        
    Returns:
        Lista de oraciones
    """
    # Patrón simple para dividir en oraciones
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]


def get_text_stats(text: str) -> dict:
    """
    Obtiene estadísticas del texto.
    
    Args:
        text: Texto a analizar
        
    Returns:
        Diccionario con estadísticas
    """
    words = text.split()
    sentences = split_into_sentences(text)
    
    return {
        "num_characters": len(text),
        "num_words": len(words),
        "num_sentences": len(sentences),
        "avg_word_length": sum(len(w) for w in words) / len(words) if words else 0,
        "avg_sentence_length": len(words) / len(sentences) if sentences else 0
    }