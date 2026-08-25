# Copyright 2026 Aaron John Schlosser, PhD
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0

from pathlib import Path
import argparse

import torch
from peft import PeftConfig, PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ADAPTER_DIRECTORY = Path(
    "/home/aaron/src/derrida/derrida-qwen3-4b-lora7"
)

FALLBACK_BASE_MODEL = "Qwen/Qwen3-4B-Instruct-2507"

SYSTEM_MESSAGE = (
    "You are a Derrida studies research assistant. "
    "Ground textual claims in the supplied sources. "
    "Distinguish quotation, paraphrase, and interpretation. "
    "Distinguish Derrida's own claims from claims attributed to other authors. "
    "Do not invent quotations, citations, page numbers, or bibliographical details."
)


# ---------------------------------------------------------------------------
# Load adapter configuration
#
# The LoRA adapter config normally records which base model it was trained on.
# ---------------------------------------------------------------------------

if not ADAPTER_DIRECTORY.exists():
    raise FileNotFoundError(
        f"Adapter directory does not exist: {ADAPTER_DIRECTORY}"
    )


peft_config = PeftConfig.from_pretrained(
    str(ADAPTER_DIRECTORY)
)

BASE_MODEL = (
    peft_config.base_model_name_or_path
    or FALLBACK_BASE_MODEL
)

print(f"Base model: {BASE_MODEL}")
print(f"Adapter:    {ADAPTER_DIRECTORY}")


# ---------------------------------------------------------------------------
# Tokenizer
#
# IMPORTANT:
# Load the tokenizer from the BASE MODEL, not from the LoRA adapter directory.
# ---------------------------------------------------------------------------

tokenizer = AutoTokenizer.from_pretrained(
    BASE_MODEL
)

if tokenizer.pad_token_id is None:
    tokenizer.pad_token = tokenizer.eos_token


# ---------------------------------------------------------------------------
# Load base model
#
# Do NOT use Mxfp4Config(dequantize=True).
#
# Keeping the native GPT-OSS MXFP4 weights is important on a 16 GB GPU.
# ---------------------------------------------------------------------------

if not torch.cuda.is_available():
    raise RuntimeError(
        "CUDA is required for this GPT-OSS configuration."
    )

print(
    "GPU:",
    torch.cuda.get_device_name(0)
)

print(
    "VRAM:",
    round(
        torch.cuda.get_device_properties(0).total_memory
        / (1024 ** 3),
        2,
    ),
    "GiB",
)


base_model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,

    # Preserve the model's native quantized representation.
    torch_dtype="auto",

    # For inference, allow Transformers to place the model appropriately.
    device_map="auto",

    use_cache=True,
)


# ---------------------------------------------------------------------------
# Attach LoRA adapter
# ---------------------------------------------------------------------------

model = PeftModel.from_pretrained(
    base_model,
    str(ADAPTER_DIRECTORY),
    is_trainable=False,
)

model.eval()


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------

def generate(
    prompt: str,
    max_new_tokens: int = 768,
    temperature: float = 0.3,
    top_p: float = 0.9,
) -> str:

    messages = [
        {
            "role": "system",
            "content": SYSTEM_MESSAGE,
        },
        {
            "role": "user",
            "content": prompt,
        },
    ]

    # apply_chat_template produces the exact input format expected by the
    # GPT-OSS tokenizer.
    inputs = tokenizer.apply_chat_template(
        messages,
        add_generation_prompt=True,
        return_tensors="pt",
        return_dict=True,
    )

    # Put the token tensors on the same device as the model's input embeddings.
    input_device = model.get_input_embeddings().weight.device

    inputs = {
        key: value.to(input_device)
        for key, value in inputs.items()
    }

    generation_kwargs = {
        "max_new_tokens": max_new_tokens,
        "do_sample": temperature > 0,
        "pad_token_id": tokenizer.pad_token_id,
        "eos_token_id": tokenizer.eos_token_id,
    }

    if temperature > 0:
        generation_kwargs.update(
            {
                "temperature": temperature,
                "top_p": top_p,
            }
        )

    with torch.inference_mode():
        output = model.generate(
            **inputs,
            **generation_kwargs,
        )

    # Remove the prompt tokens and decode only the generated continuation.
    prompt_length = inputs["input_ids"].shape[-1]

    generated_tokens = output[0][prompt_length:]

    response = tokenizer.decode(
        generated_tokens,
        skip_special_tokens=True,
    )

    return response.strip()


# ---------------------------------------------------------------------------
# CLI / interactive mode
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "prompt",
        nargs="*",
        help="Prompt to send to the Derrida model",
    )

    parser.add_argument(
        "--max-new-tokens",
        type=int,
        default=768,
    )

    parser.add_argument(
        "--temperature",
        type=float,
        default=0.3,
    )

    parser.add_argument(
        "--top-p",
        type=float,
        default=0.9,
    )

    args = parser.parse_args()

    if args.prompt:
        prompt = " ".join(args.prompt)

        response = generate(
            prompt,
            max_new_tokens=args.max_new_tokens,
            temperature=args.temperature,
            top_p=args.top_p,
        )

        print(response)
        return

    # Interactive mode.
    print()
    print("Derrida research assistant")
    print("Type 'quit' or 'exit' to stop.")
    print()

    while True:
        try:
            prompt = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not prompt:
            continue

        if prompt.lower() in {
            "quit",
            "exit",
        }:
            break

        try:
            response = generate(
                prompt,
                max_new_tokens=args.max_new_tokens,
                temperature=args.temperature,
                top_p=args.top_p,
            )

            print()
            print(response)
            print()

        except torch.cuda.OutOfMemoryError:
            print()
            print("CUDA out of memory.")
            print(
                "Try lowering --max-new-tokens or close other GPU applications."
            )
            print()

            torch.cuda.empty_cache()


if __name__ == "__main__":
    main()