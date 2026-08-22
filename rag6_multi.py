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

# STANDARD LIBRARIES
import math
import json
import difflib
import argparse

# LLM
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_chroma import Chroma
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_community.document_transformers import LongContextReorder
from langchain_chroma import Chroma
from langchain_core.documents import Document

# LOGGING
import logging
import sys
from pathlib import Path

# TYPING
from dataclasses import dataclass
from typing import Dict, Any, Optional

# CONFIGURATION
EMBEDDING_MODEL   = "bge-m3:latest" #"nomic-embed-text"
CHAT_MODEL        = "gpt-oss:20b"
CHAT_TEMPERATURE  = 0.4
OLLAMA_BASE_URL   = "http://localhost:11434"

DB_PATH           = "./chroma_db_local-tuned6_multilang"
SOURCE_TEXT       = "./data/derrida6_multi.jsonl"

BATCH_SIZE        = 1000          # Prevents Ollama tokenizer OOM crashes
K_VALUE           = 15
FETCH_K_VALUE     = 500
LAMBDA_MULT_VALUE = 0.7           # Lower = more diversity; higher = more query relevance

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

# DATA CLASSES
@dataclass
class ChatConfig:
    base_url: str = OLLAMA_BASE_URL
    model: str = CHAT_MODEL
    temperature: float = CHAT_TEMPERATURE

@dataclass
class EmbedConfig:
    model: str = EMBEDDING_MODEL
    base_url: str = OLLAMA_BASE_URL

@dataclass
class StoreConfig:
    persist_directory: str = DB_PATH

@dataclass
class LangChainConfig:
    chat: ChatConfig
    embedding: EmbedConfig
    store: StoreConfig

    @classmethod
    def from_defaults(cls) -> "LangChainConfig":
        return cls(
            chat=ChatConfig(),
            embedding=EmbedConfig(),
            store=StoreConfig(),
        )

# LOGGER
class Logger:
    @staticmethod
    def setup(name: str = __name__, level: int = logging.INFO) -> logging.Logger:
        _format = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
        _datefmt = "%Y-%m-%d %H:%M:%S"
        logger = logging.getLogger(name)
        logger.setLevel(level)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        file_handler = logging.FileHandler(Path("derridai6_multi.log"), mode="w")
        file_handler.setFormatter(logging.Formatter(_format, _datefmt))
        formatter = logging.Formatter(_format, _datefmt)
        handler.setFormatter(formatter)
        if not logger.hasHandlers():
            logger.addHandler(handler)
            logger.addHandler(file_handler)
        return logger
LOG = Logger.setup()

# PROMPT TEMPLATES

review_prompt_template = """
You are a strict evidence auditor.

Evaluate every SENTENCE in the RESPONSE against the EVIDENCE.

Do not use outside knowledge.
Do not assume that text appearing inside a Derrida work was written or asserted by Derrida.
Distinguish carefully among:
- Derrida speaking in his own voice
- Derrida quoting or paraphrasing another author
- an editor
- a translator
- a secondary commentator
- unknown attribution

A sentence may be:
- directly supported by one evidence block
- supported by multiple evidence blocks
- a synthesis derived from multiple sources
- only partially supported
- unsupported

Do not force an unsupported sentence to match a source.

Do not infer that Derrida endorses, privileges, or foregrounds a concept
merely because the source says that the concept serves as a "fil conducteur"
or appears in Derrida's analytical procedure.

Distinguish the object Derrida analyzes from the method or path of his analysis.

[RESPONSE]
{response_content}
[/RESPONSE]

[EVIDENCE]
{context}
[/EVIDENCE]

Return one object for every sentence.

Output schema:

[
  {{
    "id": "000",
    "claim": "...",
    "claim_type": "thesis | argument | observation | synthesis",
    "claim_source": "source | original",
    "support_type": "direct | partial | synthesis | unsupported",

    "evidence_block_ids": ["00-0"],
    "canonical_work_ids": ["margins-of-philosophy-1"],

    "source_speaker": "Jacques Derrida",
    "source_target": "Martin Heidegger",
    "source_role": "derrida | derrida_quoting_other | editor | translator | secondary_author | unknown",
    "source_region_type": "main_text | footnote | introduction | translator_note | editor_note | bibliography | unknown",

    "source_text_supporting_claim": "...",

    "attribution_confidence": 0.95,
    "claim_confidence": 0.92,

    "revised_claim": {{
      "text": "...",
      "evidence_block_ids": ["00-0"],
      "source_speaker": "Jacques Derrida",
      "source_target": "Martin Heidegger",
      "source_role": "derrida"
    }},

    "revise_claim": false,
    "drop_claim": false,
    "reason": "..."
  }}
]

Rules:

1. Never invent a source.
2. Never assign a source merely because it discusses the same topic.
3. If the evidence does not support the sentence, use:
   "support_type": "unsupported",
   "evidence_block_ids": [],
   "claim_confidence": 0.0,
   "drop_claim": true
4. If a sentence overstates the evidence, revise it narrowly.
5. If a sentence makes a corpus-level claim such as
   "Across Derrida's works..." or "Derrida consistently...",
   require evidence from at least two distinct canonical works.
6. Do not infer présence from présent, différance from différence,
   or other related Derridean terms solely from lexical similarity.
7. Preserve source-language wording exactly when quoting evidence.
8. Do not generate bibliography metadata. Only identify evidence blocks
   and source roles.
9. Output valid JSON only. No markdown, comments, or code fences.
"""

