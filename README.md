![Jacques Derrida](https://www.philomag.com/sites/default/files/styles/sidebar_full_image/public/images/derrida_leemage.prt385js_042-copie.jpg)

# DerridAI RAG Project

DerridAI is a minimal Python implementation of a Retrieval‑Augmented Generation (RAG) pipeline for philosophical texts, centred on the works of Jacques **Derrida**. The code is organised into the following key components:

* **Vector store** – Documents are embedded with the *nomic‑embed‑text* model and stored in a local [Chroma](https://www.trychroma.com/) database.
* **RAG driver** – `rag.py` queries the vector store using an Ollama‑served chat model.
* **Utility helpers** – `src/derrida/store/store.py` exposes a global :class:`Chroma` instance and helper functions.
* **Configuration** – Default settings live in `src/derrida/config/defaults.py` and are re‑exported from `src/derrida/config/__init__.py`.
* **Logging** – All modules import :func:`src.derrida.logging.get_logger` so logs are consistent.
* **Data** – Source JSONL documents are expected in `src/derrida/data/derrida3.jsonl`.
* **Tests** – A test suite in `src/derrida/tests/` validates behaviour.

The project is intentionally minimal – it can be run from a single command line without any framework scaffolding.

## Prerequisites

* **Python 3.10+** – the project is tested against CPython 3.11.
* **Ollama** – running locally at `http://localhost:11434`. The default embedding model is `nomic-embed-text`; the default chat model is `gpt‑oss:20b` (you can override via CLI).
* **Source data** – a JSONL file at `src/derrida/data/derrida3.jsonl` containing at least the fields `text`, `author`, `source_title`, and `record_type`.
* **Optional** – a GPU with sufficient VRAM if you plan to fine‑tune a LoRA adapter.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## RAG Pipeline (`rag.py`)

Query a local Chroma vector store built from the source JSONL corpus. On first run (or with `--force-rebuild`) the store is created automatically.

```bash
# Ask a question (builds the vector store on first run)
python rag.py --query "Explain Derrida's concept of différance"

# Filter results to a specific author or text
python rag.py --query "What is trace?" --author "Jacques Derrida"
python rag.py --query "What is trace?" --title "Of Grammatology"

# Force a full rebuild of the vector store
python rag.py --query "What is presence?" --force-rebuild

# Use a different Ollama chat model
python rag.py --query "What is iterability?" --model "llama3"
```

### `rag.py` options

| Flag | Default | Description |
|------|---------|-------------|
| `--query`, `-q` | `"What does Derrida say about presence?"` | Question to ask the pipeline |
| `--author` | — | Filter vector search by author |
| `--title` | — | Filter vector search by source title |
| `--record-type` | `primary_source` | Filter by record type; pass `all` to disable |
| `--force-rebuild` | `false` | Rebuild the Chroma store from source JSONL |
| `--cheat` | `false` | Whether to cite sources in the response |
| `--keyword` | `false` | Weight retrieval toward keyword‑matched texts |
| `--min` | `5` | Minimum number of sentences in the response |
| `--max` | `5` | Maximum number of sentences in the response |
| `--also` | `"- You must double-check your work at the end."` | Extra instructions appended to the prompt |
| `--model` | `gpt-oss:20b` | Ollama chat model to use |

## Example output

In response to a query like "What would Derrida say about **Flamin' Hot Cheetos**?" a typical response might be:

>In sum, Derrida would likely read a Flamin’ Hot Cheeto not as a mere snack but as a performative text that exemplifies différance, the trace, and the destabilisation of binary oppositions. The heat of the chip defers meaning, the brand and packaging create a network of differences, and the act of consumption becomes a covert crossing that challenges the eater’s expectations. Through these lenses, the snack becomes a site for philosophical interrogation, illustrating how everyday objects can reveal the structures of meaning that Derrida sought to expose.

## LoRA Fine‑Tuning (`finetune_pretrained.py`)

Fine‑tune `Qwen/Qwen2.5-0.5B-Instruct` (or another base model) on your JSONL corpus using supervised fine‑tuning with LoRA via the `trl` / `peft` libraries. The adapter is saved to `derrida-qwen-lora/`.

```bash
python finetune_pretrained.py
```

Update the `RECORDS_FILE`, `MODEL_NAME`, and `OUTPUT_DIRECTORY` constants at the top of the file to change the data source, base model, or output path.

## Export for Ollama (`export_for_ollama.py`)

Merge the trained LoRA adapter back into the base model weights and save a standalone Hugging Face model to `derrida-qwen-merged/`. This directory is what the `Modelfile` references.

```bash
python export_for_ollama.py
```

Once merged, register the model with Ollama:

```bash
ollama create derrida-critic -f Modelfile
```

## Running the Critic (`run_critic.py`)

Generate a close reading of a passage using the fine‑tuned LoRA adapter directly (without Ollama).

```bash
# Pass a text file
python run_critic.py passage.txt

# Paste a passage interactively (type END on its own line to finish)
python run_critic.py
```

### `run_critic.py` options

| Flag | Default | Description |
|------|---------|-------------|
| `passage_file` (positional) | — | Optional path to a UTF-8 text file |
| `--instruction` | Deconstructionist system prompt | Override the critical instruction |
| `--max-new-tokens` | `300` | Maximum response length in tokens |
| `--temperature` | `0.6` | Sampling temperature |

## Contributing

Feel free to submit pull requests or open issues. Ensure the style guidelines are followed and tests pass before merging.
