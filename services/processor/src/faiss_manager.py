"""
Gestor de índice FAISS para búsqueda semántica
"""
import os
import pickle
import numpy as np
import faiss
from typing import List, Dict, Optional, Tuple
from sentence_transformers import SentenceTransformer

from config import (
    EMBEDDING_MODEL,
    FAISS_INDEX_DIR,
    FAISS_INDEX_FILE,
    FAISS_METADATA_FILE
)


class FAISSManager:
    """
    Gestiona el índice FAISS y los embeddings
    """
    
    def __init__(self):
        """
        Inicializa el gestor de FAISS
        """
        self.model = None
        self.index = None
        self.metadata = []
        self.dimension = None
        
        # Crear directorio si no existe
        os.makedirs(FAISS_INDEX_DIR, exist_ok=True)
        
        # Cargar modelo de embeddings
        print(f"🧠 Cargando modelo de embeddings: {EMBEDDING_MODEL}")
        self.model = SentenceTransformer(EMBEDDING_MODEL)
        self.dimension = self.model.get_sentence_embedding_dimension()
        print(f"   ✅ Modelo cargado (dimensión: {self.dimension})")
        
        # Cargar o crear índice
        self._load_or_create_index()
    
    def _load_or_create_index(self):
        """
        Carga el índice existente o crea uno nuevo
        """
        index_path = os.path.join(FAISS_INDEX_DIR, FAISS_INDEX_FILE)
        metadata_path = os.path.join(FAISS_INDEX_DIR, FAISS_METADATA_FILE)
        
        if os.path.exists(index_path) and os.path.exists(metadata_path):
            print(f"📂 Cargando índice FAISS existente desde {index_path}")
            self.index = faiss.read_index(index_path)
            
            with open(metadata_path, 'rb') as f:
                self.metadata = pickle.load(f)
            
            print(f"   ✅ Índice cargado: {self.index.ntotal} vectores")
        else:
            print(f"🆕 Creando nuevo índice FAISS")
            # Usar IndexFlatL2 para búsqueda exacta (mejor para datasets pequeños)
            # Para datasets grandes, considerar IndexIVFFlat o IndexHNSWFlat
            self.index = faiss.IndexFlatL2(self.dimension)
            self.metadata = []
            print(f"   ✅ Nuevo índice creado")
    
    def add_texts(self, texts: List[str], metadata_list: List[Dict]):
        """
        Añade textos al índice FAISS
        
        Args:
            texts: Lista de textos a indexar
            metadata_list: Lista de metadatos correspondientes a cada texto
        """
        if not texts:
            return
        
        if len(texts) != len(metadata_list):
            raise ValueError("texts y metadata_list deben tener la misma longitud")
        
        # Generar embeddings
        print(f"   🔢 Generando embeddings para {len(texts)} textos...")
        embeddings = self.model.encode(
            texts,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True  # Normalizar para usar cosine similarity
        )
        
        # Añadir al índice
        self.index.add(embeddings.astype('float32'))
        
        # Añadir metadata con el texto original
        for i, (text, meta) in enumerate(zip(texts, metadata_list)):
            meta_with_text = meta.copy()
            meta_with_text['text'] = text
            meta_with_text['index_position'] = self.index.ntotal - len(texts) + i
            self.metadata.append(meta_with_text)
        
        print(f"   ✅ {len(texts)} vectores añadidos al índice (total: {self.index.ntotal})")
    
    def search(
        self,
        query: str,
        k: int = 5,
        filter_empresa: Optional[str] = None
    ) -> List[Tuple[Dict, float]]:
        """
        Busca textos similares en el índice
        
        Args:
            query: Texto de consulta
            k: Número de resultados a devolver
            filter_empresa: Filtrar resultados por empresa (opcional)
            
        Returns:
            Lista de tuplas (metadata, score) ordenadas por relevancia
        """
        if self.index.ntotal == 0:
            print("⚠️  El índice está vacío")
            return []
        
        # Generar embedding de la query
        query_embedding = self.model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        
        # Buscar en FAISS (k más cercanos)
        # Para IndexFlatL2 con embeddings normalizados, menor distancia = mayor similitud
        distances, indices = self.index.search(query_embedding.astype('float32'), k * 3)  # Buscar más para filtrar
        
        # Recopilar resultados
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < len(self.metadata):
                meta = self.metadata[idx]
                
                # Aplicar filtro de empresa si se especifica
                if filter_empresa and meta.get('empresa') != filter_empresa:
                    continue
                
                # Convertir distancia L2 a similitud (1 - distancia normalizada)
                # Con embeddings normalizados, distancia L2 ~ 2 * (1 - cosine_sim)
                similarity = 1 - (dist / 2)
                
                results.append((meta, float(similarity)))
                
                if len(results) >= k:
                    break
        
        return results
    
    def search_by_report_id(self, report_id: int, k: int = 10) -> List[Tuple[Dict, float]]:
        """
        Obtiene todos los chunks de un reporte específico
        
        Args:
            report_id: ID del reporte
            k: Número máximo de chunks a devolver
            
        Returns:
            Lista de tuplas (metadata, score) del reporte
        """
        results = []
        for i, meta in enumerate(self.metadata):
            if meta.get('report_id') == report_id:
                results.append((meta, 1.0))  # Score máximo para chunks del mismo reporte
        
        # Ordenar por chunk_index
        results.sort(key=lambda x: x[0].get('chunk_index', 0))
        
        return results[:k]
    
    def get_all_empresas(self) -> List[str]:
        """
        Obtiene lista única de empresas en el índice
        
        Returns:
            Lista de nombres de empresas
        """
        empresas = set()
        for meta in self.metadata:
            if 'empresa' in meta:
                empresas.add(meta['empresa'])
        return sorted(list(empresas))
    
    def save(self):
        """
        Guarda el índice y metadata en disco
        """
        index_path = os.path.join(FAISS_INDEX_DIR, FAISS_INDEX_FILE)
        metadata_path = os.path.join(FAISS_INDEX_DIR, FAISS_METADATA_FILE)
        
        # Guardar índice FAISS
        faiss.write_index(self.index, index_path)
        
        # Guardar metadata
        with open(metadata_path, 'wb') as f:
            pickle.dump(self.metadata, f)
        
        print(f"   💾 Índice guardado: {self.index.ntotal} vectores")
    
    def get_stats(self) -> Dict:
        """
        Obtiene estadísticas del índice
        
        Returns:
            Diccionario con estadísticas
        """
        empresas = self.get_all_empresas()
        
        # Contar chunks por empresa
        chunks_por_empresa = {}
        for meta in self.metadata:
            empresa = meta.get('empresa', 'Unknown')
            chunks_por_empresa[empresa] = chunks_por_empresa.get(empresa, 0) + 1
        
        return {
            'total_vectors': self.index.ntotal,
            'dimension': self.dimension,
            'num_empresas': len(empresas),
            'empresas': empresas,
            'chunks_por_empresa': chunks_por_empresa,
            'embedding_model': EMBEDDING_MODEL
        }