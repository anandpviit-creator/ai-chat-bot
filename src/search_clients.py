from opensearchpy import OpenSearch
from langchain_community.vectorstores.pgvector import PGVector
from .config import settings
from .llm_client import get_embedding_model

def get_opensearch_client():
    """Initializes and returns an OpenSearch client."""
    return OpenSearch(
        hosts=[{'host': settings.OPENSEARCH_HOST, 'port': settings.OPENSEARCH_PORT}],
        http_auth=None, # Assuming no auth for local dev
        use_ssl=False,
        verify_certs=False,
        ssl_assert_hostname=False,
        ssl_show_warn=False,
    )

def get_vector_store() -> PGVector:
    """Initializes and returns a PGVector store instance."""
    embedding_model = get_embedding_model()

    vector_store = PGVector(
        connection_string=settings.database_url,
        embedding_function=embedding_model,
        collection_name="confluence_documents" # Langchain uses this as the table name
    )
    return vector_store

# Initialize clients globally to be reused
opensearch_client = get_opensearch_client()
vector_store = get_vector_store()
