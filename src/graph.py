import operator
from typing import TypedDict, Annotated, List, Dict
from langchain_core.prompts import PromptTemplate
from langgraph.graph import StateGraph, END, START
from .config import settings
from .llm_client import get_llm
from .search_clients import opensearch_client, vector_store
from .schemas import SearchResult

# Define the state for our graph
from langchain_core.messages import BaseMessage

class GraphState(TypedDict):
    query: str
    available_spaces: List[str]
    classified_space_key: str
    keyword_results: List[Dict]
    vector_results: List[Dict]
    documents: List[Dict]
    generation: str
    chat_history: List[BaseMessage]

# --- Nodes ---

def classify_query_node(state: GraphState) -> dict:
    """
    Uses the LLM to classify the user's query and determine the most relevant Confluence space.
    """
    query = state["query"]
    available_spaces = state["available_spaces"]

    prompt_template = """
    You are an expert at routing user questions to the correct Confluence knowledge base space.
    Based on the user's query, select the single most relevant space from the following list.
    Return ONLY the key of the selected space, and nothing else.

    Available Spaces:
    {spaces}

    User Query:
    "{query}"

    Selected Space Key:
    """

    prompt = PromptTemplate(
        template=prompt_template,
        input_variables=["spaces", "query"]
    )

    llm = get_llm()
    chain = prompt | llm

    # Format the spaces for the prompt
    spaces_str = "\n".join([f"- {s}" for s in available_spaces])

    # Invoke the chain and clean up the response
    classified_space = chain.invoke({"spaces": spaces_str, "query": query}).strip()

    # Basic validation to ensure the LLM returned a valid space
    if classified_space not in available_spaces:
        # Fallback to the first available space if classification fails
        print(f"Warning: Classified space '{classified_space}' is not in the available list. Falling back.")
        classified_space = available_spaces[0] if available_spaces else ""

    print(f"Query classified to space: {classified_space}")
    return {"classified_space_key": classified_space}


def keyword_search_node(state: GraphState) -> dict:
    """Performs keyword search using OpenSearch, filtered by the classified space key."""
    query = state["query"]
    space_key = state["classified_space_key"]

    search_query = {
        "query": {
            "bool": {
                "must": {
                    "multi_match": {
                        "query": query,
                        "fields": ["title^2", "content"]
                    }
                },
                "filter": {
                    "term": {
                        "space_key": space_key
                    }
                }
            }
        }
    }
    response = opensearch_client.search(
        index=settings.OPENSEARCH_INDEX_NAME,
        body=search_query,
        size=settings.TOP_K
    )

    documents = [
        {
            "id": hit["_id"],
            "score": hit["_score"],
            "content": hit["_source"]["content"],
            "metadata": {"space_key": hit["_source"].get("space_key"), "title": hit["_source"].get("title"), "url": hit["_source"].get("url")}
        } for hit in response["hits"]["hits"]
    ]
    return {"keyword_results": documents}

def vector_search_node(state: GraphState) -> dict:
    """Performs semantic search using PGVector, filtered by the classified space key."""
    query = state["query"]
    space_key = state["classified_space_key"]

    # The filter for PGVector is a dictionary targeting the metadata
    search_filter = {"space_key": space_key}

    results = vector_store.similarity_search_with_score(
        query,
        k=settings.TOP_K,
        filter=search_filter
    )

    documents = [
        {
            "id": f"{doc.metadata.get('page_id', '')}_{doc.metadata.get('chunk_num', '')}",
            "score": 1 - score, # Invert score because lower is better for distance
            "content": doc.page_content,
            "metadata": doc.metadata
        } for doc, score in results
    ]
    return {"vector_results": documents}

def fusion_node(state: GraphState) -> dict:
    """
    Fuses results from keyword and vector search using weighted scoring.
    """
    keyword_results = state["keyword_results"]
    vector_results = state["vector_results"]

    # Normalize scores (example: min-max normalization)
    def normalize_scores(results: List[Dict]):
        scores = [r['score'] for r in results]
        min_score, max_score = min(scores) if scores else (0, 1), max(scores) if scores else (0, 1)
        if max_score == min_score:
            return [{**r, 'norm_score': 1.0} for r in results]
        return [{**r, 'norm_score': (r['score'] - min_score) / (max_score - min_score)} for r in results]

    norm_keyword_results = normalize_scores(keyword_results)
    norm_vector_results = normalize_scores(vector_results)

    # Fuse scores
    fused_scores = {}
    for res in norm_keyword_results:
        fused_scores[res['id']] = {'doc': res, 'score': res['norm_score'] * settings.HYBRID_SEARCH_ALPHA}

    for res in norm_vector_results:
        if res['id'] in fused_scores:
            fused_scores[res['id']]['score'] += res['norm_score'] * settings.HYBRID_SEARCH_BETA
        else:
            fused_scores[res['id']] = {'doc': res, 'score': res['norm_score'] * settings.HYBRID_SEARCH_BETA}

    # Sort by fused score
    sorted_docs_with_scores = sorted(fused_scores.values(), key=lambda x: x['score'], reverse=True)

    # Filter by threshold and take top K
    final_docs = [item['doc'] for item in sorted_docs_with_scores if item['score'] > settings.HYBRID_SEARCH_THRESHOLD][:settings.TOP_K]

    return {"documents": final_docs}

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage

def generate_node(state: GraphState) -> dict:
    """
    Generates an answer using the LLM, taking into account the retrieved documents and chat history.
    Also updates the chat history with the latest turn.
    """
    query = state["query"]
    documents = state["documents"]
    chat_history = state["chat_history"]

    context = "\n\n".join([doc["content"] for doc in documents])

    # The system prompt provides instructions
    system_prompt = """
    You are a helpful assistant for a Confluence knowledge base.
    Answer the user's question based on the following context and the conversation history.
    If the context does not contain the answer, state that you don't have enough information.
    Do not make up answers.

    Context:
    {context}
    """

    # The prompt template now includes placeholders for history and the user's input
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{question}"),
    ])

    llm = get_llm()
    chain = prompt | llm

    # Invoke the chain with all necessary inputs
    generation = chain.invoke({
        "context": context,
        "question": query,
        "chat_history": chat_history
    })

    # Update the chat history with the new turn
    updated_history = chat_history + [HumanMessage(content=query), AIMessage(content=generation)]

    return {
        "generation": generation,
        "documents": documents, # Pass documents through for final output
        "chat_history": updated_history
    }


# --- Graph Definition ---

def create_graph():
    workflow = StateGraph(GraphState)

    # Add nodes
    workflow.add_node("classify_query", classify_query_node)
    workflow.add_node("keyword_search", keyword_search_node)
    workflow.add_node("vector_search", vector_search_node)
    workflow.add_node("fuse_results", fusion_node)
    workflow.add_node("generate", generate_node)

    # Build the graph workflow
    workflow.set_entry_point("classify_query")

    # After classification, run searches in parallel
    workflow.add_edge("classify_query", "keyword_search")
    workflow.add_edge("classify_query", "vector_search")

    # After parallel searches, fuse the results.
    # This syntax ensures that the 'fuse_results' node is only called after
    # BOTH 'keyword_search' and 'vector_search' have completed.
    workflow.add_edge(["keyword_search", "vector_search"], "fuse_results")

    # After fusing, generate the final response
    workflow.add_edge("fuse_results", "generate")
    workflow.add_edge("generate", END)

    return workflow.compile()

# Create the graph instance
app_graph = create_graph()
