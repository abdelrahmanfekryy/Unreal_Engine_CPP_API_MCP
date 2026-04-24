#!/usr/bin/env python3
"""
Convert block-markdown content from Epic API HTML files to Markdown.

Reads HTML files from epic_api_docs_5.6/ and extracts the <div class="block-markdown">
content, converting it to clean Markdown using markdownify.
"""
from pathlib import Path
from bs4 import BeautifulSoup
from markdownify import markdownify as md
import sys
import re

OUTPUT_DIR = Path("epic_api_docs_5.6")


def convert_html_to_md(html_path: Path) -> bool:
    """Convert a single HTML file to Markdown. Returns True on success."""
    try:
        html = html_path.read_text(encoding="utf-8")
        soup = BeautifulSoup(html, "html.parser")

        # Get page title from h1
        title_tag = soup.find("h1")
        title = title_tag.get_text(strip=True) if title_tag else html_path.stem.replace("_", " ").title()

        # Find block-markdown div
        md_div = soup.find("div", class_="block-markdown")
        if md_div is None:
            print(f"  [SKIP] No block-markdown: {html_path.name}")
            return False

        # Convert to markdown
        inner = str(md_div)
        result = md(inner, heading_style="ATX", bullet_char="-")
        result = f"# {title}\n\n{result}"

        # Strip URLs from markdown links, keeping text in bold
        # Handles nested brackets like [operator[]](url) → **operator[]**
        def _strip_links(text):
            out = []
            i = 0
            while i < len(text):
                if text[i] == '[':
                    depth, j = 1, i + 1
                    while j < len(text) and depth > 0:
                        if text[j] == '[': depth += 1
                        elif text[j] == ']': depth -= 1
                        j += 1
                    if depth == 0 and j < len(text) and text[j] == '(':
                        k, pd = j + 1, 1
                        while k < len(text) and pd > 0:
                            if text[k] == '(': pd += 1
                            elif text[k] == ')': pd -= 1
                            k += 1
                        if pd == 0:
                            inner = text[i+1:j-1]
                            out.append(f'**{inner}**')
                            i = k
                            continue
                out.append(text[i])
                i += 1
            return ''.join(out)
        result = _strip_links(result)

        # Write .md file alongside the .html file
        md_path = html_path.with_suffix(".md")
        md_path.write_text(result, encoding="utf-8")
        print(f"  [OK]   {html_path.name} -> {md_path.name} ({len(result)} chars)")
        return True

    except Exception as e:
        print(f"  [FAIL] {html_path.name}: {e}")
        return False


def main():
    html_files = sorted(OUTPUT_DIR.rglob("*.html"))

    if not html_files:
        print(f"No HTML files found in {OUTPUT_DIR}")
        sys.exit(1)

    print(f"Found {len(html_files)} HTML files\n")

    success = 0
    skipped = 0

    for i, html_file in enumerate(html_files, 1):
        rel = html_file.relative_to(OUTPUT_DIR)
        print(f"[{i}/{len(html_files)}] {rel}")

        if convert_html_to_md(html_file):
            success += 1
        else:
            skipped += 1

    print(f"\nDone: {success} converted, {skipped} skipped, {len(html_files)} total")


if __name__ == "__main__":
    main()
