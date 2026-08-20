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

4. SECONDARY EXPOSITION AND POSITION HOLDER

    The speaker identifies who wrote the evidence.
    The position_holder identifies whose philosophical position the evidence
    is reporting.

    Do NOT confuse citation provenance with intellectual attribution.

    If:
        speaker = Barbara Johnson
        position_holder = Jacques Derrida
        proposition_status = exposition / paraphrase / description

    then the final answer MAY keep Derrida as the intellectual subject.

    PERMITTED:
        "Derrida's critique of logocentrism privileges neither speech nor
        writing as a simple center, Barbara Johnson writes (Derrida 4)."

        "As Barbara Johnson writes,Derrida treats logocentrism as a system organized around the
        self-presence of meaning (Derrida 4)."

        "According to Johnson, Derrida treats logocentrism as... (Derrida 4)"

    All are acceptable.

    DO NOT write:
        "Johnson argues that logocentrism..."
    unless the proposition is Johnson's own interpretation.

    Citation provenance and position ownership are separate:
        citation source = Johnson
        philosophical position = Derrida

5. QUOTATION ATTRIBUTION:
   Quotation marks do NOT establish that the document author said the words.
   Determine the quoted speaker from metadata and textual context.

6. NEVER infer authorship from the title of the work.
   An excerpt from a book by Derrida may be written by a translator,
   editor, introducer, commentator, or quoted author.

INTELLECTUAL-SUBJECT RULE

When the user's question asks what Derrida thinks, argues, means, or does:

Prefer prose centered on Derrida's philosophical position.

If a secondary source faithfully explicates Derrida
(position_holder = Derrida), the secondary source may provide citation
provenance without becoming the main grammatical subject.

Prefer:
    "Derrida's account of logocentrism privileges..."
    (Johnson 4)

over repetitive constructions such as:
    "Johnson says that Derrida..."
    "Bass explains that Derrida..."
    "Johnson further notes..."

Use the secondary author's name in the prose when:
- their interpretation itself matters;
- their wording is quoted;
- position_holder is the secondary author;
- attribution would otherwise be ambiguous.

Do not let attribution correctness turn an essay about Derrida
into an essay about Derrida's translators.   

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

    ROLE_PRIORITY = {
        "main_text": 0,
        "author_footnote": 1,
        "interview": 2,
        "translator_introduction": 3,
        "translator_note": 4,
        "editor_introduction": 5,
        "review": 6,
    }

    # retrieved_docs = retriever.invoke(f"""
    #     [PROMPT]
    #     {user_query}
    #     [/PROMPT]

    #     KEYWORDS: {json.dumps(keywords)}
    # """)

    def source_priority(doc):
        m = doc.metadata

        speaker = (m.get("speaker") or "").lower()
        region_type = (m.get("region_type") or "").lower()
        discourse_role = (m.get("discourse_role") or "").lower()

        # Primary Derrida evidence
        if "derrida" in speaker and region_type == "main_text":
            return 0

        if "derrida" in speaker and "footnote" in region_type:
            return 1

        if "derrida" in speaker:
            return 2

        # Secondary scholarly framing
        if "translator" in region_type:
            return 4

        if "introduction" in region_type:
            return 5

        # Tertiary material
        if "review" in discourse_role or "review" in region_type:
            return 8

        return 6

    retrieval_query = f"""
        [PROMPT]
        {user_query}
        [/PROMPT]

        KEYWORDS: {json.dumps(keywords)}
    """

    retrieved_docs = sorted(
        retriever.invoke(retrieval_query),
        key=source_priority
    )

    FINAL_K = 25
    PRIMARY_K = 12
    SECONDARY_K = 8
    OTHER_K = 5

    search_kwargs = {
        "k": 40,
        "fetch_k": FETCH_K_VALUE,
        "lambda_mult": LAMBDA_MULT_VALUE,
    }

    retriever = get_retriever(
        search_kwargs=search_kwargs,
        search_type="mmr",
    )

    candidates = retriever.invoke(retrieval_query)

    def is_derrida_primary(doc):
        speaker = (doc.metadata.get("speaker") or "").lower()
        holder = (doc.metadata.get("position_holder") or "").lower()

        return (
            "derrida" in speaker
            and "derrida" in holder
        )


    def is_derrida_secondary(doc):
        speaker = (doc.metadata.get("speaker") or "").lower()
        holder = (doc.metadata.get("position_holder") or "").lower()

        return (
            "derrida" not in speaker
            and "derrida" in holder
        )


    primary_docs = []
    secondary_docs = []
    other_docs = []

    for doc in candidates:
        if is_derrida_primary(doc):
            primary_docs.append(doc)
        elif is_derrida_secondary(doc):
            secondary_docs.append(doc)
        else:
            other_docs.append(doc)

    selected = (
        primary_docs[:PRIMARY_K]
        + secondary_docs[:SECONDARY_K]
        + other_docs[:OTHER_K]
    )

    # Backfill unused capacity with remaining candidates,
    # preserving original MMR order.
    selected_ids = {id(d) for d in selected}

    for doc in candidates:
        if len(selected) >= FINAL_K:
            break

        if id(doc) not in selected_ids:
            selected.append(doc)
            selected_ids.add(id(doc))

    retrieved_docs = selected

    # retrieved_docs = sorted(
    #     retrieved_docs,
    #     key=lambda d: ROLE_PRIORITY.get(
    #         d.metadata.get("region_type", ""),
    #         99
    #     )
    # )

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
    # Reorder GROUPS to optimize LLM attention
    # ---------------------------------------------------------------------------
    LOG.info("Reordering context groups with LongContextReorder...")
    reordering = LongContextReorder()
    reordered_groups = reordering.transform_documents(unique_docs)

    def evidence_class(doc):
        m = doc.metadata

        speaker = (m.get("speaker") or "").lower()
        holder = (m.get("position_holder") or "").lower()
        status = (m.get("proposition_status") or "").lower()
        discourse = (
            m.get("discourse_mode")
            or m.get("discourse_role")
            or ""
        ).lower()

        # Derrida stating his own position
        if "derrida" in speaker and "derrida" in holder:
            return (
                "PRIMARY_DERRIDA — Derrida is both textual speaker and "
                "position holder. Direct Derrida attribution permitted."
            )

        # Secondary author accurately explaining Derrida
        if "derrida" not in speaker and "derrida" in holder:
            return (
                "SECONDARY_EXPOSITION_OF_DERRIDA — citation provenance belongs "
                f"to {m.get('speaker') or 'the secondary source'}, but Derrida "
                "may remain the intellectual subject if the proposition is "
                "faithful exposition rather than the secondary author's own interpretation."
            )

        # Derrida talking about somebody else
        if "derrida" in speaker and holder and "derrida" not in holder:
            return (
                "DERRIDA_DISCUSSING_OTHER — Derrida is the textual speaker, "
                f"but the represented position belongs to {m.get('position_holder')}."
            )

        return (
            "OTHER_OR_UNCERTAIN — preserve the actual position holder and "
            "do not infer Derrida ownership."
        )

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
source_url: {doc.metadata.get('source_url') or 'Unknown'}

