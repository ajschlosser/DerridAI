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

"""rag6_multi.py -- Retrieval-augmented generation demo with CLI controls and progress logs."""

import os

os.environ["TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD"] = "1"

# STANDARD LIBRARIES
import json
import argparse
import math
import random
from datetime import date

# LLM
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.document_transformers import LongContextReorder
from sentence_transformers import CrossEncoder


from prompts import (
    focused_prompt_template,
    review_prompt_template,
    initial_prompt_template,
    research_prompt_template,
    query_improvement_template,
    initial_retrieval_prompt_template,
)

from defaults import (
    CHAT_TEMPERATURE,
    LAMBDA_MULT_VALUE,
    K_VALUE,
    FETCH_K_VALUE,
    DB_PATH,
    RERANK_COUNT,
    keys
)

from logger import Logger

from client import LangChainClient

#NLP
import nltk
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lex_rank import LexRankSummarizer
import re
import unicodedata

import pyphen
from dehyphen import FlairScorer
from symspellpy import SymSpell, Verbosity

# DOWNLOAD NECESSARY NLTK DATA
nltk.download('punkt_tab')
nltk.download('punkt')

# CLI ARGUMENTS
parser = argparse.ArgumentParser(description="RAG Pipeline for Philosophical Texts")
parser.add_argument(
    "--prompt",
    "-p",
    "--query",
    "-q",
    type=str,
    default="What does Derrida say about presence?",
    help="Question to ask the RAG pipeline.",
)
args = parser.parse_args()

LOG = Logger.setup()

summarizer = LexRankSummarizer()

reranker = CrossEncoder(
    "cross-encoder/ms-marco-MiniLM-L-6-v2"
)

def rerank_top_n(query, docs, reranker, top_n=RERANK_COUNT):
    pairs = [
        [query, doc.page_content]
        for doc in docs
    ]

    scores = reranker.predict(pairs)

    ranked_indices = sorted(
        range(len(docs)),
        key=lambda i: float(scores[i]),
        reverse=True
    )

    return [docs[i] for i in ranked_indices[:top_n]]

def generate_citation_strings(doc) -> tuple[str, str]:

    author = doc.metadata.get("document_author", doc.metadata.get("speaker"))
    speaker = doc.metadata.get("speaker", "")
    work = doc.metadata.get("work", "")
    edition = doc.metadata.get("edition", "")
    year = doc.metadata.get("year", "")
    page_start = doc.metadata.get("page_start")
    translator = doc.metadata.get("translator", None)
    page_end = doc.metadata.get("page_end")
    author_last_name = author.split(' ')[-1]
    inline_author = author_last_name
    # if speaker and speaker != author:
    #     inline_author = doc.metadata.get('speaker').split(' ')[-1]
    author_name_reversed = f"{author.split(' ')[-1]}, {author.split(' ')[0]}"
    inline_citation = f"({inline_author} {year}, {page_start if (not page_end or page_end == page_start) else f'{page_start}-{page_end}'})"
    full_citation = f"{author_name_reversed}. {work}.{f' {translator} trans.' if translator else ''} {edition}. {year}"
    return inline_citation, full_citation

