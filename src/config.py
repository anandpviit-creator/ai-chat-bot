import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings:
    # Confluence
    CONFLUENCE_URL = os.getenv("CONFLUENCE_URL")
    CONFLUENCE_USERNAME = os.getenv("CONFLUENCE_USERNAME")
    CONFLUENCE_API_TOKEN = os.getenv("CONFLUENCE_API_TOKEN")
    CONFLUENCE_SPACE_KEY = os.getenv("CONFLUENCE_SPACE_KEY")

    # PostgreSQL
    POSTGRES_DB = os.getenv("POSTGRES_DB")
    POSTGRES_USER = os.getenv("POSTGRES_USER")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
    POSTGRES_PORT = os.getenv("POSTGRES_PORT", 5432)

    @property
    def database_url(self):
        return f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # OpenSearch
    OPENSEARCH_HOST = os.getenv("OPENSEARCH_HOST", "opensearch")
    OPENSEARCH_PORT = os.getenv("OPENSEARCH_PORT", 9200)
    OPENSEARCH_INDEX_NAME = os.getenv("OPENSEARCH_INDEX_NAME", "confluence_idx")

    @property
    def opensearch_url(self):
        return f"http://{self.OPENSEARCH_HOST}:{self.OPENSEARCH_PORT}"

    # LLM
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://host.docker.internal:11434")
    LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "mistral")

    # Hybrid Search
    HYBRID_SEARCH_ALPHA = float(os.getenv("HYBRID_SEARCH_ALPHA", 0.6))
    HYBRID_SEARCH_BETA = float(os.getenv("HYBRID_SEARCH_BETA", 0.4))
    HYBRID_SEARCH_THRESHOLD = float(os.getenv("HYBRID_SEARCH_THRESHOLD", 0.4))
    TOP_K = int(os.getenv("TOP_K", 5))

    # Embedding Model
    EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

settings = Settings()
