#!/usr/bin/env python3
"""
Build a FAISS knowledge base from Epic UE5.6 API documentation markdown files.
Chunks are split by markdown header hierarchy (# through ######).
Uses sentence-transformers for embedding and faiss-cpu for similarity search.
"""

import os
import re
import json
import glob
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer
import faiss

# --- Configuration ---
DOCS_DIR = "/media/abdelrahman/Data/MCP-UE5/epic_api_docs_5.6"
OUTPUT_DIR = "/media/abdelrahman/Data/MCP-UE5/ue5_faiss_kb"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # Fast, lightweight, 384-dim
# Chunks are split by markdown header hierarchy (# through ######)


def clean_markdown(text: str) -> str:
    """Strip navigation breadcrumbs, redundant table artifacts, and keep readable content."""
    lines = text.split("\n")
    cleaned = []

    skip_patterns = [
        r"^\[API\]",                     # navigation breadcrumb links
        r"^Copy full snippet",          # code block copy button
        r"^\(Showing lines \d",         # truncated preview notice
        r"^$",                          # empty lines (keep some for spacing)
    ]

    prev_empty = False
    for line in lines:
        # Skip navigation lines
        if re.search(r"\[API\].*application_version", line):
            continue
        # Skip "Copy full snippet"
        if "Copy full snippet" in line:
            continue
        # Skip truncated notice
        if re.match(r"^\(Showing lines", line):
            continue
        # Skip pure separator lines from broken markdown tables
        if re.match(r"^(\|?\s*[-:|]+\s*)+$", line) and len(line) > 20:
            continue

        # Collapse multiple empty lines
        if line.strip() == "":
            if prev_empty:
                continue
            prev_empty = True
            cleaned.append(line)
        else:
            prev_empty = False
            cleaned.append(line)

    return "\n".join(cleaned).strip()


def extract_sections(text: str):
    """
    Split markdown into sections based on header hierarchy.
    Each section includes its full header path (all ancestor headers).
    Returns list of (section_text, header_path_string).
    """
    lines = text.split("\n")
    sections = []  # list of (header_path, [lines])
    current_headers = []  # stack of (level, header_text)
    current_lines = []
    current_path = ""

    header_re = re.compile(r"^(#{1,6})\s+(.+)$")

    for line in lines:
        m = header_re.match(line)
        if m:
            # Save previous section
            if current_lines:
                section_text = "\n".join(current_lines).strip()
                if section_text:
                    sections.append((current_path, section_text))

            level = len(m.group(1))
            header_text = m.group(2).strip()

            # Pop headers that are at same or lower level
            while current_headers and current_headers[-1][0] >= level:
                current_headers.pop()

            # Build the header path from remaining stack + current
            ancestor_lines = [h[1] for h in current_headers]
            ancestor_lines.append(header_text)
            current_path = "\n".join(ancestor_lines)

            current_headers.append((level, header_text))
            current_lines = []
        else:
            current_lines.append(line)

    # Save last section
    if current_lines:
        section_text = "\n".join(current_lines).strip()
        if section_text:
            sections.append((current_path, section_text))

    return sections


def chunk_text(text: str, doc_path: str, doc_name: str, global_offset: int):
    """
    Split text into hierarchical sections by header hierarchy. Each chunk contains
    the full header path plus the section content, preserving parent header context.
    Returns list of (chunk_text, metadata).
    """
    sections = extract_sections(text)
    if not sections:
        return []

    total_chunks = len(sections)
    chunks = []

    for i, (header_path, section_body) in enumerate(sections):
        # Prepend header path to each section so context is preserved
        chunk_content = f"{header_path}\n\n{section_body}"

        meta = {
            "file": doc_path,
            "doc_name": doc_name,
            "chunk_id": global_offset + i,
            "file_chunk_idx": i,
            "total_chunks": total_chunks,
            "header_path": header_path,
            "chunk_content": chunk_content,
        }
        chunks.append((chunk_content, meta))

    return chunks


def build_kb():
    print(f"[1/5] Loading embedding model: {EMBEDDING_MODEL} ...")
    model = SentenceTransformer(EMBEDDING_MODEL, device="cpu")

    # Collect all .md files recursively
    md_files = sorted(glob.glob(os.path.join(DOCS_DIR, "**", "*.md"), recursive=True))
    print(f"[2/5] Found {len(md_files)} markdown files")

    # Process files
    all_chunks = []
    skipped = 0
    for fpath in md_files:
        rel_path = os.path.relpath(fpath, DOCS_DIR)
        doc_name = Path(rel_path).stem

        try:
            with open(fpath, "r", encoding="utf-8") as f:
                raw = f.read()
        except Exception:
            continue

        cleaned = clean_markdown(raw)
        if not cleaned:
            skipped += 1
            continue

        line_count = cleaned.count("\n") + 1
        chunks = chunk_text(cleaned, rel_path, doc_name, len(all_chunks))
        # Add line count to each chunk's metadata
        for c in chunks:
            c[1]["file_lines"] = line_count
        if not chunks:
            skipped += 1
            continue

        all_chunks.extend(chunks)

    print(f"[3/5] Total chunks after cleaning: {len(all_chunks)} (skipped {skipped} files)")

    if len(all_chunks) == 0:
        print("ERROR: No chunks generated. Check the docs directory.")
        return

    # Embed chunks in batches
    texts = [c[0] for c in all_chunks]
    all_embeddings = []
    batch_size = 256
    print(f"[4/5] Embedding {len(texts)} chunks (batch={batch_size}) ...")

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        emb = model.encode(batch, show_progress_bar=True, normalize_embeddings=True)
        all_embeddings.append(emb)

    embeddings = np.vstack(all_embeddings).astype("float32")
    dim = embeddings.shape[1]
    print(f"     Embeddings shape: {embeddings.shape} (dim={dim})")

    # Build FAISS index
    index = faiss.IndexFlatIP(dim)  # Inner product (works with normalized vectors = cosine similarity)
    index.add(embeddings)
    print(f"[5/5] FAISS index built: {index.ntotal} vectors")

    # Save everything
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # FAISS index
    index_path = os.path.join(OUTPUT_DIR, "faiss_index.bin")
    faiss.write_index(index, index_path)
    print(f"     Saved index -> {index_path}")

    # Metadata (chunk texts + metadata)
    meta_path = os.path.join(OUTPUT_DIR, "chunks_metadata.json")
    # Only save metadata (not full text) to keep file small; full text can be re-read from source
    meta_list = []
    for _, m in all_chunks:
        meta_list.append(m)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta_list, f, ensure_ascii=False, indent=2)
    print(f"     Saved metadata -> {meta_path}")

    # Save config for loading
    config = {
        "docs_dir": DOCS_DIR,
        "embedding_model": EMBEDDING_MODEL,
        "dim": dim,
        "index_type": "IndexFlatIP",
        "chunk_count": len(all_chunks),
    }
    config_path = os.path.join(OUTPUT_DIR, "config.json")
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
    print(f"     Saved config -> {config_path}")

    print(f"\nDone! Knowledge base saved to: {OUTPUT_DIR}")
    print(f"  - {len(all_chunks)} chunks indexed")
    print(f"  - Use query_kb.py to search the index")


if __name__ == "__main__":
    build_kb()
