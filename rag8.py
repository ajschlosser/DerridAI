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
import json
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.document_transformers import LongContextReorder
from sentence_transformers import CrossEncoder
import nltk
import re
import toons
import argparse
from prompts import (
    query_improvement_template,
    focused_prompt_template,
    #focused_prompt_template_claims,
)

from defaults import CHAT_TEMPERATURE, keys
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

args = argparse.ArgumentParser()
args.add_argument("-p", "--prompt", type=str, default="defaults", help="The prompt for DerriDAI to use")
args = args.parse_args()

LOG = Logger.setup("rag8.py")

def strip_code_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:toon|json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()

from client import RAG_LLM

client = RAG_LLM()
reranker = CrossEncoder(
    "cross-encoder/ms-marco-MiniLM-L-6-v2"
)

def prompt(params: dict, store: str = "defaults", toon: bool = False) -> tuple:
    start = time.perf_counter()
    LOG.info("Generating prompt with parameters...")
    default_system_prompts = [
        "Your name is DerridAI.",
        "You are a helpful AI research assistant specializing in the works of Jacques Derrida.",
        "Users can give you prompts like 'Explain Derrida's concept of deconstruction.' or 'What does Derrida say about hospitality?'",
    ]
    system_messages = params["system"] if "system" in params else [("system", message) for message in default_system_prompts]
    user_messages = [("user", params["user"])] if "user" in params else [("user", "{prompt}")]
    template = ChatPromptTemplate([
        *system_messages,
        *user_messages,
    ])
    prompt_value = template.invoke(params["template"])

    LOG.info(f"Invoking prompt...")
    response = client.chat(store if store else client.key).invoke(prompt_value)
    cleaned_response = strip_code_fence(response.content)
    if toon:
        try:
            cleaned_response = toons.loads(cleaned_response)
        except Exception as e:
            LOG.warning("Prompt response is not in TOON format: %s", e)
    else:
        try:
            cleaned_response = json.loads(cleaned_response)
        except Exception as e:
            LOG.warning("Prompt response is not in JSON format: %s", e)
    LOG.info("Prompt generation and response completed in %.2f seconds", time.perf_counter() - start)
    return cleaned_response, response

def rerank_top_n(query, docs, reranker, top_n=7):
    start = time.perf_counter()
    pairs = [
        [query, doc.page_content if (hasattr(doc, "page_content")) else doc]
        for doc in docs
    ]

    scores = reranker.predict(pairs)

    ranked_indices = sorted(
        range(len(docs)),
        key=lambda i: float(scores[i]),
        reverse=True
    )
    idx = min(top_n, len(docs) - 1)
    LOG.info("Reranking completed in %.2f seconds", time.perf_counter() - start)
    return [docs[i] for i in ranked_indices[:idx]]

def generate_language_filters(materials_languages: list) -> dict:
    filters = []
    if "en" in materials_languages:
        filters.append({"language": {"$eq": "en_us"}})
    if "fr" in materials_languages:
        filters.append({"language": {"$eq": "fr_fr"}})
    if len(filters) == 1:
        return filters[0]
    return {"$or": filters} if filters else {}

def generate_citation_strings(doc) -> tuple[str, str]:

    author = doc.metadata.get("document_author", doc.metadata.get("speaker"))
    work = doc.metadata.get("work", "")
    edition = doc.metadata.get("edition", "")
    year = doc.metadata.get("year", "")
    page_start = doc.metadata.get("page_start")
    translator = doc.metadata.get("translator", None)
    page_end = doc.metadata.get("page_end")
    author_last_name = author.split(' ')[-1]
    inline_author = author_last_name
    author_name_reversed = f"{author.split(' ')[-1]}, {author.split(' ')[0]}"
    inline_citation = f"({inline_author} {year}, {page_start if (not page_end or page_end == page_start) else f'{page_start}-{page_end}'})"
    full_citation = f"{author_name_reversed}. {work}.{f' {translator} trans.' if translator else ''} {edition}. {year}"
    return inline_citation, full_citation

