![Jacques Derrida](https://www.philomag.com/sites/default/files/styles/sidebar_full_image/public/images/derrida_leemage.prt385js_042-copie.jpg)

# DerridAI RAG + LoRA Project

DerridAI minimal Python implementation of a retrieval‑augmented generation (RAG) + LoRA pipeline. A Retrieval-Augmented Generation (RAG) pipeline is a system architecture that enhances large language models (LLMs) by fetching factual data from external knowledge bases at query time. The project demonstrates how to embed documents, store the embeddings locally, and query them with a language model, producing responses with direct references to and synthesis of primary sources.

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

