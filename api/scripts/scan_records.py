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

DEFAULTS = {
    "BATCH_SIZE": 2,
    "REASONING": False,
    "TEMPERATURE": 0.0,
    "ETA": 0.12,
    "TAU": 2.5,
    "TOP_K": 0,
    "TOP_P": 1.0,
    "MODEL": LLMModels.PHI4_14B,
    "MIROSTAT": 0,
    "NUM_CTX": 262114 // 32,
    "START_LINE": None,
    "START_ID": None, 
}

BATCH_SIZE = 1
REASONING = False
TEMPERATURE = 0.0 # disabled
ETA = 0.12  # 0.07 smooth and steady
TAU = 2.5   # 5.0 = matches natural language; 2.0 = code generation; 7.0 = creative
TOP_K = 0 # Low = conservative; 0 = disabled
TOP_P = 1.0 # Low = conservative; 1.0 = disabled
MODEL = LLMModels.GEMMA4_E2B
MIROSTAT = 0
NUM_CTX = 262144 // 32 # 262144 // 32 = 8K, 40 = 6K, 56 = 4
START_LINE = None
#START_ID = "som-2b238d2ddadca7-00101"
START_ID = ""
FILE_STR = f"{MODEL.replace("/", "_")}-{NUM_CTX}-eta_{ETA}-tau_{TAU}-temp_{TEMPERATURE}-batch_{BATCH_SIZE}-{"reasoning" if REASONING else "standard"}" if MIROSTAT != 0 else f"{MODEL.replace("/", "_")}-{NUM_CTX}-temp_{TEMPERATURE}-batch_{BATCH_SIZE}-{"reasoning" if REASONING else "standard"}"
configure_logging(logging.DEBUG, f"./logs/derridai-scan_records.4-{FILE_STR}.log")
LOG = logging.getLogger(__name__)

#GEMMA4_12B no reasoning works well
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

