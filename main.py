import streamlit as st
from utils import *
from chromadb.utils import embedding_functions
import json
import asyncio
from chromadb.config import Settings
from chromadb import PersistentClient
import io
import time
from pygwalker.api.streamlit import StreamlitRenderer

st.set_page_config(
    page_title="AI->SQL->DATABASE",
    layout="wide"
)

with open(f'{YOUR_PATH_TO_CONFIG}', 'r') as file:
    config = json.load(file)

def get_model_client():
    return OpenAIModel(base_url=f"{URL_OF_LLM_INSTANCE}", temperature=0.5, max_new_tokens=1024)

@st.cache_resource
def get_model_emb():
    return embedding_functions.SentenceTransformerEmbeddingFunction('/home/srv_user/.cache/torch/sentence_transformers/BAAI_bge-m3')

if "client" not in st.session_state:
    st.session_state.client = get_model_client()

if "emb_model" not in st.session_state:
    st.session_state.emb_model = get_model_emb()

if "messages" not in st.session_state:
    st.session_state.messages = []

if "user_input" not in st.session_state:
    st.session_state.user_input = None

if 'is_correct' not in st.session_state:
    st.session_state.is_correct=None

if "query" not in st.session_state:
    st.session_state.query = None
    st.session_state.prompt = None

if 'button' not in st.session_state:
    st.session_state.button = False
    st.session_state.button_name = "Modify the query"

if "button_name" not in st.session_state:
    st.session_state.button_name = "Modify the query"

if 'button_disabled' not in st.session_state:
    st.session_state.button_disabled = False

def disable_buttons():
    st.session_state.button_disabled = True

if "prompt" not in st.session_state:
    st.session_state.prompt = None

if "dataframe" not in st.session_state:
    st.session_state.dataframe = None

if "add_to_rag" not in st.session_state:
    st.session_state.add_to_rag = True

if "vector_db" not in st.session_state:
    st.session_state.session_col_name='demo'
    st.session_state.vector_db = PersistentClient(path='/home/srv_user/ai_doc/testChri/chromadb', settings=Settings(anonymized_telemetry=False))

if "collection" not in st.session_state:
    st.session_state.collection = st.session_state.vector_db.get_or_create_collection(name=st.session_state.session_col_name,embedding_function=st.session_state.emb_model)

if "call_db" not in st.session_state:
    st.session_state.call_db=True
    
if "ddl_schema" not in st.session_state: #fare un db vett per i ddl_schema?
    st.session_state.ddl_print, st.session_state.ddl_schema =infer_schema(config['POSTGRES']['database_url'])


def get_pyg_renderer() -> "StreamlitRenderer":
    return StreamlitRenderer(st.session_state.dataframe)
    
for message in st.session_state.messages:
    if message['role']=='user' or message['role']=='assistant':
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    else:
        with st.status("Sending request..."):
            st.write(message["content"])

if "prompt" not in st.session_state or st.session_state.prompt==None:
    st.session_state.prompt = st.chat_input("Write something...")

if st.session_state.prompt != 'JUMP' and st.session_state.prompt != None :
    with st.chat_message("user"):
        st.markdown(st.session_state.prompt)
    st.session_state.user_input=st.session_state.prompt
    #st.session_state.messages.append({"role": "user", "content": st.session_state.prompt})
    with st.status("Sending request..."):
        if st.session_state.query==None: 
            previous_queries = query_collection(collection=st.session_state.collection, search=st.session_state.prompt, limit=2)
            st.write("Sending message...")
            messages = return_prompt(system_p= SYSTEM_QUERY_PROMPT, user_p=USER_QUERY_PROMPT, ddl_schema=st.session_state.ddl_schema, previous_cases=previous_queries , question=st.session_state.prompt, schema= QuerySQL)
            st.write(messages)
            assert (st.session_state.client.tokenizer_count(SYSTEM_QUERY_PROMPT) +  st.session_state.client.tokenizer_count(USER_QUERY_PROMPT)) < 7000
            query = st.session_state.client(messages, schema=QuerySQL, is_json=True)[0]

            query = json.loads(query)["query"]

            st.session_state.query=query
            st.session_state.messages.append({"role": "status", "content": messages})

