import time
from langchain.text_splitter import RecursiveCharacterTextSplitter
from src.config import settings
from src.confluence_utils import get_confluence_client, get_all_pages_from_space, clean_html_content
from src.search_clients import opensearch_client, vector_store

def create_opensearch_index():
    """Creates the OpenSearch index if it doesn't already exist."""
    index_name = settings.OPENSEARCH_INDEX_NAME
    if not opensearch_client.indices.exists(index=index_name):
        index_body = {
            "settings": {
                "analysis": {
                    "analyzer": {
                        "default": {
                            "type": "standard"
                        }
                    }
                }
            },
            "mappings": {
                "properties": {
                    "title": {"type": "text"},
                    "content": {"type": "text"},
                    "url": {"type": "keyword"},
                    "space_key": {"type": "keyword"}
                }
            }
        }
        opensearch_client.indices.create(index=index_name, body=index_body)
        print(f"Created OpenSearch index: {index_name}")
    else:
        print(f"OpenSearch index '{index_name}' already exists.")

def index_data():
    """
    Main function to fetch data from Confluence, process it,
    and index it into OpenSearch and PGVector.
    """
    print("Starting Confluence indexing process...")

    # 1. Initialize clients
    confluence_client = get_confluence_client()

    # 2. Ensure OpenSearch index exists
    create_opensearch_index()

    # 3. Fetch pages from Confluence
    print(f"Fetching all pages from space: {settings.CONFLUENCE_SPACE_KEY}...")
    pages = get_all_pages_from_space(confluence_client, settings.CONFLUENCE_SPACE_KEY)
    if not pages:
        print("No pages found in the specified Confluence space.")
        return

    print(f"Found {len(pages)} pages to index.")

    # 4. Process and split documents
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )

    all_chunks = []
    all_metadata = []

    for page in pages:
        page_id = page['id']
        title = page['title']
        url = settings.CONFLUENCE_URL + page['_links']['webui']
        space_key = page['space']['key']

        try:
            html_content = page['body']['storage']['value']
            clean_content = clean_html_content(html_content)
        except KeyError:
            clean_content = "No content found."

        chunks = text_splitter.split_text(clean_content)

        for i, chunk in enumerate(chunks):
            chunk_metadata = {
                "page_id": page_id,
                "chunk_num": i,
                "title": title,
                "url": url,
                "space_key": space_key
            }
            all_chunks.append(chunk)
            all_metadata.append(chunk_metadata)

    print(f"Split documents into {len(all_chunks)} chunks.")

    # 5. Index into PGVector
    print("Indexing chunks into PGVector... (This may take a while)")
    if all_chunks:
        vector_store.add_texts(texts=all_chunks, metadatas=all_metadata)
        print("PGVector indexing complete.")
    else:
        print("No chunks to index in PGVector.")


    # 6. Index into OpenSearch
    print("Indexing chunks into OpenSearch...")
    for i, chunk in enumerate(all_chunks):
        doc_id = f"{all_metadata[i]['page_id']}_{all_metadata[i]['chunk_num']}"
        document = {
            "title": all_metadata[i]['title'],
            "content": chunk,
            "url": all_metadata[i]['url'],
            "space_key": all_metadata[i]['space_key']
        }
        opensearch_client.index(
            index=settings.OPENSEARCH_INDEX_NAME,
            body=document,
            id=doc_id,
            refresh=True # Use 'wait_for' in production for better performance
        )
    print("OpenSearch indexing complete.")

    print("Indexing process finished successfully!")


if __name__ == "__main__":
    # Wait for services to be ready
    time.sleep(10)
    index_data()
