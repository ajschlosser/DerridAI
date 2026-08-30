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
print("Starting DerridAI...")

import os
import re
import nltk

from text import (
    detect_languages,
    extract_keywords,
    correct_spelling,
    extract_likeness,
    get_language_status,
    remove_stopwords,
    summarize_text,
    translate,
    extract_query_and_flters,
    detect_phrasing,
    extract_json_objects,
    strip_code_fence
)
os.environ["TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD"] = "1"
import time
import json
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.document_transformers import LongContextReorder
from sentence_transformers import CrossEncoder
import argparse
from prompts import (
    query_improvement_template,
    focused_prompt_template,
    focused_prompt_template_claims,
)

if not nltk.download('punkt', quiet=True):
    nltk.download('punkt')
    nltk.download('punkt_tab')
    nltk.download('stopwords')

from defaults import keys
from logger import Logger

start = time.perf_counter()

args = argparse.ArgumentParser()
args.add_argument("-p", "--prompt", type=str, default="defaults", help="The prompt for DerriDAI to use")
args.add_argument("-n", "--top_n", type=int, default=10, help="The number of top documents to rerank")
args.add_argument("-c", "--claims", type=bool, default=False, help="Use the claims-focused prompt template")
args = args.parse_args()
if args.claims:
    focused_prompt_template = focused_prompt_template_claims

LOG = Logger.setup("rag8.py")

LOG.info("Initializing RAG client...")
from client import RAG_LLM

client = RAG_LLM()
LOG.info("RAG client initialized.")

LOG.info("Initializing reranker...")
reranker = CrossEncoder(
    "cross-encoder/ms-marco-MiniLM-L-6-v2"
)
LOG.info("Reranker initialized.")

def prompt(params: dict, store: str = "defaults", extract_json=False) -> tuple:
    start = time.perf_counter()
    default_system_prompts = [
        "Your name is DerridAI.",
        "You are a helpful AI research assistant specializing in the works of Jacques Derrida.",
    ]
    system_messages = params["system"] if "system" in params else [("system", message) for message in default_system_prompts]
    user_messages = [("user", params["user"])] if "user" in params else [("user", "{prompt}")]
    template = ChatPromptTemplate([
        *system_messages,
        *user_messages,
    ])
    prompt_value = template.invoke(params["template"])
    LOG.info("Invoking prompt... %s", prompt_value)
    response = client.chat(store if store else client.key).invoke(prompt_value)
    cleaned_response = strip_code_fence(response.content, extract_json=extract_json)
    if extract_json:
        try:
            cleaned_response = json.loads(cleaned_response)
        except Exception as e:
            LOG.warning("Prompt response is not in JSON format: %s", e)
    LOG.info("Prompt generation and response completed in %.2f seconds", time.perf_counter() - start)
    return cleaned_response, response

def rerank_top_n(query, docs, reranker, top_n=args.top_n):
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
    translator = doc.metadata.get("translator")
    page_end = doc.metadata.get("page_end", "")
    author_last_name = author.split(' ')[-1]
    inline_author = author_last_name
    author_name_reversed = f"{author.split(' ')[-1]}, {author.split(' ')[0]}"

    if page_start is None:
        pages_cited = ""
    elif page_end is None or page_end == page_start:
        pages_cited = str(page_start)
    else:
        pages_cited = f"{page_start}-{page_end}"
    inline_citation = f"{inline_author} {year}{': ' + pages_cited if pages_cited else ''}"
    full_citation = f"{author_name_reversed}. {work}.{f' {translator} trans.' if translator else ''} {edition}. {year}"
    return inline_citation, full_citation

def generate_context_string(docs: list) -> str:
    context_str = ""
    for i, doc in enumerate(docs):
        doc.metadata["inline_citation"], doc.metadata["full_citation"] = generate_citation_strings(doc)
        d = doc.metadata
        discourse_role = d.get('discourse_role', 'general text')
        holder = d.get("position_holder", "")
        speaker = d.get("speaker", "")
        work = d.get("work", "")
        stance = d.get("stance")
        topics = d.get("topics")
        concepts = d.get("concepts")
        text = " ".join(d.get("text").split())
        context_str += f"""\n<BEGIN EVIDENCE_TAG E{i}>
evidence_tag=[E{i}]
record_id={d.get("record_id")}
speaker={"Derrida" if speaker == "Jacques Derrida" else speaker}
position_holder={holder}{f"\nstance={stance}" if stance else ""}
position_status={d.get("proposition_status", "")}
target={d.get("target", "")}
role={discourse_role}{f"\ntopics={', '.join(topics)}" if topics else ""}{f"\nconcepts={', '.join(concepts)}" if concepts else ""}
text={text}
<END EVIDENCE_TAG E{i}>\n"""
    cleaned_context_str = " ".join(context_str.split())
    return cleaned_context_str

