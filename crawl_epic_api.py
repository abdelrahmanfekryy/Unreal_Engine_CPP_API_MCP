#!/usr/bin/env python3
"""
BFS Crawler for Epic Games UE5 API Documentation.

Uses StealthyFetcher (headless Chrome) to bypass anti-bot detection.
Folder structure matches URL paths under epic_api_docs/.
"""
import os
import time
import json
import pickle
from collections import deque
from pathlib import Path
from urllib.parse import urljoin, urlparse

from scrapling import StealthyFetcher

BASE_URL = "https://dev.epicgames.com/documentation/unreal-engine/API?application_version=5.6"
OUTPUT_DIR = Path("epic_api_docs_5.6")
CRAWL_DELAY = 0.0
MAX_DEPTH = None
CRAWL_API_PREFIX = "/documentation/unreal-engine/API"
SAVE_STATE_FILE = Path("crawl_state.pkl")
CRAWL_LOG = Path("crawl_log.jsonl")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
visited_urls = set()
all_queued_urls = set()
pages_crawled = [0]
jsonl_file = None


def url_to_path(url):
    parsed = urlparse(str(url))
    path_part = parsed.path
    base_path = urlparse(BASE_URL).path
    if path_part == base_path:
        path_part = "API_index"
    elif path_part.startswith(base_path + "/"):
        path_part = path_part[len(base_path) + 1:]
    else:
        path_part = path_part.lstrip("/")
    path_part = path_part.rstrip("/")
    if not path_part:
        path_part = "API_index"
    safe_path = path_part.replace("/", os.sep)
    return OUTPUT_DIR / (safe_path + ".html")


def save_page(response, url, sub_urls=None):
    global jsonl_file
    if jsonl_file is None:
        jsonl_file = open(CRAWL_LOG, "a", encoding="utf-8")
    file_path = url_to_path(url)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    html = response.body
    with open(file_path, "wb") as f:
        f.write(html)
    title_el = response.find("title")
    title = str(title_el.text) if title_el else ""
    metadata = {
        "url": str(url),
        "status": response.status,
        "title": title,
        "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "file": str(file_path.relative_to(OUTPUT_DIR)),
        "sub-urls": sub_urls if sub_urls else [],
    }
    jsonl_file.write(json.dumps(metadata, ensure_ascii=False) + "\n")
    jsonl_file.flush()
    return file_path


def extract_api_links(response, url):
    links = response.css("a[href]")
    valid_links = []
    base = BASE_URL.rsplit("?", 1)[0]
    for link in links:
        href = str(link.attrib.get("href", ""))
        clean_href = href.split("?")[0]
        full_url = urljoin(base + "/", clean_href) + "?application_version=5.6"
        if full_url != url and full_url not in valid_links:
            if clean_href.startswith(CRAWL_API_PREFIX + "/"):
                valid_links.append(full_url)
    return valid_links


def save_state(queue):
    state = {
        "visited_urls": visited_urls,
        "all_queued_urls": all_queued_urls,
        "pages_crawled": pages_crawled[0],
        "queue": queue,
    }
    with open(SAVE_STATE_FILE, "wb") as f:
        pickle.dump(state, f)


def load_state():
    global visited_urls, all_queued_urls, pages_crawled
    if SAVE_STATE_FILE.exists():
        with open(SAVE_STATE_FILE, "rb") as f:
            state = pickle.load(f)
        visited_urls = state["visited_urls"]
        all_queued_urls = state["all_queued_urls"]
        pages_crawled[0] = state["pages_crawled"]
        return state.get("queue", deque())
    return deque()


def crawl_bfs(resume=False):
    queue = deque()
    crawl_start = time.time()

    if resume:
        queue = load_state()
        print(f"Loaded queue: {len(queue)} items remaining")
    else:
        queue.append((BASE_URL, 0))
        all_queued_urls.add(BASE_URL)

    print(f"Starting BFS crawl (resume={resume})")
    print(f"Max depth: {'Unlimited' if MAX_DEPTH is None else MAX_DEPTH} | Delay: {CRAWL_DELAY}s")
    print(f"Output: {OUTPUT_DIR.absolute()}")
    print(f"Visited: {len(visited_urls)} | Already crawled: {pages_crawled[0]}\n")

    while queue:
        url, depth = queue.popleft()

        if MAX_DEPTH is not None and depth > MAX_DEPTH:
            continue
        if url in visited_urls:
            continue

        visited_urls.add(url)

        try:
            print(f"[{depth}] Crawling: {url}")
            response = StealthyFetcher.fetch(url)

            if response.status != 200:
                print(f"  [WARN] Status {response.status}, skipping.")
                continue

            child_links = extract_api_links(response, url) if (MAX_DEPTH is None or depth < MAX_DEPTH) else []
            file_path = save_page(response, url, sub_urls=child_links)
            title_el = response.find("title")
            title = str(title_el.text) if title_el else "N/A"
            print(f"  [OK] Saved: {file_path.relative_to(OUTPUT_DIR)} | {title}")
            pages_crawled[0] += 1

            if MAX_DEPTH is None or depth < MAX_DEPTH:
                for child_url in child_links:
                    if child_url not in visited_urls and child_url not in all_queued_urls:
                        queue.append((child_url, depth + 1))
                        all_queued_urls.add(child_url)
                print(f"  [Queued {len(child_links)} child pages, {len(queue)} remaining]")

        except Exception as e:
            print(f"  [ERROR] {e}")
            continue

        time.sleep(CRAWL_DELAY)

        # Save progress every 10 pages
        if pages_crawled[0] % 10 == 0:
            save_state(queue)

    elapsed = time.time() - crawl_start

    # Final summary
    print(f"\n=== Crawl Complete ===")
    print(f"Total pages visited: {len(visited_urls)}")
    print(f"Total pages crawled: {pages_crawled[0]}")
    print(f"Output directory: {OUTPUT_DIR.absolute()}")
    print(f"Time elapsed: {elapsed:.1f}s")
    if pages_crawled[0] > 0:
        print(f"Pages per minute: {pages_crawled[0] / (elapsed / 60):.1f}")

    total_files = sum(1 for _ in OUTPUT_DIR.rglob("*"))
    html_files = sum(1 for _ in OUTPUT_DIR.rglob("*.html"))
    print(f"Files created: {total_files} (HTML: {html_files})")
    print(f"Crawl log: {CRAWL_LOG.absolute()} ({pages_crawled[0]} entries)")

    # Directory tree
    def print_tree(directory, prefix=""):
        items = sorted(directory.iterdir())
        for i, item in enumerate(items):
            is_last = i == len(items) - 1
            connector = "└── " if is_last else "├── "
            print(prefix + connector + item.name)
            if item.is_dir():
                extension = "    " if is_last else "│   "
                print_tree(item, prefix + extension)

    print(f"\nDirectory structure under {OUTPUT_DIR}/:")
    print_tree(OUTPUT_DIR)

    # Clean up state file if fully complete
    if SAVE_STATE_FILE.exists():
        SAVE_STATE_FILE.unlink()

    # Close jsonl file handle
    if jsonl_file is not None:
        jsonl_file.close()


if __name__ == "__main__":
    import sys
    resume = "--resume" in sys.argv
    crawl_bfs(resume=resume)
