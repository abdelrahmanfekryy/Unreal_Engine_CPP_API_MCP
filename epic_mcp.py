from mcp.server.fastmcp import FastMCP
from scrapling import Fetcher, StealthyFetcher
from models import EpicDocument, SearchResponse

mcp = FastMCP("Epic Games Dev API")

API_URL = "https://dev.epicgames.com/community/api/search/index.json"
DOC_URL = "https://dev.epicgames.com/community/api/documentation/document.json"

_fetcher = Fetcher()
_stealth = StealthyFetcher()


def _build_params(
    query: str,
    page: int = 1,
    per_page: int = 20,
    item_types: list[str] | None = None,
) -> str:
    parts = [
        f"page={page}",
        f"per_page={per_page}",
        f"query={query}",
        "published_at_range=any_time",
        "sort_by=relevancy",
        "preferred_locale=en-us",
    ]
    if item_types:
        parts.append("item_types%5B%5D=" + ",".join(item_types))
    return "&".join(parts)


# @mcp.tool()
def search_epic_docs(
    query: str,
    page: int = 1,
    per_page: int = 20,
    item_types: list[str] | None = None,
    use_stealth: bool = False,
) -> dict:
    """Search Epic Games Developer documentation and API references.

    Args:
        query: Search keywords, e.g. 'widget', 'UMG', 'API'.
        page: Page number for pagination.
        per_page: Results per page (max 50).
        item_types: Filter by content types. Options include:
            'api_document', 'forum_post', 'kb_article', 'kb_entry',
            'release_notes', 'tutorial', 'video', 'article'.
        use_stealth: Use browser-based fetcher with Cloudflare solving.
    """
    params = _build_params(query, page, per_page, item_types)
    url = f"{API_URL}?{params}"

    client = _stealth if use_stealth else _fetcher
    if use_stealth:
        resp = client.fetch(url, solve_cloudflare=True)
    else:
        resp = client.get(url)

    if resp.status >= 400:
        raise RuntimeError(f"HTTP {resp.status}: {resp.body[:500]}")
    return SearchResponse(**resp.json()).model_dump()


@mcp.tool()
def get_api_documentation(
    query: str,
    page: int = 1,
    per_page: int = 20,
    item_types: list[str] | None = None,
    use_stealth: bool = False,
) -> dict:
    """Search only API documentation on the Epic Games Developer portal.

    Args:
        query: Search keywords for API docs.
        page: Page number for pagination.
        per_page: Results per page (max 50).
        item_types: Filter by content types.
        use_stealth: Use browser-based fetcher with Cloudflare solving.
    """
    return search_epic_docs(
        query=query,
        page=page,
        per_page=per_page,
        item_types=item_types or ["api_document"],
        use_stealth=use_stealth,
    )


@mcp.tool()
def get_document_content(
    path: str,
    application_version: str = "5.7",
    lang: str = "en-us",
    use_stealth: bool = False,
) -> dict:
    """Fetch the full content of an Epic Games documentation page.

    Args:
        path: The documentation slug path, e.g.
              'documentation/unreal-engine/BlueprintAPI/ActivatableWidget/ActivateWidget'.
        application_version: UE version, e.g. '5.7', '5.6', '5.5'.
        lang: Locale, default 'en-us'.
        use_stealth: Use browser-based fetcher with Cloudflare solving.
    """
    from urllib.parse import quote

    encoded_path = quote(path, safe="/")
    url = f"{DOC_URL}?path={encoded_path}&application_version={application_version}&lang={lang}"

    client = _stealth if use_stealth else _fetcher
    if use_stealth:
        resp = client.fetch(url, solve_cloudflare=True)
    else:
        resp = client.get(url)

    if resp.status >= 400:
        raise RuntimeError(f"HTTP {resp.status}: {resp.body[:500]}")
    return EpicDocument(**resp.json()).model_dump()


if __name__ == "__main__":
    mcp.run()