if st.session_state.prompt != None:
    with st.chat_message("assistant"):

        if isinstance(st.session_state.query, str):
            st.session_state.query = io.StringIO(st.session_state.query)

        response = st.write_stream(st.session_state.query) 
        print(response)

        if 'DELETE' in response or 'CREATE' in response or 'DROP' in response:
            st.error("DO NOT ASK THE DB TO CREATE OR DELETE ANYTHING, reloading the page")
            time.sleep(3)
            st.session_state.query = None
            st.session_state.messages = []
            st.session_state.dataframe = None
            st.session_state.user_input = None
            st.session_state.dataframe = None
            st.session_state.prompt = None
            st.session_state.add_to_rag=True
            st.session_state.button_disabled=False
            st.session_state.call_db=False
            st.rerun()
        
        if st.session_state.call_db==True:

            try:
                df= asyncio.run(query_PostgresDB(response))

                st.session_state.dataframe=df
                st.text(f"Totale number of rows found: {df.shape[0]}")
                st.data_editor(
                    df,
                    hide_index=True,
                    num_rows="fixed",
                    width=1000
                )

                info_str = "\n".join([f"{col}: {dtype}" for col, dtype in df.dtypes.items()])
                st.write(info_str)
                
                st.session_state.call_db=False
            except:
                st.error("Ops execution failed, reloading the page")
                time.sleep(3)
                st.session_state.query = None
                st.session_state.messages = []
                st.session_state.dataframe = None
                st.session_state.user_input = None
                st.session_state.dataframe = None
                st.session_state.prompt = None
                st.session_state.add_to_rag=True
                st.session_state.button_disabled=False
                st.session_state.call_db=False
                if 'is_correct' in st.session_state:
                    st.session_state.pop('is_correct')
                st.rerun()
                

        st.session_state.query=response

if st.session_state.query!= None:

    st.write("SQL code is correct?")

    if st.button('YES', type="primary", disabled=st.session_state.button_disabled):
        st.session_state.is_correct = 'yes'
        disable_buttons()
        st.session_state.call_db=False
        st.rerun()
        
    if st.button('NO', type="primary", disabled=st.session_state.button_disabled):
        st.session_state.is_correct = 'no'
        disable_buttons()
        st.session_state.call_db=False
        st.rerun()

    if st.session_state.is_correct=='yes':
        #st.write('YES')
        
        st.write('Aggiunto alla collection...')

        #st.write(f"DOMANDA: {st.session_state.user_input} \n\n RISPOSTA: {st.session_state.query}")
        
        if st.session_state.add_to_rag==True:
            try:
                add_to_collection(st.session_state.collection, { 'question': st.session_state.user_input ,'answer': {'sql': st.session_state.query } })
                st.session_state.add_to_rag=False
            except:
                st.session_state.vector_db.get_or_create_collection(name=st.session_state.session_col_name)
                add_to_collection(st.session_state.collection, { 'question': st.session_state.user_input ,'answer': {'sql': st.session_state.query } })
                st.session_state.add_to_rag=False

        if st.button('Grafic editor', type="primary"):
            st.write('Loading grafic editor...')  
            renderer = get_pyg_renderer()
            renderer.explorer()

                

    elif st.session_state.is_correct=='no':
        #st.write('NO')

        st.session_state.messages=[]

        st.text_area("Modifica la query",
                                     st.session_state.query,
                                     key="textarea", height=50)
        
        col21, col22 = st.columns([0.5, 0.5])

        with col21:
           if st.button(st.session_state.button_name, type="primary"):
                if st.session_state.button_name == "Modifica la query":
                    st.session_state.button_name = "Esegui la nuova query"
                else:
                    st.session_state.query = st.session_state.textarea
                    st.session_state.button_name = "Modifica la query"
                    #st.session_state.messages = []
                    st.session_state.dataframe = None
                    st.session_state.prompt = 'JUMP'
                    st.session_state.call_db=True
                    st.session_state.button_disabled=False
                    st.session_state.add_to_rag=True
                    if 'is_correct' in st.session_state:
                        st.session_state.pop('is_correct')
                    st.rerun()
                st.session_state.button = not st.session_state.button
                st.rerun()
                
    if st.button('Resetta chat '):
        st.session_state.query = None
        st.session_state.messages = []
        st.session_state.dataframe = None
        st.session_state.user_input = None
        st.session_state.dataframe = None
        st.session_state.prompt = None
        st.session_state.add_to_rag=True
        st.session_state.button_disabled=False
        st.session_state.call_db=True
        if 'is_correct' in st.session_state:
            st.session_state.pop('is_correct')
        st.rerun()

with st.sidebar:

    if st.button('Resetta chat'):
        st.session_state.query = None
        st.session_state.messages = []
        st.session_state.dataframe = None
        st.session_state.user_input = None
        st.session_state.dataframe = None
        st.session_state.prompt = None
        st.session_state.add_to_rag=True
        st.session_state.button_disabled=False
        st.session_state.call_db=False
        if 'is_correct' in st.session_state:
            st.session_state.pop('is_correct')
        st.rerun()

    st.divider()
    st.write("DATABASE STRUCTURE ")
    st.divider()
    st.markdown(st.session_state.ddl_print)
    st.divider()


    if st.button('🆘Reset collection'):
        try:
            st.session_state.vector_db.delete_collection(name=st.session_state.session_col_name)
            st.session_state.pop("collection")
            time.sleep(1)
            if 'is_correct' in st.session_state:
                st.session_state.pop('is_correct')
            st.write('RESET')
        except:
            st.write('Collection is empty already') #you get this only if you keep spamming the button
            pass
        st.rerun()  


        
               







































    





            
                   
                



        
        

