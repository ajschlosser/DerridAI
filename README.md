![Jacques Derrida](https://www.philomag.com/sites/default/files/styles/sidebar_full_image/public/images/derrida_leemage.prt385js_042-copie.jpg)

# DerridAI RAG + LoRA Project

DerridAI is a minimal Python implementation of a Retrieval‑Augmented Generation (RAG) pipeline combined with a LoRA fine-tuning workflow, purpose-built for philosophical and literary texts — primarily the works of Jacques Derrida.

The RAG pipeline embeds source documents into a local [Chroma](https://www.trychroma.com/) vector store and queries them via an [Ollama](https://ollama.com/)-served language model, producing responses grounded in primary sources. The LoRA workflow fine-tunes a small causal language model (Qwen 2.5-0.5B-Instruct by default) into a deconstructionist literary critic, exports the merged weights, and makes the result available as an Ollama custom model.

---

## Prerequisites

- Python 3.10+
- [Ollama](https://ollama.com/) running locally at `http://localhost:11434` with the `nomic-embed-text` embedding model and your chosen chat model pulled
- A source data file at `./data/derrida3.jsonl` (JSONL records with at minimum `text`/`passage`, `author`, `source_title`, and `record_type` fields)
- A GPU with sufficient VRAM is recommended for fine-tuning

---

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

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
| `--keyword` | `false` | Weight retrieval toward keyword-matched texts |
| `--min` | `5` | Minimum number of sentences in the response |
| `--max` | `5` | Maximum number of sentences in the response |
| `--also` | `"- You must double-check your work at the end."` | Extra instructions appended to the prompt |
| `--model` | `gpt-oss:20b` | Ollama chat model to use |

---

## LoRA Fine-Tuning (`finetune_pretrained.py`)

Fine-tune `Qwen/Qwen2.5-0.5B-Instruct` (or another base model) on your JSONL corpus using supervised fine-tuning with LoRA via the `trl` / `peft` libraries. The adapter is saved to `derrida-qwen-lora/`.

```bash
python finetune_pretrained.py
```

Update the `RECORDS_FILE`, `MODEL_NAME`, and `OUTPUT_DIRECTORY` constants at the top of the file to change the data source, base model, or output path.

---

## Export for Ollama (`export_for_ollama.py`)

Merge the trained LoRA adapter back into the base model weights and save a standalone Hugging Face model to `derrida-qwen-merged/`. This directory is what the `Modelfile` references.

```bash
python export_for_ollama.py
```

Once merged, register the model with Ollama:

```bash
ollama create derrida-critic -f Modelfile
```

---

## Running the Critic (`run_critic.py`)

Generate a close reading of a passage using the fine-tuned LoRA adapter directly (without Ollama).

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

---

## Contributing

Feel free to submit pull requests or open issues. Ensure the style guidelines are followed and tests pass before merging.

---

