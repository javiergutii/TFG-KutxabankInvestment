# check_chunks.py - actualiza con esto
import pickle

with open('/app/shared/faiss_index/metadata.pkl', 'rb') as f:
    meta = pickle.load(f)

for m in meta:
    t = m.get('text', '')
    if 'revenue reached' in t.lower() or '9 billion' in t.lower():
        print(f"Chunk {m.get('chunk_index')}: {t}")
        print('---')