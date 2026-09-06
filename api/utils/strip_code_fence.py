import re
import json
from .extract_json_objects import extract_json_objects
import logging

LOG = logging.getLogger(__name__)

def strip_code_fence(text: str, extract_json: bool = False) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:toon|json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    if extract_json:
        try:
            extracted_text = list(extract_json_objects(text))
            text = extracted_text[0] if extracted_text else text  # Get the first JSON object found, or empty string if none
        except json.JSONDecodeError as e:
            LOG.warning("JSON: %s", e)
    LOG.debug("Extracted text: %s", text)
    return text