import os
import time
from datetime import datetime, timezone
import json
from clients.llm import LLMClient
from utils.strip_code_fence import strip_code_fence
from utils.extract_json_objects import extract_json_objects
from schemas.schemas import LLMModels
from logging_config import logging, configure_logging
from json_repair import repair_json

BATCH_SIZE = 1
REVIEW_PASSES = 2
REASONING = False
TEMPERATURE = 0.0 # disabled
ETA = 0.12  # 0.07 smooth and steady
TAU = 2.5   # 5.0 = matches natural language; 2.0 = code generation; 7.0 = creative
TOP_K = 0 # Low = conservative; 0 = disabled
TOP_P = 1.0 # Low = conservative; 1.0 = disabled
MODEL = LLMModels.GEMMA4_E2B
MIROSTAT = 0
NUM_CTX = 262144 // 24 # 262144 // 32 = 8K, 40 = 6K, 56 = 4
START_LINE = None
#START_ID = "som-627e04a8022507-00055"
START_ID = ""
FILE_STR = f"{MODEL.replace("/", "_")}-{NUM_CTX}-eta_{ETA}-tau_{TAU}-temp_{TEMPERATURE}-batch_{BATCH_SIZE}-{"reasoning" if REASONING else "standard"}" if MIROSTAT != 0 else f"{MODEL.replace("/", "_")}-{NUM_CTX}-temp_{TEMPERATURE}-batch_{BATCH_SIZE}-{"reasoning" if REASONING else "standard"}"
configure_logging(logging.DEBUG, f"./logs/derridai-audit-{FILE_STR}.log")
LOG = logging.getLogger(__name__)

llm = LLMClient(
    model=MODEL,
    reasoning=REASONING,
    temperature=TEMPERATURE,
    mirostat=MIROSTAT,
    top_k=TOP_K,
    top_p=TOP_P,
    num_ctx=NUM_CTX,
    #mirostat_eta=ETA, #2.0
    #mirostat_tau=TAU, #0.1
)

#SOURCE="data/base/out/notes_derrida9_primary_en.jsonl_hf.co_unsloth_gemma-4-E4B-it-GGUF:Q8_0-8192-temp_0.0-batch_1-standard.jsonl"
SOURCE="data/base/derrida9_primary_en.jsonl"
DEST=f"data/base/out/audit_notes_{os.path.split(SOURCE[:10])[-1]}_{FILE_STR}.jsonl"

def remove_noise(doc: dict) -> dict:
    doc = doc.copy()
    if hasattr(doc, "processor_notes"):
        del doc["processor_notes"]
    del doc["year"]
    del doc["translator"]
    del doc["edition"]
    if hasattr(doc, "editor"):
        del doc["editor"]
    del doc["text_length"]
    del doc["needs_review"]
    del doc["review_reason"]
    del doc["document_language"]
    del doc["concepts"]
    del doc["original_language"]
    if hasattr(doc, "location"):
        del doc["location"]
    if hasattr(doc, "original_year"):
        del doc["original_year"]
    del doc["primary_text"]
    del doc["region_author"]
    del doc["region_type"]
    del doc["topics"]
    del doc["works_referenced"]
    del doc["document_is_translation"]
    if hasattr(doc, "semantic_function"):
        del doc["semantic_function"]
    del doc["full_citation"]
    del doc["attribution_confidence"]
    del doc["canonical_work_id"]
    del doc["extraction_quality"]
    if hasattr(doc, "semantic_classification_confidence"):
        del doc["semantic_classification_confidence"]
    return doc

def neighbor_context(d):
    return {
        "record_id": d["record_id"],
        "page_start": d.get("page_start"),
        "page_end": d.get("page_end"),
        "text": d["text"],
    }

