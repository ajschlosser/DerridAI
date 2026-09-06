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

BATCH_SIZE = 0
REVIEW_PASSES = 1
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
    keep = {
        "record_id",
        "work",
        "page_start",
        "page_end",
        "text",
        "quoted_speaker",
    }
    return {k: v for k, v in doc.items() if k in keep}

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
                try:
                    d = json.loads(line)
                except json.JSONDecodeError as e:
                    LOG.debug("Skipping line: %s", e)
                    continue
                if not started:
                    if d.get("record_id") != START_ID:
                        continue
                    started = True
                records.append(d)
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

Audit only CURRENT_RECORD. Change quoted_speaker only with clear textual evidence.

VALID:
1. "Hamlet: ..." → Hamlet
2. '"..." says Hamlet' → Hamlet
3. "Kant calls this Marktpreis" → Kant
4. A quotation explicitly introduced as someone's words.

INVALID:
1. A person is merely discussed.
2. Their theory, legacy, philosophy, or influence is discussed.
3. Their name is near somebody else's quotation.
4. A work title such as "(Hamlet)" appears after a stage direction.
5. Neighboring records quote them.

For every new speaker, provide an exact evidence_span from CURRENT_RECORD.
If you cannot quote the evidence, make no change.

Existing non-null values get extra protection:
do not delete or replace them unless clearly wrong.

Named/searchable fictional identities are valid.

Valid:
- Hamlet
- Horatio
- Ghost (Hamlet)
- Hamlet's Ghost
- Timon of Athens

Usually invalid because too generic:
- Painter
- Stranger
- King
- Guard
- Someone
- a ghost

A generic role becomes valid only when the work/context makes it a
specific searchable identity, e.g. Ghost (Hamlet).

Return JSON only.

<CURRENT_RECORD>
{current_record}
</CURRENT_RECORD>

<CURRENT_RECORD_IN_CONTEXT>
{context}
</CURRENT_RECORD_IN_CONTEXT>

OUTPUT
Return exactly one JSON object and nothing else.

Example JSON that adds a new speaker:

    {{
        "update_fields": {{
            "quoted_speaker": "Bilbo Baggins", <-- only if new! otherwise update_fields = {{}},
            "is_direct_quote": true
        }},
        "evidence_type": "explicit_attribution",
        "evidence_span": "Says Hamlet",
        "adjudication_reason": "Explicit attribution."
    }}

Example JSON that deletes an existing speaker:

    {{
        "update_fields": {{
            "quoted_speaker": null, <-- explicitly null out the existing speaker
            "is_direct_quote": null
        }},
        "evidence_type": null,
        "evidence_span": null,
        "adjudication_reason": "No speaker present."
    }}

Example JSON that indicates NO CHANGE or NO OP to the record:

    {{
        "update_fields": {{}},
        "evidence_type": null,
        "evidence_span": null,
        "adjudication_reason": "Current record is fine."
    }}

VALID_EVIDENCE_TYPES = {{
    "dialogue_label",
    "explicit_attribution",
    "explicit_source",
    "quotation_continuation"
}}
"""

    REVIEW_PROMPT = """
You are a veto reviewer.

Your ONLY task is to decide whether the proposed quoted_speaker change
is sufficiently supported by the CURRENT_RECORD.

Do not propose a different speaker.
Do not repair the proposal.
Do not infer missing metadata.

ACCEPT only if the CURRENT_RECORD itself contains clear textual evidence
for every proposed speaker.

VALID FOR ACCEPTANCE:
1. "Hamlet: ..." → Hamlet
2. '"..." says Hamlet' → Hamlet
3. "Kant calls this Marktpreis" → Kant
4. A quotation explicitly introduced as someone's words.

INVALID FOR ACCEPTANCE:
1. A person is merely discussed.
2. Their theory, legacy, philosophy, or influence is discussed.
3. Their name is near somebody else's quotation.
4. A work title such as "(Hamlet)" appears after a stage direction.
5. Neighboring records quote them.
When more than 50 percent uncertain, REJECT.

IMPORTANT NEGATIVE EXAMPLES

1. "Marx's legacy remains..." 
   → Do NOT assign Marx. Marx is being discussed.

2. "Enter the ghost, exit the ghost (Hamlet)"
   → Do NOT assign Hamlet. "Hamlet" identifies the work, not the speaker.

3. "Hamlet's tragedy concerns..."
   → Do NOT assign Hamlet unless actual words are attributed to Hamlet.

4. "Kant placed dignity above Marktpreis"
   → Kant MAY be valid because a distinctive Kantian formulation is
     explicitly sourced to Kant.

Named/searchable fictional identities are valid.

Valid:
- Hamlet
- Horatio
- Ghost (Hamlet)
- Hamlet's Ghost
- Timon of Athens

Usually invalid because too generic:
- Painter
- Stranger
- King
- Guard
- Someone
- a ghost

A generic role becomes valid only when the work/context makes it a
specific searchable identity, e.g. Ghost (Hamlet).

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

