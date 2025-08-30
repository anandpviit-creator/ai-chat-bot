from langchain_community.llms import Ollama
from langchain_community.embeddings import OllamaEmbeddings
from langchain_huggingface import HuggingFaceEmbeddings
from .config import settings

def get_llm():
    """Initializes and returns the Ollama LLM client."""
    return Ollama(
        base_url=settings.LLM_BASE_URL,
        model=settings.LLM_MODEL_NAME
    )

def get_embedding_model():
    """Initializes and returns the sentence-transformer embedding model."""
    # Using a local sentence-transformer model is generally faster for embeddings
    return HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL_NAME)
