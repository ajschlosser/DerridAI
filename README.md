# Derrida‑Qwen Project

This repository contains a fine‑tuned **Qwen‑2.5‑0.5B‑Instruct** model adapted for literary criticism and a small helper package to generate deconstructionist close readings.

---

## Project layout
```
├── data/                 # Raw data files (records.jsonl, training sets, etc.)
├── derrida-merged/       # Merged base model and LoRA adapter (used by `run_critic.py`)
├── derrida-lora/         # LoRA adapter and model card
│   ├── README.md         # Detailed model card (kept separate from root README)
│   └── …                 # Model files, checkpoints, tokenizer, template
├── finetune_pretrained.py
├── run_critic.py
├── requirements.txt
├── export_for_ollama.py
├── Modelfile
└── README.md             # ← this file
```

## Prerequisites
* Python 3.11+ (recommended).  Use a virtual environment.
* PyTorch 2.13+ (CPU or CUDA).  For GPU use an NVIDIA card with the matching CUDA toolkit.
* `pip install -r requirements.txt`

The `requirements.txt` contains the runtime dependencies (`torch`, `transformers`, `peft`, `trl`).

## Finetuning
The LoRA was trained with the script `finetune_pretrained.py`.  It expects a base model in `HuggingFaceTB/SmolLM2-360M-Instruct`, a data folder with JSONL examples, and uses TRL with SFT.  After training the LoRA weights are copied into `derrida-lora`.

```
python finetune_pretrained.py \
    --data_dir ./data \
    --output_dir ./derrida-lora \
    --base_model HuggingFaceTB/SmolLM2-360M-Instruct
```

## Running the critic
The executable `run_critic.py` loads `Qwen/Qwen2.5-0.5B-Instruct` and the LoRA from `derrida-qwen-lora`.  Provide a textual passage either as a file or via standard input.

### Command‑line usage
```bash
# Using a file
python run_critic.py passage.txt

# Inline passage: press ENTER for a new line, finish with a line containing only END
python run_critic.py

# Optional flags
--instruction "<custom instruction>"
--max-new-tokens N
--temperature x
```

The script prints:
1. The instruction used.
2. Model details.
3. The generated literary criticism.

### Example
```text
If you had a time machine, but could only go to the past or the future once and never return, which would you choose and why?

Response: …
```

## Using with Ollama
The `export_for_ollama.py` script builds an `ollama export`‑compatible tarball that can be loaded into an Ollama local instance.

```
python export_for_ollama.py
```

## Model card
For detailed model provenance, training settings, and licensing, see `derrida-lora/README.md`.

## Contributing
Pull requests are welcome.  Please run the test suite (`pytest`) before submitting.

## License
This project is released under the Apache‑2.0 license.  See the `LICENSE` file for details.
