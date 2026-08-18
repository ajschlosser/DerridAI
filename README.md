# Derrida RAG + LoRA Project

A minimal Python implementation of a retrieval‑augmented generation (RAG) + LoRA pipeline. The project demonstrates how to embed documents, store the embeddings locally, and query them with a language model.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

Run the script with either `--ingest` to create the local vector store or `--query "<your question>"` to get an answer.

```bash
python rag.py --ingest
python rag.py --query "Explain Derrida’s concept of différance"
```

## Contributing

Feel free to submit pull requests or open issues. Ensure the style guidelines are followed and tests pass before merging.

---

Author: A. Aaron 2026

