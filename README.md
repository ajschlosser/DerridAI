![Jacques Derrida](https://www.philomag.com/sites/default/files/styles/sidebar_full_image/public/images/derrida_leemage.prt385js_042-copie.jpg)

# DerridAI

DerridAI is a local-first Python project for:

1. Retrieval-augmented generation (RAG) over a Derrida-focused corpus (`rag.py`)
2. LoRA fine-tuning for literary criticism (`finetune_pretrained.py`)
3. Running the fine-tuned critic directly (`run_critic.py`)
4. Exporting a merged model for Ollama (`export_for_ollama.py` + `Modelfile`)

## Repository layout

- `/home/runner/work/DerridAI/DerridAI/rag.py` — main RAG CLI
- `/home/runner/work/DerridAI/DerridAI/config/` — defaults + CLI argument parsing + env/arg overrides
- `/home/runner/work/DerridAI/DerridAI/store/store.py` — Chroma initialization and incremental indexing
- `/home/runner/work/DerridAI/DerridAI/models/models.py` — Ollama embedding/chat model factories
- `/home/runner/work/DerridAI/DerridAI/helpers/` — logging, query parsing, retrieval helpers
- `/home/runner/work/DerridAI/DerridAI/finetune_pretrained.py` — LoRA supervised fine-tuning
- `/home/runner/work/DerridAI/DerridAI/run_critic.py` — inference with base model + LoRA adapter
- `/home/runner/work/DerridAI/DerridAI/export_for_ollama.py` — merge adapter into standalone model
- `/home/runner/work/DerridAI/DerridAI/server/server/server.py` — simple HTTP wrapper that streams `rag6.py` output

## Requirements

- Python 3.10+
- Local Ollama server at `http://localhost:11434`
- Models available in Ollama for RAG:
  - Embeddings: `bge-m3:latest` (default)
  - Chat: `gpt-oss:20b` (default)
- A JSONL corpus file at the configured source path (default: `./data/derrida6_multi.jsonl`)

Install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## RAG usage (`rag.py`)

Run:

```bash
python rag.py --query "What does Derrida say about presence?"
```

Examples:

```bash
# Filter by author/title
python rag.py --query "What is trace?" --author "Jacques Derrida"
python rag.py --query "What is trace?" --title "Of Grammatology"

# Exhaustive mention search
python rag.py --find-all "différance" --title "Of Grammatology"

# Rebuild vector store
python rag.py --query "What is pharmakon?" --force-rebuild

# Switch model
python rag.py --query "What is iterability?" --model "llama3"
```

### `rag.py` CLI options

| Flag | Default | Description |
|---|---|---|
| `--query`, `-q` | `What does Derrida say about presence?` | Prompt/question to run |
| `--find-all` | `None` | Return all exact mentions of a term |
| `--author` | `None` | Filter by author |
| `--title` | `None` | Filter by source title |
| `--record-type` | `primary_source` | Filter by record type (`all` disables) |
| `--force-rebuild` | `False` | Rebuild vector store from source JSONL |
| `--cheat` | `False` | Disable inline citations and use bibliography mode |
| `--keyword` | `False` | Enable keyword-to-text weighting |
| `--thorough` | `False` | Run a second editorial improvement pass |
| `--min` | `5` | Minimum sentence count target |
| `--max` | `5` | Maximum sentence count target |
| `--also` | `- You must double-check your work at the end.` | Extra prompt instruction |
| `--bibliography` | `False` | Append works cited processing |
| `--model` | `gpt-oss:20b` | Chat model override |
| `--recursions` | `0` | Recursive review count (parsed; currently not consumed in `rag.py`) |

## Configuration defaults

Current defaults in `/home/runner/work/DerridAI/DerridAI/config/defaults.py`:

- `EMBEDDING_MODEL = "bge-m3:latest"`
- `CHAT_MODEL = "gpt-oss:20b"`
- `CHAT_TEMPERATURE = 0.5`
- `OLLAMA_SERVER_URL = "http://localhost:11434"`
- `DB_PATH = "./chroma_db_local-tuned6_multilang"`
- `SOURCE_TEXT = "./data/derrida6_multi.jsonl"`
- `BATCH_SIZE = 1000`
- `K_VALUE = 30`
- `FETCH_K_VALUE = 1000`
- `LAMBDA_MULT_VALUE = 0.7`

You can override these via matching environment variables and/or CLI flags where available.

## Fine-tuning workflow

### 1) Train LoRA adapter

```bash
python finetune_pretrained.py
```

Important: update constants in `finetune_pretrained.py` before running (notably `RECORDS_FILE`, which currently points to a machine-specific absolute path).

### 2) Run the critic directly

```bash
# From a file
python run_critic.py passage.txt

# Interactive paste mode (type END on its own line to finish)
python run_critic.py
```

Key options:

- `--instruction`
- `--max-new-tokens` (default `300`)
- `--temperature` (default `0.6`)

### 3) Export merged model for Ollama

```bash
python export_for_ollama.py
ollama create derrida-critic -f Modelfile
```

## Optional local HTTP server

A simple streaming server is available at:

- `/home/runner/work/DerridAI/DerridAI/server/server/server.py`

Run:

```bash
python server/server/server.py
```

By default it serves on `http://localhost:8000/` and streams output from `rag6.py` via `/api/execute`.

## Project status notes

- There is currently no `tests/` directory in this repository.
- The primary maintained RAG entrypoint appears to be `rag.py`; `rag6.py` is still present and used by the lightweight server wrapper.

## Contributing

Issues and pull requests are welcome.
