# PDF Document Intelligence Pipeline

A local, end-to-end pipeline that turns a PDF into a queryable knowledge base using the Claude API, sentence-transformers, and ChromaDB — all running on your machine.

## What it does

| Stage | Description |
|---|---|
| **Parse** | Extracts text with `pdfplumber`, handles multi-column layouts, skips scanned/empty pages |
| **Chunk** | Splits text into sentence-aware chunks (configurable size + overlap) |
| **Extract** | Calls Claude (`claude-sonnet-4-20250514`) to produce structured JSON per chunk |
| **Embed + Store** | Embeds chunks with `all-MiniLM-L6-v2` and stores them in a local ChromaDB collection |
| **Query** | Takes a natural-language question, embeds it, and returns the top-k most relevant chunks |

## Structured schema

Each chunk is analyzed into a `ChunkStructure` Pydantic model:

```python
class ChunkStructure(BaseModel):
    document_title:  Optional[str]
    section_heading: Optional[str]
    key_topics:      list[str]
    summary:         str
    entities:        list[Entity]   # name + type (person|org|date|technical_term)
```

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Copy and fill in your API key
cp .env.example .env
# edit .env and set ANTHROPIC_API_KEY=sk-ant-...
```

## Usage

```bash
# Basic — uses a default test query
python pdf_pipeline.py path/to/document.pdf

# With a custom query
python pdf_pipeline.py path/to/document.pdf "Who are the key people mentioned?"
```

### Example output

```
=======================================================
   PDF DOCUMENT INTELLIGENCE PIPELINE
=======================================================

[1/5] PARSING PDF
  Page 1/8: 2341 chars extracted
  ...
  → 8 page(s) with text

[2/5] CHUNKING TEXT  (chunk_size=500 tokens, overlap=50 tokens)
  → 21 chunks created

[3/5] EXTRACTING STRUCTURE via Claude API
  → Structure extracted for 21 chunks

[4/5] EMBEDDING + STORING IN CHROMADB
  Encoding 21 chunks…
  Stored 21 chunks in collection 'pdf_chunks'

[5/5] QUERYING
  Question: "What are the main topics in this document?"

  [Result 1]  distance=0.2813
  Title:   Introduction to Machine Learning
  Section: Overview
  Topics:  machine learning, supervised learning, neural networks
  Summary: This section introduces core ML concepts and terminology.
  Snippet: Machine learning is a subset of artificial intelligence …
```

## Configuration

All tunable parameters are arguments to the core functions:

| Parameter | Default | Where |
|---|---|---|
| `chunk_size` | `500` tokens | `chunk_text()` |
| `overlap` | `50` tokens | `chunk_text()` |
| `top_k` | `5` | `query_collection()` |
| Claude model | `claude-sonnet-4-20250514` | `extract_structure()` |
| Embedding model | `all-MiniLM-L6-v2` | `main()` |

## File structure

```
Test/
├── pdf_pipeline.py   # Full pipeline implementation
├── requirements.txt  # Python dependencies
├── .env.example      # Template for API key
└── README.md         # This file
```

## Error handling

- **Scanned pages**: detected by low character count, logged and skipped.
- **LLM JSON errors**: `extract_structure_safe()` catches `JSONDecodeError` and `ValidationError`, logs a warning, and substitutes a blank `ChunkStructure` so the rest of the pipeline continues.
- **Missing API key**: raises a clear `EnvironmentError` before any API call is made.
