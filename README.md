# Epic Games Dev MCP Server

MCP (Model Context Protocol) server for searching and fetching Epic Games Developer documentation.

## Features

- Search Epic Games documentation by keywords
- Filter results by content type (API docs, tutorials, release notes, etc.)
- Fetch full documentation page content
- Pagination support for search results

## Installation

1. Create a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

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

## Cloudflare Bypass

If you encounter rate limiting or Cloudflare challenges, set `use_stealth=True` to use the browser-based fetcher. This requires Playwright to be installed:

```bash
playwright install chromium
```

## Development

Run tests:

```bash
python test_epic_api.ipynb
```
