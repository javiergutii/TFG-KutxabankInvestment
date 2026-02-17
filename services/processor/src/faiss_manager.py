"""
Gestor de índice FAISS con búsqueda híbrida (semántica + keyword)
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

    def __init__(self):
        self.model = None
        self.index = None
        self.metadata = []
        self.dimension = None

        os.makedirs(FAISS_INDEX_DIR, exist_ok=True)

        print(f"🧠 Cargando modelo de embeddings: {EMBEDDING_MODEL}")
        self.model = SentenceTransformer(EMBEDDING_MODEL)
        self.dimension = self.model.get_sentence_embedding_dimension()
        print(f"   ✅ Modelo cargado (dimensión: {self.dimension})")

        self._load_or_create_index()

    def _load_or_create_index(self):
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
            self.index = faiss.IndexFlatL2(self.dimension)
            self.metadata = []
            print(f"   ✅ Nuevo índice creado")

    def add_texts(self, texts: List[str], metadata_list: List[Dict]):
        if not texts:
            return

        if len(texts) != len(metadata_list):
            raise ValueError("texts y metadata_list deben tener la misma longitud")

        print(f"   🔢 Generando embeddings para {len(texts)} textos...")
        embeddings = self.model.encode(
            texts,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True
        )

        self.index.add(embeddings.astype('float32'))

        for i, (text, meta) in enumerate(zip(texts, metadata_list)):
            meta_with_text = meta.copy()
            meta_with_text['text'] = text
            meta_with_text['index_position'] = self.index.ntotal - len(texts) + i
            self.metadata.append(meta_with_text)

        print(f"   ✅ {len(texts)} vectores añadidos al índice (total: {self.index.ntotal})")

    def _keyword_search(self, query: str, k: int = 10) -> List[Tuple[Dict, float]]:
        """
        Búsqueda por palabras clave exactas en el texto de los chunks.
        Devuelve chunks que contienen alguna de las palabras de la query.
        Score = proporción de palabras encontradas (1.0 = todas presentes).
        """
        # Extraer palabras significativas de la query (>3 letras)
        query_words = [
            w.lower() for w in query.split()
            if len(w) > 3
        ]

        if not query_words:
            return []

        results = []
        for meta in self.metadata:
            text_lower = meta.get('text', '').lower()
            # Contar cuántas palabras de la query aparecen en el chunk
            matches = sum(1 for w in query_words if w in text_lower)
            if matches > 0:
                score = matches / len(query_words)  # Score 0-1
                results.append((meta, score))

        # Ordenar por score descendente
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:k]

    def search(
        self,
        query: str,
        k: int = 10,
        filter_empresa: Optional[str] = None
    ) -> List[Tuple[Dict, float]]:
        """
        Búsqueda híbrida: combina resultados semánticos (FAISS) y keyword.
        Los resultados de keyword se priorizan cuando hay coincidencias exactas.
        """
        if self.index.ntotal == 0:
            print("⚠️  El índice está vacío")
            return []

        # --- 1. Búsqueda semántica con FAISS ---
        query_embedding = self.model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        distances, indices = self.index.search(
            query_embedding.astype('float32'), min(k * 3, self.index.ntotal)
        )

        semantic_results = {}
        for dist, idx in zip(distances[0], indices[0]):
            if idx < len(self.metadata):
                meta = self.metadata[idx]
                if filter_empresa and meta.get('empresa') != filter_empresa:
                    continue
                similarity = 1 - (dist / 2)
                pos = meta.get('index_position', idx)
                semantic_results[pos] = (meta, similarity)

        # --- 2. Búsqueda por keyword ---
        keyword_results = {}
        for meta, score in self._keyword_search(query, k=k * 2):
            if filter_empresa and meta.get('empresa') != filter_empresa:
                continue
            pos = meta.get('index_position', 0)
            # Boost: los keyword matches tienen score alto (0.9 mínimo)
            keyword_results[pos] = (meta, 0.9 + score * 0.1)

        # --- 3. Combinar: keyword tiene prioridad, luego semántico ---
        combined = {}

        # Añadir semánticos primero
        for pos, (meta, score) in semantic_results.items():
            combined[pos] = (meta, score)

        # Los keyword sobreescriben con score más alto
        for pos, (meta, score) in keyword_results.items():
            combined[pos] = (meta, score)

        # Ordenar por score descendente y devolver top k
        final = sorted(combined.values(), key=lambda x: x[1], reverse=True)
        return final[:k]

    def save(self):
        index_path = os.path.join(FAISS_INDEX_DIR, FAISS_INDEX_FILE)
        metadata_path = os.path.join(FAISS_INDEX_DIR, FAISS_METADATA_FILE)

        faiss.write_index(self.index, index_path)
        with open(metadata_path, 'wb') as f:
            pickle.dump(self.metadata, f)

        print(f"   💾 Índice guardado: {self.index.ntotal} vectores")

    def get_stats(self) -> Dict:
        empresas = set(m.get('empresa', 'Unknown') for m in self.metadata)
        chunks_por_empresa = {}
        for meta in self.metadata:
            empresa = meta.get('empresa', 'Unknown')
            chunks_por_empresa[empresa] = chunks_por_empresa.get(empresa, 0) + 1

        return {
            'total_vectors': self.index.ntotal,
            'dimension': self.dimension,
            'num_empresas': len(empresas),
            'empresas': sorted(list(empresas)),
            'chunks_por_empresa': chunks_por_empresa,
            'embedding_model': EMBEDDING_MODEL
        }

    def get_all_empresas(self) -> List[str]:
        return sorted(set(m.get('empresa', '') for m in self.metadata if m.get('empresa')))