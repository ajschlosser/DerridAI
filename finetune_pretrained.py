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
import json

from datasets import Features, Value, load_dataset
from peft import LoraConfig
from transformers.trainer_utils import get_last_checkpoint
from trl import SFTConfig, SFTTrainer

from logger import Logger

LOG = Logger.setup("finetune_pretrained")

#MODEL_NAME = "HuggingFaceTB/SmolLM2-360M-Instruct"
RECORDS_FILE = "/home/aaron/src/derrida/data/derrida7_ids-training.jsonl"
#OUTPUT_DIRECTORY = "/home/aaron/src/derrida/derrida-lora7"
#MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct"
MODEL_NAME = "openai/gpt-oss-20b"
OUTPUT_DIRECTORY = "derrida-gpt-oss-lora7"

# Load the same JSONL records used by the educational Transformer.
CLEAN_FILE = "training-records.jsonl"

with open(RECORDS_FILE, encoding="utf-8") as source, open(CLEAN_FILE, "w", encoding="utf-8") as target:
    for line in source:
        record = json.loads(line)
        target.write(json.dumps({
            "topics": record.get("topics", []),
            "work": record.get("work", ""),
            "text": record.get("text", ""),
            "page_start": record.get("page_start", ""),
            "page_end": record.get("page_end", ""),
        }) + "\n")


dataset = load_dataset(
    "json",
    data_files=CLEAN_FILE,
    split="train",
)


def convert_record(record):

    # if record.get("mode") == "knowledge":
    #     system_message = (
    #         "You are a knowledgeable literary scholar. "
    #         "Answer factual questions directly and concisely. "
    #         "If you genuinely do not know, say so."
    #     )
    #     user_message = record["instruction"]
    # elif record.get("mode") == "primary_source":
    #     # These records are shaped like this:
    #     # {"id": "jacques-derrida-of-grammatology-text", "mode": "primary_source", "passage": "In a totally different context, we have elsewhere specified the epoch of writing as the suspension of being-upright (\"Force et signification\" and \"La parole souffiee\" in L'ecriture et la difference) . 32. Bk.", "page_number": "332", "author": "Jacques Derrida", "source_title": "Of Grammatology", "publisher": "Editions de Minuit"}
    #     system_message = (
    #         f"You are a knowledgeable literary scholar who knows the text {record['source_title']} intimately. "    
    #     )
    #     user_message = f"What happened on page {record['page_number']} of {record['source_title']} by {record['author']}?"
    #     response = record["text"]
    # else:

    system_message = (
        "You are a Derrida studies research assistant. Ground textual claims in the supplied sources. Distinguish quotation, paraphrase, and interpretation. Never invent citationss."
    )

    page_number = f"{record['page_start']}{('-' + str(record['page_end'])) if 'page_end' in record else ''}"

    user_message = (
        f"{';'.join(record['topics'])} in {record['work']} on page {page_number}"
    )

    return {
        "prompt": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message},
        ],
        "completion": [
            {"role": "assistant", "content": record["text"]},
        ],
    }

dataset = dataset.map(
    convert_record,
    remove_columns=dataset.column_names,
)

with open('training-data.json', 'r', encoding='utf-8') as file:
    data = json.load(file)
    for record in data:

        record = record["messages"]

        system = record[0]
        user = record[1]
        assistant = record[2]

        dataset.add_item({
            "prompt": [
                {"role": "system", "content": system["content"]},
                {"role": "user", "content": user["content"]},
            ],
            "completion": [
                {"role": "assistant", "content": assistant["content"]}
            ]
        })

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
    #save_strategy="epoch",
    report_to="none",

    save_strategy="steps",
    save_steps=100,
    # Optional evaluation frequency
    # eval_strategy="steps",
    # eval_steps=100,
    # Keep only the 3 most recent checkpoints
    save_total_limit=3,
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
