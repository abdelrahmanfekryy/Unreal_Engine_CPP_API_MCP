# AGENTS.md

## Quick Start
```bash
.venv/bin/python epic_mcp.py   # Run the MCP server
```

## Environment
Always use the project venv at `.venv/`. Do not use system Python.
```bash
.venv/bin/python <script>
.venv/bin/pip install <pkg>
.venv/bin/jupyter nbconvert --execute <notebook>
```

## Architecture
- **MCP server** — `epic_mcp.py` entrypoint, uses `FastMCP` from the `mcp` package. Imports models from the `models/` package (a directory with `__init__.py` + `document.py`, not `models.py`).
- **Local RAG KB** — `ue5_faiss_kb/` holds a FAISS index + metadata JSON built from UE5.6 API docs. Queried via `query_ue5_docs()` tool. Embeddings use `all-MiniLM-L6-v2` (384-dim, CPU).
- **Docs pipeline** — three-stage: crawl HTML (`crawl_epic_api.py`) → convert to markdown (`convert_to_markdown.py`) → build KB (`build_faiss_kb.py`).

## Developer Commands
- **Run MCP server:** `python epic_mcp.py`
- **Build FAISS KB:** `python build_faiss_kb.py` (must run after `convert_to_markdown.py`)
- **Convert HTML to MD:** `python convert_to_markdown.py` (reads from `epic_api_docs_5.6/`, writes `.md` alongside each `.html`)
- **Crawl Epic docs:** `python crawl_epic_api.py` (writes HTML to `epic_api_docs_5.6/`)

## Gotchas
- **requirements.txt is incomplete.** Missing: `faiss-cpu`, `sentence-transformers`, `numpy`, `beautifulsoup4`, `markdownify` (listed), `scrapling` (listed). Install with `pip install faiss-cpu sentence-transformers numpy beautifulsoup4`.
- **`build_faiss_kb.py` has hardcoded absolute paths** (`DOCS_DIR` and `OUTPUT_DIR` point to `/media/abdelrahman/Data/MCP-UE5/...`). Do not move without updating those constants.
- **`convert_to_markdown.py` strips URLs from all markdown links** — `[](url)` becomes bold `**text**`. Do not revert this unless the user requests it.
- **Stealth fetcher requires Playwright:** `playwright install chromium` before using `use_stealth=True`.
- **README test command is wrong.** `python test_epic_api.ipynb` cannot execute a Jupyter notebook directly. Use `jupyter nbconvert --execute experiments/test_epic_api.ipynb` or run interactively.
- **FAISS index must be rebuilt** if you modify docs or change `convert_to_markdown.py`.
- **`.gitignore` excludes** `epic_api_docs_5.6/`, `ue5_faiss_kb/`, `experiments/`, `*.jsonl`, `crawl_state.pkl`.

## File Layout
```
epic_mcp.py          # MCP server (main entrypoint)
crawl_epic_api.py    # Crawl dev.epicgames.com HTML
convert_to_markdown.py  # HTML → Markdown
build_faiss_kb.py    # Markdown → FAISS KB
models/              # Pydantic models (document.py)
epic_api_docs_5.6/   # Crawled HTML docs (gitignored)
ue5_faiss_kb/        # FAISS index + metadata (gitignored)
experiments/         # Jupyter notebooks
```

## Framework/Toolchain
- MCP server protocol via `mcp` package (FastMCP)
- HTTP scraping via `scrapling` (Fetcher + StealthyFetcher)
- Semantic search via `faiss` (IndexFlatIP, cosine similarity on normalized vectors)
- Embeddings via `sentence-transformers` (all-MiniLM-L6-v2, 384-dim)
