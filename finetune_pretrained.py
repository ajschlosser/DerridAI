# Copyright 2026 Aaron John Schlosser, PhD
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0

from pathlib import Path
import json

import torch
from datasets import Dataset
from peft import LoraConfig, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer
from transformers.trainer_utils import get_last_checkpoint
from trl import SFTConfig, SFTTrainer

from logger import Logger


LOG = Logger.setup("finetune_pretrained")

MODEL_NAME = "openai/gpt-oss-20b"

RECORDS_FILE = (
    "/home/aaron/src/derrida/data/derrida7_ids-training.jsonl"
)

TRAINING_DATA_FILE = "training-data.json"

BENNINGTON_FILE = "./data/bennington-training.jsonl"

OUTPUT_DIRECTORY = Path(
    "/home/aaron/src/derrida/derrida-gpt-oss-lora7"
)


# ---------------------------------------------------------------------------
# Dataset construction
# ---------------------------------------------------------------------------

SYSTEM_MESSAGE = (
    "You are a Derrida studies research assistant. "
    "Ground textual claims in the supplied sources. "
    "Distinguish quotation, paraphrase, and interpretation. "
    "Never invent citations."
)


def format_page_range(record):
    start = record.get("page_start")
    end = record.get("page_end")

    if start in (None, ""):
        return ""

    if end in (None, "", start):
        return str(start)

    return f"{start}-{end}"


def derrida_record_to_example(record):
    topics = record.get("topics") or []
    work = record.get("work") or ""
    text = record.get("text") or ""

    page_range = format_page_range(record)

    subject = "; ".join(str(topic) for topic in topics)

    pieces = []

    if subject:
        pieces.append(subject)

    if work:
        pieces.append(f"in {work}")

    if page_range:
        pieces.append(f"on page {page_range}")

    user_message = " ".join(pieces)

    return {
        "prompt": [
            {
                "role": "system",
                "content": SYSTEM_MESSAGE,
            },
            {
                "role": "user",
                "content": user_message,
            },
        ],
        "completion": [
            {
                "role": "assistant",
                "content": text,
            },
        ],
    }


def messages_to_example(messages):
    if len(messages) < 3:
        raise ValueError(
            f"Expected at least 3 messages, got {len(messages)}"
        )

    system = messages[0]
    user = messages[1]
    assistant = messages[2]

    return {
        "prompt": [
            {
                "role": "system",
                "content": system["content"],
            },
            {
                "role": "user",
                "content": user["content"],
            },
        ],
        "completion": [
            {
                "role": "assistant",
                "content": assistant["content"],
            },
        ],
    }


examples = []


# Primary Derrida corpus records.
with open(RECORDS_FILE, encoding="utf-8") as file:
    for line in file:
        line = line.strip()

        if not line:
            continue

        record = json.loads(line)

        example = derrida_record_to_example(record)

        if example["completion"][0]["content"].strip():
            examples.append(example)


# Other supervised training examples.
training_data_path = Path(TRAINING_DATA_FILE)

if training_data_path.exists():
    with training_data_path.open(encoding="utf-8") as file:
        data = json.load(file)

    for record in data:
        messages = record.get("messages")

        if messages:
            examples.append(
                messages_to_example(messages)
            )


# Bennington training examples.
bennington_path = Path(BENNINGTON_FILE)

if bennington_path.exists():
    with bennington_path.open(encoding="utf-8") as file:
        for line in file:
            line = line.strip()

            if not line:
                continue

            record = json.loads(line)

            messages = record.get("messages")

            if messages:
                examples.append(
                    messages_to_example(messages)
                )


LOG.info(
    "Constructed dataset containing %d examples",
    len(examples),
)

dataset = Dataset.from_list(examples)

LOG.info("Dataset: %s", dataset)


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------

tokenizer = AutoTokenizer.from_pretrained(
    MODEL_NAME,
)

if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token


# ---------------------------------------------------------------------------
# Model
#
# IMPORTANT:
#
# Do NOT use Mxfp4Config(dequantize=True) on a 16 GB GPU.
#
# gpt-oss-20b already contains its native MXFP4 quantization configuration.
# Loading it normally preserves the quantized MoE weights instead of
# expanding them to BF16.
# ---------------------------------------------------------------------------

if not torch.cuda.is_available():
    raise RuntimeError(
        "CUDA GPU required for this training configuration."
    )