async def audit_records():

    #============================#
    # 1. LOAD RECORDS
    #============================#
    records = []
    try:
        started = False if START_ID != "" else True
        #started = True
        with open(SOURCE) as f:
            for line in f:
                if started:
                    try:
                        d = json.loads(line.strip())
                        records.append(d)
                    except json.JSONDecodeError as e:
                        LOG.debug(f"Skipping line due to JSON error: {e}")
                d = json.loads(line.strip())
                if START_ID != "" and d.get("record_id") == START_ID:
                    started = True
    except FileNotFoundError as e:
        LOG.debug(f"Error loading files: {e}")
        records = [] # Ensure records is empty if files fail to load

    #============================#
    # 2. CREATE CONTEXT WINDOWS
    #============================#
    context_windows = []
    record_length = len(records)
    LOG.debug("Loaded %d records", record_length)

    # Iterate through the indices of the records list
    for i in range(record_length):
        # Current record is the one at index i
        current_record = records[i]
        
        # 1. Previous Context (Look-Behind BATCH_SIZE)
        start_index = max(0, i - BATCH_SIZE)
        previous_context = records[start_index:i]
        previous_context.reverse()

        # 2. Next Context (Look-Ahead BATCH_SIZE)
        
        # Start index is the record immediately after the current one
        start_index_next = i + 1
        
        # End index: i + BATCH_SIZE + 1 ensures we capture indices up to i + BATCH_SIZE.
        # We cap this at record_length to prevent errors at the end of the file.
        end_index_next = min(record_length, i + BATCH_SIZE + 1)
        
        next_context = records[start_index_next:end_index_next]

        previous_text = "\n".join([f"""
{"\n".join([f"{k}={v}" for k, v in neighbor_context(d).items()])}
""" for d in previous_context])

        current_text = "\n".join([f"""
{"\n".join([f"{k}={v}" for k, v in remove_noise(current_record).items()])}
"""])

        next_text = "\n".join([f"""
{"\n".join([f"{k}={v}" for k, v in neighbor_context(d).items()])}
""" for d in next_context])

        # 3. Assemble the full context window for the current record
        context_window = {
            "current_record": current_record,
            "previous_context": previous_context,
            "next_context": next_context,
            "full_context": "<BEGIN PREVIOUS_RECORD_CONTEXT>" + previous_text + "<END PREVIOUS_RECORD_CONTEXT><CURRENT_RECORD>" + current_text + "</CURRENT_RECORD><BEGIN NEXT_RECORD_CONTEXT>" + next_text + "</END NEXT_RECORD_CONTEXT>"
        }
        #LOG.debug("Context window for record #%d [%s]: %s", i, current_record.get("record_id"), context_window["full_context"])
        #LOG.debug("Creating context window #%d", len(context_windows) + 1)
        context_windows.append(context_window)

    # The 'context_windows' list now contains a fully processed context for every record.
    LOG.info(f"\nSuccessfully generated {len(context_windows)} context windows.")

    #============================#
    # 3. ITERATE OVER CONTEXTS
    #============================#

    AUDIT_PROMPT = """
You are a conservative auditor of records pertaining to the works of Jacques Derrida.

Your job is to audit the `quoted_speaker` field of the CURRENT_RECORD.

A `quoted_speaker` must be:
    - A named being (real human being, fictional character, mythological being, but some named being of a kind)
    - Directly quoted in the `text` field of the CURRENT_RECORD, and speaking in that quote
    - A being with a name, NOT a description of a person or being, or a role, or a category (e.g., NOT "someone" or "the ghost")

Example valid values: ["George Washington", "Medusa", "Hamlet", "Bilbo Baggins", "Thomas Jefferson", "God"]
Example invalid values: ["somebody", "the teacher", "a ghost", "a person", "Someone", "a Person", "Somebody"]

Just because a word is capitalized, do not assume it is a proper noun, e.g. "Someone" is not a valid name, even with a capital 'S'.

Beware of attributing nearby names to the `quoted_speaker`.

If the CURRENT_RECORD is not clear enough, use the surrounding CURRENT_RECORD_IN_CONTEXT to help you make a decision.

The `quoted_speaker` must come from the CURRENT_RECORD, but the CONTEXT can help you identify the `quoted_speaker`,
especially if the quoted text bleeds between records.

DO NOT let speakers from PREVIOUS_RECORD_CONTEXT or NEXT_RECORD_CONTEXT to bleed into CURRENT_RECORD.
DO NOT guess a CURRENT_RECORD `quoted_speaker` by extrapolating from PREVIOUS_RECORD_CONTEXT or NEXT_RECORD_CONTEXT.
However, if a quotation begins in the PREVIOUS_RECORD_CONTEXT and ends in the CURRENT_RECORD, use the `quoted_speaker` from
the PREVIOUS_RECORD_CONTEXT.

<CURRENT_RECORD>
{current_record}
</CURRENT_RECORD>

<CURRENT_RECORD_IN_CONTEXT>
{context}
</CURRENT_RECORD_IN_CONTEXT>

OUTPUT
Return exactly one JSON object and nothing else.
You may use Array[String] for passages with multiple speakers, e.g.: ["Bilbo Baggins", "Frodo Baggins"].
`is_direct_quote` is always Boolean, and refers to whether or not the `text` _contains_ a `quoted_speaker`.

Example JSON that adds a new speaker:

    {{
        "update_fields": {{
            quoted_speaker: "Bilbo Baggins", <-- only if new! otherwise update_fields = {{}},
            is_direct_quote: true
        }},
        "adjudication_reason": "Speaker Bilbo Baggins quoted saying 'I'm not a dog'.", <-- no more than 20 words MAX; use concise, sparing language, cite supporting quotation directly
    }}

Example JSON that deletes an existing speaker:

    {{
        "update_fields": {{
            quoted_speaker: null, <-- explicitly null out the existing speaker
            is_direct_quote: null
        }},
        "adjudication_reason": "Bilbo Baggins is in the passage, but is is not the one who says 'I'm not a dog'." <-- no more than 20 words MAX; use concise, sparing language
    }}

Be strict, precise, and conservative in your judgments. Err on the side of making fewer changes when not certain.
"""

    REVIEW_PROMPT = """
You are a careful second-pass reviewer of audited records of the works of Jacques Derrida.

Your job is to audit the `quoted_speaker` field of the CURRENT_RECORD.

Assume that the PROPOSED_CHANGES are incorrect and that you must justify them again.
Do not tblindlyt rust the PROPOSED_CHANGES. Assume a less-stringent auditor carelessly made them.
Your job is to make sure they are correct and, most important, PREVENT HARMFUL CHANGES.
If there is no direct evidence for the change, revert the PROPOSED_CHANGES.
The exception is deleting data-- in that case, ensure that the deletion is justified. For example,
removing "Someone" from the `quoted_speaker` field makes sense since "Someone" isn't a named being

You must decide if the PROPOSED_CHANGES are:
    - GOOD: corrects incorrect metadata, adds correct metadata, removes incorrect metadata, improves metadata quality
    - NEUTRAL: no-ops, normalizations, changes to records that do not make them substantively worse
    - HARMFUL: makes metadata less correct, removes correct metadata, adds incorrect metadata, generally worsens record quality

A `quoted_speaker` must be:
    - A named being (real human being, fictional character, mythological being, but some named being of a kind)
    - Directly quoted in the `text` field of the CURRENT_RECORD, and speaking in that quote
    - A being with a name, NOT a description of a person or being, or a role, or a category (e.g., "someone" or "the ghost")

Example valid values: ["George Washington", "Medusa", "Hamlet", "Bilbo Baggins", "Thomas Jefferson", "God"]
Example invalid values: ["somebody", "the teacher", "a ghost", "a person", "Someone", "a Person", "Somebody"]

Just because a word is capitalized, do not assume it is a proper noun, e.g. "Someone" is not a valid name, even with a capital 'S'.
Beware of attributing nearby names to the `quoted_speaker`.
If the `quoted_speaker` has a generic name like "Ghost", then citing the work in parentheses afterwards is encouraged: "Ghost (Hamlet)"
If the CURRENT_RECORD is not clear enough, use the surrounding CONTEXT to help you make a decision.
The `quoted_speaker` must come from the CURRENT_RECORD, but the CONTEXT can help you identify the `quoted_speaker`,
especially if the quoted text bleeds between records.
Be aware of context bleeds. If the preceding context cites Hamlet but the CURRENT_RECORD does not, do not let the preceding record's
metadata bleed into this records.

Be strict, precise, and conservative in your judgments. Err on the side of making fewer changes when not certain.

<CURRENT_RECORD>
{current_record}
</CURRENT_RECORD>

<CONTEXT>
{context}
</CONTEXT>

<PROPOSED_CHANGES>
{update_fields}
</PROPOSED_CHANGES>

<REASONS>
{previous_adjudication_reason}
</REASONS>

OUTPUT:
Return exactly one JSON object and nothing else.
Return ONLY JSON in your response.

Example response for a REJECTION of the proposed change):

{{
    "adjudication_result" "HARMFUL", <-- can be HARMFUL | DESTRUCTIVE
    "adjudication_reason": "The proposed quoted speaker is not actually quoted in the passage. It's a dog saying 'bark'.", <-- no more than 20 words MAX; use concise, sparing language
    "update_fields": {{}}
}}

Example response for an ACCEPTANCE of the proposed change:

{{
    "adjudication_result": "GOOD", <-- can be GOOD | NEUTRAL
    "adjudication_reason": "The proposed quoted speaker is quoted in the passage saying 'I'm not a dog'.", <-- no more than 20 words MAX; use concise, sparing language
    "update_fields": {{
        quoted_speaker: "Bilbo Baggins" <-- only if new and adjudicated as GOOD or NEUTRAL! otherwise update_fields = {{}},
    }},
}}

"""

    for i, c_window in enumerate(context_windows):
        start = time.perf_counter()
        full_context_str = c_window.get("full_context", "")
        current_record = c_window.get("current_record", None)

        # Failsafe
        if not current_record:
            raise TypeError("current_record needs to be a dict, not None")

        current_record_medadata_str = current_record_metadata_str = "\n".join([f"{k}={v}" for k, v in remove_noise(current_record).items() if k != "current_record_metadata_str"])

        prompt_result_str, _ = await llm.prompt(params={
            "user": AUDIT_PROMPT,
            "template": {
                "context": full_context_str,
                "current_record": current_record_medadata_str
            }
        })

        prompt_result_str = repair_json(strip_code_fence(prompt_result_str))
        prompt_result_dict = json.loads(prompt_result_str)
        if type(prompt_result_dict) is list:
            prompt_result_dict = prompt_result_dict[0]
        LOG.info("Prompt result: %s", prompt_result_dict)
        LOG.info("Update fields: %s", prompt_result_dict.get("update_fields"))

        review_result_dict = dict()
        count = int(REVIEW_PASSES if REVIEW_PASSES else 0)
        while count > 0:
            LOG.info("Beginning review pass #%d", count)
            review_result_str, _ = await llm.prompt(params={
                "user": REVIEW_PROMPT,
                "template": {
                    "update_fields": json.dumps(prompt_result_dict.get("update_fields")),
                    "previous_adjudication_reason": prompt_result_dict.get("adjudication_reason"),
                    "context": full_context_str,
                    "current_record": current_record_medadata_str
                }
            })
            review_result_str = repair_json(strip_code_fence(review_result_str))
            review_result_dict = json.loads(review_result_str)
            if type(review_result_dict) is list:
                review_result_dict = review_result_dict[0]
            prompt_result_dict = review_result_dict
            LOG.info("Review result: %s", review_result_dict)
            count -= 1

        # final_audit_str, _ = await llm.prompt(params={
        #     "user": REVIEW_PROMPT,
        #     "template": {
        #         "update_fields": json.dumps(review_result_dict.get("update_fields")),
        #         "previous_adjudication_reason": review_result_dict.get("adjudication_reason"),
        #         "context": full_context_str,
        #         "current_record": current_record_medadata_str
        #     }
        # })

        # final_audit_str = repair_json(strip_code_fence(final_audit_str))
        # final_audit_dict = json.loads(final_audit_str)

        final_audit_dict = review_result_dict if len(review_result_dict.items()) else prompt_result_dict

        LOG.info("Final audit result for record [%s]: %s", current_record.get("record_id"), prompt_result_dict)
        LOG.info(f"model: {MODEL} | ctx: {NUM_CTX} | temp: {TEMPERATURE} | top_k: {TOP_K} | top_p: {TOP_P} | mirostat_eta: {ETA if MIROSTAT > 0 else "n/a"} | mirostat_tau: {TAU if MIROSTAT >0 else "n/a"} | mirostat: {"disabled" if MIROSTAT == 0 else "enabled"} | surrounding neighbor batch size: {BATCH_SIZE} | reasoning: {"disabled" if REASONING == False else "enabled"}")
        LOG.info("Total time elapsed: %.2f", time.perf_counter() - start)

        update_fields = review_result_dict.get("update_fields", dict())

        if len(update_fields.keys()) > 0:

            with open(DEST, "a") as out:
                new_record = {
                    **current_record,
                    **update_fields
                }
                updates_to_apply = new_record.get("updates", [])
                for field_name in list(update_fields.keys()):
                    old_value = current_record.get(field_name, "Error")
                    new_value =  update_fields.get(field_name, "Error")

                    if json.dumps(old_value) == json.dumps(new_value):
                        LOG.warning("values are the same, skipping: %s", old_value)
                        continue

                    updates_to_apply.append({
                        "field": field_name,
                        "old_value": old_value,
                        "new_value": new_value,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                updates = {}
                if len(updates_to_apply) > 0:
                    updates["updates"] = updates_to_apply
                    record = {
                        **new_record,
                        **updates
                    }
                    LOG.info(f"Record [{review_result_dict.get("record_id")}] is invalid, saving reasoning")
                    out.write(json.dumps(record) + "\n")

async def main():
    result = await audit_records()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())