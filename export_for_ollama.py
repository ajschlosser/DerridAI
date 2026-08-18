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
Merge the trained literary-critic LoRA adapter into SmolLM2.

Input:
    literary-critic-lora/

Output:
    literary-critic-merged/

The output is a complete standalone Hugging Face model that Ollama
can import. This does not alter or delete the original LoRA adapter.
"""

from pathlib import Path

from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer


#BASE_MODEL = "HuggingFaceTB/SmolLM2-360M-Instruct"
BASE_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
ADAPTER_DIRECTORY = Path("derrida-qwen-lora")
OUTPUT_DIRECTORY = Path("derrida-qwen-merged")


def main():
    if not ADAPTER_DIRECTORY.exists():
        raise FileNotFoundError(
            f"Could not find {ADAPTER_DIRECTORY.resolve()}\n"
            "Run finetune_pretrained.py first."
        )

    print(f"Loading original model: {BASE_MODEL}")

    # SmolLM2-360M is small enough that merging it on the CPU is practical.
    base_model = AutoModelForCausalLM.from_pretrained(BASE_MODEL)

    print(f"Loading LoRA adapter: {ADAPTER_DIRECTORY}")

    model_with_adapter = PeftModel.from_pretrained(
        base_model,
        ADAPTER_DIRECTORY,
    )

    print("Merging LoRA weights into the original model...")

    # This produces a normal standalone Transformers model.
    # safe_merge=True also checks for invalid NaN values while merging.
    merged_model = model_with_adapter.merge_and_unload(
        safe_merge=True
    )

    print(f"Saving merged model to: {OUTPUT_DIRECTORY}")

    merged_model.save_pretrained(
        OUTPUT_DIRECTORY,
        safe_serialization=True,
    )

    # Ollama also needs the tokenizer and its chat-template configuration.
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    tokenizer.save_pretrained(OUTPUT_DIRECTORY)

    print("\nExport complete.")
    print(f"Merged model: {OUTPUT_DIRECTORY.resolve()}")


if __name__ == "__main__":
    main()