initial_prompt_template = """
    You are a scholar of the works of Jacques Derrida and poststructuralist philosophy.

    You have been prompted by the user with the following instructions:
    
    [MASTER PROMPT AND INSTRUCTIONS]
        "{prompt}"
    [/MASTER PROMPT AND INSTRUCTIONS]

    REQUIREMENTS:

        - RESPONSE MUST BE A MINIMUM OF 20 SENTENCES OR TWO PARAGRAPHS, WHICHEVER IS LONGER

    When you cite works, whether inline or in a bibliography, you use the MLA citation format.

    You write in a clear, coherent, accurate style, breaking down complex ideas into understandable explanations.

    Use multiple paragraphs as needed.

    YOU MUST strictly follow the instructions provided by the user.

    Do not make any claim broader than the accepted evidence supports.

    A corpus-level claim such as:
    "Across Derrida's works..."
    "Derrida consistently..."
    "In Derrida's thought..."
    requires support from at least two distinct canonical works.

    If only one canonical work survives review, explicitly limit the answer
    to that work.

    Do not infer présence from présent solely because the words are lexically related.

    Do not introduce différance, trace, absence, logocentrism, the Other,
    or other Derridean concepts unless an accepted claim explicitly supports them.

    Answer the question based ONLY on the following citations:

    [SOURCES, CITATIONS, EVIDENCE]
    {context}
    [/SOURCES, CITATIONS, EVIDENCE]
"""

query_improvement_template = """
    [PROMPT]
        "{prompt}"
    [/PROMPT]

    Also identify the language of the prompt,
    the language of the materials being sought,
    the expected language of the response,
    and put them in the JSON object.

    Assume response_language is the same as prompt_language unless otherwise specified.

    Assume materials_language is null (all languages) unless otherwise specified. (e.g., "you can use only French and English")

    Finally, add some details about the query itself:
        - tone of the query
        - quality of the query (0.0 to 1.0, with 0.0 being idiotic and 1.0 being expert-level)

    OUTPUT FORMAT: valid JSON object
    {{
        "prompt": "{prompt}",
        "prompt_query": "..." <-- the part of the prompt that contains the actual question or request
        "prompt_query_fr": "...", <-- the part of the prompt that contains the actual question or request translated into French
        "prompt_instructions": "..." <-- any additional instructions or context provided in the prompt
        "keywords": ["keyword1", "keyword2", ...], <-- 1-2 relevant SEARCH keywords, not related to how to style/format/etc. a response
        "keywords_fr": ["motclé1", "motclé2", ...], <-- 1-2 relevant SEARCH keywords in French, not related to how to style/format/etc. a response
        "prompt_language": ["en_us"], <-- query is in English
        "materials_language": ["fr_fr"], <-- query is asking you to look ONLY at French materials, or null if not specified (all languages)
        "response_language": ["fr_fr"], <-- query is asking you to respond in French
        "tone": "neutral | casual | academic | offensive | creative | hostile | vulgar"
        "query_quality": 0.8,
        "is_fetch_query": false, <--- whether or not the user is asking for appearances of "x" in the source materials (true) or just a general answer (false)
        "fetch_query_content": null <--- the specific content to look for in the source materials if is_fetch_query is true
        "fetch_query_content_fr": null <--- the specific content to look for in the source materials if is_fetch_query is true (in French)
    }}

    OUTPUT ONLY VALID JSON OBJECT. NO COMMENTS. NO ``` NO MARKDOWN OR EXTRA TEXT
"""

