import os
import re
import time
import unicodedata
from datetime import datetime, timezone
import json
from clients.llm import LLMClient
from utils.strip_code_fence import strip_code_fence
from utils.extract_json_objects import extract_json_objects
from schemas.schemas import LLMModels
from logging_config import logging, configure_logging
from json_repair import repair_json

BATCH_SIZE = 2
REVIEW_PASSES = 0
REASONING = False #"low" #False
TEMPERATURE = 0.0 # disabled
ETA = 0.12  # 0.07 smooth and steady
TAU = 2.5   # 5.0 = matches natural language; 2.0 = code generation; 7.0 = creative
TOP_K = 0 # Low = conservative; 0 = disabled
TOP_P = 1.0 # Low = conservative; 1.0 = disabled
MODEL = LLMModels.QWEN_9B   # For GPT_OSS, don't forget to set reasoning to "low"
MIROSTAT = 0
NUM_CTX = 262144 // 64 #// 32 = 8K, 40 = 6K, 56 = 4
START_LINE = None
#START_ID = "som-627e04a8022507-00055"
START_ID = ""
FILE_STR = f"{MODEL.replace("/", "_")}-{NUM_CTX}-review_{REVIEW_PASSES}-eta_{ETA}-tau_{TAU}-temp_{TEMPERATURE}-batch_{BATCH_SIZE}-{"reasoning" if REASONING else "standard"}" if MIROSTAT != 0 else f"{MODEL.replace("/", "_")}-{NUM_CTX}-temp_{TEMPERATURE}-batch_{BATCH_SIZE}-{"reasoning" if REASONING else "standard"}"
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

SOURCE="data/base/derrida9_primary_en.jsonl"
SOURCE_NAME = os.path.splitext(os.path.basename(SOURCE))[0]
RUN_ID = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
DEST = (
    f"data/base/out/"
    f"audit_notes_{SOURCE_NAME}_{FILE_STR}_{RUN_ID}.jsonl"
)

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

def normalize_text(s):
    if not s:
        return ""

    text = unicodedata.normalize("NFKC", str(s))

    # Remove only line-break hyphenation and invisible discretionary hyphens.
    text = re.sub(
        r"(?<=\w)-[ \t]*\r?\n[ \t]*(?=\w)",
        "",
        text,
    )
    text = re.sub(r"\u00ad\s*", "", text)

    # Treat visually equivalent quotation marks, dashes, and zero-width
    # characters identically when checking a verbatim evidence span.
    text = text.translate(
        str.maketrans(
            {
                "\u2018": "'",
                "\u2019": "'",
                "\u201a": "'",
                "\u201b": "'",
                "\u201c": '"',
                "\u201d": '"',
                "\u201e": '"',
                "\u201f": '"',
                "\u2010": "-",
                "\u2011": "-",
                "\u2012": "-",
                "\u2013": "-",
                "\u2014": "-",
                "\u2015": "-",
                "\u200b": "",
                "\u200c": "",
                "\u200d": "",
                "\ufeff": "",
            }
        )
    )

    return " ".join(text.split()).casefold()


def validate_quoted_speaker(value):
    if value is None:
        return None

    if isinstance(value, str):
        value = value.strip()
        if not value:
            raise ValueError("quoted_speaker cannot be an empty string")
        return value

    if isinstance(value, list):
        if not value:
            raise ValueError("quoted_speaker list cannot be empty")

        cleaned = []

        for item in value:
            if not isinstance(item, str) or not item.strip():
                raise ValueError(
                    "quoted_speaker list must contain only non-empty strings"
                )

            item = item.strip()

            if item not in cleaned:
                cleaned.append(item)

        return cleaned

    raise ValueError(
        f"Invalid quoted_speaker type: {type(value).__name__}"
    )

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
/no_think
You are a conservative auditor of records pertaining to the works of Jacques Derrida.

Your job is to audit the `quoted_speaker` field of the CURRENT_RECORD.

A quoted_speaker is valid only when the CURRENT_RECORD provides
specific textual evidence attributing words, a quotation, or a distinctive
cited formulation to that speaker.

VALID evidence includes:
- Explicit dialogue: "Hamlet: ..."
- Explicit attribution: '"..." says Hamlet'
- Explicit source language: 'as Marx writes...', 'Kant calls this Marktpreis'
- A quotation clearly introduced as the words of a named character/person
- A recognizable quoted formulation explicitly tied to its source