# MAIN FUNCTION
def main():
    client = LangChainClient()

    client.add_new_records(batch_size=1000)

    # Initial query processing
    a_query_improvement_prompt = ChatPromptTemplate.from_template(query_improvement_template)
    a_formatted_query_improvement_prompt = a_query_improvement_prompt.format(prompt=args.prompt)



    a_query_details = client.invoke(a_formatted_query_improvement_prompt)
    a_prompt_options = json.loads(a_query_details.content)

    # a_prompt_options =  {
    #     'prompt': "Describe Derrida's notion of hospitality",
    #     'prompt_query': "Describe Derrida's notion of hospitality",
    #     'prompt_query_fr': "Décrivez la notion d'hospitalité de Derrida",
    #     'prompt_instructions': '',
    #     'keywords': ['hospitality', 'Derrida'],
    #     'keywords_fr': ['hospitalité', 'Derrida'],
    #     'prompt_language': ['en_us'],
    #     'materials_language': ['en_en', 'fr_fr'],
    #     'response_language': ['fr_fr'],
    #     'is_fetch_query': False,
    #     'fetch_query_content': None,
    #     'fetch_query_content_fr': None
    # }

    LOG.info("Chat model response: %s", a_prompt_options)


    if a_prompt_options.get("is_fetch_query") and (a_prompt_options.get("fetch_query_content") or a_prompt_options.get("fetch_query_content_fr")):
        LOG.info("User is asking for appearances of specific content in the source materials: '%s'", a_prompt_options["fetch_query_content"])
        if a_prompt_options.get("fetch_query_content_fr"):
            wher_doc_filter = {"$or": [{ "$contains": a_prompt_options["fetch_query_content"]}, { "$contains": a_prompt_options.get("fetch_query_content_fr")}]}
        else:
            wher_doc_filter = {"$contains": a_prompt_options.get("fetch_query_content", "")}
        LOG.info("Fetching results with where_doc_filter: %s", wher_doc_filter)
        where_filter = {}
        if len(a_prompt_options.get("materials_language")) > 1:
            where_filter = { "$or": [{"document_language": {"$contains": lang}} for lang in a_prompt_options.get("materials_language")] }
        else:
            where_filter = { "document_language": { "$contains": a_prompt_options.get("materials_language")[0] } }
        LOG.info("Where filter for fetching results: %s", where_filter)
        fetched_results = client.vector_store.get(where_document=wher_doc_filter, where=where_filter)

        if len(fetched_results["ids"]) == 0:
            LOG.info("No results found for the fetch query.")
            or_conditions = [{"$contains": keyword} for keyword in a_prompt_options["keywords"]]
            if a_prompt_options.get("keywords_fr"):
                or_conditions_fr = [{"$contains": keyword} for keyword in a_prompt_options.get("keywords_fr")]
                #or_conditions.extend([{"$contains": keyword} for keyword in or_conditions_fr])
            else:
                or_conditions_fr = []
            fetched_keword_results = {
                "ids": [],
                "metadatas": [],
                "documents": []
            }
            fetched_keword_results_fr = {
                "ids": [],
                "metadatas": [],
                "documents": []
            }
            materials_language = a_prompt_options.get("materials_language")
            if "en_us" in materials_language:
                fetched_keword_results = client.vector_store.get(where_document={"$and": or_conditions}, where={ "document_language": { "$contains": "en_us" } })
            if "fr_fr" in materials_language:
                fetched_keword_results_fr = client.vector_store.get(where_document={"$and": or_conditions_fr}, where={ "document_language": { "$contains": "fr_fr" } })
            combined_results = {
                "ids": fetched_keword_results["ids"] + fetched_keword_results_fr["ids"],
                "metadatas": fetched_keword_results["metadatas"] + fetched_keword_results_fr["metadatas"],
                "documents": fetched_keword_results["documents"] + fetched_keword_results_fr["documents"]
            }
            LOG.info("Fetched keyword results: %d", len(fetched_keword_results["ids"]))
            if len(fetched_keword_results["ids"]) == 0:
                LOG.info("No results found for the keyword fetch query.")
            fetched_results = combined_results
            
        ids = fetched_results["ids"]
        metadatas = fetched_results["metadatas"]
        docs = fetched_results["documents"]
        LOG.info("Fetched results: %d", len(ids))

        if a_prompt_options.get("fetch_limit", False):

            prompt_key = "prompt_query"
            if a_prompt_options.get("materials_language"):
                prompt_key = "prompt_query_fr" if "fr" in a_prompt_options.get("materials_language")[0] else "prompt_query"

            docs = rerank_top_n(a_prompt_options[prompt_key], docs, reranker, top_n=int(a_prompt_options.get("fetch_limit")))

        cleaned_results = [
            {
                "document_author": m.get("document_author"),
                "speaker": m.get("speaker"),
                "work": m.get("work"),
                "edition": m.get("edition"),
                "year": m.get("year"),
                "text": d,
                "pagination": f"{m.get('page_start') if (not m.get('page_end') or m.get('page_end') == m.get('page_start')) else f'{m.get('page_start')}-{m.get('page_end')}'}",
                "citation_inline": f"({m.get('speaker', m.get('document_author', m.get('work'))).split(' ')[1]} {m.get('year')}, {m.get('page_start') if (not m.get('page_end') or m.get('page_end') == m.get('page_start')) else f'{m.get('page_start')}-{m.get('page_end')}'})"
            } for m, d in zip(metadatas, docs)
        ]

        output = {
            "prompt": args.prompt,
            "bibliography": [],
            "results": cleaned_results,
            "total": len(cleaned_results)
        }

        for doc in cleaned_results:
            author = doc.get('document_author', '')
            if doc.get('speaker') and doc.get('speaker') != author:
                author = doc.get('speaker')
            author_reversed = f"{author.split(' ')[-1]}, {author.split(' ')[0]}"
            citation = f"{author_reversed}. {doc.get('work', '')}. {doc.get('edition', '')}. {doc.get('year', '')}"
            #LOG.info("Generated citation: %s", citation)
            if citation not in output["bibliography"]:
                output["bibliography"].append(citation)
        LOG.info("Cleaned results: %d", len(cleaned_results))
        LOG.info("Generated bibliography: %s", output["bibliography"])
        LOG.info("Cleaned results and generated bibliography completed: %s", cleaned_results)


        dehyphenator = FlairScorer(lang="multi-v0")
        hyphenators = {
            "fr_fr": pyphen.Pyphen(lang="fr_FR"),
            "en_us": pyphen.Pyphen(lang="en_US"),
        }
        symspell = SymSpell(
            max_dictionary_edit_distance=1,
            prefix_length=7,
        )
        symspell.create_dictionary_entry("logocentrisme", 10000)
        symspell.create_dictionary_entry("métaphysique", 10000)
        symspell.create_dictionary_entry("présence", 10000)
        symspell.create_dictionary_entry("différance", 10000)
        symspell.create_dictionary_entry("phénoménologie", 10000)
        symspell.create_dictionary_entry("onto-théologie", 10000)
        symspell.create_dictionary_entry("heideggerienne", 10000)
        symspell.create_dictionary_entry("husserlienne", 10000)

        PROTECTED = [
            "différance",
            "archi-écriture",
            "logo-centrisme",
            "onto-théologie",
            "phonè",
            "ousia",
            "Derrida",
            "Heidegger",
            "Husserl",
            "Lévinas",
        ]

        WORD = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿœŒæÆ'-]+")

        def correct_token(token):
            if token in PROTECTED:
                return token

            # Don't touch very short words.
            if len(token) < 5:
                return token

            suggestions = symspell.lookup(
                token.lower(),
                Verbosity.TOP,
                max_edit_distance=1,
                include_unknown=True,
            )

            if not suggestions:
                return token

            best = suggestions[0]

            # No correction found.
            if best.distance == 0 or best.term == token.lower():
                return token

            # Only accept a one-character correction.
            if best.distance != 1:
                return token

            return best.term


        def correct_ocr_words(text):
            return WORD.sub(lambda m: correct_token(m.group(0)), text)

        response_str = ""
        for i, doc in enumerate((lambda x: (random.shuffle(x) or x))(cleaned_results), start=1):
            text = doc.get("text", "")
            #text = dehyphenator.dehyphen(text)
            text = correct_ocr_words(text)
            language = a_prompt_options.get("materials_language", ["en_us"])[0].split("_")[0]
            if language in hyphenators:
                text = hyphenators[language].inserted(text)
            parser = PlaintextParser.from_string(text, Tokenizer(language))
            summary = summarizer(parser.document, 5)
            text_summary = " [...] ".join([str(sentence) for sentence in summary])
            author_name = f"{doc.get('document_author', '').split(' ')[-1]}, {doc.get('document_author', '').split(' ')[0]}"
            response_str += f"""
{i}. "{text_summary}"
        - {doc.get('speaker', '')}
            in {author_name}. **{doc.get('work', '')}**. {doc.get('edition', '')}, {doc.get('year', '')}: {doc.get('pagination', '')}.
"""
        LOG.info("Generated response string: %s", response_str)
        LOG.info("Original prompt: %s", args.prompt)
        LOG.info("Interpreted fetch prompt: %s", a_prompt_options.get("fetch_query_content"))
        LOG.info("Materials language: %s", a_prompt_options.get("materials_language"))
        return response_str

        fetch_prompt = f"""
        CREATE A CITATION LIST: "{args.prompt}"

        REQUIREMENTS:
            - Use this bibliography:
        {"\n    * ".join(output["bibliography"])}
            - Provide the citation in this format:
                1. " ...citation content... ", in Last Name, First Name. Title. Publisher. Year: page number(s).
            - DO REMOVE any result that seems irrelevant/useless.
            - DO NOT keep useless results.
            - DO NOT SYNTHESIZE ARGUMENTS OR DRAW CONCLUSIONS. JUST PRESENT THE DATA
            - DO CITE EVERY RECORD

        [RECORD TO BE CITED]
        {"\n".join([json.dumps({
            "text": doc.get("text", ""),
            "author": doc.get("author", ""),
            "work": doc.get("work", ""),
            "edition": doc.get("edition", ""),
            "year": doc.get("year"),
            "pagination": doc.get("pagination")
        }) for doc in (lambda x: (random.shuffle(x) or x))(cleaned_results)[:math.ceil(K_VALUE / 2)]])}
        [/RECORD TO BE CITED]

        Final response format examaple:
            1. " ...first citation content... " in Last Name, First Name. Title. Publisher. Year: page number(s).
            2. " ...second citation content... " in Last Name, First Name. Title. Publisher. Year: page number(s).
            3. " ...third citation content... " in Last Name, First Name. Title. Publisher. Year: page number(s).
            4. " ...fourth citation content... " in Last Name, First Name. Title. Publisher. Year: page number(s).
            ...

        FINAL REVIEW:
        - Double-check citations
        - Remove all duplicates
"""

        response = client.invoke(fetch_prompt)
        output["summary"] = response.content
        LOG.info("Original prompt: %s", args.prompt)
        LOG.info("Interpreted fetch prompt: %s", fetch_prompt)
        LOG.info("Fetched results summary: %s", response.content)
        return response.content
    else:
        LOG.info("User is asking for a general answer, not specific appearances.")

    # Initial filtering and retriever creation
    initial_search_kwargs = {
        "k": math.ceil(K_VALUE / 4) if a_prompt_options["keywords"] or a_prompt_options["keywords_fr"] else K_VALUE,
        "fetch_k": FETCH_K_VALUE,
        "lambda_mult": LAMBDA_MULT_VALUE,
        "filter": { "$and": [{"text_length": {"$gt": 500}}, {"extraction_quality": {"$gt": 0.8}}] }
    }
    similarity_seach_kwargs = {
        "k": math.ceil(K_VALUE / 4) if a_prompt_options["keywords"] or a_prompt_options["keywords_fr"] else K_VALUE,
        "filter": { "$and": [{"text_length": {"$gt": 500}}, {"extraction_quality": {"$gt": 0.8}}] }
    }
    LOG.info("Initial search kwargs: %s", initial_search_kwargs)
    if a_prompt_options["materials_language"]:
        LOG.info("Filtering by materials language: %s", a_prompt_options["materials_language"])

        language = a_prompt_options["materials_language"]
        lang_filter = {
            "document_language": {
                "$contains": language[0]
            }
        }
        if len(language) > 1:
            lang_filter = {
                "$or": [{"document_language": {"$contains": lang}} for lang in language]
            }
        initial_search_kwargs["filter"]["$and"].append(lang_filter)
        similarity_seach_kwargs["filter"]["$and"].append(lang_filter)
    else:
        LOG.info("No materials language specified, not adding language filter.")
        initial_search_kwargs["filter"] = { "$and": [{"text_length": {"$gt": 500}}, {"extraction_quality": {"$gt": 0.8}}] }
        similarity_seach_kwargs["filter"] = { "$and": [{"text_length": {"$gt": 500}}, {"extraction_quality": {"$gt": 0.8}}] }

    if a_prompt_options["limit_author"]:
        author_filter = {"speaker": {"$eq": a_prompt_options["limit_author"]}}
        initial_search_kwargs["filter"]["$and"].append(author_filter)
        similarity_seach_kwargs["filter"]["$and"].append(author_filter)

    initial_retriever = client.create_retriever(search_kwargs=initial_search_kwargs, search_type="mmr")
    secondary_retriever = client.create_retriever(search_kwargs=similarity_seach_kwargs, search_type="similarity")

    # Initial retrieval using the created retriever
    b_initial_retrieval_prompt = ChatPromptTemplate.from_template(initial_retrieval_prompt_template)
    b_formatted_initial_retrieval_prompt = b_initial_retrieval_prompt.format(
        prompt_query=a_prompt_options["prompt_query"],
        prompt_query_fr=a_prompt_options["prompt_query_fr"],
        keywords=json.dumps(a_prompt_options["keywords"]),
        keywords_fr=json.dumps(a_prompt_options["keywords_fr"])
    )
    LOG.info("Formatted initial retrieval prompt: %s", b_formatted_initial_retrieval_prompt)
    candidates = initial_retriever.invoke(b_formatted_initial_retrieval_prompt)
    LOG.info("Looking for additional candidates using the secondary retriever...")
    additional_candidates = secondary_retriever.invoke(b_formatted_initial_retrieval_prompt)

    canonical_candidates = []
    combined_canonical_candidates = []
    if (a_prompt_options["keywords"] or a_prompt_options["keywords_fr"]):
        LOG.info("Retrieving canonical works by keyword: %s", a_prompt_options["keywords_fr"])

        canonical_work_ids = []
        canonical_work_ids_fr = []

        for keyword in a_prompt_options["keywords"]:
            if keyword.lower() in keys.get("en_us", {}):
                canonical_work_ids.append(keys["en_us"][keyword.lower()])
        for keyword in a_prompt_options["keywords_fr"]:
            if keyword.lower() in keys.get("fr_fr", {}):
                canonical_work_ids_fr.append(keys["fr_fr"][keyword.lower()])

        combined_work_ids = [item for sublist in (canonical_work_ids + canonical_work_ids_fr) for item in sublist]
        # dedupe
        combined_work_ids = list(set(combined_work_ids))
        #combined_work_ids = canonical_work_ids + canonical_work_ids_fr
        LOG.info("Combined canonical work IDs: %s", combined_work_ids)
        if combined_work_ids:

            canonical_search_kwargs = {
                "k": math.ceil(K_VALUE / 2),
                "filter": {
                    "$and": [
                        # {
                        #     "document_author": {
                        #         "$eq": "Jacques Derrida"
                        #     }
                        # },
                        {
                            "text_length": {
                                "$gt": 500
                            }
                        },
                    ]
                }
            }

            if len(combined_work_ids) > 1:
                canonical_search_kwargs["filter"]["$and"].append({
                    "$or": [{"canonical_work_id": {"$eq": work_id}} for work_id in combined_work_ids]
                })
            else:
                canonical_search_kwargs["filter"]["$and"].append({
                    "canonical_work_id": {
                        "$eq": combined_work_ids[0]
                    }
                })
            
            
            if a_prompt_options["materials_language"]:


                if len(a_prompt_options["materials_language"]) > 1:
                    canonical_search_kwargs["filter"]["$and"].append({
                        "$or": [{"document_language": {"$contains": lang}} for lang in a_prompt_options["materials_language"]]
                    })
                else:
                    canonical_search_kwargs["filter"]["$and"].append({
                        "document_language": {
                            "$contains": a_prompt_options["materials_language"][0]
                        }
                    })

            if a_prompt_options["limit_author"]:
                author_filter = {"speaker": {"$eq": a_prompt_options["limit_author"]}}
                canonical_search_kwargs["filter"]["$and"].append(author_filter)

            LOG.info("Canonical search similarity kwargs: %s", canonical_search_kwargs)
            canonical_work_retriever = client.create_retriever(
                search_kwargs=canonical_search_kwargs, search_type="similarity")
            canonical_candidates = canonical_work_retriever.invoke(b_formatted_initial_retrieval_prompt)
            canonical_search_kwargs["fetch_k"] = math.ceil(K_VALUE / 2)
            canonical_search_kwargs["lambda_mult"] = LAMBDA_MULT_VALUE
            LOG.info("Canonical search MMR kwargs: %s", canonical_search_kwargs)
            canonical_work_retriever_mmr = client.create_retriever(
                search_kwargs=canonical_search_kwargs, search_type="mmr")
            canonical_candidates_mmr = canonical_work_retriever_mmr.invoke(b_formatted_initial_retrieval_prompt)
            combined_canonical_candidates = canonical_candidates + canonical_candidates_mmr
            LOG.info("Combined canonical candidates after search: %d", len(combined_canonical_candidates))


    reordering = LongContextReorder()
    reordered_candidates = reordering.transform_documents(candidates)
    reordered_additional_candidates = reordering.transform_documents(additional_candidates)
    reordered_canonical_candidates = reordering.transform_documents(combined_canonical_candidates)

    #combined_candidates = reordered_candidates[:math.ceil(K_VALUE / 4)] + reordered_additional_candidates[:math.ceil(K_VALUE / 4)] + reordered_canonical_candidates[:math.ceil(K_VALUE / 2)]
    combined_candidates = reordered_candidates + reordered_additional_candidates + reordered_canonical_candidates

    if not combined_candidates:
        LOG.warning("No context found matching the query and filter criteria.")
        print("\n--- No matching results found ---")
        return

    
    # Filter out candidates whose document_language is not in materials_language
    if a_prompt_options["materials_language"]:
        combined_candidates = [
            doc for doc in combined_candidates
            if doc.metadata.get("document_language", ["fr_fr"])[0] in a_prompt_options["materials_language"]
        ]
        LOG.info("Filtered candidates based on materials_language: %s", a_prompt_options["materials_language"])
    else:
        LOG.info("No materials_language filter specified; keeping all candidates.")
    LOG.info("Candidates after materials_language filtering: %d", len(combined_candidates))

    seen = set()
    unique_candidates = []
    for doc in combined_candidates:
        chunk_id = doc.metadata.get("record_id")

        if chunk_id not in seen:
            seen.add(chunk_id)
            text = doc.metadata.get("text", "")
            language = doc.metadata.get("document_language", ["fr_fr"])[0].split("_")[0]
            parser = PlaintextParser.from_string(text, Tokenizer(language))
            summary = summarizer(parser.document, 5)
            text_summary = " [...] ".join([str(sentence) for sentence in summary])
            doc.metadata["text"] = text_summary

            doc.metadata["inline_citation"], doc.metadata["full_citation"] = generate_citation_strings(doc)

            unique_candidates.append(doc)

    LOG.info("Filtered to %d unique candidates after removing duplicates.", len(unique_candidates))

    unique_candidates = rerank_top_n(a_prompt_options["prompt_query"], unique_candidates, reranker, top_n=RERANK_COUNT)

    LOG.info("Top %d candidates after reranking: %d", RERANK_COUNT, len(unique_candidates))

    # Reorder the retrieved context groups to prioritize the most relevant and coherent evidence blocks
    LOG.info("Reordering context groups with LongContextReorder...")
    reordering = LongContextReorder()
    reordered_groups = reordering.transform_documents(unique_candidates)

    context = "\n[EVIDENCE BLOCK]\n".join(
        f"""| EVIDENCE_BLOCK_ID: 00-{i} | ID: {doc.metadata.get("canonical_work_id", "N/A")} | Length: {doc.metadata.get("text_length", "N/A")}

| If using the EVIDENCE in this BLOCK, attribute the claim to the position_holder: "{doc.metadata.get("position_holder", doc.metadata.get("speaker", "Unknown Position Holder"))}".
| The speaker in the EVIDENCE below is "{doc.metadata.get("speaker", "Unknown Speaker")}".
| This EVIDENCE is playing the role of "{doc.metadata.get("discourse_role", "Unknown Role")}".
| TO CITE THIS EVIDENCE:
|| - MLA inline: {doc.metadata.get("inline_citation")}
|| - Works Cited: {doc.metadata.get("full_citation")}
| EVIDENCE BEGINS BELOW:
|---------------------------------
| {json.dumps(doc.metadata.get("text"))}
|---------------------------------
[/EVIDENCE]
"""
        for i, doc in enumerate(reordered_groups)
    )

    LOG.info("Constructed evidence, source, and citation context blocks: %s", context)

    prompt = ChatPromptTemplate.from_template(focused_prompt_template)
    final_prompt = prompt.format(
        context=context,
        prompt_query=a_prompt_options["prompt_query"],
        prompt_instructions=a_prompt_options["prompt_instructions"]
    )
    #LOG.info("Final prompt: %s", final_prompt)

    # Invoke the final prompt with the chat model
    response = client.invoke(final_prompt)
    LOG.info(f"""
Initial prompt: {a_prompt_options["prompt"]}
Instructions taken from prompt: {a_prompt_options["prompt_instructions"]}
Query taken from prompt: {a_prompt_options["prompt_query"]}
""")
    LOG.info(f"""
Model response:
{response.content}
k: {K_VALUE} | retrieved_candidates: {len(combined_candidates)}
unique_candidates: {len(unique_candidates)} | lambda_mult: {LAMBDA_MULT_VALUE}
chat_temperature: {CHAT_TEMPERATURE}
""")
    doc = json.loads(response.content)
    client.add_record_to_response_store({
        "text": doc["response"],
        "metadata": {
            "title": doc["title"],
            "works_cited": doc["works_cited"],
            "timestamp": date.today().isoformat(),
            "original_query": args.prompt,
            #"query_details": a_prompt_options,
            "prompt_query": a_prompt_options["prompt_query"],
            "prompt_instructions": a_prompt_options["prompt_instructions"],
            "materials_language": a_prompt_options.get("materials_language"),
            "response_language": a_prompt_options.get("response_language"),
            "k": K_VALUE,
            "fetch_k": FETCH_K_VALUE,
            "db_path": DB_PATH,
            "retrieved_candidates": len(combined_candidates),
            "unique_candidates": len(unique_candidates),
            "combined_canonical_candidates": len(combined_canonical_candidates),
            "lambda_mult": LAMBDA_MULT_VALUE,
            "chat_temperature": CHAT_TEMPERATURE
        }
    })

    data = {
        "messages": [
            {
            "role": "system",
            "content": "You are a Derrida studies research assistant. Ground textual claims in the supplied sources. Distinguish quotation, paraphrase, and interpretation. Never invent citationss."
            },
            {
            "role": "user",
                "content": a_prompt_options["prompt_query"]
            },
            {
            "role": "assistant",
                "content": doc["response"]
            }
        ]
    }
    path = "training-data.json"

    try:
        with open(path, encoding="utf-8") as f:
            training_data = json.load(f)
    except FileNotFoundError:
        training_data = []

    if isinstance(training_data, dict):
        training_data = [training_data]

    training_data.append(data)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(training_data, f, ensure_ascii=False, indent=2)
    LOG.info("Training data saved to training-data.json")

