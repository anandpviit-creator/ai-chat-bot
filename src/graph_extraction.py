from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from .llm_client import get_llm

# Pydantic models to define the structure of the extracted graph
class Node(BaseModel):
    id: str = Field(description="Unique identifier for the node (e.g., page title, person's name).")
    type: str = Field(description="Type of the node (e.g., 'Page', 'Person', 'Project').")
    properties: Dict = Field(default_factory=dict, description="Additional properties of the node.")

class Relationship(BaseModel):
    source: str = Field(description="The id of the source node.")
    target: str = Field(description="The id of the target node.")
    type: str = Field(description="The type of the relationship (e.g., 'LINKS_TO', 'MENTIONS').")
    properties: Dict = Field(default_factory=dict, description="Additional properties of the relationship.")

class ExtractedGraph(BaseModel):
    nodes: List[Node]
    relationships: List[Relationship]

# The prompt for the LLM to extract the graph
EXTRACTION_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
You are an expert at extracting information from documents to build a knowledge graph.
Your task is to identify entities and the relationships between them from the provided text.
The entities should be one of the following types: 'Page', 'Person', 'Project', 'Technology', or 'Date'.
The relationships should be one of the following types: 'LINKS_TO', 'MENTIONS', 'WORKS_ON', 'USES'.

Analyze the text and respond with ONLY a valid JSON object containing two keys: "nodes" and "relationships".
The "nodes" key should contain a list of all identified entities.
The "relationships" key should contain a list of all identified relationships between those entities.
Ensure the 'id' of each node is a simple, descriptive name (e.g., 'Project Phoenix', 'Jules the Engineer').
The 'source' and 'target' of a relationship must match the 'id' of a node in the 'nodes' list.
Do not include any nodes or relationships that are not explicitly mentioned in the text.
""",
        ),
        (
            "human",
            "Here is the text to analyze:\n\n---\n\n{text_chunk}",
        ),
    ]
)

def extract_graph_from_text(text: str) -> Optional[ExtractedGraph]:
    """
    Uses an LLM to extract a knowledge graph (nodes and relationships) from a chunk of text.
    """
    if not text or not text.strip():
        return None

    llm = get_llm()

    # Use the with_structured_output method to get a guaranteed Pydantic object
    chain = EXTRACTION_PROMPT | llm.with_structured_output(ExtractedGraph)

    try:
        graph = chain.invoke({"text_chunk": text})
        return graph
    except Exception as e:
        print(f"Error during graph extraction from text: {e}")
        # This could happen if the LLM output is not valid JSON or doesn't match the Pydantic model.
        return None