NOT sufficient:
- The person is merely discussed
- The person is the target, subject, author, or position_holder
- The person's theory, legacy, influence, or philosophy is discussed
- The person's name appears near a quotation by someone else
- Neighboring records quote that person
- A work title appears without evidence that a character/person is speaking

When uncertain, preserve the existing value.

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

<CURRENT_RECORD_IN_CONTEXT>
{context}
</CURRENT_RECORD_IN_CONTEXT>

OUTPUT

Return exactly one JSON object and nothing else.

Determine the COMPLETE set of supported quoted speakers in CURRENT_RECORD.
If multiple valid speakers are directly quoted, include all of them.

For every proposed non-null quoted_speaker, provide one evidence object
for each proposed speaker.

Addition or replacement example:

{{
  "update_fields": {{
    "quoted_speaker": ["Hamlet", "Ghost (Hamlet)"]
  }},
  "speaker_evidence": [
    {{
      "speaker": "Hamlet",
      "evidence_type": "dialogue_label",
      "evidence_span": "Hamlet: . . . Sweare."
    }},
    {{
      "speaker": "Ghost (Hamlet)",
      "evidence_type": "dialogue_label",
      "evidence_span": "Ghost [beneath]: Sweare."
    }}
  ],
  "adjudication_reason": "Both speakers are explicitly dialogue-labeled."
}}

Deletion example:

{{
  "update_fields": {{
    "quoted_speaker": null
  }},
  "speaker_evidence": [],
  "adjudication_reason": "The existing quoted_speaker is unsupported."
}}

No-change example:

{{
  "update_fields": {{}},
  "speaker_evidence": [],
  "adjudication_reason": "No change required."
}}

VALID_EVIDENCE_TYPES = [
  "dialogue_label",
  "explicit_attribution",
  "explicit_source",
  "quotation_continuation"
]
/no_think
"""

    REVIEW_PROMPT = """
/no_think
You are a veto reviewer.

Your ONLY task is to decide whether the proposed quoted_speaker change
is sufficiently supported by the CURRENT_RECORD.

Do not propose a different speaker.
Do not repair the proposal.
Do not infer missing metadata.

ACCEPT only if the CURRENT_RECORD itself contains clear textual evidence
for every proposed speaker.

REJECT if:
- the speaker is merely discussed;
- attribution depends primarily on neighboring records;
- the quotation belongs to another speaker;
- the evidence is ambiguous.

When uncertain, REJECT.

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

<PROPOSAL_EVIDENCE>
{proposal_evidence}
</PROPOSAL_EVIDENCE>

OUTPUT:

Accept:

{{
  "decision": "ACCEPT",
  "reason": "Every proposed speaker is directly supported by CURRENT_RECORD."
}}

Reject:

