import html2text
from atlassian import Confluence
from .config import settings

def get_confluence_client():
    """Initializes and returns a Confluence API client."""
    return Confluence(
        url=settings.CONFLUENCE_URL,
        username=settings.CONFLUENCE_USERNAME,
        password=settings.CONFLUENCE_API_TOKEN
    )

def get_all_pages_from_space(client: Confluence, space_key: str):
    """Fetches all pages from a given Confluence space."""
    start = 0
    limit = 50
    pages = []

    while True:
        results = client.get_all_pages_from_space(space_key, start=start, limit=limit, expand='body.storage,version')
        if not results:
            break
        pages.extend(results)
        start += limit

    return pages

def clean_html_content(html_content: str) -> str:
    """Converts HTML to clean Markdown-like text."""
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = True
    return h.handle(html_content)

def get_page_descendants(client: Confluence, page_id: str):
    """
    Fetches all descendant pages (children, grandchildren, etc.) for a given parent page.
    """
    descendants = []
    # The API call get_page_child_by_type fetches direct children.
    # We need to recursively call this for each child to get the full tree.
    # The `atlassian-python-api` doesn't have a built-in recursive fetch, so we do it manually.

    # Let's get the page tree using CQL instead, which can be more efficient.
    # The `ancestor` field in CQL can find all descendants.
    cql = f"ancestor={page_id}"

    start = 0
    limit = 50

    while True:
        results = client.cql(cql, start=start, limit=limit, expand='body.storage,version,space')
        if not results or 'results' not in results:
            break

        pages = results['results']
        if not pages:
            break

        descendants.extend(pages)

        if len(pages) < limit:
            break # Last page of results

        start += limit

    return descendants
