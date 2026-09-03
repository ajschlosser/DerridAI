import time
import json
from clients.llm import LLMClient
from utils.strip_code_fence import strip_code_fence
from schemas.schemas import LLMModels
from logging_config import logging, configure_logging

configure_logging(logging.DEBUG, "derridai-scan_records.log")
LOG = logging.getLogger(__name__)

BATCH_SIZE = 1

#GEMMA4_12B no reasoning works well
llm = LLMClient(
    model=LLMModels.GEMMA4_12B,
    reasoning=False,
    temperature=0.4,
    mirostat_eta=0.5,
    mirostat_tau=0.5,
)

old_prompt =  """

    <INSTRUCTIONS>
    You are auditing records in a RAG pipeline database.
    These records are chunks of the English and French works of the French philosopher Jacques Derrida.
    Look at the `text` field for each record to see if the other fields, especially the metadata fields, are correct.
    Fields like `position_holder`, `speaker`, `stance`, `discourse_role`, `quoted_speaker`, etc. are especially important.
    Audit them extremely carefully.
    </INSTRUCTIONS>
    <CURRENT RECORD>
    Now look at this record metadata for [record_id {record_id}]:

    {current_record_metadata_str}

    Note also the following metadata about the above record (perhaps consider adding any new references): {current_metadata}
    </CURRENT RECORD>
    <CONTEXT>
    That record has the following surround context:

    {full_context}

    Note that the context shows which records come before and which records come after this record.
    </CONTEXT>
    <REQUIREMENTS>
    Given the above context and this record's text, is this record's metadata correct? Or does it need to be fixed?

    DO NOT assume a record is incorrect just because fields are `null`.

    DO NOT fix a record's metadata using data or metadata from surrounding records. That is strictly forbidden.

    DO NOT make small changes. DO NOT add new categories or types of values.
    
    DO NOT turn arrays or objects into strings. Arrays remain arrays, even arrays of one.
    
    You are required to follow convention. For example, to know what to use as `discourse_role`, look at what other records have done.

    Return ONLY JSON in your response, following the example schema below:

    {{
        "record_id": c.get("record_id")
        "update_fields": {{
            ... <-- pick ONE field, if any, in the record that requires updating/fixing, and provide the new value, e.g.:
            position_holder: <new_value>
        }}
    }}

    ONLY add fields to "update_fields" if they require updating. Do not add repeat values.

    If "update_fields" has fields that require updating, also add a "processor_notes" field to "update_fields" with a value of 20-30 words to help an LLM correctly read the record
    </REQUIREMENTS>
    
"""

async def scan_records():
    # --- STEP 1: Load All Records (Keep this part) ---
    # We use the 'records' list to hold all loaded data.
    records = []
    try:
        with open("data/base/derrida9_primary_en.jsonl") as f:
            for line in f:
                try:
                    d = json.loads(line.strip())
                    records.append(d)
                except json.JSONDecodeError as e:
                    LOG.debug(f"Skipping line due to JSON error: {e}")
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
{"\n".join([f"{k}={v}" for k, v in d.items()])}
""" for d in previous_context])

        next_text = "\n".join([f"""
{"\n".join([f"{k}={v}" for k, v in d.items()])}
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
    # LOG.debug("Example context for the first record:")
    # LOG.debug(json.dumps(context_windows[BATCH_SIZE]))

    responses= []

    for i, c in enumerate(context_windows):
        start = time.perf_counter()
        full_context = c.get("full_context", "")
        record_str = json.dumps(c)
        current_text = c.get("current_record").get("text", "")
        #current_metadata = extract(text=current_text, lang="en")
        #LOG.debug("current_metadata: %s", json.dumps(current_metadata))
        current_record_metadata_str = "\n".join([f"{k}={v}" for k, v in c.get("current_record", {}).items() if k != "current_record_metadata_str"])
        LOG.info("Processing record %s", c.get("current_record", {}).get("record_id", ""))
        LOG.info("Record metadata: %s", current_record_metadata_str)
        LOG.debug("Record context: %s", full_context)
        r, _ = await llm.prompt(params={
            "user": """

    <INSTRUCTIONS>
    You are auditing records in a RAG pipeline database. You are focused only on the `position_holder` field and its correct values.
    Now, look at the `text` field for the record '{record_id}' to see if the `position_holder` field for record '{record_id}' is correct.
    If it is, move on to the next record.
    If not, make the appropriate change.
    Audit them extremely carefully.
    </INSTRUCTIONS>
    <CURRENT RECORD>
    Now look at this record metadata for [record_id {record_id}]:

    {current_record_metadata_str}

    </CURRENT RECORD>
    <REQUIREMENTS>    
    You are required to follow convention. For example, to know what to use as `position_holder`, look at what other records have done.
    Do not assume that the `document_author`, `speaker`, `target`, etc. is the same as the `discourse_role`. Read the text to see who is.
    The `position_holder` is the person whose position is being described. Sometimes, there is more than one `discourse_role`.
    If there is more than one `position_holder`, you may use an array of strings, e.g. ["Jacques Derrida", "Hamlet"]
    If you make a change to `position_holder`, confirm that `is_direct_quote`, `quoted_speaker`, `speaker`, and related fields don't also need adjustments.
    Return ONLY JSON in your response, following the example schema below:

    {{
        "record_id": c.get("record_id")
        "update_fields": {{
            position_holder: <new_value> <-- only if new! otherwise update_fields = {{}}
        }}
    }}

    ONLY add a field to "update_fields" if it requires updating. Do not add repeat values. Do not add no-ops.

    </REQUIREMENTS>
    
    """,
            "template": {
                "record_str": record_str,
                "full_context": full_context,
                "record_id": c.get("record_id"),
                "current_record_metadata_str": current_record_metadata_str,
            }
        })
        r = strip_code_fence(r)


        #LOG.debug("LLM response: %s", r)
        try:
            r_dict = json.loads(r)
            if (len(r_dict.get("update_fields")) > 0): # rule out nitpicks/processor notes
                LOG.info("Need to update fields: %s", json.dumps(r_dict.get("update_fields")))
                with open("data/base/notes.jsonl", "a") as out:
                    new_record = {
                        **c.get("current_record", {}),
                        **r_dict.get("update_fields")
                    }
                    LOG.info(f"Record [{r_dict.get("record_id")}] is invalid, saving reasoning")
                    out.write(json.dumps(new_record) + "\n")
        except json.JSONDecodeError as e:
            LOG.error(e)
            continue
        LOG.info("Step time: %d", time.perf_counter() - start)
        responses.append(r)
    return responses

async def main():
    LOG.info("Starting record scanner script...")
    result = await scan_records()
    LOG.info("Result: %s", result)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())