{{
  "decision": "REJECT",
  "reason": "At least one proposed speaker is not directly supported by CURRENT_RECORD."
}}
/no_think
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

        try:
            prompt_result_dict = json.loads(prompt_result_str)
        except (json.JSONDecodeError, TypeError) as e:
            LOG.warning("Rejecting malformed audit response: %s", e)
            continue

        if isinstance(prompt_result_dict, list):
            prompt_result_dict = (
                prompt_result_dict[0]
                if prompt_result_dict
                and isinstance(prompt_result_dict[0], dict)
                else {}
            )
        elif not isinstance(prompt_result_dict, dict):
            prompt_result_dict = {}

        LOG.info("Prompt result: %s", prompt_result_dict)
        LOG.info("Update fields: %s", prompt_result_dict.get("update_fields"))

        # ============================================================
        # SAFETY GATES BEFORE REVIEW
        # ============================================================

        raw_update_fields = prompt_result_dict.get("update_fields")

        if not isinstance(raw_update_fields, dict):
            LOG.warning(
                "Rejecting malformed update_fields: %r",
                raw_update_fields,
            )
            raw_update_fields = {}

        # This auditor is allowed to modify quoted_speaker only.
        unexpected_fields = set(raw_update_fields) - {"quoted_speaker"}

        if unexpected_fields:
            LOG.warning(
                "Discarding unauthorized update fields: %s",
                sorted(unexpected_fields),
            )

        update_fields = {}
        has_speaker_change = False

        if "quoted_speaker" in raw_update_fields:
            try:
                proposed_speaker = validate_quoted_speaker(
                    raw_update_fields["quoted_speaker"]
                )
            except ValueError as e:
                LOG.warning(
                    "Rejecting malformed quoted_speaker proposal: %s",
                    e,
                )
            else:
                old_speaker = current_record.get("quoted_speaker")

                # Remove literal no-op proposals.
                if proposed_speaker != old_speaker:
                    update_fields["quoted_speaker"] = proposed_speaker

            has_speaker_change = "quoted_speaker" in update_fields

            # Additions/replacements require evidence.
            if (
                has_speaker_change
                and update_fields["quoted_speaker"] is not None
            ):
                valid_evidence_types = {
                    "dialogue_label",
                    "explicit_attribution",
                    "explicit_source",
                    "quotation_continuation",
                }

                proposed = update_fields["quoted_speaker"]

                proposed_speakers = (
                    proposed
                    if isinstance(proposed, list)
                    else [proposed]
                )

                speaker_evidence = prompt_result_dict.get("speaker_evidence")

                reject_change = False

                if not isinstance(speaker_evidence, list):
                    LOG.warning(
                        "Rejecting quoted_speaker update: "
                        "speaker_evidence must be a list"
                    )
                    reject_change = True

                else:
                    evidence_by_speaker = {}

                    for item in speaker_evidence:
                        if not isinstance(item, dict):
                            continue

                        speaker = item.get("speaker")

                        if isinstance(speaker, str) and speaker.strip():
                            evidence_by_speaker[speaker.strip()] = item

                    current_text_normalized = normalize_text(
                        current_record.get("text", "")
                    )

                    for speaker in proposed_speakers:
                        evidence = evidence_by_speaker.get(speaker)

                        if evidence is None:
                            LOG.warning(
                                "Rejecting quoted_speaker update: "
                                "no evidence object for speaker=%r",
                                speaker,
                            )
                            reject_change = True
                            break

                        evidence_type = evidence.get("evidence_type")
                        evidence_span = evidence.get("evidence_span")

                        if evidence_type not in valid_evidence_types:
                            LOG.warning(
                                "Rejecting quoted_speaker update: "
                                "invalid evidence_type=%r for speaker=%r",
                                evidence_type,
                                speaker,
                            )
                            reject_change = True
                            break

                        if (
                            not isinstance(evidence_span, str)
                            or not evidence_span.strip()
                        ):
                            LOG.warning(
                                "Rejecting quoted_speaker update: "
                                "missing evidence_span for speaker=%r",
                                speaker,
                            )
                            reject_change = True
                            break

                        evidence_normalized = normalize_text(evidence_span)

                        if evidence_normalized not in current_text_normalized:
                            LOG.warning(
                                "Rejecting quoted_speaker update: "
                                "evidence_span not found for speaker=%r: %r",
                                speaker,
                                evidence_span,
                            )
                            reject_change = True
                            break

                if reject_change:
                    update_fields.pop("quoted_speaker", None)
                    has_speaker_change = False

        prompt_result_dict["update_fields"] = update_fields

        # ============================================================
        # REVIEW
        # ============================================================

        review_result_dict = {}
        proposal_evidence = prompt_result_dict.get("speaker_evidence", [])

        # Do not review records that have no quoted_speaker proposal.
        count = REVIEW_PASSES if has_speaker_change else 0

        while count > 0:
            LOG.info("Beginning review pass #%d", count)
            update_fields = prompt_result_dict.get("update_fields", dict())
            review_result_str, _ = await llm.prompt(params={
                "user": REVIEW_PROMPT,
                "template": {
                    "update_fields": json.dumps(update_fields),
                    "proposal_evidence": json.dumps(proposal_evidence),
                    "context": full_context_str,
                    "current_record": current_record_medadata_str
                }
            })
            review_result_str = repair_json(strip_code_fence(review_result_str))

            try:
                review_result_dict = json.loads(review_result_str)
            except (json.JSONDecodeError, TypeError) as e:
                LOG.warning("Rejecting malformed review response: %s", e)
                review_result_dict = {}

            if isinstance(review_result_dict, list):
                review_result_dict = (
                    review_result_dict[0]
                    if review_result_dict
                    and isinstance(review_result_dict[0], dict)
                    else {}
                )
            elif not isinstance(review_result_dict, dict):
                review_result_dict = {}

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
                        "evidence": final_audit_dict.get("speaker_evidence", {}),
                        "adjudication_reason": final_audit_dict.get("adjudication_reason", ""),
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
