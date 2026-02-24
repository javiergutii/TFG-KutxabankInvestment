import pickle
with open('/app/shared/faiss_index/metadata.pkl', 'rb') as f:
    meta = pickle.load(f)

telefonica = [m for m in meta if m.get('empresa') == 'Telefónica']
print('Total chunks Telefónica:', len(telefonica))
print()

for m in telefonica:
    if 'ebitda' in m.get('text', '').lower() and '3 billion' in m.get('text', '').lower():
        print('ENCONTRADO chunk', m.get('chunk_index'), ':')
        print(m.get('text')[:300])
        print('---')
