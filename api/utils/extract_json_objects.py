import json
import re
import logging

LOG = logging.getLogger(__name__)

def extract_json_objects(text):
    """Finds and yields valid JSON objects from a text string."""
    # Find all starting positions of potential JSON objects
    for match in re.finditer(r"\{", text):
        start_index = match.start()

        # Attempt to decode the string from this starting position onward
        try:
            # raw_decode reads until it finds a complete, valid JSON structure
            obj, end_index = json.JSONDecoder().raw_decode(text[start_index:])
            yield obj
        except json.JSONDecodeError:
            # If it fails, it wasn't a valid JSON start point; keep looking
            continue
        except Exception as e:
            LOG.warning("Unexpected error while extracting JSON object: %s", e)
            continue