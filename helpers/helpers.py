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

import json
from .logging import get_logger

LOG = get_logger(__name__)

def parse_natural_language_find_query(query: str, llm_client) -> dict:
    """
    Uses the local LLM to extract structured search parameters from natural language.
    Returns a dict: {'is_find_all': bool, 'term': str, 'title': str, 'author': str}
    """
    LOG.info("Parsing natural language to improve query...")
    prompt = f"""
    Analyze the following user query and extract search parameters as a JSON object.
    
    Query: "{query}"
    
    Extract these fields:
    - "is_find_all": true if the user is asking to find/list/get *every* mention, instance, or occurrence of a specific word or phrase. False if it is a general question or conceptual RAG prompt.
    - "original_query": the original query.
    - "term": your determination of the exact keyword or phrase they want to find (null if none) based on the query.
    - "title": the book or source title mentioned in the query, if any (null if none).
    - "author": the author mentioned in the query, if any (null if none).
    - "specifiers": an array of 4-7 specifying keywords NOT IN the query but related to the query (e.g. a query like 'Did Derrida like The Beach Boys?' might have specifying topics like ["music" "surf music","rock and roll","brian wilson","pet sounds"])

    Note:
    - If the user only provides part of the book or author's name, complete it for the JSON value.
    - If the user mispells or makes a mistake with any term, fix it for them.
    - Valid authors are: Jacques Derrida, Martin Heidegger
    - Valid books by Jacques Derrida are:
        * Of Grammatology
        * Spectres of Marx
        * Monolingualism of the Other; or, The Prosthesis of Origin
        * Writing and Difference
        * Limited, Inc.
        * Glas
        * Margins of Philosophy
        * Dissemination
        * The Ear of the Other
        * The Animal That Therefore I Am
        * The Postcard
        * Of Spirit: Heidegger and the Question
        * Acts of Literature
        * Hospitality, Vol. 1
        * The Truth in Painting
        * Speech and Phenomena
        * "Structure, Sign, and Play in the Discourse of the Human Sciences"
    - Valid books by Martin Heidegger are:
        * Being and Time
        * Nietzsche, Vols. 1 and 2
        * Nietzsche, Vols. 3 and 4


    Return ONLY valid JSON with no markdown formatting or extra text.
    Example format: {{"is_find_all": true, "term": "What is democracy?", "title": "Spectres of Marx", "author": null, "specifiers": ["politics","marxism"]}}
    """
    try:
        response = llm_client.invoke(prompt)
        # Clean up response content in case the model wraps it in markdown blocks
        content = response.content.strip()
        if content.startswith("```json"):
            content = content[7:-3].strip()
        elif content.startswith("```"):
            content = content[3:-3].strip()
        data = json.loads(content)
        LOG.info(f"LLM improved query: {data}")
        return data
    except Exception as e:
        LOG.warning("Failed to parse query via LLM helper: %s. Falling back to standard RAG.", e)
        return {"is_find_all": False, "term": None, "title": None, "author": None}
