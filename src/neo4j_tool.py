from langchain_core.prompts import ChatPromptTemplate
from .llm_client import get_llm
from .neo4j_client import neo4j_client

# Prompt template for converting a question into a Cypher query
CYPHER_GENERATION_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
You are an expert Neo4j developer and Cypher query writer.
Your task is to convert a user's natural language question into a Cypher query based on the provided Neo4j graph schema.
Only return the Cypher query, with no additional text, explanation, or preamble.

Here is the schema of the graph:
{schema}
""",
        ),
        (
            "human",
            "Question: {question}",
        ),
    ]
)

def generate_cypher_query(question: str, schema: dict) -> str:
    """
    Uses an LLM to generate a Cypher query from a natural language question and the graph schema.
    """
    llm = get_llm()
    chain = CYPHER_GENERATION_PROMPT | llm

    # The schema dictionary needs to be converted to a string for the prompt
    schema_str = f"Node Labels: {schema['node_labels']}\nRelationship Types: {schema['relationship_types']}"

    cypher_query = chain.invoke({"question": question, "schema": schema_str})
    return cypher_query.strip()

def execute_cypher_query(query: str) -> list:
    """
    Executes a Cypher query against the Neo4j database.
    """
    with neo4j_client._driver.session() as session:
        result = session.run(query)
        # Convert the result to a list of dictionaries for easier processing
        return [r.data() for r in result]

def query_knowledge_graph(question: str) -> dict:
    """
    The main tool function that the agent will call.
    It takes a natural language question, generates a Cypher query,
    executes it, and returns the result.
    """
    print(f"--- Querying Knowledge Graph for: '{question}' ---")

    # 1. Get the graph schema
    try:
        schema = neo4j_client.get_schema()
        if not schema.get("node_labels") and not schema.get("relationship_types"):
            return {"error": "The knowledge graph is empty. Please run the indexing script first."}
    except Exception as e:
        return {"error": f"Failed to connect to Neo4j or get schema: {e}"}

    # 2. Generate the Cypher query
    print("Generating Cypher query...")
    cypher_query = generate_cypher_query(question, schema)
    print(f"  > Generated Query: {cypher_query}")

    # 3. Execute the query
    print("Executing query...")
    try:
        result = execute_cypher_query(cypher_query)
        print(f"  > Query returned {len(result)} results.")
        return {"result": result}
    except Exception as e:
        print(f"  > Error executing Cypher query: {e}")
        return {"error": f"Failed to execute the generated Cypher query: {e}"}