Example response for a ACCEPTANCE of the proposed change):

{{
  "decision": "ACCEPT",
  "reason": "Marx is directly quoted by the author."
  "update_fields": {{
    "quoted_speaker": ["Karl Marx"],
    "is_direct_quote": true
  }}
}}

Example response for an REJECTION of the proposed change:

{{
  "decision": "REJECT",
  "update_fields": {{}}
  "reason": "Marx is discussed but no words are directly attributed to him."
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

        # ============================================================
        # SAFETY GATES BEFORE REVIEW
        # ============================================================

        update_fields = prompt_result_dict.get("update_fields", {})

        # 1. Only care about quoted_speaker changes here.
        has_speaker_change = "quoted_speaker" in update_fields

        # 2. Hard evidence validation for additions/replacements.
        if has_speaker_change and update_fields.get("quoted_speaker") is not None:
            valid_evidence_types = {
                "dialogue_label",
                "explicit_attribution",
                "explicit_source",
                "quotation_continuation",
            }

            evidence_type = prompt_result_dict.get("evidence_type")
            evidence_span = prompt_result_dict.get("evidence_span")

            def normalize_text(s):
                if not s:
                    return ""
                return " ".join(str(s).replace("\n", " ").split()).lower()

            current_text_normalized = normalize_text(current_record.get("text", ""))
            evidence_normalized = normalize_text(evidence_span)

            if evidence_type not in valid_evidence_types:
                LOG.warning(
                    "Rejecting quoted_speaker update: invalid evidence_type=%s",
                    evidence_type,
                )
                update_fields.pop("quoted_speaker", None)
                has_speaker_change = False

            elif not evidence_span:
                LOG.warning(
                    "Rejecting quoted_speaker update: missing evidence_span"
                )
                update_fields.pop("quoted_speaker", None)
                has_speaker_change = False

            elif evidence_normalized not in current_text_normalized:
                LOG.warning(
                    "Rejecting quoted_speaker update: evidence_span not found in current text: %s",
                    evidence_span,
                )
                update_fields.pop("quoted_speaker", None)
                has_speaker_change = False

        # 3. Protect existing non-null speaker values.
        old_speaker = current_record.get("quoted_speaker")
        new_speaker = update_fields.get("quoted_speaker")

        if (
            has_speaker_change
            and old_speaker is not None
            and new_speaker != old_speaker
        ):
            LOG.warning(
                "Rejecting destructive quoted_speaker replacement: %s -> %s",
                old_speaker,
                new_speaker,
            )
            update_fields.pop("quoted_speaker", None)
            has_speaker_change = False

        # Put sanitized updates back into the result.
        prompt_result_dict["update_fields"] = update_fields

        # ============================================================
        # REVIEW
        # ============================================================

        review_result_dict = {}

        # Do not review records that have no quoted_speaker proposal.
        count = REVIEW_PASSES if has_speaker_change else 0

        while count > 0:
            LOG.info("Beginning review pass #%d", count)
            update_fields = prompt_result_dict.get("update_fields", dict())
            review_result_str, _ = await llm.prompt(params={
                "user": REVIEW_PROMPT,
                "template": {
                    "update_fields": json.dumps(update_fields),
                    "previous_adjudication_reason": json.dumps({
                        "quoted_speaker": update_fields.get("quoted_speaker"),
                        "evidence_span": prompt_result_dict.get("evidence_span"),
                    }),
                    "context": full_context_str,
                    "current_record": current_record_medadata_str
                }
            })
            review_result_str = repair_json(strip_code_fence(review_result_str))
            review_result_dict = json.loads(review_result_str)

            if type(review_result_dict) is list:
                review_result_dict = review_result_dict[0]

            decision = review_result_dict.get("decision")

            if decision == "ACCEPT":
                # Reviewer may only preserve the original proposal.
                review_result_dict["update_fields"] = update_fields

            else:
                # REJECT, malformed output, uncertainty, etc. = veto.
                review_result_dict["update_fields"] = {}

            prompt_result_dict = review_result_dict

            LOG.info("Review result: %s", review_result_dict)
            count -= 1

        final_audit_dict = review_result_dict if len(review_result_dict.items()) else prompt_result_dict

        LOG.info("Final audit result for record [%s]: %s", current_record.get("record_id"), final_audit_dict)
        LOG.info(f"model: {MODEL} | ctx: {NUM_CTX} | temp: {TEMPERATURE} | top_k: {TOP_K} | top_p: {TOP_P} | mirostat_eta: {ETA if MIROSTAT > 0 else "n/a"} | mirostat_tau: {TAU if MIROSTAT >0 else "n/a"} | mirostat: {"disabled" if MIROSTAT == 0 else "enabled"} | surrounding neighbor batch size: {BATCH_SIZE} | reasoning: {"disabled" if REASONING == False else "enabled"}")
        LOG.info("Total time elapsed: %.2f", time.perf_counter() - start)

        update_fields = final_audit_dict.get("update_fields", dict())

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