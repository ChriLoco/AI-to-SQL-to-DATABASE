from chromadb.config import Settings
from chromadb import PersistentClient
from chromadb.utils import embedding_functions
from settings import *

#with open('/{YOUR_PATH}/config.json', 'r') as file:
#    config = json.load(file)

collection_name='demo'
    
client = PersistentClient(path='/home/srv_user/ai_doc/chromadb2',
                              settings=Settings(anonymized_telemetry=False))

# Function to cancel ocllection
def delete_collection(client, collection_name):
    try:
        client.delete_collection(name=collection_name)
        print(f"Collection '{collection_name}' eliminata con successo.")
    except Exception as e:
        print(f"Errore nell'eliminazione della collection '{collection_name}': {e}")

# delete collection if exists
delete_collection(client, collection_name)

#client.clear_system_cache()

#create a new collection
collection = client.get_or_create_collection(name=collection_name, embedding_function= embedding_functions.SentenceTransformerEmbeddingFunction('/home/srv_user/.cache/torch/sentence_transformers/BAAI_bge-m3'))

existing_count = collection.count()

print(collection.count())