K_VALUE = 32
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

    # 0. PREPROCESSING
    #===========================================
    preprocessing_start = time.perf_counter()
    p = args.prompt
    extracted_filters = extract_query_and_flters(p, "en")
    LOG.info("Extracted filters: %s", extracted_filters)
    languages = detect_languages(p)
    extracted_filters["document_languages"] = ["en", "fr"]
    en, fr = get_language_status(languages)
    if en:
        p_fr = translate(p, from_lang="en", to_lang="fr")
    elif fr:
        p_fr = p
        p = translate(p, from_lang="fr", to_lang="en")
    extracted_filters["prompt"] = p
    extracted_filters["prompt_fr"] = p_fr
    k = extract_keywords(p)
    k_fr = [key.replace("l’", "").replace("L’", "").replace("d’", "").replace("D’", "") for key in translate(", ".join(k), from_lang="en", to_lang="fr").split(", ")]
    extracted_filters["keywords"] = k
    extracted_filters["keywords_fr"] = k_fr
    LOG.info("keywords: %s", k + k_fr)
    limit_fr = detect_phrasing(
        text=p,
        instructions=["only check French sources", "consult only French", "only look at French texts", "use French resources only"]
    )
    if limit_fr:
        extracted_filters["document_languages"] = ["fr"]
    else:
        limit_en = detect_phrasing(
            text=p,
            instructions=["only check English sources", "consult only English", "only look at English texts", "use English resources only"]
        )
        if limit_en:
            extracted_filters["document_languages"] = ["en"]
    extracted_filters["is_fetch_query"] = detect_phrasing(
        text=p,
        instructions=["get me every mention", "fetch all occurrences", "retrieve all instances", "look up all references", "search for all mentions"]
    )
    extracted_filters["is_chatbot_query"] = detect_phrasing(
        text=p,
        instructions=["who are you", "whom do you", "what do you", "respond in the first-person","respond as yourself","tell me about you","talk to me about your","what do you think about","what do you have to say about"]
    )

    preprocessing_elapsed = time.perf_counter() - preprocessing_start
    LOG.info("Preprocessing completed in %.4f seconds", preprocessing_elapsed)

    # 1. QUERY DETAILS
    #===========================================
    query_start = time.perf_counter()
    q, _ = prompt(params={
        "user": query_improvement_template,
        "template": { "prompt": p, "prompt_fr": p_fr }
    }, extract_json=True)
    LOG.info("Response: %s", q)

    q["is_fetch_query"] = extracted_filters["is_fetch_query"]
    q["is_chatbot_query"] = extracted_filters["is_chatbot_query"]
    q = {**q, **extracted_filters}

    LOG.info("Response merged with preprocessing: %s", q)

    if q["is_fetch_query"]:
        handle_fetch_query(q['keywords'])
    document_languages = q["document_languages"]
    query_elapsed = time.perf_counter() - query_start
    LOG.info("Query processing completed in %.4f seconds", query_elapsed)

    # 2. LOOKUP
    #===========================================
    lookup_start = time.perf_counter()
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
    keywords = q['keywords'] if "en" in q["document_languages"] else []
    keywords += q['keywords_fr'] if "fr" in q["document_languages"] else []
    keywords = list(dict.fromkeys(keywords))
    LOG.info("Retrieving canonical works by keyword: %s", keywords)
    canonical_work_ids = q["canonical_work_ids"]
    for keyword in keywords:
        for lang in q["document_languages"]:
            if keyword.lower() in keys.get(lang, {}):
                canonical_work_ids.append(keys[lang][keyword.lower()])
            if keyword in keys.get(lang, {}):
                canonical_work_ids.append(keys[lang][keyword])
    flattened_canonical_work_ids = [item for sublist in canonical_work_ids for item in (sublist if isinstance(sublist, list) else [sublist])]
    deduped_work_ids = list(dict.fromkeys(flattened_canonical_work_ids))
    LOG.info("Canonical work IDs to retrieve documents from: %s", deduped_work_ids)
    if len(deduped_work_ids) > 1:
        canonical_filter = {
            "$or": [{"canonical_work_id": {"$eq": work_id}} for work_id in deduped_work_ids]
        }
    elif len(deduped_work_ids) == 1:
        canonical_filter = {"canonical_work_id": {"$eq": deduped_work_ids[0]}}
    if (len(deduped_work_ids) > 0):
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
    else:
        combined_canonical_results = []

    # Basic English keyword MMR lookup
    keyword_filter = {
        "$or": [{"target": {"$eq": keyword.lower()}} for keyword in q['keywords'] if "en" in document_languages]
              + [{"target": {"$eq": keyword}} for keyword in q['keywords'] if "en" in document_languages]
              + [{"target": {"$eq": keyword.lower()}} for keyword in q['keywords_fr'] if "fr" in document_languages]
              + [{"target": {"$eq": keyword}} for keyword in q['keywords_fr'] if "fr" in document_languages]
              + [{"concepts": {"$contains": keyword.lower()}} for keyword in q['keywords'] if "en" in document_languages]
              + [{"concepts": {"$contains": keyword}} for keyword in q['keywords'] if "en" in document_languages]
              + [{"concepts": {"$contains": keyword.lower()}} for keyword in q['keywords_fr'] if "fr" in document_languages]
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
    lookup_elapsed = time.perf_counter() - lookup_start
    LOG.info("Lookup completed in %.4f seconds", lookup_elapsed)

    # 3. RETRIEVAL POST-PROCESSING
    # ====================================================
    # Reordering and reranking
    post_processing_start = time.perf_counter()
    LOG.info("Reordering context groups with LongContextReorder...")
    reordering = LongContextReorder()
    reordered_results = reordering.transform_documents(deduplicated_results)
    LOG.info("Reranking top_n results with the reranker...")
    rerank_prompt = q["prompt_query"] + "\n" + q["prompt_query_fr"]
    reranked_results = rerank_top_n(rerank_prompt, reordered_results, reranker)
    LOG.info("Total results after top_n reranking: %d", len(reranked_results))
    if (len(reranked_results) == 0):
        LOG.warning("No results retrieved after reranking.")
        exit(0)
    # Generate and store citation strings for each document
    for doc in reranked_results:
        doc.metadata["inline_citation"], doc.metadata["full_citation"] = generate_citation_strings(doc)

    # Build context string
    works = {}
    for i, doc in enumerate(reranked_results):
        works[f"E{i}"] = doc.metadata["inline_citation"]
    LOG.info("Works in reranking: %s", works)
    context = generate_context_string(reranked_results)
    LOG.info(f"Context:\n{context}")
    post_processing_elapsed = time.perf_counter() - post_processing_start
    LOG.info("Post-processing completed in %.4f seconds", post_processing_elapsed)

    # 4. PROMPTING
    # ====================================================
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
    LOG.info("Focused prompt response prior to source binding: %s", r)

    # Citation attribution and source binding
    works_cited_str = ""
    works_cited_seen = []
    for i, doc in enumerate(reranked_results):
        r = re.sub(
            r"\(([^()]*)\)|\[([^\[\]]*)\]",
            lambda group: "(" + re.sub(
                r"\bE\d+\b",
                lambda reference: works.get(reference.group(), reference.group()),
                group.group(1) if group.group(1) is not None else group.group(2),
            ) + ")",
            r,
        )
        if doc.metadata["canonical_work_id"] not in works_cited_seen:
            works_cited_str += f"{len(works_cited_seen) + 1}. {doc.metadata['full_citation']}\n"
            works_cited_seen.append(doc.metadata["canonical_work_id"])
    r += "\n\nWorks Cited:\n" + works_cited_str

    LOG.info("Focused prompt response with sources bound: %s", r)

    # 4. WRAP-UP
    # ====================================================
    # Report results
    LOG.info("Original query: %s", q)
    total_elapsed = time.perf_counter() - start
    LOG.info("Total time elapsed: %.4f seconds", total_elapsed)
    LOG.info(f"k: {K_VALUE} | fetch_k: {FETCH_K_VALUE} | lambda_mult: {LAMBDA_MULT_VALUE} | chat_temperature: 0.4")
    LOG.info(f"initial mmr and similarity results: {len(basic_results)} | combined canonical results: {len(combined_canonical_results)} | keyword results: {len(keyword_results)} | total combined retrieved: {total_retrieved_count} | total after deduplication: {len(deduplicated_results)} | total after reranking: {len(reranked_results)}")
    return

begin = time.perf_counter() - start
LOG.info("Time elapsed since start: %.4f seconds", begin)

if __name__ == "__main__":
    main()