initial_retrieval_prompt_template = """
    en_us: "{prompt_query}"
    fr_fr: "{prompt_query_fr}"
    [{keywords}]
"""

# LANGCHAIN CLIENT WRAPPER
class LangChainClient:
    """
    A thin wrapper that builds a LangChain chat model, an embeddings model,
    and a Chroma vector store based on a user‑supplied configuration.

    Parameters
    ----------
    config : Optional[LangChainConfig] = None
        A typed configuration object.  If omitted, defaults from the module
        constants are used.
    """
    def __init__(self, config: Optional[LangChainConfig] = None):
        cfg = config or LangChainConfig.from_defaults()
        LOG.info("Initializing LangChainClient with configuration: %s", cfg)
        LOG.info(f"""\n
=================
| CONFIGURATION |
=================
MODEL: {cfg.chat.model}
TEMPERATURE: {cfg.chat.temperature}
BASE_URL: {cfg.chat.base_url}
EMBEDDING_MODEL: {cfg.embedding.model}
DB_PATH: {cfg.store.persist_directory}
        """)
        self.chat_model = ChatOllama(
            model=cfg.chat.model,
            temperature=cfg.chat.temperature,
            base_url=cfg.chat.base_url,
            timeout=45.0, # 45s
        )
        self.embedding_model = OllamaEmbeddings(
            model=cfg.embedding.model,
            base_url=cfg.embedding.base_url,
        )
        self.vector_store = Chroma(
            persist_directory=cfg.store.persist_directory,
            embedding_function=self.embedding_model,
        )
        LOG.info("LangChainClient initialized successfully.")
    def invoke(self, prompt: str):
        LOG.info(f"Invoking chat model [{self.chat_model.model}] with prompt: {prompt}")
        return self.chat_model.invoke(prompt)
    def create_retriever(self, search_kwargs: dict, search_type: str = "mmr"):
        LOG.info(f"Creating retriever with search_kwargs: {search_kwargs} and search_type: {search_type}")
        self.retrievers = getattr(self, "retrievers", [])
        retriever = self.vector_store.as_retriever(search_kwargs=search_kwargs, search_type=search_type)
        self.retrievers.append(retriever)
        return retriever

