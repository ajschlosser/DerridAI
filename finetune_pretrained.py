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

from pathlib import Path

from datasets import load_dataset
from peft import LoraConfig
from transformers.trainer_utils import get_last_checkpoint
from trl import SFTConfig, SFTTrainer


#MODEL_NAME = "HuggingFaceTB/SmolLM2-360M-Instruct"
RECORDS_FILE = "/home/aaron/src/derrida/data/records.jsonl"
#OUTPUT_DIRECTORY = "/home/aaron/src/derrida/derrida-lora"
MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct"
OUTPUT_DIRECTORY = "derrida-qwen-lora"

# Load the same JSONL records used by the educational Transformer.
dataset = load_dataset(
    "json",
    data_files=RECORDS_FILE,
    split="train",
)


def convert_record(record):
    response = record["response"]

    if record.get("mode") == "knowledge":
        system_message = (
            "You are a knowledgeable literary scholar. "
            "Answer factual questions directly and concisely. "
            "If you genuinely do not know, say so."
        )
        user_message = record["instruction"]
    elif record.get("mode") == "primary_source":
        # These records are shaped like this:
        # {"id": "jacques-derrida-of-grammatology-text", "mode": "primary_source", "passage": "In a totally different context, we have elsewhere specified the epoch of writing as the suspension of being-upright (\"Force et signification\" and \"La parole souffiee\" in L'ecriture et la difference) . 32. Bk.", "page_number": "332", "author": "Jacques Derrida", "source_title": "Of Grammatology", "publisher": "Editions de Minuit"}
        system_message = (
            f"You are a knowledgeable literary scholar who knows the text {record['source_title']} intimately. "    
        )
        user_message = f"What happened on page {record['page_number']} of {record['source_title']} by {record['author']}?"
        response = record["passage"]
    else:
        system_message = (
            "You are a careful deconstructionist, post-structuralist literary critic. Ground every claim "
            "in the supplied passage and never invent quotations."
        )
        user_message = (
            f"{record['instruction']}\n\n"
            f"Passage:\n{record['passage']}"
        )

    return {
        "prompt": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message},
        ],
        "completion": [
            {"role": "assistant", "content": response},
        ],
    }


dataset = dataset.map(
    convert_record,
    remove_columns=dataset.column_names,
)


# LoRA adds small trainable matrices while leaving the pretrained weights
# frozen. "all-linear" avoids relying on architecture-specific layer names.
lora_config = LoraConfig(
    task_type="CAUSAL_LM",
    target_modules="all-linear",
    r=8,
    lora_alpha=16,
    lora_dropout=0.05,
)


training_config = SFTConfig(
    output_dir=OUTPUT_DIRECTORY,

    # Start conservatively. Gradient accumulation gives an effective batch
    # size of eight examples while loading only one example at a time.
    per_device_train_batch_size=1,
    gradient_accumulation_steps=8,

    num_train_epochs=3,
    learning_rate=1e-4,
    max_length=16384,

    # Since the dataset has separate prompt and completion fields, only the
    # desired assistant completion contributes to the loss.
    completion_only_loss=True,

    logging_steps=1,
    save_strategy="epoch",
    save_total_limit=2,
    report_to="none",
)


trainer = SFTTrainer(
    model=MODEL_NAME,
    args=training_config,
    train_dataset=dataset,
    peft_config=lora_config,
)


# Automatically continue from the most recent saved training checkpoint.
output_path = Path(OUTPUT_DIRECTORY)

last_checkpoint = (
    get_last_checkpoint(str(output_path))
    if output_path.exists()
    else None
)

trainer.train(resume_from_checkpoint=last_checkpoint)

# Save the final LoRA adapter and tokenizer-related files.
trainer.save_model(OUTPUT_DIRECTORY)

print(f"Saved the literary-criticism adapter to {OUTPUT_DIRECTORY}")
