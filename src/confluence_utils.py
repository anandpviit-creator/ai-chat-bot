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