EVIDENCE CLASS:
{evidence_class(doc)}

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
        draft = response.content
        thorough_prompt = f"""
        You are a strict claim-evidence auditor.

        You are given:
        1. A generated answer.
        2. Retrieved source chunks with metadata.

        Your task is NOT to improve style.
        Your task is to evaluate every substantive claim against its cited evidence.

        For each claim:

        1. Split compound sentences into ATOMIC propositions.
        2. Identify the cited source chunk(s).
        3. Determine attribution class:

        A0 = primary author speaking directly
        A1 = primary author quoting another position holder
        A2 = primary author discussing/paraphrasing another person
        A3 = translator/editor/introduction author
        A4 = secondary commentator
        A5 = attribution uncertain

        4. Determine entailment class:

        E0 = explicit statement
        E1 = close paraphrase
        E2 = one-step local inference
        E3 = synthesis across supported ideas
        E4 = unsupported/speculative

        5. Compare the generated claim to the source proposition on:

        - speaker
        - subject
        - predicate
        - object
        - modality
        - causality
        - scope
        - quantifiers
        - temporal scope
        - endorsement status

        6. A claim is NOT directly supported if any of those relationships are materially changed.

        7. Detect missing premises.
        If the claim requires information not present in the supplied evidence, classify E4.

        8. Detect subject expansion.
        Examples:
        Marx -> Marxism
        one passage -> Derrida's entire philosophy
        schooling in Algeria -> later theory of logocentrism
        discussion of phallus -> theory of sexuality

        9. Detect causal expansion.
        Words such as:
        shaped, caused, informed, led to, resulted in, explains, produced
        require explicit causal evidence.

        10. Detect quotation errors.
        Anything in quotation marks must match the cited source closely.

        11. Decide action:

        KEEP
        REWRITE_AS_PARAPHRASE
        MARK_AS_INFERENCE
        MARK_AS_SYNTHESIS
        MARK_AS_APPLICATION
        FIX_ATTRIBUTION
        REMOVE

        Return JSON only.

        ANSWER TO AUDIT:
        {draft}

        SOURCES:
        {context_str}
        """.format(prompt=args.query, response=response.content)
        audit_response = llm.invoke(thorough_prompt)

        try:
            audit_json = json.loads(audit_response.content)
        except json.JSONDecodeError:
            LOG.error(
                "Audit model did not return valid JSON:\n%s",
                audit_response.content
            )
            audit_json = {
                "claims": [],
                "audit_error": "invalid_json"
            }

        repair_prompt = f"""
        You are revising an academic answer using a completed evidence audit.

        Rules:
        - KEEP claims marked KEEP.
        - E0/E1 may be stated directly.
        - E2 must be qualified.
        - E3 must be explicitly identified as synthesis.
        - E4 must be removed.
        - Correct attribution exactly as instructed.
        - Do not introduce new claims.
        - Prefer deletion over speculative repair.

        ORIGINAL ANSWER:
        {draft}

        AUDIT:
        {json.dumps(audit_json, ensure_ascii=False, indent=2)}

        SOURCES:
        {context_str}
        """
        response = llm.invoke(repair_prompt)
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

        ANSWERABILITY GATE

        Before drafting, determine whether the supplied evidence directly
        addresses the user's requested subject.

        Choose exactly one:

        1. DIRECTLY_ANSWERABLE
        Primary or appropriately attributed secondary sources explicitly
        discuss the requested subject.

        2. PARTIALLY_ANSWERABLE
        Sources explicitly discuss a sufficiently close concept, but some
        interpretation is required.

        3. OUT_OF_CORPUS
        Sources do not discuss the requested subject.

        If OUT_OF_CORPUS:

        - State that the supplied evidence does not answer the question.
        - Identify, briefly, the closest relevant material if useful.
        - Do not infer why the author failed to discuss the subject.
        - Do not transform adjacent concepts into an answer.
        - Do not construct a general theoretical framework merely because
        semantically related material was retrieved.
        - Do not speculate about the author's likely position.
        - Prefer a short answer.
        - Write the answer in the STYLE of Jacques Derrida.

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

        For every proposed claim assign exactly one ATTRIBUTION CLASS:

        A0 = Derrida speaking directly
        A1 = Derrida quoting another person
        A2 = Derrida paraphrasing/discussing another person
        A3 = Translator/editor speaking
        A4 = Secondary commentator speaking
        A5 = Attribution uncertain
        
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

        A close paraphrase may move no more than ONE semantic step beyond
        the explicit proposition in its supporting source.

        If reaching the claim requires:
        - combining multiple concepts,
        - supplying an unstated causal relationship,
        - converting a metaphor into a general doctrine,
        - generalizing from one passage to Derrida's entire philosophy,
        - inferring an implication not explicitly stated,

        the claim is SYNTHESIS and must be marked and handled accordingly.
        
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
        - "This is a synthesis rather than an explicit claim in the source."

        For every proposed claim assign exactly one:

        E0 — EXPLICIT
        The source directly states the proposition.

        E1 — CLOSE PARAPHRASE
        Same proposition, wording generalized.

        E2 — LOCAL INFERENCE
        One inferential step from explicit evidence.

        E3 — SYNTHESIS
        Requires combining propositions/chunks.

        E4 — SPECULATION
        Requires assumptions not supplied by evidence.

        Generation policy:

        E0 → may write "Derrida states/argues/writes..."
        E1 → may write "Derrida argues/describes..."
        E2 → use "The passage suggests/indicates..."
        E3 → MUST use "Considered together, these passages could suggest..." / "A reading of these passages
            could suggest..." / similar phrasing
        E4 → omit unless user explicitly requests speculation.        

        ============================================================
        FINAL CHECK
        ============================================================

        ATTRIBUTION CLASS MATRIX

        E0/A0 = EXPLICIT + PRIMARY AUTHOR
        Directly stated by Derrida.
        → Safe for direct attribution:
        "Derrida states..."
        "Derrida argues..."
        "Derrida writes..."

        E0/A1 = EXPLICIT + QUOTED OTHER
        Explicitly stated by someone Derrida is quoting.
        → Attribute to quoted speaker:
        "Marx states, as quoted by Derrida..."
        → Never automatically attribute to Derrida.

        E0/A2 = EXPLICIT + DISCUSSED OTHER
        Explicit proposition belonging to someone Derrida is discussing/paraphrasing.
        → "Derrida describes Fukuyama as arguing..."
        → Not: "Derrida argues..."

        E0/A3 = EXPLICIT + TRANSLATOR/EDITOR
        Direct statement by Johnson, Bass, editor, etc.
        → "Johnson explains..."
        → Not: "Derrida states..."

        E0/A4 = EXPLICIT + SECONDARY COMMENTATOR
        Direct statement by reviewer/scholar/commentator.
        → "The commentator argues..."
        → Never convert into Derrida's own claim.

        E0/A5 = EXPLICIT + UNCERTAIN SPEAKER
        Statement is explicit, but speaker cannot be established.
        → "The passage states..."
        → Avoid personal attribution.


        E1/A0 = CLOSE PARAPHRASE + PRIMARY AUTHOR
        Close semantic restatement of Derrida's explicit proposition.
        → Safe:
        "Derrida argues..."
        "Derrida maintains..."

        E1/A1 = CLOSE PARAPHRASE + QUOTED OTHER
        Close paraphrase of someone Derrida quotes.
        → Attribute to quoted person.
        → "Marx argues, in the passage quoted by Derrida..."

        E1/A2 = CLOSE PARAPHRASE + DISCUSSED OTHER
        Close paraphrase of a position Derrida attributes to another person.
        → "Derrida presents Fukuyama as maintaining..."

        E1/A3 = CLOSE PARAPHRASE + TRANSLATOR/EDITOR
        Close paraphrase of Johnson/Bass/editor.
        → "Johnson characterizes Derrida's position as..."

        E1/A4 = CLOSE PARAPHRASE + SECONDARY COMMENTATOR
        Close paraphrase of secondary interpretation.
        → "The commentator interprets Derrida as..."

        E1/A5 = CLOSE PARAPHRASE + UNCERTAIN SPEAKER
        Meaning is clear but speaker isn't.
        → "The passage suggests/states..."
        → Do not assign to Derrida.


        E2/A0 = LOCAL INFERENCE + PRIMARY AUTHOR
        One inferential step from Derrida's explicit statement.
        → Qualify:
        "Derrida's discussion suggests..."
        "The passage indicates..."
        → Avoid presenting inference as direct statement.

        E2/A1 = LOCAL INFERENCE + QUOTED OTHER
        Inference from words Derrida quotes from another person.
        → "The quoted passage suggests..."
        → Do not attribute inference directly to Derrida or quoted author.

        E2/A2 = LOCAL INFERENCE + DISCUSSED OTHER

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
            current_text = response.content
            recursion_prompt = f"""
            ... your editing rules ...

            TEXT TO EDIT:

            {current_text}

            SOURCES FOR THE TEXT:

            {context_str}
            """
            response = llm.invoke(recursion_prompt)

    final_prompt = f"""
    You are the final prose renderer for an evidence-grounded academic system.

    The text below has already undergone evidence and attribution auditing.

    Rewrite it as polished academic prose.

    CRITICAL:
    Do not expose source-analysis or reasoning procedures.
    Do not discuss retrieved evidence, chunks, metadata, audits, evidence classes,
    attribution rules, or why a claim was accepted or rejected.

    State supported propositions directly.

    Preserve:
    - factual content
    - necessary qualifications
    - explicit synthesis markers where required
    - citations
    - correct attribution

    Remove:
    - meta-commentary about evidence
    - explanations of citation decisions
    - explanations of attribution decisions
    - explanations of epistemic decisions
    - redundant source descriptions

    Do not introduce any new substantive claims.
    Do not strengthen qualified claims.
    Do not remove necessary synthesis markers.
    Do not alter citations except to fix formatting.

    CITATION ENTAILMENT

    A citation must support the entire factual or interpretive proposition
    immediately preceding it.

    Do not use a citation to support an inference merely because the citation
    supports the premises from which that inference was constructed.

    Example:

    SOURCE:
    "Derrida was born in French Algeria."

    ALLOWED:
    "Derrida was born in French Algeria (Source)."

    NOT ALLOWED:
    "Derrida's Algerian birth shaped his critique of Western metaphysics
    (Source)."

    The source establishes the birthplace. It does not establish the causal
    relationship.

    If a source establishes A, you may state A.
    Do not state A → B unless the source also establishes that relationship.

    BIOGRAPHY → THOUGHT RULE

    Never infer that a biographical fact caused, shaped, influenced,
    anticipated, informed, reinforced, explains, illuminates, or gave rise
    to a philosophical position unless a supplied source explicitly makes
    that connection.

    This prohibition applies even when the connection seems plausible,
    widely accepted, or interpretively useful.

    INFERENTIAL TRIGGERS

    Before producing any sentence containing language such as:

    - shaped
    - influenced
    - informed
    - led to
    - gave rise to
    - reinforced
    - reflects his experience
    - can be traced to
    - provides the basis for
    - explains his later
    - resonates with his experience
    - likely
    - suggests that his experience
    - offers a backdrop for
    - can be understood through

    verify that the SOURCE ITSELF asserts the relationship.

    If not, remove the inference.

    TEXT:
    {response.content}

    SOURCES:
    {context_str}
    """

    response = llm.invoke(final_prompt)

    print(f"\n--- Answer from {CHAT_MODEL} ---")
    print(response.content)

if __name__ == "__main__":
    main()