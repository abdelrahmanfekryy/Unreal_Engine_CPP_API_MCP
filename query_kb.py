#!/usr/bin/env python3
"""
Query the UE5 API FAISS knowledge base.
Usage:
    python query_kb.py "how to spawn an actor in ue5"
    python query_kb.py "character movement component jump" -n 5
"""

import os
import sys
import json
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss

# --- Configuration (must match build_faiss_kb.py) ---
KB_DIR = "/media/abdelrahman/Data/MCP-UE5/ue5_faiss_kb"
DOCS_DIR = "/media/abdelrahman/Data/MCP-UE5/epic_api_docs_5.6"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"


def load_config():
    config_path = os.path.join(KB_DIR, "config.json")
    with open(config_path, "r") as f:
        return json.load(f)


def load_metadata():
    meta_path = os.path.join(KB_DIR, "chunks_metadata.json")
    with open(meta_path, "r") as f:
        return json.load(f)


def load_index():
    index_path = os.path.join(KB_DIR, "faiss_index.bin")
    return faiss.read_index(index_path)


def query(query_text: str, top_k: int = 5):
    # Load model, index, metadata
    print(f"Loading model: {EMBEDDING_MODEL} ...")
    model = SentenceTransformer(EMBEDDING_MODEL, device="cpu")

    print("Loading FAISS index ...")
    index = load_index()

    print("Loading metadata ...")
    metadata = load_metadata()

    print(f"\nQuery: '{query_text}'\n")
    print("-" * 70)

    # Embed query
    query_emb = model.encode([query_text], normalize_embeddings=True)
    query_vec = query_emb.astype("float32")

    # Search
    scores, indices = index.search(query_vec, min(top_k, len(metadata)))

    for rank in range(len(indices[0])):
        idx = indices[0][rank]
        score = float(scores[0][rank])
        meta = metadata[idx]

        # Read the relevant portion from the source file
        fpath = os.path.join(DOCS_DIR, meta["file"])
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                lines = f.readlines()
                # Show ~10 lines around the chunk
                total = meta.get("total_chunks", 1)
                file_lines = meta.get("file_lines", len(lines))
                chunk_idx = meta.get("file_chunk_idx", 0)
                line_per_chunk = file_lines / max(total, 1)
                line_start = int(chunk_idx * line_per_chunk) - 3
                line_end = int((chunk_idx + 1) * line_per_chunk) + 3
                line_start = max(0, line_start)
                line_end = min(len(lines), line_end)
                preview = "".join(lines[line_start:line_end]).strip()
        except Exception:
            preview = "(could not read source file)"

        print(f"  [{rank+1}] score={score:.4f}  |  {meta['doc_name']} ({meta['file']})")
        fc = meta.get("file_chunk_idx", meta.get("chunk_id", "?"))
        print(f"      Chunk {fc}/{meta.get('total_chunks', '?')}")
        print(f"      {preview[:200]}...")
        print()


def main():
    top_k = 5
    if "-n" in sys.argv:
        idx = sys.argv.index("-n")
        top_k = int(sys.argv[idx + 1])
        sys.argv.pop(idx)
        sys.argv.pop(idx)

    if len(sys.argv) < 2:
        print(__doc__)
        print("Usage: python query_kb.py <query> [-n <top_k>]")
        sys.exit(1)

    query_text = " ".join(sys.argv[1:])
    query(query_text, top_k)


if __name__ == "__main__":
    main()
