import time
from langchain.text_splitter import RecursiveCharacterTextSplitter
from .config import settings
from .confluence_utils import get_confluence_client, get_all_pages_from_space, get_page_descendants, clean_html_content
from .search_clients import opensearch_client, vector_store

class ConfluenceIndexer:
    """
    A class to handle the logic of fetching, processing, and indexing
    Confluence data into OpenSearch and PGVector.
    """
    def __init__(self):
        self.confluence_client = get_confluence_client()

    def clear_existing_data(self):
        """
        Clears all documents from the OpenSearch index and the PGVector table.
        """
        # Clear OpenSearch index
        index_name = settings.OPENSEARCH_INDEX_NAME
        if opensearch_client.indices.exists(index=index_name):
            print(f"Clearing all documents from OpenSearch index: {index_name}...")
            opensearch_client.delete_by_query(
                index=index_name,
                body={"query": {"match_all": {}}},
                refresh=True,
                wait_for_completion=True
            )
            print("OpenSearch index cleared.")

        # Clear PGVector table
        # The LangChain PGVector implementation doesn't have a simple `delete_all` method.
        # A common approach is to delete the underlying table and let it be recreated.
        # This is simple but can be slow. For this implementation, we'll assume this is acceptable.
        # NOTE: This requires the database user to have table modification privileges.
        try:
            with vector_store._connect() as conn:
                with conn.cursor() as cur:
                    table_name = vector_store.collection_name
                    print(f"Dropping PGVector table: {table_name}...")
                    cur.execute(f"DROP TABLE IF EXISTS {table_name};")
                    print("PGVector table dropped. It will be recreated on the next indexing run.")
        except Exception as e:
            print(f"Could not drop PGVector table. It might not exist yet, which is okay. Error: {e}")


    def run_indexing(self, clear_first: bool = False):
        """
        Executes the full indexing process.

        Args:
            clear_first (bool): If True, clears all existing data before indexing.
        """
        print("Starting Confluence indexing process...")

        if clear_first:
            self.clear_existing_data()

        # Ensure OpenSearch index exists (it might have been deleted)
        if not opensearch_client.indices.exists(index=settings.OPENSEARCH_INDEX_NAME):
            self._create_opensearch_index()

        # 1. Fetch pages from all configured Confluence sources
        all_pages = self._fetch_all_sources()
        if not all_pages:
            print("No pages found to index. Exiting.")
            return

        print(f"Found a total of {len(all_pages)} pages to index from all sources.")

        # 2. Process and split documents
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200, length_function=len)
        all_chunks, all_metadata = self._process_and_split_pages(all_pages, text_splitter)
        print(f"Split documents into {len(all_chunks)} chunks.")

        if not all_chunks:
            print("No content chunks to index. Exiting.")
            return

        # 3. Index into PGVector
        print("Indexing chunks into PGVector... (This may take a while)")
        vector_store.add_texts(texts=all_chunks, metadatas=all_metadata)
        print("PGVector indexing complete.")

        # 4. Index into OpenSearch
        print("Indexing chunks into OpenSearch...")
        self._index_into_opensearch(all_chunks, all_metadata)
        print("OpenSearch indexing complete.")

        print("Indexing process finished successfully!")

    def _fetch_all_sources(self):
        all_pages = []
        if not settings.CONFLUENCE_SOURCES:
            print("No Confluence sources configured. Please set CONFLUENCE_SOURCES in your .env file.")
            return []

        for source in settings.CONFLUENCE_SOURCES:
            space_key = source.get("space")
            parent_page_id = source.get("parent_page_id")

            if not space_key:
                print(f"Skipping source due to missing 'space' key: {source}")
                continue

            if parent_page_id:
                print(f"Fetching pages from folder '{parent_page_id}' in space '{space_key}'...")
                pages = get_page_descendants(self.confluence_client, parent_page_id)
                print(f"Found {len(pages)} pages in folder.")
            else:
                print(f"Fetching all pages from space: {space_key}...")
                pages = get_all_pages_from_space(self.confluence_client, space_key)
                print(f"Found {len(pages)} pages in space.")

            all_pages.extend(pages)
        return all_pages

    def _process_and_split_pages(self, pages, text_splitter):
        all_chunks = []
        all_metadata = []
        for page in pages:
            page_id = page['id']
            title = page['title']
            # Handle potential missing keys gracefully
            url = settings.CONFLUENCE_URL + page.get('_links', {}).get('webui', '')
            space_key = page.get('space', {}).get('key', '')

            try:
                html_content = page['body']['storage']['value']
                clean_content = clean_html_content(html_content)
            except KeyError:
                clean_content = "No content found."

            chunks = text_splitter.split_text(clean_content)

            for i, chunk in enumerate(chunks):
                chunk_metadata = {
                    "page_id": page_id, "chunk_num": i, "title": title,
                    "url": url, "space_key": space_key
                }
                all_chunks.append(chunk)
                all_metadata.append(chunk_metadata)
        return all_chunks, all_metadata

    def _index_into_opensearch(self, chunks, metadatas):
        for i, chunk in enumerate(chunks):
            doc_id = f"{metadatas[i]['page_id']}_{metadatas[i]['chunk_num']}"
            document = {
                "title": metadatas[i]['title'], "content": chunk,
                "url": metadatas[i]['url'], "space_key": metadatas[i]['space_key']
            }
            opensearch_client.index(
                index=settings.OPENSEARCH_INDEX_NAME, body=document,
                id=doc_id, refresh=True
            )

    def _create_opensearch_index(self):
        """Creates the OpenSearch index if it doesn't already exist."""
        index_name = settings.OPENSEARCH_INDEX_NAME
        index_body = {
            "settings": {"analysis": {"analyzer": {"default": {"type": "standard"}}}},
            "mappings": {
                "properties": {
                    "title": {"type": "text"}, "content": {"type": "text"},
                    "url": {"type": "keyword"}, "space_key": {"type": "keyword"}
                }
            }
        }
        opensearch_client.indices.create(index=index_name, body=index_body)
        print(f"Created OpenSearch index: {index_name}")
