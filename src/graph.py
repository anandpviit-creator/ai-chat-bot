import operator
from typing import TypedDict, Annotated, List, Dict
from langchain_core.prompts import PromptTemplate
from langgraph.graph import StateGraph, END, START
from .config import settings
from .llm_client import get_llm
from .search_clients import opensearch_client, vector_store
from .schemas import SearchResult

# Define the state for our graph
class GraphState(TypedDict):
    query: str
    keyword_results: List[Dict]
    vector_results: List[Dict]
    documents: List[Dict]
    generation: str

# --- Nodes ---

def keyword_search_node(state: GraphState) -> dict:
    """Performs keyword search using OpenSearch."""
    query = state["query"]
    search_query = {
        "query": {
            "multi_match": {
                "query": query,
                "fields": ["title^2", "content"]
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
    """Performs semantic search using PGVector."""
    query = state["query"]
    results = vector_store.similarity_search_with_score(query, k=settings.TOP_K)

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

def generate_node(state: GraphState) -> dict:
    """Generates an answer using the LLM based on the retrieved documents."""
    query = state["query"]
    documents = state["documents"]

    context = "\n\n".join([doc["content"] for doc in documents])

    prompt_template = """
    You are a helpful assistant for a Confluence knowledge base.
    Answer the user's question based on the following context.
    If the context does not contain the answer, state that you don't have enough information.

    Context:
    {context}

    Question:
    {question}

    Answer:
    """

    prompt = PromptTemplate(
        template=prompt_template,
        input_variables=["context", "question"]
    )

    llm = get_llm()
    chain = prompt | llm

    generation = chain.invoke({"context": context, "question": query})

    return {"generation": generation, "documents": documents} # Pass documents through for final output


# --- Graph Definition ---

def create_graph():
    workflow = StateGraph(GraphState)

    # Add nodes
    workflow.add_node("keyword_search", keyword_search_node)
    workflow.add_node("vector_search", vector_search_node)
    workflow.add_node("fuse_results", fusion_node)
    workflow.add_node("generate", generate_node)

    # Build the graph for parallel execution
    workflow.add_edge(START, "keyword_search")
    workflow.add_edge(START, "vector_search")

    # Both search nodes will update the state, then we fuse the results
    workflow.add_edge("keyword_search", "fuse_results")
    workflow.add_edge("vector_search", "fuse_results")

    workflow.add_edge("fuse_results", "generate")
    workflow.add_edge("generate", END)

    return workflow.compile()

# Create the graph instance
app_graph = create_graph()
