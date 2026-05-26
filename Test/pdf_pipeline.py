"""
PDF Document Intelligence Pipeline

Parses a PDF → chunks text → extracts structure via Claude API →
embeds with sentence-transformers → stores in ChromaDB → supports
natural-language querying.
"""

import json
import os
import re
import sys
import uuid
from typing import Optional

import chromadb
import pdfplumber
from anthropic import Anthropic
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError
from sentence_transformers import SentenceTransformer

load_dotenv()


# ---------------------------------------------------------------------------
# Pydantic schema for structured extraction
# ---------------------------------------------------------------------------

class Entity(BaseModel):
    name: str
    type: str  # person | org | date | technical_term


class ChunkStructure(BaseModel):
    document_title: Optional[str] = None
    section_heading: Optional[str] = None
    key_topics: list[str] = []
    summary: str = ""
    entities: list[Entity] = []


# ---------------------------------------------------------------------------
# 1. PARSE
# ---------------------------------------------------------------------------

def _reconstruct_columns(page) -> str:
    """
    Detect and handle two-column layouts by sorting words into left/right
    columns and reassembling them independently before joining.
    """
    words = page.extract_words(x_tolerance=3, y_tolerance=3)
    if not words:
        return ""

    xs = [w["x0"] for w in words]
    x_min, x_max = min(xs), max(xs)
    page_width = x_max - x_min

    # Only attempt column split if there is a meaningful gap in the middle third
    mid_low = x_min + page_width * 0.35
    mid_high = x_min + page_width * 0.65
    mid_words = [w for w in words if mid_low <= w["x0"] <= mid_high]
    mid_density = len(mid_words) / max(len(words), 1)

    if mid_density > 0.15:
        # Dense middle → single-column, return default extraction
        return page.extract_text(x_tolerance=3, y_tolerance=3) or ""

    # Two-column layout
    midpoint = (x_min + x_max) / 2
    left = [w for w in words if w["x0"] < midpoint]
    right = [w for w in words if w["x0"] >= midpoint]

    def words_to_text(word_list):
        lines: dict[int, list] = {}
        for w in word_list:
            top = round(w["top"] / 5) * 5  # bucket by 5-pt rows
            lines.setdefault(top, []).append(w)
        result = []
        for top in sorted(lines):
            line_words = sorted(lines[top], key=lambda w: w["x0"])
            result.append(" ".join(w["text"] for w in line_words))
        return "\n".join(result)

    return words_to_text(left) + "\n" + words_to_text(right)


def parse_pdf(file_path: str) -> list[dict]:
    """Extract text from every page, skipping scanned/empty pages gracefully."""
    print(f"  Opening: {file_path}")
    pages = []

    with pdfplumber.open(file_path) as pdf:
        total = len(pdf.pages)
        for i, page in enumerate(pdf.pages):
            raw = page.extract_text(x_tolerance=3, y_tolerance=3) or ""

            if len(raw.strip()) < 20:
                print(f"  [WARN] Page {i + 1}/{total} appears scanned or empty — skipping")
                continue

            # Try column-aware extraction; fall back to raw if it's shorter
            col_text = _reconstruct_columns(page)
            text = col_text if len(col_text) > len(raw) else raw

            pages.append({"page_num": i + 1, "text": text.strip()})
            print(f"  Page {i + 1}/{total}: {len(text.strip())} chars extracted")

    return pages


# ---------------------------------------------------------------------------
# 2. CHUNK
# ---------------------------------------------------------------------------

def _token_estimate(text: str) -> int:
    """Rough 4-chars-per-token estimate."""
    return max(1, len(text) // 4)


def chunk_text(
    pages: list[dict],
    chunk_size: int = 500,
    overlap: int = 50,
) -> list[dict]:
    """
    Sentence-aware chunking.  Sentences are never split mid-way; overlap
    is achieved by carrying the tail sentences of the previous chunk into
    the next one.
    """
    full_text = " ".join(p["text"] for p in pages)

    # Split on sentence-ending punctuation followed by whitespace
    raw_sentences = re.split(r"(?<=[.!?])\s+", full_text.strip())
    sentences = [s.strip() for s in raw_sentences if s.strip()]

    chunks: list[dict] = []
    current: list[str] = []
    current_tokens = 0

    for sentence in sentences:
        s_tokens = _token_estimate(sentence)

        if current_tokens + s_tokens > chunk_size and current:
            chunks.append({"text": " ".join(current), "chunk_index": len(chunks)})

            # Build overlap tail from the end of the current chunk
            tail: list[str] = []
            tail_tokens = 0
            for s in reversed(current):
                t = _token_estimate(s)
                if tail_tokens + t > overlap:
                    break
                tail.insert(0, s)
                tail_tokens += t

            current = tail
            current_tokens = tail_tokens

        current.append(sentence)
        current_tokens += s_tokens

    if current:
        chunks.append({"text": " ".join(current), "chunk_index": len(chunks)})

    return chunks


# ---------------------------------------------------------------------------
# 3. EXTRACT STRUCTURE
# ---------------------------------------------------------------------------

_EXTRACTION_PROMPT = """\
Analyze the following text chunk and extract structured information.

Text:
{text}

Return a JSON object with exactly these fields:
- document_title  : string or null
- section_heading : string or null
- key_topics      : list of strings (main topics)
- summary         : string (1-2 sentences)
- entities        : list of objects, each with "name" (string) and "type"
                    (one of: person, org, date, technical_term)

Return ONLY valid JSON — no markdown fences, no extra text."""


def _strip_fences(text: str) -> str:
    text = re.sub(r"^```(?:json)?\s*", "", text.strip())
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def extract_structure(chunk: dict, client: Anthropic) -> ChunkStructure:
    """Call Claude to extract structured metadata from one chunk."""
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": _EXTRACTION_PROMPT.format(text=chunk["text"]),
            }
        ],
    )
    raw = _strip_fences(response.content[0].text)
    data = json.loads(raw)
    return ChunkStructure(**data)