# MAIN FUNCTION
def main():
    client = LangChainClient()


    # LOG.info("Formatted prompt: %s", formatted_prompt)

    # Initial query processing
    a_query_improvement_prompt = ChatPromptTemplate.from_template(query_improvement_template)
    a_formatted_query_improvement_prompt = a_query_improvement_prompt.format(prompt=args.prompt)
    a_query_details = client.invoke(a_formatted_query_improvement_prompt)
    a_prompt_options = json.loads(a_query_details.content)
    LOG.info("Chat model response: %s", a_prompt_options)


    if a_prompt_options.get("is_fetch_query"):
        LOG.info("User is asking for appearances of specific content in the source materials: '%s'", a_prompt_options["fetch_query_content"])
        fetched_results = client.vector_store.get(where_document={"$or": [{ "$contains": a_prompt_options["fetch_query_content"]}, { "$contains": a_prompt_options.get("fetch_query_content_fr")}]})

        if len(fetched_results["ids"]) == 0:
            LOG.info("No results found for the fetch query.")
            or_conditions = [{"$contains": keyword} for keyword in a_prompt_options["keywords"]]
            if a_prompt_options.get("keywords_fr"):
                or_conditions.extend([{"$contains": keyword} for keyword in a_prompt_options["keywords_fr"]])
            fetched_keword_results = client.vector_store.get(where_document={"$or": or_conditions})
            LOG.info("Fetched keyword results: %d", len(fetched_keword_results["ids"]))
            if len(fetched_keword_results["ids"]) == 0:
                LOG.info("No results found for the keyword fetch query.")
            fetched_results = fetched_keword_results
            
        ids = fetched_results["ids"]
        metadatas = fetched_results["metadatas"]
        docs = fetched_results["documents"]
        LOG.info("Fetched results: %d", len(ids))

        cleaned_results = [
            {
                # "author": m.get("document_author"),
                # "section_author": m.get("section_author"),
                # "work": m.get("work"),
                # "edition": m.get("edition"),
                # "year": m.get("year"),
                "text": d,
                "pagination": f"{m.get('page_start') if (not m.get('page_end') or m.get('page_end') == m.get('page_start')) else f'{m.get('page_start')}-{m.get('page_end')}'}",
                "citation_inline": f"({m.get('section_author', m.get('document_author', m.get('work'))).split(' ')[1]} {m.get('year')}, {m.get('page_start') if (not m.get('page_end') or m.get('page_end') == m.get('page_start')) else f'{m.get('page_start')}-{m.get('page_end')}'})"
            } for m, d in zip(metadatas, docs)
        ]

        output = {
            "prompt": args.prompt,
            "bibliography": [],
            "results": cleaned_results,
            "total": len(cleaned_results)
        }

        for doc in cleaned_results:
            # if doc.get('page_start') and doc.get('page_end') and doc.get('page_start') is not doc.get('page_end'):
            #     page_number = f"{doc.get('page_start', '')}-{doc.get('page_end', '')}"
            # else:
            #     page_number = f"{doc.get('page_start', '')}"

            author = doc.get('author', '')
            if doc.get('section_author') and doc.get('section_author') != author:
                author = doc.get('section_author')
            author_reversed = f"{author.split(' ')[-1]}, {author.split(' ')[0]}"
            
            citation = f"{author_reversed}. {doc.get('work', '')}. {doc.get('edition', '')}. {doc.get('year', '')}"
            if citation not in output["bibliography"]:
                output["bibliography"].append(citation)

        LOG.info("Fetched results content: %s", output)
        return output
    else:
        LOG.info("User is asking for a general answer, not specific appearances.")

    # Initial filtering and retriever creation
    initial_search_kwargs = {
        "k": K_VALUE,
        "fetch_k": FETCH_K_VALUE,
        "lambda_mult": LAMBDA_MULT_VALUE,
        "filter": { "$and": [{"text_length": {"$gt": 500}}] }
    }
    LOG.info("Initial search kwargs: %s", initial_search_kwargs)
    if a_prompt_options["materials_language"]:
        LOG.info("Filtering by materials language: %s", a_prompt_options["materials_language"])
        initial_search_kwargs["filter"]["$and"].append({
            "document_language": {
                "$in": a_prompt_options["materials_language"]
            }
        })
    else:
        LOG.info("No materials language specified, not adding language filter.")
        initial_search_kwargs["filter"] = { "text_length": {"$gt": 500} }
    initial_retriever = client.create_retriever(search_kwargs=initial_search_kwargs, search_type="mmr")
    secondary_retriever = client.create_retriever(search_kwargs={ "k": K_VALUE, "filter": { "text_length": {"$gt": 500}}}, search_type="similarity")

    # Initial retrieval using the created retriever
    b_initial_retrieval_prompt = ChatPromptTemplate.from_template(initial_retrieval_prompt_template)
    b_formatted_initial_retrieval_prompt = b_initial_retrieval_prompt.format(
        prompt_query=args.prompt,
        keywords=json.dumps(a_prompt_options["keywords"])
    )
    LOG.info("Formatted initial retrieval prompt: %s", b_formatted_initial_retrieval_prompt)
    candidates = initial_retriever.invoke(b_formatted_initial_retrieval_prompt)
    additional_candidates = secondary_retriever.invoke(b_formatted_initial_retrieval_prompt)
    combined_candidates = candidates + additional_candidates
    LOG.info("Retrieved %d candidates using MMR and similarity search.", len(combined_candidates))

    if not candidates:
        LOG.warning("No context found matching the query and filter criteria.")
        print("\n--- No matching results found ---")
        return

    seen = set()
    unique_candidates = []

    for doc in combined_candidates:
        chunk_id = doc.metadata.get("record_id")

        if chunk_id not in seen:
            seen.add(chunk_id)
            unique_candidates.append(doc)

    LOG.info("Filtered to %d unique candidates after removing duplicates.", len(unique_candidates))

    # Reorder the retrieved context groups to prioritize the most relevant and coherent evidence blocks
    LOG.info("Reordering context groups with LongContextReorder...")
    reordering = LongContextReorder()
    reordered_groups = reordering.transform_documents(unique_candidates)

    context = "\n============================================\n".join(
        f"""// EVIDENCE_BLOCK_ID: 00-{i} | ID: {doc.metadata.get("canonical_work_id", "N/A")} | Length: {doc.metadata.get("text_length", "N/A")}
{json.dumps(doc.metadata)}
"""
        for i, doc in enumerate(reordered_groups)
    )

    LOG.info("Constructed evidence, source, and citation context blocks: %s", context)

    prompt = ChatPromptTemplate.from_template(initial_prompt_template)
    final_prompt = prompt.format(context=context, prompt=a_prompt_options)
    LOG.info("Final prompt: %s", final_prompt)

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