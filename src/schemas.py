from pydantic import BaseModel, Field
from typing import List, Optional

class ChatRequest(BaseModel):
    query: str = Field(..., description="The user's query for the chatbot.")
    session_id: Optional[str] = Field(None, description="A unique identifier for the chat session.")

class Document(BaseModel):
    page_id: str
    title: str
    url: str
    content: str
    space_key: str

class SearchResult(BaseModel):
    doc_id: str
    score: float
    content: str
    metadata: dict

class HybridSearchResult(BaseModel):
    keyword_results: List[SearchResult]
    vector_results: List[SearchResult]

class ChatResponse(BaseModel):
    answer: str
    retrieved_documents: List[Document]
    session_id: str
