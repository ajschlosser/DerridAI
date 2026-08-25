# Copyright 2026 Aaron John Schlosser, PhD

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://apache.org

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Generate literary criticism with the pretrained model plus your LoRA adapter.

After running finetune_pretrained.py, use either:

    python run_critic.py passage.txt

or:

    python run_critic.py

The second form accepts pasted multiline text. Enter a line containing only
END when the passage is complete.
"""

import argparse
import sys
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer


#BASE_MODEL = "HuggingFaceTB/SmolLM2-360M-Instruct"
ADAPTER_DIRECTORY = "derrida-lora7"
BASE_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"

DEFAULT_INSTRUCTION = (
    "You are a careful deconstructionist, post-structuralist literary critic influenced by Jacques Derrida, Michel Foucault, and Roland Barthes."
)


def read_passage(path_argument):
    """Read a passage from a file, redirected input, or the terminal."""

    if path_argument:
        passage_path = Path(path_argument)

        if not passage_path.is_file():
            raise FileNotFoundError(f"Could not find {passage_path}.")

        return passage_path.read_text(encoding="utf-8").strip()

    # This supports commands such as: python run_critic.py < passage.txt
    if not sys.stdin.isatty():
        return sys.stdin.read().strip()

    print("Paste the literary or otherwise textual passage below.")
    print("When finished, enter a line containing only END.\n")

    lines = []

    while True:
        try:
            line = input()
        except EOFError:
            break

        if line == "END":
            break

        lines.append(line)

    return "\n".join(lines).strip()


parser = argparse.ArgumentParser(
    description="Generate a close reading using your LoRA literary critic."
)
parser.add_argument(
    "passage_file",
    nargs="?",
    help="Optional UTF-8 text file containing the passage.",
)
parser.add_argument(
    "--instruction",
    default=DEFAULT_INSTRUCTION,
    help="Override the default critical instruction.",
)
parser.add_argument(
    "--max-new-tokens",
    type=int,
    default=300,
    help="Maximum response length in model tokens.",
)
parser.add_argument(
    "--temperature",
    type=float,
    default=0.6,
    help="Sampling randomness; lower values are more predictable.",
)
args = parser.parse_args()


passage = read_passage(args.passage_file)

if not passage:
    raise ValueError("The passage is empty.")

if args.max_new_tokens < 1:
    raise ValueError("--max-new-tokens must be at least 1.")

if args.temperature <= 0:
    raise ValueError("--temperature must be greater than zero.")


adapter_path = Path(ADAPTER_DIRECTORY)
if not adapter_path.is_dir():
    raise FileNotFoundError(
        f"Could not find {ADAPTER_DIRECTORY}. Run finetune_pretrained.py first."
    )


if torch.cuda.is_available():
    device = "cuda"
elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
    device = "mps"
else:
    device = "cpu"

print(f"Loading model on {device}...")


# The adapter directory contains the saved tokenizer and chat template. The
# original base weights are loaded separately and then combined with LoRA.
tokenizer = AutoTokenizer.from_pretrained(ADAPTER_DIRECTORY)
base_model = AutoModelForCausalLM.from_pretrained(BASE_MODEL)
model = PeftModel.from_pretrained(base_model, ADAPTER_DIRECTORY)
model = model.to(device)
model.eval()


messages = [
    {
        "role": "system",
        "content": (
            "You are a Derrida studies research assistant. Ground textual claims in the supplied sources."
        ),
    },
    {
        "role": "user",
        #"content": f"{args.instruction}\n\nPassage:\n{passage}",
        "content": passage,
    },
]


model_inputs = tokenizer.apply_chat_template(
    messages,
    add_generation_prompt=True,
    tokenize=True,
    return_dict=True,
    return_tensors="pt",
).to(device)


with torch.no_grad():
    generated = model.generate(
        **model_inputs,
        max_new_tokens=args.max_new_tokens,
        do_sample=False,
        repetition_penalty=1.05,
        pad_token_id=tokenizer.eos_token_id,
    )


# Decode only newly generated tokens, excluding the prompt.
prompt_length = model_inputs["input_ids"].shape[1]
new_tokens = generated[0, prompt_length:]
response = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

print("\nRunning literary criticism with the following parameters:")
print(f"Max new tokens: {args.max_new_tokens}")
print(f"Model: {BASE_MODEL} + {ADAPTER_DIRECTORY}")
print("\n--- Literary criticism ---\n")
print(response)


