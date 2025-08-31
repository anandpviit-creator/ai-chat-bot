from fastapi import FastAPI, HTTPException
from .schemas import ChatRequest, ChatResponse, Document
from .graph import app_graph
import uuid

app = FastAPI(
    title="Confluence Q&A Chatbot",
    description="A chatbot that answers questions based on Confluence documents using hybrid search.",
    version="1.0.0"
)

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Receives a user query, processes it through the hybrid search graph,
    and returns a generated answer along with the source documents.
    """
    if not request.query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    session_id = request.session_id or str(uuid.uuid4())

    # The input to the graph must match the GraphState structure
    from .config import settings
    from .schemas import HistoryMessage
    from langchain_core.messages import AIMessage, HumanMessage

    # Convert chat history from Pydantic models to LangChain messages
    history = [msg.to_langchain_message() for msg in (request.chat_history or [])]
    history = [msg for msg in history if msg is not None]

    graph_input = {
        "query": request.query,
        "available_spaces": settings.CONFLUENCE_SPACE_KEYS,
        "chat_history": history,
        "keyword_results": [],
        "vector_results": [],
        "documents": []
    }

    try:
        # Run the graph
        final_state = app_graph.invoke(graph_input)

        # Extract results from the final state
        answer = final_state.get("generation", "Sorry, I couldn't find an answer.")
        retrieved_docs_data = final_state.get("documents", [])
        updated_history_lc = final_state.get("chat_history", [])

        # Format documents for the response
        retrieved_documents = [
            Document(
                page_id=doc.get("id", ""),
                title=doc.get("metadata", {}).get("title", "Unknown Title"),
                url=doc.get("metadata", {}).get("url", ""),
                content=doc.get("content", ""),
                space_key=doc.get("metadata", {}).get("space_key", "")
            ) for doc in retrieved_docs_data
        ]

        # Convert updated history back to Pydantic models for the response
        updated_history_pydantic = []
        for msg in updated_history_lc:
            if isinstance(msg, HumanMessage):
                updated_history_pydantic.append(HistoryMessage(role="human", content=msg.content))
            elif isinstance(msg, AIMessage):
                updated_history_pydantic.append(HistoryMessage(role="ai", content=msg.content))

        return ChatResponse(
            answer=answer,
            retrieved_documents=retrieved_documents,
            session_id=session_id,
            chat_history=updated_history_pydantic
        )

    except Exception as e:
        # Log the exception for debugging
        print(f"Error during graph invocation: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred.")

@app.get("/health", status_code=200)
def health_check():
    """Health check endpoint to verify the service is running."""
    return {"status": "ok"}