AUDIT_PROMPT = r"""
You are a conservative metadata auditor for a scholarly RAG corpus. Resolve
exactly one field: `quoted_speaker`. Treat its current value as an
untrusted hypothesis. Accuracy is more important than finding a correction.

DEFINITION
A quoted speaker is a specifically identified real human person whose words are
reproduced as a direct quotation in current_record.text. The quotation may be
inline, block-formatted, translated, or imperfectly punctuated by OCR, but the
text must present the words as that person's words.

The document author, current narrator, speaker, position holder, target, or
cited author is NOT a quoted speaker merely because that person owns, states,
discusses, or is associated with the surrounding prose. A document author can
count only when the current text explicitly reproduces that author's earlier
words as a quotation.

NOT DIRECT QUOTATION
- paraphrase, summary, indirect speech, or reported belief;
- a name or citation without reproduced words;
- scare quotes, use/mention, a technical term, a title, a slogan with no human
  attribution, or words mentioned as words;
- the current document's ordinary prose or an unattributed dramatic voice;
- words attributed only by guessing from topic, work, target, or metadata.

A fictional or dramatic character such as Hamlet, Horatio, or Marcellus can be
a "human" source for this field. When the current record reproduces lines from a
literary work, name its author only if the supplied text explicitly attributes
those quoted words to that person. Do not supply an author from outside
knowledge merely because you recognize the work.

BOUNDARY CONTEXT
Decide what belongs to the CURRENT record only. BEFORE and AFTER excerpts may
be used solely to resolve an attribution or quotation whose syntax crosses the
current record boundary. Never copy a neighbor's quoted_speaker or other
metadata, and never count quoted words that occur only in a neighbor.

RESOLUTION PROCEDURE
1. Locate every candidate quotation whose words occur in `text` field of CURRENT_RECORD.
2. Exclude every candidate covered by NOT DIRECT QUOTATION.
3. For each remaining quotation, identify the human source from explicit local
   attribution. A boundary excerpt may resolve a pronoun or continued block only
   when the connection is unambiguous.
4. Return the complete resolved value, whether or not it differs from the
   current value.
5. If a qualifying quotation is plausible but its human source cannot be
   resolved from the supplied text, do not guess.

VALUE RULES
- Use `null` when no specifically identified human is directly quoted.
- Use the full canonical name already established by the supplied evidence.
  Otherwise use the name exactly as printed. Do not invent an expansion,
  nickname, spelling change, identity, or merged name.
- One person is normally a string; multiple people are an array of unique
  strings ordered by first quoted appearance.
- Container formatting is handled by the program. Concentrate on correct name
  membership, not whether a one-person value is a string or one-item array.

EVIDENCE RULES
- Evidence must be a short, contiguous, verbatim excerpt from
  `text` ield of CURRENT_RECORD containing the quoted words. Do not use ellipses
  unless they occur in the source.
- Evidence must be a short, contiguous, verbatim excerpt from the
  current text or boundary excerpts that identifies or unambiguously links the
  person to those words.
- If you propose a non-null value that differs from the current membership,
  evidence is required. Do not invent evidence.

Use these contrasts as rules, not as facts about the input:
- `Arendt argues that judgment is political.` is paraphrase: no quoted speaker.
- `Arendt writes, "judgment is political".` directly quotes Arendt.
- `the word "judgment"` is use/mention: no quoted speaker.
- `(Arendt, p. 20)` alone is a citation: no quoted speaker.

WARNING:
    - There will often be many names to choose from, and you will be tempted
    to mistake a nearby name for the actual `quoted_speaker`. In cases where
    you cannot resolve the name, err on NO CHANGE.
    - More often than not, if the original value is `null`, it's meant to be `null`.
    - Be EXTRA wary when you are reviewing potentially destructive changes to existing metadata
    - Watch for ontology leakage in moments of ambiguity!
    
OUTPUT
Return exactly one JSON object and nothing else.

Example JSON that adds a new speaker:   

    {{
        "update_fields": {{
            quoted_speaker: "Bilbo Baggins" <-- only if new! otherwise update_fields = {{}},
        }},
        "adjudication_reason": "The proposed quoted speaker is quoted in the passage saying 'I'm not a dog'.", <-- do NOT use nested quotation marks in this value! Paraphrase the speaker's quoted remarks
    }}

Example JSON that deletes an existing speaker:

    {{
        "update_fields": {{
            quoted_speaker: null <-- explicitly null out the existing speaker
        }},
        "adjudication_reason": "The proposed quoted speaker is not actually quoted in the passage. It's a dog saying 'bark'.", <-- do NOT use nested quotation marks in this value! Paraphrase the speaker's quoted remarks
    }}

Only add a field to "update_fields" if it requires updating.
Do not use quotation marks of any kind in your field values. Quotation marks are used for the JSON schema and must not be in field values.

<CURRENT_RECORD>
{current_record_metadata_str}
</CURRENT_RECORD>
<EVIDENCE>
{full_context}
</EVIDENCE>

IMPORTANT: VALIDATE YOUR JSON BEFORE RESPONDING. FIX IT IF IT FAILS.
Do not use quotation marks of any kind in your field values. Quotation marks are used for the JSON schema and must not be in field values.

Make sure your JSON encloses field/property names and string values with double-quotes and uses proper JSON types.

""".strip()

