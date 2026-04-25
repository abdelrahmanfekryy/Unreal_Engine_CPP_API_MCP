# Epic Games Dev MCP Server

MCP (Model Context Protocol) server for searching and fetching Epic Games Developer documentation, plus a local RAG knowledge base for UE5 API docs.

## Features

- **Search** Epic Games documentation by keywords with filtering and pagination
- **Fetch** full documentation page content
- **Local RAG** — semantic search over UE5.6 API docs via FAISS index
- **Cloudflare bypass** — browser-based stealth fetcher for rate-limited sites

## Installation

1. Create a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt faiss-cpu sentence-transformers numpy
```

> `requirements.txt` is incomplete by design. Always install `faiss-cpu`, `sentence-transformers`, and `numpy` separately.

## Usage

Run the MCP server:

```bash
python epic_mcp.py
```

### Available Tools

#### `search_epic_docs`

Search Epic Games Developer documentation.

| Parameter | Description | Default |
|-----------|-------------|---------|
| `query` | Search keywords | (required) |
| `page` | Page number for pagination | `1` |
| `per_page` | Results per page (max 50) | `20` |
| `item_types` | Filter by content type | `None` |
| `use_stealth` | Use browser-based fetcher (Cloudflare) | `False` |

Valid `item_types` values: `api_document`, `forum_post`, `kb_article`, `kb_entry`, `release_notes`, `tutorial`, `video`, `article`.

#### `get_api_documentation`

Search only API documentation pages. Same parameters as `search_epic_docs`, defaults to filtering by `api_document`.

#### `get_document_content`

Fetch the full content of a documentation page.

| Parameter | Description | Default |
|-----------|-------------|---------|
| `path` | Documentation slug path | (required) |
| `application_version` | UE version | `5.7` |
| `lang` | Locale | `en-us` |
| `use_stealth` | Use browser-based fetcher | `False` |

#### `query_ue5_docs`

Search the local UE5.6 API documentation knowledge base using semantic similarity. Built on a FAISS index of markdown-converted docs.

| Parameter | Description | Default |
|-----------|-------------|---------|
| `query` | Natural-language search query | (required) |
| `top_k` | Number of results to return | `5` |

## Docs Pipeline

The project includes a three-stage pipeline for building and maintaining the local FAISS knowledge base:

| Stage | Script | Description |
|-------|--------|-------------|
| 1. Crawl | `python crawl_epic_api.py` | Crawls `dev.epicgames.com` HTML pages into `epic_api_docs_5.6/` |
| 2. Convert | `python convert_to_markdown.py` | Converts HTML to Markdown, writes `.md` files alongside each `.html` |
| 3. Build KB | `python build_faiss_kb.py` | Embeds markdown chunks into a FAISS index at `ue5_faiss_kb/` |

Run the pipeline in order. The FAISS index must be rebuilt if docs are modified.

## Cloudflare Bypass

If you encounter rate limiting or Cloudflare challenges, set `use_stealth=True`. This requires Playwright:

```bash
playwright install chromium
```

## Architecture

```
epic_mcp.py          # MCP server entrypoint, imports models from models/
models/              # Pydantic models (document.py, __init__.py)
epic_api_docs_5.6/   # Crawled HTML docs (gitignored)
ue5_faiss_kb/        # FAISS index + metadata (gitignored)
experiments/         # Jupyter notebooks
```

- **MCP** — Uses `FastMCP` from the `mcp` package
- **Scraping** — Uses `scrapling` (Fetcher + StealthyFetcher)
- **RAG** — FAISS `IndexFlatIP` (cosine similarity) with `all-MiniLM-L6-v2` embeddings (384-dim, CPU)

## Gotchas

- **Stealth requires Playwright** — install `chromium` before using `use_stealth=True`
- **FAISS index must be rebuilt** if you modify docs or change `convert_to_markdown.py`
- **Notebooks** must be executed via `jupyter nbconvert --execute`, not `python`
