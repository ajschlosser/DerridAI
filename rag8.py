#!/usr/bin/env python3

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

"""rag8.py -- Retrieval-augmented generation demo with CLI controls and progress logs."""

import os
os.environ["TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD"] = "1"
import time
from langchain_core.prompts import ChatPromptTemplate
import nltk
import re
import toons
from prompts import (
    query_improvement_template,
)
from logger import Logger

start = time.perf_counter()

# DOWNLOAD NECESSARY NLTK DATA
try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("punkt")

try:
    nltk.data.find("tokenizers/punkt_tab")
except LookupError:
    nltk.download("punkt_tab")

LOG = Logger.setup("rag8.py")

def strip_code_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:toon|json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()

from client import RAG_LLM

client = RAG_LLM()


def prompt(params: dict, toon: bool = True) -> tuple:
    LOG.info("Generating prompt with parameters: %s", params)
    default_system_prompts = [
        "Your name is DerridAI.",
        "You are a helpful AI research assistant specializing in the works of Jacques Derrida.",
    ]
    if toon:
        default_system_prompts.append("You must always respond in TOON format.")
        default_system_prompts.append("Use TOON schema definitions, default values, and example responses as guidance.")
    system_messages = params["system"] if "system" in params else [("system", message) for message in default_system_prompts]
    user_messages = [("user", params["user"])] if "user" in params else [("user", "{prompt}")]

    template = ChatPromptTemplate([
        *system_messages,
        *user_messages,
    ])
    prompt_value = template.invoke(params["template"])
    response = client.chat().invoke(prompt_value)
    cleaned_response = strip_code_fence(response.content)
    if toon:
        try:
            cleaned_response = toons.loads(cleaned_response)
        except Exception as e:
            LOG.warning("Prompt response is not in TOON format: %s", e)
    return (cleaned_response, response)

def handle_fetch_query():
    print("ok")

def generate_language_filters(materials_language: list) -> dict:
    filters = []
    if "en" in materials_language:
        filters.append({"language": {"$eq": "en_us"}})
    if "fr" in materials_language:
        filters.append({"language": {"$eq": "fr_fr"}})
    if len(filters) == 1:
        return filters[0]
    return {"$or": filters} if filters else {}
        

K_VALUE = 64
FETCH_K_VALUE = 500
LAMBDA_MULT_VALUE = 0.7

start = time.perf_counter()
# MAIN FUNCTION
def main():
    elapsed = time.perf_counter() - start
    LOG.info("Time it took to get things set up: %.4f seconds", elapsed)

    # Get query details
    q, _ = prompt({
        "user": query_improvement_template,
        "template": { "prompt": "Fetch me every mention of hospitality and Levinas in Derrida." }
    })
    LOG.info("Response: %s", q)

    if q["is_fetch_query"]:
        handle_fetch_query()

    total_elapsed = time.perf_counter() - start
    LOG.info("Time it took to process the initial query: %.4f seconds", total_elapsed - elapsed)


    # BASIC LOOKUP
    # Set up default filters
    # TODO: Have separate collections for common
    default_mmr_search_kwargs = {
        "k": K_VALUE // 4 if q["keywords"] or q["keywords_fr"] else K_VALUE,
        "fetch_k": FETCH_K_VALUE,
        "lambda_mult": LAMBDA_MULT_VALUE,
        "filter": {
            "$and": [
                {
                    "$or": [
                        {"position_holder": {"$eq": "Jacques Derrida"}},
                        {"speaker": {"$eq": "Jacques Derrida"}}
                    ]
                },
                {
                    "$and": [
                        {"region_author": { "$eq": "Jacques Derrida"}},
                        {"discourse_role": {"$nin": ["citation", "footnote", "endnote", "commentary", "bibliography"]}},
                        {"region_type": {"$eq": "main_text"}},
                        {"primary_text": {"$eq": True}},
                        # {"text_length": {"$gt": 300}},
                        {"extraction_quality": {"$gt": 0.8}}
                    ]   
                }
            ]
        }
    }

    retriever = client.store().as_retriever(
        search_kwargs=default_mmr_search_kwargs,
        search_type="mmr"
    )
    results = retriever.invoke(f"'{q['prompt_query']}'\n'{q['prompt_query_fr']}'\n{q['keywords'] + q['keywords_fr']}")

    lookup_elapsed = time.perf_counter() - total_elapsed

    LOG.info("Results: %d", len(results))
    total_elapsed = time.perf_counter() - start
    LOG.info("Time it took for lookup: %.4f seconds", lookup_elapsed)
    LOG.info("Total time elapsed: %.4f seconds", lookup_elapsed - total_elapsed)

    return

if __name__ == "__main__":
    main()