def generate_context_string(docs: list) -> str:
    context_str = ""
    for i, doc in enumerate(docs):
        doc.metadata["inline_citation"], doc.metadata["full_citation"] = generate_citation_strings(doc)
        d = doc.metadata
        record_id = d.get("record_id", "")
        discourse_role = d.get('discourse_role', 'general text')
        author = d.get("document_author")
        editor = d.get("editor")
        translator = d.get("translator")
        region_author = d.get("region_author", "")
        quoted_speaker = d.get("quoted_speaker", "")
        holder = d.get("position_holder", "")
        speaker = d.get("speaker", "")
        target = d.get("target", "")
        work = d.get("work", "")
        persons = d.get("persons", [])
        topics = d.get("topics", [])

        chat_str = "Say things like: "
        attr_str = f"In this evidence block, which is functioning as {discourse_role}, "

        if region_author:
            attr_str += f'the writer of this particular section of the work is "{region_author}", '
            chat_str += f"\n- In {author}'s **{work}**, {region_author} writes that {holder if (holder not in author and holder not in region_author and holder not in speaker) else 'he'} believes that {target} ..."
        if quoted_speaker:
            attr_str += f'the quoted speaker is "{quoted_speaker}", '
            chat_str += f"\n- {quoted_speaker} is quoted in this passage as saying that {target}..."
        if holder:
            attr_str += f"it is {holder}'s position being expressed, " 
            chat_str += f"\n- In the passage, {holder} claims that {target}..."
        if speaker:
            attr_str += f"{speaker} is the one doing the speaking/writing, " 
            chat_str += f"\n- In the cited text, {speaker} says clearly that {target}..."
        if target:
            attr_str += f"the target of {holder}'s claim is {target}, "
            chat_str += f"\n- In this excerpt, {holder} takes aim at {target}, writing that ..."
        if persons:
            attr_str += f"the persons mentioned in this passage are {' and '.join(persons)}, "
            chat_str += f"\n- {speaker} mentions {' and '.join(persons)} when {holder if holder is not speaker else 'he'} says that {target}..."
        if topics:
            attr_str += f"the topics discussed in this passage are {' and '.join(topics)}, "
            chat_str += f"\n- The passage discusses {' and '.join(persons + topics)} in relation to {target}..."

        attr_str += f"and the passage is from **{work}** ({d.get('year')}) by {author}. "
        chat_str += f"\n- As far back as {d.get('year')}, {author} wrote in **{work}** that {target} ..."
        if translator:
            attr_str += f" The work is translated by: {translator}. "
        if editor:
            attr_str += f" The editor of the work is: {editor}. "

        context_str += f"""<EVIDENCE>
Evidence ID: {i} | Record ID: {record_id}
Text: {d.get("text")}
To cite the evidence in this block, use MLA format:
 - MLA inline: {d.get("inline_citation")}
 - MLA full works cited: {d.get("full_citation")}
</EVIDENCE>
"""
    return context_str

K_VALUE = 98
FETCH_K_VALUE = 500
LAMBDA_MULT_VALUE = 0.7
CHAT_TEMPERATURE = 0.4

# Fetch queries
def handle_fetch_query(keywords: list[str]):
    print("ok fetch", keywords)
    
