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

"""rag.py – Retrieval‑augmented generation demo with CLI controls and progress logs."""

import math
import json
import difflib
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_chroma import Chroma
from langchain_ollama import ChatOllama
from langchain_community.document_transformers import LongContextReorder

from config import (
    CHAT_MODEL,
    CHAT_TEMPERATURE,
    OLLAMA_SERVER_URL,
    DB_PATH,
    SOURCE_TEXT,
    BATCH_SIZE,
    K_VALUE,
    FETCH_K_VALUE,
    LAMBDA_MULT_VALUE,
    args
)

from helpers import (
    get_logger,
    get_search_filters,
    keyword_map,
    parse_natural_language_find_query
)

from models import (
    get_llm_chat
)

from store import (
    database_exists,
    delete_vector_store,
    get_retriever,
    get_store
)

LOG = get_logger(__name__)

# ---------------------------------------------------------------------------
# Main Routine
# ---------------------------------------------------------------------------

def main():
    
    # ---------------------------------------------------------------------------
    # Vector store setup / rebuild logic (Batched & Streamed)
    # ---------------------------------------------------------------------------

    vector_store = get_store()
    if database_exists(DB_PATH) and not args.force_rebuild:
        LOG.info("Loading existing vector store from '%s'...", DB_PATH)
    elif args.force_rebuild or not database_exists(DB_PATH):
        # if args.force_rebuild:
        #     delete_vector_store(DB_PATH)
        LOG.info("Initializing new Chroma database at '%s'...", DB_PATH)
        
        doc_batch = []
        id_batch = []
        total_indexed = 0

        LOG.info("Streaming and indexing documents in batches of %d...", BATCH_SIZE)
        
        with open(SOURCE_TEXT, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                
                record = json.loads(line)
                doc = Document(
                    page_content=record["text"],
                    metadata={**record}
                )
                
                doc_batch.append(doc)
                id_batch.append(record["id"])

                # Whenever we hit the batch limit, send to Chroma & clear buffer
                if len(doc_batch) >= BATCH_SIZE:
                    vector_store.add_documents(documents=doc_batch, ids=id_batch)
                    total_indexed += len(doc_batch)
                    LOG.info("Indexed %d documents so far...", total_indexed)
                    doc_batch.clear()
                    id_batch.clear()

            # Flush any remaining documents in the final batch
            if doc_batch:
                vector_store.add_documents(documents=doc_batch, ids=id_batch)
                total_indexed += len(doc_batch)
                LOG.info("Indexed final batch. Total documents indexed: %d", total_indexed)

        LOG.info("Vector store creation complete.")

    # ---------------------------------------------------------------------------
    # LLM setup
    # ---------------------------------------------------------------------------
    llm = get_llm_chat()

    # ---------------------------------------------------------------------------
    # RAG prompt template
    # ---------------------------------------------------------------------------
    prompt_template = """
You are a scholar of the works of Jacques Derrida and poststructuralist philosophy.

When you cite works, whether inline or in a bibliography, you use the MLA citation format.

You write in a clear, coherent, accurate style, breaking down complex ideas into understandable explanations.

Use multiple paragraphs as needed.

A user has asked you this question: "{question}"

Answer the question based ONLY on the following citations.

CRITICAL ATTRIBUTION RULES

The metadata supplied with each source excerpt is authoritative for
determining WHO IS SPEAKING.

1. SPEAKER METADATA OVERRIDES SEMANTIC ASSUMPTIONS.
   If metadata says:
       speaker = Barbara Johnson
   then statements made in that excerpt MUST NOT be attributed directly
   to Jacques Derrida merely because the excerpt discusses Derrida's ideas.

2. DISTINGUISH THESE ROLES:
   - document_author: author of the overall work
   - region_author: author of this particular section
   - speaker: person whose voice makes the statement in the excerpt
   - position_holder: person whose philosophical position is being described
   - persons: people merely mentioned

   These roles MUST NOT be treated as interchangeable.

3. DIRECT ATTRIBUTION REQUIRES SPEAKER SUPPORT.
   A sentence such as:
       "Derrida argues..."
       "Derrida writes..."
       "Derrida claims..."
       "According to Derrida..."
   is permitted only when the supporting excerpt has:
       speaker = Jacques Derrida
   OR the excerpt explicitly quotes/attributes that proposition to Derrida.

4. SECONDARY EXPOSITION MUST BE IDENTIFIED AS SECONDARY EXPOSITION.
   If:
       speaker = Barbara Johnson
       position_holder = Jacques Derrida
   write:
       "Johnson explains that Derrida..."
       "According to Johnson's account of Derrida..."
       "Johnson characterizes Derrida's position as..."
   NOT:
       "Derrida argues..."

5. QUOTATION ATTRIBUTION:
   Quotation marks do NOT establish that the document author said the words.
   Determine the quoted speaker from metadata and textual context.

6. NEVER infer authorship from the title of the work.
   An excerpt from a book by Derrida may be written by a translator,
   editor, introducer, commentator, or quoted author.

REQUIREMENTS:
- Your response MUST have a MINIMUM of {min} sentences.
- Your response MUST have a MAXIMUM of {max} sentences.
- Your response MUST be written in the style of an academic paper with full paragraphs.

ALL CLAIMS IN YOUR RESPONSE MUST BE SUPPORTED BY FOLLOWING CITATIONS:

{context}

"""
    if not (args.cheat):
        prompt_template += """

STRICT GUIDELINES:

- Use MLA citation format for inline citations (Title, Page #)
- Add a Works Cited section at the end in MLA format
    * Ensure all cited works in the text are included in the Works Cited section MLA style
- IF POSSIBLE cite more than 1 work and at least 3 different pages/passages

EVIDENCE INTERPRETATION RULES:

For every evidence block, distinguish:
- document_author: author of the containing work
- region_author: author of this section
- speaker: person currently speaking
- position_holder: person whose proposition/position is represented
- proposition_status: whether that proposition is asserted, attributed,
  quoted, questioned, rejected, hypothetical, etc.
- claim_scope: how broadly the evidence supports generalization

Never assume document_author = speaker = position_holder.

Do not convert:
- quotation into endorsement
- attribution into authorial assertion
- exposition into endorsement
- questioning into assertion
- rejected claims into authorial positions
- local/textual claims into universal claims

Metadata constrains interpretation but is not infallible. When metadata
confidence is low or metadata conflicts with the source text, use cautious
attribution and preserve uncertainty.

A generated claim may move at most ONE reasonable inferential step beyond
its supporting evidence while being presented as a direct claim.

Claims requiring additional inference, application, generalization, or
combination of multiple passages must be explicitly marked as synthesis,
for example:
- "A Derridean reading could suggest..."
- "Taken together, these passages suggest..."
- "This can be read as..."

Never invent citations or page numbers.

FOR EVERY CLAIM WITH A CITATION:

1. Identify the cited context block.
2. Read:
   - SPEAKER
   - REGION_AUTHOR
   - POSITION_HOLDER
   - DISCOURSE_ROLE
   - DIRECT_AUTHOR_STATEMENT

3. Identify the grammatical subject of the generated claim.

4. Ask:
   "Does the metadata permit this proposition to be directly
   attributed to that grammatical subject?"

5. If NO:
   rewrite the attribution.

Example:

SOURCE METADATA:
    DOCUMENT_AUTHOR: Jacques Derrida
    REGION_AUTHOR: Barbara Johnson
    SPEAKER: Barbara Johnson
    POSITION_HOLDER: Jacques Derrida
    DISCOURSE_ROLE: Secondary exposition

BAD:
    Derrida argues that Western metaphysics is structured by
    hierarchical binary oppositions (Dissemination 8).

GOOD:
    In her introduction to Dissemination, Barbara Johnson describes
    Derrida's critique of Western metaphysics as targeting hierarchical
    binary oppositions (Dissemination 8).

DO NOT preserve an existing citation if the proposition is attributed
to the wrong person. Correct the sentence even when the citation itself
points to the correct page.

"""
    else:
        prompt_template += """
- DO NOT add direct citations
- DO list unique texts you refer to in a bibliography at the end (MLA style)
"""
        

    prompt = ChatPromptTemplate.from_template(prompt_template)


    user_query = args.query

    keywords = llm.invoke(f"""
        Identify 5-10 key words to go along with this prompt:
        
        [PROMPT]
        {user_query}
        [/PROMPT]

        OUTPUT FORMAT: JSON array of keywords, e.g. ["keyword1", "keyword2", ...]

        ONLY OUTPUT VALID JSON ARRAY. NO COMMENTS. NO ``` MARKDOWN
    """)

    LOG.info("Raw keywords response: %s", keywords)
    keywords = json.loads(keywords.content)
    LOG.info("Identified keywords: %s", keywords)

    search_kwargs = {"k": K_VALUE, "fetch_k": FETCH_K_VALUE, "lambda_mult": LAMBDA_MULT_VALUE}
    retriever = get_retriever(search_kwargs=search_kwargs, search_type="mmr")
    
    retrieved_docs = retriever.invoke(f"""
        [PROMPT]
        {user_query}
        [/PROMPT]

        KEYWORDS: {json.dumps(keywords)}
    """)

    LOG.info("Retrieved %d documents.", len(retrieved_docs))

    # Deduplicate while preserving rank order
    seen_text = set()
    unique_docs = []
    for doc in retrieved_docs:
        if doc.page_content not in seen_text:
            seen_text.add(doc.page_content)
            unique_docs.append(doc)
    LOG.info("Of these, %d unique documents.", len(unique_docs))

    if not unique_docs:
        LOG.warning("No context found matching the query and filter criteria.")
        print("\n--- No matching results found ---")
        return

    # ---------------------------------------------------------------------------
    # Neighbor Expansion (Group & preserve internal sequence)
    # ---------------------------------------------------------------------------
    LOG.info("Fetching adjacent records for context expansion...")
    
    # We will build list of "grouped" Documents, where each group is merged into one Document
    grouped_documents = []
    collection = vector_store._collection
    total_records = 0

    for doc in unique_docs:
        rec_id = str(doc.metadata.get("record_id", ""))
        
        target_ids = []
        if "-" in rec_id:
            prefix, num_str = rec_id.rsplit("-", 1)
            if num_str.isdigit():
                numeric_id = int(num_str)
                # Build target IDs for 1 before, target, and 1 after
                target_ids = [f"{prefix}-{n:05d}" for n in (numeric_id - 2, numeric_id - 1, numeric_id, numeric_id + 1, numeric_id + 2)]
            else:
                target_ids = [rec_id]
        else:
            target_ids = [rec_id]

        # Query Chroma for these specific adjacent IDs
        result = collection.get(where={"record_id": {"$in": target_ids}})

        if result and result["documents"]:
            # Zip and sort internal records strictly by numeric suffix
            group_records = []
            for r_text, r_meta in zip(result["documents"], result["metadatas"]):
                r_id = str(r_meta.get("record_id", ""))
                try:
                    num = int(r_id.rsplit("-", 1)[1]) if "-" in r_id else 0
                except (ValueError, IndexError):
                    num = 0
                group_records.append((num, r_text, r_meta))

            # SORT WITHIN GROUP: Keep contiguous reading order
            group_records.sort(key=lambda x: x[0])

            # Merge the ordered group records into a single cohesive string
            combined_text = "".join([r[1] for r in group_records])
            
            # Preserve primary document metadata for citations
            primary_meta = doc.metadata.copy()

            total_records = total_records + len(group_records)
            
            grouped_documents.append(
                Document(page_content=combined_text, metadata=primary_meta)
            )

    LOG.info("Created %d contiguous group blocks of %d records.", len(grouped_documents), total_records)

    # ---------------------------------------------------------------------------
    # Reorder GROUPS to optimize LLM attention
    # ---------------------------------------------------------------------------
    LOG.info("Reordering context groups with LongContextReorder...")
    reordering = LongContextReorder()
    reordered_groups = reordering.transform_documents(grouped_documents)

    # Format retrieved context with source citations
    context_str = "\n\n---\n\n".join(
    [
        f"""
[EVIDENCE #{i + 1}]
work: {doc.metadata.get('work')}
pages: {doc.metadata.get('page_start', '??')}-{doc.metadata.get('page_end', '??')}
document_author: {doc.metadata.get('document_author') or 'Unknown'}
region_type: {doc.metadata.get('region_type') or 'Unknown'}
region_author: {doc.metadata.get('region_author') or 'Unknown'}
speaker: {doc.metadata.get('speaker') or 'Unknown'}
position_holder: {doc.metadata.get('position_holder') or 'Unknown'}
target: {doc.metadata.get('target') or 'Unknown'}
proposition_status: {doc.metadata.get('proposition_status') or 'Unknown'}
discourse_mode: {doc.metadata.get('discourse_mode') or doc.metadata.get('discourse_role') or 'Unknown'}
semantic_function: {", ".join(doc.metadata.get('semantic_function', [])) or 'Unknown'}
stance: {doc.metadata.get('stance') or 'Unknown'}
claim_scope: {doc.metadata.get('claim_scope') or 'Unknown'}
attribution_confidence: {doc.metadata.get('attribution_confidence', 'Unknown')}
extraction_quality: {doc.metadata.get('extraction_quality', 'Unknown')}

[TEXT]
{doc.page_content}
[/TEXT]
"""
            for i, doc in enumerate(reordered_groups)
        ]
    )

    # Generate response
    LOG.info("Generating response with LLM.")
    final_prompt = prompt.format(context=context_str, question=user_query, also=args.also, min=args.min, max=args.max)
    LOG.info(f"Final prompt built: \n{final_prompt}")
    LOG.info(f"Final prompt built.")
    response = llm.invoke(final_prompt)
    LOG.info("LLM finished generating response.")

    if (args.thorough):
        LOG.info("Double-checking in thorough mode...")
        thorough_prompt = """
            You are an academic scholar of Derrida and post-structuralism.
            You are an editor for academic papers.

            REQUIREMENTS:
                - Examine, below, the response to the prompt for clarity, accuracy, and thoroughness.
                - Fix typos and other artifacts.
                - Structure it like an article/essay.
                - DO NOT add subheadings.
                - DO NOT remove page number/citations
                - DO NOT alter citations (unless to clean up typos/artifacts)

            GOAL:
                - Improve the response as needed, then respond with ONLY the improved response.
                - Ensure that the response remains faithful to the original sources.
                - Maintain the original meaning and intent of the response.
                - Avoid introducing new information not present in the original response.
                - Do not fabricate citations or sources.
                - Ensure that all improvements adhere to academic standards and maintain the integrity of the original text.
                - A high-quality academic essay should be produced, adhering to the above requirements.
                - Ensure that all changes are clearly documented in the DEBUG section.
                - Below the response append a brief DEBUG section with any changes you made during generation to improve the result
                    * For each change, provide the a/b diff
                    * At very end, add your CONFIDENCE SCORE (out of 100%) signaling your confidence in your accuracy as a Derridean scholar

            Prompt: {prompt}

            Response: {response}
        """.format(prompt=args.query, response=response)
        response = llm.invoke(thorough_prompt)
    
    if (args.bibliography):
        LOG.info("Adding bibliography...")
        bibliography_prompt = """
            You are an academic scholar of Derrida and post-structuralism.
            You are an editor for academic papers.

            REQUIREMENTS:
                - DO identify every unique source in this text and add a corresponding Works Cited section at the bottom
                - DO follow MLA standards or citation format, e.g. when citing directly or indirectly use the inline (Work, Page #) format.
                - DO inline footnotes to the text that correspond to works cited.
                    * e.g., "Derrida called Cheetos 'tasty' (Of Grammatology, 20)[1]."
                - DO NOT remove page numbers unless they are incorrect.

            EXAMPLE:

                Derrida felt that the Beach Boys were "too good to be true" (Dissemination 54).[3]

                WORKS CITED

                1. ...
                2. ...
                3. Derrida, Jacques. Dissemination. University of Bucko Press, 1995.

            TEXT:

            {response}
        """.format(response=response)
        LOG.info(f"Final prompt after bibliography: {bibliography_prompt}")
        response = llm.invoke(bibliography_prompt)


    if (args.recursions):

        recursion_prompt = """
        You are an academic editor specializing in Derrida and post-structuralism.

        Your primary task is EVIDENCE CONTROL, not stylistic improvement.

        You are given:
        1. A generated academic response.
        2. The source chunks from which that response was generated.

        Your job is to revise the response so that every substantive claim is
        accurately supported, accurately attributed, and does not exceed the
        evidence without explicit qualification.

        ============================================================
        1. CITATION ACCURACY
        ============================================================

        For EVERY substantive claim:

        Determine whether the cited source actually supports that specific claim.

        Classify the relationship internally as:

        DIRECT:
        The source explicitly states or clearly asserts the claim.

        CLOSE INFERENCE:
        The claim follows from the source through ONE small and reasonable
        interpretive step.

        SYNTHESIS:
        The claim combines multiple source statements, applies a concept,
        generalizes beyond the source, or requires MORE THAN ONE inferential step.

        UNSUPPORTED:
        The supplied sources do not adequately establish the claim.

        Rules:

        - DIRECT claims may be stated normally.
        - CLOSE INFERENCE claims may be stated normally if the inference is
        conservative and does not change the scope or position holder.
        - SYNTHESIS claims MUST be explicitly marked with language such as:
            "A Derridean reading could suggest..."
            "This can be read as..."
            "Taken together, these passages suggest..."
            "Extending this argument..."
        - UNSUPPORTED claims MUST be removed or rewritten to match the evidence.

        Never convert an interpretation into a direct textual claim.

        ============================================================
        2. ATTRIBUTION
        ============================================================

        PROPER ATTRIBUTION IS ABSOLUTELY ESSENTIAL.

        For every claim and quotation determine the actual POSITION HOLDER.

        Possible position holders include:

        - Derrida
        - another philosopher or author quoted by Derrida
        - an interlocutor
        - translator
        - editor
        - critic/reviewer
        - introduction author
        - footnote/endnote author
        - generated synthesis

        A statement appearing inside a book by Derrida is NOT automatically
        a statement made or endorsed by Derrida.

        Examples:

        If Derrida quotes Rousseau:
            "Rousseau argues..." NOT "Derrida argues..."

        If an editor describes Derrida:
            "The editor describes Derrida as..." NOT "Derrida states..."

        If Derrida describes another author's position:
            "Derrida describes X as arguing..." NOT "Derrida argues..."

        Correct all attribution errors.

        ============================================================
        3. INFERENTIAL DISTANCE
        ============================================================

        Do not allow a generated claim to move more than ONE inferential step
        beyond its supporting source without explicitly identifying the claim
        as interpretation or synthesis.

        Example:

        SOURCE:
        Derrida critiques the privileging of speech over writing.

        ACCEPTABLE:
        "Derrida critiques the privileging of speech over writing."

        ACCEPTABLE CLOSE INFERENCE:
        "This critique challenges the hierarchy between speech and writing."

        TOO FAR AS DIRECT CLAIM:
        "Derrida therefore provides a political program for dismantling
        colonial epistemology."

        If such a connection is useful and reasonably motivated, write:
        "A Derridean reading could extend this critique to questions of
        colonial epistemology."

        ============================================================
        4. SCOPE CONTROL
        ============================================================

        Preserve the scope of the source.

        Do NOT silently transform:

        "Western metaphysics"
        into
        "the West"

        "language"
        into
        "all representation"

        "a critique of presence"
        into
        "a rejection of presence"

        "can be applied to"
        into
        "Derrida argues"

        "questions"
        into
        "rejects"

        "complicates"
        into
        "disproves"

        Do not strengthen modality, causality, universality, intention,
        or philosophical commitment beyond the evidence.

        ============================================================
        5. SEMANTIC RELATIONSHIPS
        ============================================================

        Check not only whether the correct concepts appear, but whether the
        RELATIONSHIP between those concepts is supported.

        For example, a source mentioning both "logocentrism" and "hierarchy"
        does NOT automatically support every generated causal relationship
        between logocentrism and hierarchy.

        Check whether the source supports:

        - X causes Y
        - X critiques Y
        - X entails Y
        - X is an example of Y
        - X opposes Y
        - X produces Y
        - X is equivalent to Y
        - X is Derrida's own position

        Do not infer these relationships merely because both concepts occur
        in the same source chunk.

        ============================================================
        6. CITATIONS
        ============================================================

        Maintain MLA-style inline citations.

        Do not remove or alter an existing citation unless it is incorrect.

        If a citation does not support the claim:
        - replace it with a supporting supplied citation if available;
        - otherwise qualify or remove the claim.

        NEVER invent citations, page numbers, quotations, or sources.

        ============================================================
        7. EDITING BEHAVIOR
        ============================================================

        Do NOT expand the paper merely to make it sound more sophisticated.

        Do NOT add new philosophical claims unless supported by the supplied
        sources.

        Prefer:
            narrower + accurate
        over:
            broader + plausible.

        Preserve accurate material.

        Remove unnecessary repetition.

        Do not repeatedly paraphrase the same source merely to increase length.

        ============================================================
        8. DIRECT-SUPPORT CLASSIFICATION
        ============================================================

        For every sentence, distinguish between:

        1. EXPLICIT SOURCE CLAIM
        The cited source directly states or clearly entails the proposition.

        2. CLOSE PARAPHRASE
        The proposition restates the source without adding a new conceptual
        relationship.

        3. SYNTHESIS
        The proposition combines two or more source-supported ideas.

        4. APPLICATION
        A source concept is applied to an object, event, person, or domain
        not explicitly discussed in the cited passage.

        5. UNSUPPORTED
        The proposition introduces information not established by the
        supplied sources.

        CRITICAL RULE:
        Correct attribution does NOT establish correct entailment.

        A statement may correctly identify the speaker but still falsely
        attribute a proposition that the speaker never makes.

        Never describe a SYNTHESIS or APPLICATION as:
        - "the author states"
        - "the author argues"
        - "the author observes"
        - "the passage shows"
        - "directly supported"

        Instead use explicit markers such as:
        - "A reading of this passage could suggest..."
        - "Applied to X, this concept could..."
        - "Taken together, these passages may support..."
        - "This is a synthesis rather than an explicit claim in the source."
        
        ============================================================
        FINAL CHECK
        ============================================================

        Before returning the response, internally check every substantive
        sentence:

        1. Who is the position holder?
        2. Which source supports it?
        3. Does that source support the exact semantic relationship asserted?
        4. How many inferential steps separate source and claim?
        5. Has the scope been expanded?
        6. If synthesis is involved, is it explicitly marked as synthesis?

        Return ONLY the revised academic response.

        TEXT TO EDIT:

        {response}

        SOURCES FOR THE TEXT:

        {context_str}
        """.format(response=response, context_str=context_str)
        for i in range(args.recursions):
            LOG.info(f"Recursion {i+1}/{args.recursions}...")
            response = llm.invoke(recursion_prompt)

    print(f"\n--- Answer from {CHAT_MODEL} ---")
    print(response.content)

if __name__ == "__main__":
    main()