#     LOG.info("Reviewing response...")

#     review_prompt = ChatPromptTemplate.from_template(review_prompt_template)
#     review_prompt = review_prompt.format(response_content=response.content, context=context)
#     reviewed = client.invoke(review_prompt)
#     LOG.info("Initial prompt: %s", args.prompt)
#     LOG.info("Reviewed response: %s", reviewed.content)

#     final_prompt = f"""
#         Please provide a final, polished response based on the reviewed content.

#         You are responding to the original PROMPT.

#         You are revising the DRAFT RESPONSE based on the CLAIMS.

#         Revise any claim with revised_claim.text fields.

#         Drop any claim with a claim_confidence < 0.9

#         Drop any claim with an attribution_confidence < 0.9

#         Use the claim data to map claims to page numbers (Author, Work, #) and for the Works Cited section.

#         Never infer or reconstruct bibliographic roles.

#         Preserve exactly:
#         - work_author
#         - contribution_author
#         - contribution_role
#         - editor
#         - translator
#         - publisher
#         - publication_year

#         Do not use pronouns for source authors; use surnames.

#         [CLAIMS]
#             {reviewed.content}
#         [/CLAIMS]

#         [DRAFT RESPONSE]
#             {response.content}
#         [/DRAFT RESPONSE]

#         [PROMPT]
#             {args.prompt}
#         [/PROMPT]

#         Your response should be in the form of an encyclopedia entry or academic essay.
# """
#     #LOG.info("After review final prompt: %s", final_prompt)
#     final_response = client.invoke(final_prompt)

    #LOG.info("Final response: %s", final_response.content)

if __name__ == "__main__":
    main()