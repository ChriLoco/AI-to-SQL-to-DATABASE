from pydantic import BaseModel
from typing import Optional
import openai
import json
import requests
import json
from settings import *
import asyncpg
import pandas as pd
from uuid import uuid4
from sqlalchemy import create_engine, MetaData, Table


with open(f'{YOUR_PATH_TO_CONFIG}', 'r') as file:
    config = json.load(file)

class OpenAIModel:
    def __init__(self, base_url: str,
                 model_name: str = "llama-3", openai_key: str = "sk-xxx",
                 max_new_tokens: int = 1024,
                 temperature: float = 0.1,
                 frequency_penalty: float = 1.2):

        self._client = openai.OpenAI(
            api_key=openai_key,
            base_url=base_url + "/v1/"
        )

        self._base_url = base_url
        self._model_name = model_name
        self._max_new_tokens = max_new_tokens
        self._temperature = temperature
        self._frequency_penalty = frequency_penalty
    
    def tokenizer(self, msg) -> list[int]:
        r = requests.post(self._base_url + "/extras/tokenize", 
                          headers = {'Content-type': 'application/json'}, 
                          data=json.dumps({"input":msg}))
        r.raise_for_status()
        r = r.json()
        return r["tokens"]
    
    def tokenizer_count(self, msg) -> int:
        r = requests.post(self._base_url + "/extras/tokenize/count", 
                          headers = {'Content-type': 'application/json'}, 
                          data=json.dumps({"input":msg}))
        r.raise_for_status()
        r = r.json()
        return r["count"]
    
    def __call__(self, msg: list[dict], is_json: bool = False, schema: Optional[BaseModel] = None ) -> str:
        if is_json:
            response_format = { "type": "json_object" }
            if schema is not None:
                response_format["schema"] = schema.model_json_schema()
            response = self._client.chat.completions.create(
                response_format=response_format,
                model=self._model_name,
                messages=msg,
                max_tokens=self._max_new_tokens,
                temperature=self._temperature,
                frequency_penalty=self._frequency_penalty
            )
        else:
            response = self._client.chat.completions.create(
                model=self._model_name,
                messages=msg,
                max_tokens=self._max_new_tokens,
                temperature=self._temperature,
                frequency_penalty=self._frequency_penalty
            )
        return response.choices[0].message.content, response.usage
    
    def stream(self, msg: list[dict]):
        return self._client.chat.completions.create(
                model=self._model_name,
                messages=msg,
                max_tokens=self._max_new_tokens,
                temperature=self._temperature,
                frequency_penalty=self._frequency_penalty,
                stream=True
        )

    
def add_to_collection(collection, document: dict): #previous_cases is list of dict (with 1st element question e 2nd element answer con dentro sql)
    #if collection does not exists does nothing
    collection.add(
        documents=[document['question']],
        metadatas=[document['answer']],         #i had to put sql into metadatas {} so i can do cosine similarity just on the question
        ids=[str(uuid4())]
    )      
    

def query_collection(collection, search, limit: int = 2):

    try: 
        if collection.count()>0:
            results = collection.query(
                query_texts=[search],
                n_results=limit if limit < collection.count() else collection.count(),
                include= ["documents", "metadatas"],
            )

            i=0
            res = ""
            for prev_question, prev_answer in zip(results["documents"][0], results["metadatas"][0]):
                i=i+1
                res += f"Esempio n°{i}: \n'''\nQuestion: {prev_question} \n\nAnswer: {prev_answer['sql']}\n''' \n\n"

            return res
        else:
            return ''
    except:
        return ''

def return_prompt(system_p: str, user_p: str, ddl_schema:str, previous_cases:str , question : str, schema : QuerySQL ):

    schema = json.dumps(schema.model_json_schema())

    system_p = system_p.format(ddl_schema=ddl_schema, previous_cases=previous_cases)
    user_p = user_p.format(question=question,schema=schema).replace("{", "{{").replace("}", "}}") 

    msg = [{"role": "system","content": system_p},
           {"role": "user", "content": user_p}]       
    return msg

def toQuery(collection_qa, client, ddl_schema, input_query): #collection will have question and answers, but semantic will be just about answers
        n_vectordb_qa=2   # previous pair q&a stored
        #Retrieves q&a couples based on the query 
        results = collection_qa.query(
                query_texts=[input_query],
                n_results= n_vectordb_qa if n_vectordb_qa < collection_qa.count() else collection_qa.count()
            )
        
        previous_queries = results["documents"][0]   # devo prendere coppie domanda-query

        msg_check = return_prompt(SYSTEM_QUERY_PROMPT, USER_QUERY_PROMPT, ddl_schema , previous_queries, input_query)
        
        json_llm, _ = client(msg=msg_check)
        
        return json_llm

async def query_PostgresDB(query: str):
    conn = await asyncpg.connect(config['POSTGRES']['database_url'])
    print("Connessione al database avvenuta con successo!")

    try:
        stream = await conn.fetch(query)
        records = [dict(record) for record in stream]
        df = pd.DataFrame(records)
        return df
    finally:
        await conn.close()
        print("Connessione chiusa.")

def infer_schema(db_url):
    # Create an engine connected to postgres db
    engine = create_engine(db_url)

    metadata = MetaData()
    metadata.reflect(bind=engine)

    definizioni_tabelle = []
    table_to_print= []
    # Get all the tables
    for table_name in metadata.tables.keys():
        table = Table(table_name, metadata, autoload_with=engine)

        create_table_str = f"CREATE TABLE {table_name} ("
        table_to_show= f"TABLE {table_name} ("
        columns = table.columns

        # Itarate on columns and add definition to sting create_table_str
        for column in columns:
            create_table_str += f"\n\t{column.name} {column.type},"
            table_to_show += f"\n\t{column.name},"

        create_table_str = create_table_str.rstrip(',') + "\n);"
        table_to_show = table_to_show.rstrip(',') + "\n);"
        definizioni_tabelle.append(create_table_str)
        table_to_print.append(table_to_show)

    # Concatenate all tables definitions into a single string
    definizioni_complete = "\n\n".join(definizioni_tabelle)
    table_to_print = "\n\n".join(table_to_print)
    # Return string with definition from tables
    return table_to_print, definizioni_complete




