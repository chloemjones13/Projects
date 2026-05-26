# PDF Document Intelligence Pipeline

A local, end-to-end pipeline that turns a PDF into a queryable knowledge base.
Works with **any LLM provider** — Anthropic, OpenAI, Google, Mistral, Cohere, Ollama, and more — via [LiteLLM](https://docs.litellm.ai).

## What it does

| Stage | Description |
|---|---|
| **Parse** | Extracts text with `pdfplumber`, handles multi-column layouts, skips scanned/empty pages |
| **Chunk** | Splits text into sentence-aware chunks (configurable size + overlap) |
| **Extract** | Calls any LLM via LiteLLM to produce structured JSON per chunk |
| **Embed + Store** | Embeds chunks with `all-MiniLM-L6-v2` and stores them in a local ChromaDB collection |
| **Query** | Takes a natural-language question, embeds it, and returns the top-k most relevant chunks |

## Supported providers

| Provider | Example model string | Required env var |
|---|---|---|
| Anthropic (default) | `claude-sonnet-4-20250514` | `ANTHROPIC_API_KEY` |
| OpenAI | `gpt-4o` | `OPENAI_API_KEY` |
| Google Gemini | `gemini/gemini-1.5-pro` | `GEMINI_API_KEY` |
| Mistral | `mistral/mistral-large-latest` | `MISTRAL_API_KEY` |
| Cohere | `cohere/command-r-plus` | `COHERE_API_KEY` |
| Ollama (local) | `ollama/llama3` | *(none)* |

Any model supported by LiteLLM works — see the [full list](https://docs.litellm.ai/docs/providers).

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

# 2. Copy and fill in the API key for your chosen provider
cp .env.example .env
# edit .env — only set the key for the provider you'll use
```

## Usage

```bash
# Default provider (Anthropic claude-sonnet-4-20250514)
python pdf_pipeline.py path/to/document.pdf

# Custom query
python pdf_pipeline.py path/to/document.pdf "Who are the key people mentioned?"

# Switch to a different provider with --model
python pdf_pipeline.py doc.pdf "Summarize" --model gpt-4o
python pdf_pipeline.py doc.pdf "Key findings" --model gemini/gemini-1.5-pro
python pdf_pipeline.py doc.pdf "Main topics" --model ollama/llama3

# Pin a default model via env var so you don't need --model every time
LLM_MODEL=gpt-4o python pdf_pipeline.py doc.pdf
```

### Example output

```
=======================================================
   PDF DOCUMENT INTELLIGENCE PIPELINE
   Model: gpt-4o
=======================================================

[1/5] PARSING PDF
  Page 1/8: 2341 chars extracted
  ...
  → 8 page(s) with text

[2/5] CHUNKING TEXT  (chunk_size=500 tokens, overlap=50 tokens)
  → 21 chunks created

[3/5] EXTRACTING STRUCTURE  [gpt-4o]
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

| Parameter | Default | How to set |
|---|---|---|
| LLM model | `claude-sonnet-4-20250514` | `--model <string>` or `LLM_MODEL` env var |
| `chunk_size` | `500` tokens | edit `main()` call to `chunk_text()` |
| `overlap` | `50` tokens | edit `main()` call to `chunk_text()` |
| `top_k` | `3` (main), `5` (function default) | edit `main()` call to `query_collection()` |
| Embedding model | `all-MiniLM-L6-v2` | edit `main()` |

## File structure

```
Test/
├── pdf_pipeline.py   # Full pipeline implementation
├── requirements.txt  # Python dependencies
├── .env.example      # Template for API keys
└── README.md         # This file
```

## Error handling

- **Scanned pages**: detected by low character count, logged and skipped.
- **LLM JSON errors**: `extract_structure_safe()` catches `JSONDecodeError` and `ValidationError`, logs a warning, and substitutes a blank `ChunkStructure` so the rest of the pipeline continues.
- **Wrong/missing API key**: LiteLLM raises a descriptive `AuthenticationError`; the pipeline prints the error and moves on to the next chunk.