REVIEW_PROMPT = """
    You are a conservative record auditor verifying the `quoted_speaker` field of certain records.

    Your job is to audit current proposed changes.

    For the following CURRENT_RECORD, a PROPOSED_CHANGE was made. Scrutinize it carefully.

    Review both the CURRENT_RECORD and the PROPOSED_CHANGE, and determine if the change is GOOD, NEUTRAL or HARMFUL/DESTRUCTIVE.
        - A change is GOOD if it improves the record's accuracy
        - A change is NEUTRAL if it's a no-op or neither improves or worsens the record's accuracy
        - A change is HARMFUL if it makes the record less accurate
        - A change is DESTRUCTIVE if it takes a record that was already good and makes it less accurate

    Keep an eye out for the following:
        - Ensure that plasusible existing speakers aren't being deleted unless clearly contradicted
        - `quoted_speaker` must be a human being (including important fictional characters). Works, publications, groups, roles, and generic descriptors of types of people fail this test.
        - Watch for nearby-name errors: make sure the person being quoted is distinguished from the person being discussed.
        - Don't just turn strings into arrays or arrays back into strings. Prefer Array[String] when adjudicating multiple values for `quoted_speaker`.

    Ask yourself:
        - Did they mistake a nearby speaker for the `quoted_speaker`?
        - Did they assume a nearby name was a `quoted_speaker` without enough evidence?
        - Did they add a nearby name to a list of `quoted_speaker` values just because it happened to be close to the `quoted_speaker`?
        - Did they add a descriptive term like "The sailor" or "A ghost" instead of a named being like "Bilbo Baggins", "Medusa", or "Benjamin Franklin"?
    If so, that's probably HARMFUL or DESTRUCTIVE. Flag it!

    IMPORTANT: Use the surroudning CONTEXT if there is record spillover.

    <CURRENT_RECORD>
    {current_record_metadata_str}
    </CURRENT_RECORD>

    <PROPOSED_CHANGE>
    {update_fields}
    </PROPOSED_CHANGE>

    <CONTEXT>
    {context}
    </CONTEXT>

    Return exactly one JSON object and nothing else.
    Return ONLY JSON in your response.

    Example response for a REJECTION of the proposed change):

    {{
        "adjudication_result" "HARMFUL", <-- can be HARMFUL | DESTRUCTIVE
        "adjudication_reason": "The proposed quoted speaker is not actually quoted in the passage. It's a dog saying 'bark'.", <-- do NOT use nested quotation marks in this value! Paraphrase the speaker's quoted remarks
        "update_fields": {{}}
    }}

    Example response for an ACCEPTANCE of the proposed change:
    
    {{
        "adjudication_result": "GOOD", <-- can be GOOD | NEUTRAL
        "adjudication_reason": "The proposed quoted speaker is quoted in the passage saying 'I'm not a dog'.", <-- do NOT use nested quotation marks in this value! Paraphrase the speaker's quoted remarks
        "update_fields": {{
            quoted_speaker: "Bilbo Baggins" <-- only if new and adjudicated as GOOD or NEUTRAK! otherwise update_fields = {{}},
        }},
    }}

    Do not use quotation marks of any kind in your field values. Quotation marks are used for the JSON schema and must not be in field values.
    Do not use `None` to mean `null`. This is JSON, not Python.
    Remember, if a record is adjudicated as GOOD or NEUTRAL, `update_fields` needs to include the field with its new value.
    If a record is adjudicated as HARMFUL or DESTRUCTIVE, leave `update_fields` empty like {{}}. This prevents the harmful change from being applied.
    Finally: if the proposed change is an empty object, ensure that it was correct NOT to change anything

    IMPORTANT: VALIDATE YOUR JSON BEFORE RESPONDING. FIX IT IF IT FAILS.
    Do not use quotation marks of any kind in your field values. Quotation marks are used for the JSON schema and must not be in field values.

    WARNING:
    - There will often be many names to choose from, and you will be tempted
    to mistake a nearby name for the actual `quoted_speaker`. In cases where
    you cannot resolve the name, err on NO CHANGE.
    - More often than not, if the original value is `null`, it's meant to be `null`.
    - Be EXTRA wary when you are reviewing potentially destructive changes to existing metadata
    - Watch for ontology leakage in moments of ambiguity!

    Make sure your JSON encloses field/property names and string values with double-quotes and uses proper JSON types.

"""

