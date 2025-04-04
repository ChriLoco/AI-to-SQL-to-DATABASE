WHAT IS THIS
--------------------------

NATURAL LANGUAGE -> AI GENERATED QUERY SQL -> INFORMATION FROM A POSTGRES DB

You can ask for some information to an LLM that will translate that into an SQL query and bring back information taken from a Postgres Database.

More specifically this project it's a Streamlit UI that it's connected to a LLM placed into the backend.
You can ask some data in natural language and it will be retrieved from a Database. 
To achieve this i used RAG (Retrieval Augmented Generation) that takes DDL schemas of the database, previous query-solutions (validated by the user) and the user prompt inserted by user into a chat like widget.

At first complex query may fail but then the users corrects them and inserts them back into a knowledge base automatically --> second time you ask that query it will work



WHY THIS
--------------------------
I think it's a very cool and wide adaptable solution. In the early GENAI era (last year) some people based entire company on this. Nowadays it can be used as a tool for an Agent or more generally as a step of
a more complex RAG pipeline

Fork it, leave a star pls ⭐. You can modify it, steal it, love it, hate, got it.

HOW TO USE THIS FAST
-------------------------

Modify settings paths and run the main.py with the 
  streamlit main.py
