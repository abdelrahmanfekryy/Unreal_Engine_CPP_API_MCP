import os
import json
import numpy as np

import faiss
from sentence_transformers import SentenceTransformer

from mcp.server.fastmcp import FastMCP
from scrapling import Fetcher, StealthyFetcher
from models import EpicDocument, SearchResponse

mcp = FastMCP("Epic Games Dev API")

# --- FAISS RAG local knowledge base ---
_KB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ue5_faiss_kb")
_DOCS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "epic_api_docs_5.6")
_EMBEDDING_MODEL = "all-MiniLM-L6-v2"
_INDEX = None
_METADATA = None
_MODEL = None


def _load_rag():
    global _INDEX, _METADATA, _MODEL
    if _MODEL is None:
        _MODEL = SentenceTransformer(_EMBEDDING_MODEL, device="cpu")
    if _INDEX is None:
        _INDEX = faiss.read_index(os.path.join(_KB_DIR, "faiss_index.bin"))
    if _METADATA is None:
        with open(os.path.join(_KB_DIR, "chunks_metadata.json"), "r") as f:
            _METADATA = json.load(f)

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


@mcp.tool()
def query_ue5_docs(
    query: str,
    top_k: int = 5,
) -> dict:
    """Search the local UE5.6 API documentation knowledge base using semantic similarity.

    This tool queries a FAISS index built from downloaded Epic Games UE5.6 API
    documentation markdown files. It returns the most relevant doc chunks for
    the given natural-language query.

    Args:
        query: The search query in natural language, e.g.
               'how to spawn an actor' or 'character movement jump'.
        top_k: Number of results to return (default 5).
    """
    _load_rag()

    if not _INDEX:
        raise RuntimeError("FAISS index not found. Run build_faiss_kb.py first.")

    query_emb = _MODEL.encode([query], normalize_embeddings=True)
    scores, indices = _INDEX.search(query_emb.astype("float32"), min(top_k, len(_METADATA)))

    results = []
    for rank in range(len(indices[0])):
        idx = indices[0][rank]
        score = float(scores[0][rank])
        meta = _METADATA[idx]

        fpath = os.path.join(_DOCS_DIR, meta["file"])
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                lines = f.readlines()
            total = meta.get("total_chunks", 1)
            chunk_idx = meta.get("file_chunk_idx", 0)
            file_lines = meta.get("file_lines", len(lines))
            line_per_chunk = file_lines / max(total, 1)
            ls = int(chunk_idx * line_per_chunk) - 3
            le = int((chunk_idx + 1) * line_per_chunk) + 3
            ls = max(0, ls)
            le = min(len(lines), le)
            preview = "".join(lines[ls:le]).strip()
        except Exception:
            preview = "(could not read source file)"

        results.append({
            "rank": rank + 1,
            "score": round(score, 4),
            "doc_name": meta["doc_name"],
            "file": meta["file"],
            "chunk": f"{meta.get('file_chunk_idx', rank)}/{total}",
            "preview": preview[:500],
        })

    return {
        "query": query,
        "top_k": top_k,
        "total_results": len(results),
        "results": results,
    }


if __name__ == "__main__":
    mcp.run()