# MAIN FUNCTION
def main():
    elapsed = time.perf_counter() - start
    LOG.info("Cold start time: %.4f seconds", elapsed)

    # 1. QUERY DETAILS
    q, _ = prompt({
        "user": query_improvement_template,
        "template": { "prompt": args.prompt }
    })
    LOG.info("Response: %s", q)
    if q["is_fetch_query"]:
        handle_fetch_query(q['keywords'])
    total_elapsed = time.perf_counter() - start
    LOG.info("Time it took to process the initial query: %.4f seconds", total_elapsed - elapsed)
    document_languages = q["materials_languages"]

    # 2. LOOKUP
    def basic_lookup(
        mmr_filter: dict = { "k": K_VALUE, "fetch_k": FETCH_K_VALUE, "lambda_mult": LAMBDA_MULT_VALUE },
        similarity_filter: dict = { "k": K_VALUE },
        search_types: list[str] = ["mmr", "similarity"],
        languages: list[str] = ["en", "fr"],
        split: bool = True,
    ) -> list[dict]:
        start = time.perf_counter()
        all_results = []
        if split:
            mmr_filter["k"] = mmr_filter["k"] // 2
            similarity_filter["k"] = similarity_filter["k"] // 2

        for search_type in search_types:
            for lang in languages:
                LOG.info(f"Starting search for type: {search_type} in language: {lang}")
                retriever = client.store(f"derrida8_primary_{lang}").as_retriever(
                    search_kwargs=mmr_filter if search_type == "mmr" else similarity_filter,
                    search_type=search_type,
                )
                invocation_str = f"'{q['prompt_query' if lang == 'en' else 'prompt_query_fr']}'"
                LOG.info(f"Invoking {search_type} retriever with query: {invocation_str}")
                results = retriever.invoke(invocation_str)
                LOG.info(f"Total {search_type} results: {len(results)}")
                all_results += results
        elapsed = time.perf_counter() - start
        LOG.info("Basic lookup completed in %.4f seconds", elapsed)
        return all_results

    # Basic MMR and similarity lookup
    basic_results = basic_lookup(languages=document_languages)

    # Canonical MMR and similarity lookup
    keywords = q['keywords'] if "en" in document_languages else []
    keywords += q['keywords_fr'] if "fr" in document_languages else []
    LOG.info("Retrieving canonical works by keyword: %s", keywords)
    canonical_work_ids = []
    for keyword in keywords:
        for lang in document_languages:
            if keyword.lower() in keys.get(lang, {}):
                canonical_work_ids.append(keys[lang][keyword.lower()])

    combined_work_ids = [item for sublist in (canonical_work_ids) for item in sublist]
    LOG.info("Canonical work IDs to retrieve documents from: %s", canonical_work_ids)
    canonical_filter = {
        "$or": [{"canonical_work_id": {"$eq": work_id}} for work_id in combined_work_ids]
    }
    LOG.info("Canonical filter: %s", canonical_filter)
    combined_canonical_results = basic_lookup(
        mmr_filter={
            "k": K_VALUE // 2,
            "fetch_k": FETCH_K_VALUE,
            "lambda_mult": LAMBDA_MULT_VALUE,
            "filter": canonical_filter,
        },
        similarity_filter={
            "k": K_VALUE // 2,
            "filter": canonical_filter,
        },
        languages=document_languages,
    )
    LOG.info("Canonical results retrieved: %d", len(combined_canonical_results))

    # Basic English keyword MMR lookup
    keyword_filter = {
        "$or": [{"target": {"$eq": keyword}} for keyword in q['keywords'] if "en" in document_languages]
              + [{"target": {"$eq": keyword}} for keyword in q['keywords_fr'] if "fr" in document_languages]
              + [{"concepts": {"$contains": keyword}} for keyword in q['keywords'] if "en" in document_languages]
              + [{"concepts": {"$contains": keyword}} for keyword in q['keywords_fr'] if "fr" in document_languages]
    }
    LOG.info("Keyword filter: %s", keyword_filter)
    keyword_results = basic_lookup(
        mmr_filter={
            "k": K_VALUE // 4,
            "fetch_k": FETCH_K_VALUE,
            "lambda_mult": LAMBDA_MULT_VALUE,
            "filter": keyword_filter,
        },
        similarity_filter={
            "k": K_VALUE // 4,
            "filter": keyword_filter,
        },
        languages=document_languages,
    )
    LOG.info("Keyword results retrieved: %d", len(keyword_results))
    total_retrieved_count = len(basic_results) + len(combined_canonical_results) + len(keyword_results)
    LOG.info("Total results retrieved: %d", total_retrieved_count)
    combined_initial_results = basic_results + combined_canonical_results + keyword_results

    # Deduplication
    seen_id = []
    deduplicated_results = []
    for doc in combined_initial_results:
        id = doc.metadata.get("record_id")
        if id not in seen_id:
            seen_id.append(id)
            deduplicated_results.append(doc)

    LOG.info("Total results after deduplication: %d", len(deduplicated_results))

    # 3. POST-PROCESSING RETRIEVAL
    # Reordering and reranking
    LOG.info("Reordering context groups with LongContextReorder...")
    reordering = LongContextReorder()
    reordered_results = reordering.transform_documents(deduplicated_results)
    LOG.info("Reranking top_n results with the reranker...")
    rerank_prompt = q["prompt_query"] + "\n" + q["prompt_query_fr"]
    reranked_results = rerank_top_n(rerank_prompt, reordered_results, reranker)
    LOG.info("Total results after top_n reranking: %d", len(reranked_results))

    # Build context string
    context = generate_context_string(reranked_results)
    LOG.info(f"Context:\n{context}")

    # 4. PROMPTING
    # Focused prompt
    LOG.info("Invoking focused prompt...")
    r, _ = prompt({
        "user": focused_prompt_template,
        "store": "derrida8_primary_en",
        "template": {
            "prompt_query": q["prompt_query"],
            "prompt_instructions": q["prompt_instructions"],
            "context": context,
        }
    })
    LOG.info("Focused prompt response: %s", r)

    # 4. WRAP-UP
    LOG.info("Original query: %s", q)
    total_elapsed = time.perf_counter() - start
    LOG.info("Total time elapsed: %.4f seconds", total_elapsed)
    LOG.info(f"k: {K_VALUE} | fetch_k: {FETCH_K_VALUE} | lambda_mult: {LAMBDA_MULT_VALUE} | chat_temperature: {CHAT_TEMPERATURE}")
    LOG.info(f"initial mmr and similarity results: {len(basic_results)} | combined canonical results: {len(combined_canonical_results)} | keyword results: {len(keyword_results)} | total combined retrieved: {total_retrieved_count} | total after deduplication: {len(deduplicated_results)} | total after reranking: {len(reranked_results)}")
    return

if __name__ == "__main__":
    main()