def extract_structure_safe(chunk: dict, client: Anthropic) -> ChunkStructure:
    """Wrapper that returns a default ChunkStructure on any extraction failure."""
    try:
        return extract_structure(chunk, client)
    except json.JSONDecodeError as exc:
        print(f"\n  [WARN] Chunk {chunk['chunk_index']}: JSON decode error — {exc}")
    except ValidationError as exc:
        print(f"\n  [WARN] Chunk {chunk['chunk_index']}: schema validation error — {exc}")
    except Exception as exc:
        print(f"\n  [WARN] Chunk {chunk['chunk_index']}: unexpected error — {exc}")
    return ChunkStructure(summary="Extraction failed.")


# ---------------------------------------------------------------------------
# 4. EMBED + STORE
# ---------------------------------------------------------------------------

def embed_and_store(
    chunks: list[dict],
    structures: list[ChunkStructure],
    embedder: SentenceTransformer,
    collection,
) -> None:
    """Embed chunks and upsert into a ChromaDB collection."""
    texts = [c["text"] for c in chunks]
    print(f"  Encoding {len(texts)} chunks…")
    embeddings = embedder.encode(texts, show_progress_bar=True).tolist()

    ids = [str(uuid.uuid4()) for _ in chunks]
    metadatas = [
        {
            "chunk_index": c["chunk_index"],
            "document_title": s.document_title or "",
            "section_heading": s.section_heading or "",
            "key_topics": ", ".join(s.key_topics),
            "summary": s.summary,
            "entities": json.dumps([e.model_dump() for e in s.entities]),
        }
        for c, s in zip(chunks, structures)
    ]

    collection.add(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)
    print(f"  Stored {len(chunks)} chunks in collection '{collection.name}'")


# ---------------------------------------------------------------------------
# 5. QUERY
# ---------------------------------------------------------------------------

def query_collection(
    question: str,
    embedder: SentenceTransformer,
    collection,
    top_k: int = 5,
) -> list[dict]:
    """Embed a question and retrieve the top-k most relevant chunks."""
    q_embedding = embedder.encode([question]).tolist()
    results = collection.query(
        query_embeddings=q_embedding,
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )
    return [
        {
            "text": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i],
        }
        for i in range(len(results["documents"][0]))
    ]


# ---------------------------------------------------------------------------
# 6. MAIN — wire it all together
# ---------------------------------------------------------------------------

def main(pdf_path: str, test_query: str = "What are the main topics in this document?"):
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY is not set. Add it to a .env file.")

    print("\n" + "=" * 55)
    print("   PDF DOCUMENT INTELLIGENCE PIPELINE")
    print("=" * 55)

    # --- Stage 1: Parse ---
    print("\n[1/5] PARSING PDF")
    pages = parse_pdf(pdf_path)
    if not pages:
        print("  ERROR: No extractable text found. All pages may be scanned.")
        sys.exit(1)
    print(f"  → {len(pages)} page(s) with text")

    # --- Stage 2: Chunk ---
    print("\n[2/5] CHUNKING TEXT  (chunk_size=500 tokens, overlap=50 tokens)")
    chunks = chunk_text(pages, chunk_size=500, overlap=50)
    print(f"  → {len(chunks)} chunks created")

    # --- Stage 3: Extract structure ---
    print("\n[3/5] EXTRACTING STRUCTURE via Claude API")
    client = Anthropic(api_key=api_key)
    structures: list[ChunkStructure] = []
    for i, chunk in enumerate(chunks):
        print(f"  Processing chunk {i + 1}/{len(chunks)}…", end="\r", flush=True)
        structures.append(extract_structure_safe(chunk, client))
    print(f"\n  → Structure extracted for {len(structures)} chunks")

    # --- Stage 4: Embed + store ---
    print("\n[4/5] EMBEDDING + STORING IN CHROMADB")
    embedder = SentenceTransformer("all-MiniLM-L6-v2")
    chroma_client = chromadb.Client()
    collection = chroma_client.get_or_create_collection("pdf_chunks")
    embed_and_store(chunks, structures, embedder, collection)

    # --- Stage 5: Query ---
    print(f"\n[5/5] QUERYING")
    print(f"  Question: \"{test_query}\"")
    results = query_collection(test_query, embedder, collection, top_k=3)

    print(f"\n{'─' * 55}")
    print(f"  TOP {len(results)} RESULTS")
    print(f"{'─' * 55}")
    for i, r in enumerate(results):
        m = r["metadata"]
        print(f"\n  [Result {i + 1}]  distance={r['distance']:.4f}")
        print(f"  Title:   {m['document_title'] or '(unknown)'}")
        print(f"  Section: {m['section_heading'] or '(none)'}")
        print(f"  Topics:  {m['key_topics'] or '(none)'}")
        print(f"  Summary: {m['summary']}")
        print(f"  Snippet: {r['text'][:220].strip()}…")

    print(f"\n{'=' * 55}")
    print("  PIPELINE COMPLETE")
    print(f"{'=' * 55}\n")
    return results


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python pdf_pipeline.py <pdf_path> [\"query string\"]")
        sys.exit(1)

    pdf = sys.argv[1]
    q = sys.argv[2] if len(sys.argv) > 2 else "What are the main topics in this document?"
    main(pdf, q)
