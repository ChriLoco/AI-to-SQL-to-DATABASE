from pydantic import BaseModel, Field

SYSTEM_QUERY_PROMPT = """You are a virtual assistant expert in Postgres databases. Below, I will provide you with the DDL Schema of a database and some pairs of correctly generated requests and queries.  
You must generate syntactically correct SQL code corresponding to the request, returning ONLY the generated query and nothing else.  

- This is the DDL Schema:  

{ddl_schema}  

- These are pairs of question-correct query:  

{previous_cases}  

"""

USER_QUERY_PROMPT = """  
- Transform the following question into an SQL query to be executed on a Postgres database. Give me only the query without any additional text:  

"{question}"  

This is the JSON schema to follow:  
{schema}  

"""

class QuerySQL(BaseModel):
    """
    This object contains the schema for the SQL selection query to be executed on the Postgres database.
    """

    query: str = Field(..., description="SQL selection query to be executed on the Postgres database")

# I suggest you to put all in the same dir

YOUR_PATH_TO_CONFIG="Insert your path to config.json here" 
YOUR_PATH_TO_CHROMADB="Insert your path to chromadb here"
URL_OF_LLM_INSTANCE="Insert your path to llm here" #es. http://0.0.0.0:8080 if you have it locally on 8080

###########################################################
# DONT FORGET POSTGRES CONNECTION STRING INTO config.json #
###########################################################