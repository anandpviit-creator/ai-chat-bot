from pydantic import BaseModel, Field
from typing import List, Optional

from langchain_core.messages import AIMessage, HumanMessage

# A Pydantic model for a single message in the chat history
class HistoryMessage(BaseModel):
    role: str # "human" or "ai"
    content: str

    def to_langchain_message(self):
        if self.role == "human":
            return HumanMessage(content=self.content)
        elif self.role == "ai":
            return AIMessage(content=self.content)
        return None

class ChatRequest(BaseModel):
    query: str = Field(..., description="The user's query for the chatbot.")
    session_id: Optional[str] = Field(None, description="A unique identifier for the chat session.")
    chat_history: Optional[List[HistoryMessage]] = Field(None, description="A list of previous messages in the conversation.")

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
    chat_history: List[HistoryMessage] = Field(..., description="The updated conversation history, including the latest turn.")