SOURCE="data/base/out/notes_derrida9_primary_en.jsonl_hf.co_unsloth_gemma-4-E4B-it-GGUF:Q8_0-8192-temp_0.0-batch_1-standard.jsonl"
DEST=f"data/base/out/notes2_{os.path.split(SOURCE)[-1]}_{FILE_STR}.jsonl"

class DerridAIRecord():

    processor_notes: str
    year: int
    
    def __init__(self):
        pass

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

async def scan_records():
    # --- STEP 1: Load All Records (Keep this part) ---
    # We use the 'records' list to hold all loaded data.
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

    # --- STEP 2: Create the Context Windows (The New Logic) ---

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
{"\n".join([f"{k}={v}" for k, v in remove_noise(d).items()])}
""" for d in previous_context])

        next_text = "\n".join([f"""
{"\n".join([f"{k}={v}" for k, v in remove_noise(d).items()])}
""" for d in next_context])

        
        # 3. Assemble the full context window for the current record
        context_window = {
            "current_record": current_record,
            "previous_context": previous_context,
            "next_context": next_context,
            "full_context": "<BEGIN PREVIOUS CONTEXT>" + previous_text + "<END PREVIOUS CONTEXT><CURRENT RECORD> [...content...] </CURRENT RECORD><BEGIN NEXT CONTEXT>" + next_text + "</END NEXT CONTEXT>"
        }

        #LOG.debug("Creating context window #%d", len(context_windows) + 1)
        context_windows.append(context_window)

    # The 'context_windows' list now contains a fully processed context for every record.
    LOG.info(f"\nSuccessfully generated {len(context_windows)} context windows.")

    responses= []

    for i, c in enumerate(context_windows):
        full_context = c.get("full_context", "")
        record_str = json.dumps(c)
        current_record = c.get("current_record")
        if hasattr(current_record, "processor_notes"):
            del current_record["processor_notes"]

        current_record_metadata_str = "\n".join([f"{k}={v}" for k, v in remove_noise(current_record).items() if k != "current_record_metadata_str"])
        LOG.info(f"model: {MODEL} | ctx: {NUM_CTX} | temp: {TEMPERATURE} | top_k: {TOP_K} | top_p: {TOP_P} | mirostat_eta: {ETA if MIROSTAT > 0 else "n/a"} | mirostat_tau: {TAU if MIROSTAT >0 else "n/a"} | mirostat: {"disabled" if MIROSTAT == 0 else "enabled"} | surrounding neighbor batch size: {BATCH_SIZE} | reasoning: {"disabled" if REASONING == False else "enabled"}")
        start = time.perf_counter()
        r, _ = await llm.prompt(params={
            "user": REVIEW_PROMPT,
            "template": {
                "context": full_context,
                "update_fields": current_record.get("update_fields"),
                #"record_id": c.get("record_id"),
                "current_record_metadata_str": current_record_metadata_str,
            }
        })

        r = strip_code_fence(text=r, extract_json=True)

        LOG.info("Initial audit (r) result: %s", r)
        r2_dict = json.dumps(r)
        r2, _ = await llm.prompt(params={
            "user": REVIEW_PROMPT,
            "template": {
                "context": full_context,
                "current_record_metadata_str": current_record_metadata_str,
                "update_fields": json.loads(repair_json(r2_dict)).get("update_fields", None)
            }
        })

        r2 = strip_code_fence(text=r2, extract_json=True)

        LOG.info("First review (r2) result: %s", r2)

        r3_dict = r2
        if type(r3_dict) is str:
            r3_dict = json.loads(repair_json(r3_dict))
        # if r3_dict.get("update_fields"):
        r3, _ = await llm.prompt(params={
            "user": REVIEW_PROMPT,
            "template": {
                "context": full_context,
                "current_record_metadata_str": current_record_metadata_str,
                "update_fields": r3_dict.get("update_fields", None)
            }
        })

        r3 = strip_code_fence(text=r3, extract_json=True)
        LOG.info("Second review (r3) result: %s", r3)
        # else:
        #     LOG.info("Skipping second review since no change has been suggested.")
        #     r3 = r2
        r4_dict = r3
        if type(r4_dict) is str:
            r4_dict = json.loads(repair_json(r4_dict))
        r4, _ = await llm.prompt(params={
            "user": REVIEW_PROMPT,
            "template": {
                "context": full_context,
                "current_record_metadata_str": current_record_metadata_str,
                "update_fields": r4_dict.get("update_fields", None)
            }
        })

        r4 = strip_code_fence(text=r3, extract_json=True)
        LOG.info("Third review (r4) result: %s", r4)
        LOG.debug("Prompting too %.2f seconds for record %s", time.perf_counter() - start, current_record.get("record_id"))
        try:
            r_dict = r3
            if (type(r_dict) is str):
                r_dict = json.loads(repair_json(r_dict))
            if (len(r_dict.get("update_fields", [])) > 0): # rule out nitpicks/processor notes
                LOG.info("Need to update fields: %s", json.dumps(r_dict.get("update_fields")))
                update_fields = r_dict.get("update_fields")
                current_record = c.get("current_record", {})
                with open(DEST, "a") as out:
                    new_record = {
                        **current_record,
                        **update_fields
                    }
                    previous_updates = new_record.get("updates", [])
                    for field_name in list(update_fields.keys()):
                        old_value = current_record.get(field_name, "Unknown/Error")
                        new_value =  update_fields.get(field_name, "Unknown/Error")

                        if field_name == "is_direct_quote" and new_value == True and not current_record.get("quoted_speaker", False):
                            LOG.warning("cannot have direct quote w/o speaker, skipping")
                            continue

                        if json.dumps(old_value) == json.dumps(new_value):
                            LOG.warning("values are the same, skipping: %s", old_value)
                            continue

                        fs = update_fields
                        cs = current_record

                        updated_qs = fs.get("quoted_speaker", "")
                        if updated_qs is not None and len(list(updated_qs)):
                            updated_qs = updated_qs if isinstance(updated_qs, str) else list(updated_qs)[0] #can be sting or list

                        if field_name == "quoted_speaker" and updated_qs == cs.get("document_author"):
                            LOG.warning("quoted_speaker is document_author, skipping: %s", cs.get("document_author"))
                            continue
                        if field_name == "quoted_speaker":
                            if updated_qs == cs.get("target"):
                                LOG.warning("quoted_speaker is target, skipping: %s", cs.get("target"))
                                continue
                            if updated_qs == cs.get("speaker"):
                                LOG.warning("quoted_speaker != speaker, skipping")
                                continue
                            
                        
                        previous_updates.append({
                            "field": field_name,
                            "old_value": old_value,
                            "new_value": new_value,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        })
                        if field_name == "quoted_speaker" and fs.get(field_name, None) and cs.get("is_direct_quote", False) == False:
                            LOG.info("Adjusting is_direct_quote: %s", fs)
                            previous_updates.append({
                                "field": "is_direct_quote",
                                "old_value": False,
                                "new_value": True,
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            })
                        if field_name == "quoted_speaker" and not fs.get(field_name, None) and cs.get("is_direct_quote", False) == True:
                            previous_updates.append({
                                "field": "is_direct_quote",
                                "old_value": True,
                                "new_value": False,
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            })

                    updates = {}
                    if len(previous_updates) > 0:
                        updates["updates"] = previous_updates
                        record = {
                            **new_record,
                            **updates
                        }
                        LOG.info(f"Record [{r_dict.get("record_id")}] is invalid, saving reasoning")
                        out.write(json.dumps(record) + "\n")
        except json.JSONDecodeError as e:
            LOG.error("trouble decoding the llm response: %s", e)
            LOG.error("oof: %s", str(r3))
            continue
        responses.append(r)
    return responses

async def main():
    LOG.info("Starting record scanner script...")
    result = await scan_records()
    LOG.info("Result: %s", json.dumps(result))

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())