USE_BF16 = torch.cuda.is_bf16_supported()

MODEL_DTYPE = (
    torch.bfloat16
    if USE_BF16
    else torch.float16
)

LOG.info(
    "GPU: %s",
    torch.cuda.get_device_name(0),
)

LOG.info(
    "VRAM: %.2f GiB",
    torch.cuda.get_device_properties(0).total_memory
    / (1024 ** 3),
)

LOG.info(
    "Using dtype: %s",
    MODEL_DTYPE,
)


model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,

    # Preserve the model's native MXFP4 expert weights.
    torch_dtype=MODEL_DTYPE,

    # Force the model onto the GPU instead of allowing device_map="auto"
    # to decide that some weights should be written to disk.
    device_map={"": 0},

    # Saves memory during training.
    use_cache=False,

    # Conservative implementation for fine-tuning.
    attn_implementation="eager",
)

model.config.use_cache = False


# ---------------------------------------------------------------------------
# LoRA
#
# Start with ordinary linear modules. This is considerably less demanding
# than also adapting every MoE expert parameter and is much more realistic
# on a 16 GB card.
#
# "all-linear" will cover the normal linear projections while leaving the
# native MXFP4 expert tensors frozen.
# ---------------------------------------------------------------------------

lora_config = LoraConfig(
    task_type="CAUSAL_LM",

    target_modules="all-linear",

    r=8,
    lora_alpha=16,

    # Keep this at zero initially for GPT-OSS.
    lora_dropout=0.0,

    bias="none",
)


model = get_peft_model(
    model,
    lora_config,
)

model.print_trainable_parameters()


# Required/useful when combining frozen base parameters with gradient
# checkpointing.
if hasattr(model, "enable_input_require_grads"):
    model.enable_input_require_grads()


# ---------------------------------------------------------------------------
# Training configuration
#
# 16k tokens is far too aggressive as a starting point on a 16 GB GPU.
#
# Get 1024 working first. If memory allows:
#
#     1024 -> 2048 -> 4096
#
# ---------------------------------------------------------------------------

training_config = SFTConfig(
    output_dir=str(OUTPUT_DIRECTORY),

    per_device_train_batch_size=1,

    # Effective batch size = 8.
    gradient_accumulation_steps=8,

    num_train_epochs=3,

    learning_rate=1e-4,

    # START SMALL.
    max_length=1024,

    completion_only_loss=True,

    gradient_checkpointing=True,

    gradient_checkpointing_kwargs={
        "use_reentrant": False,
    },

    bf16=USE_BF16,
    fp16=not USE_BF16,

    logging_steps=1,

    report_to="none",

    save_strategy="steps",
    save_steps=100,
    save_total_limit=3,

    # Reduces unnecessary host-memory duplication.
    dataloader_pin_memory=True,
)


# ---------------------------------------------------------------------------
# Trainer
#
# IMPORTANT:
#
# Pass model=model.
#
# Do NOT pass model=MODEL_NAME here. Doing that causes SFTTrainer to reload
# openai/gpt-oss-20b from scratch and recreates the disk-offload problem.
#
# Do NOT pass peft_config here either. We already applied LoRA ourselves.
# ---------------------------------------------------------------------------

trainer = SFTTrainer(
    model=model,
    args=training_config,
    train_dataset=dataset,
    processing_class=tokenizer,
)


# ---------------------------------------------------------------------------
# Resume from checkpoint
# ---------------------------------------------------------------------------

OUTPUT_DIRECTORY.mkdir(
    parents=True,
    exist_ok=True,
)

last_checkpoint = get_last_checkpoint(
    str(OUTPUT_DIRECTORY)
)


if last_checkpoint is not None:
    LOG.info(
        "Resuming from checkpoint: %s",
        last_checkpoint,
    )
else:
    LOG.info(
        "Starting training from base model."
    )


trainer.train(
    resume_from_checkpoint=last_checkpoint,
)


# ---------------------------------------------------------------------------
# Save adapter + tokenizer
# ---------------------------------------------------------------------------

trainer.save_model(
    str(OUTPUT_DIRECTORY)
)

tokenizer.save_pretrained(
    str(OUTPUT_DIRECTORY)
)

LOG.info(
    "Saved LoRA adapter to %s",
    OUTPUT_DIRECTORY,
)

print(
    f"Saved the Derrida adapter to {OUTPUT_DIRECTORY}"
)