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

"""helpers.py -- Utility helpers used across the Derrida RAG project.

The module is intentionally small -- it primarily contains the natural-language
query parsing logic used by :mod:`rag` and a helper that builds a dictionary
of search filters for the Chroma vector store. All logging is performed via
the shared logger defined in :mod:`src.derrida.logging`.
"""

import json
from .logging import get_logger
from config import args
from models import get_llm_chat

llm = get_llm_chat()

LOG = get_logger(__name__)

def parse_natural_language_find_query(query: str, llm_client = llm) -> dict:
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
        # The LLM might wrap the JSON in markdown fences; strip those.
        content = response.content.strip()
        if content.startswith("```json"):
            content = content[7:-3].strip()
        elif content.startswith("```"):
            content = content[3:-3].strip()
        data = json.loads(content)
        LOG.info("LLM improved query: %s", data)
        return data
    except Exception as e:
        LOG.warning("Failed to parse query via LLM helper: %s. Falling back to standard RAG.", e)
        return {"is_find_all": False, "term": None, "title": None, "author": None}

def get_search_filters():
    # ---------------------------------------------------------------------------
    # Dynamic filter configuration
    # ---------------------------------------------------------------------------
    raw_filters = {}
    if args.record_type and args.record_type.lower() != "all":
        raw_filters["record_type"] = args.record_type
    if args.author:
        raw_filters["author"] = args.author
    if args.title:
        raw_filters["source_title"] = args.title

    # Clean out any keys with None values
    filter_dict = {k: v for k, v in raw_filters.items() if v is not None}

    parsed_filters: dict = {}
    
    if filter_dict:
        if len(filter_dict) == 1:
            # Single condition can be passed directly
            parsed_filters = filter_dict
        else:
            # Multiple conditions require Chroma's explicit $and operator wrapper
            parsed_filters = {"$and": [{k: v} for k, v in filter_dict.items()]}
        LOG.info("Applied search filters: %s", parsed_filters)
    return parsed_filters

keyword_map = {
    # Your original entries
    "death": "Gift of Death",
    "presence": "Of Grammatology",
    "Rousseau": "Of Grammatology",
    "differance": "Of Grammatology",
    "différance": "Of Grammatology",
    "'play'": "Structure, Sign, and Play in the Discourse of the Human Sciences",

    # Spectres of Marx
    "Marx": "Spectres of Marx",
    "Marx,": "Spectres of Marx",
    "specter": "Spectres of Marx",
    "spectres": "Spectres of Marx",
    "ghost": "Spectres of Marx",
    "haunt": "Spectres of Marx",
    "haunting": "Spectres of Marx",
    "hauntology": "Spectres of Marx",
    "messianism": "Spectres of Marx",
    "messianic": "Spectres of Marx",
    "inheritance": "Spectres of Marx",
    "democracy": "Spectres of Marx",
    "democrat": "Spectres of Marx",
    "globalization": "Spectres of Marx",
    "capital": "Spectres of Marx",
    "capitalism": "Spectres of Marx",
    "spirit": "Spectres of Marx",

    # Monolingualism of the Other; or, The Prosthesis of Origin
    "language": "Monolingualism of the Other; or, The Prosthesis of Origin",
    "linguistic": "Monolingualism of the Other; or, The Prosthesis of Origin",
    "monolingualism": "Monolingualism of the Other; or, The Prosthesis of Origin",
    "monolingual": "Monolingualism of the Other; or, The Prosthesis of Origin",
    "other": "Monolingualism of the Other; or, The Prosthesis of Origin",
    "translation": "Monolingualism of the Other; or, The Prosthesis of Origin",
    "translating": "Monolingualism of the Other; or, The Prosthesis of Origin",
    "foreign": "Monolingualism of the Other; or, The Prosthesis of Origin",
    "mother tongue": "Monolingualism of the Other; or, The Prosthesis of Origin",
    "mother-tongue": "Monolingualism of the Other; or, The Prosthesis of Origin",
    "tongue": "Monolingualism of the Other; or, The Prosthesis of Origin",
    "writing": "Monolingualism of the Other; or, The Prosthesis of Origin",
    "bilingual": "Monolingualism of the Other; or, The Prosthesis of Origin",
    "bilingualism": "Monolingualism of the Other; or, The Prosthesis of Origin",
    "idiom": "Monolingualism of the Other; or, The Prosthesis of Origin",
    "accent": "Monolingualism of the Other; or, The Prosthesis of Origin",
    "colonial": "Monolingualism of the Other; or, The Prosthesis of Origin",
    "colonialism": "Monolingualism of the Other; or, The Prosthesis of Origin",
    "algeria": "Monolingualism of the Other; or, The Prosthesis of Origin",
    "france": "",

    # Writing and Difference
    "difference": "Writing and Difference",
    "trace": "Writing and Difference",
    "grammatology": "Writing and Difference",
    "structure": "Writing and Difference",
    "sign": "Writing and Difference",
    "signification": "Writing and Difference",
    "text": "Writing and Difference",
    "textual": "Writing and Difference",
    "iterability": "Writing and Difference",
    "supplement": "Writing and Difference",
    "archive": "Writing and Difference",
    "mimesis": "Writing and Difference",
    "iterable": "Writing and Difference",

    # (kept from your earlier map additions)
    "différance": "Writing and Difference",
    "differance": "Writing and Difference",

    # Dissemination
    "dissemination": "Dissemination",
    "disseminate": "Dissemination",
    "dispersal": "Dissemination",
    "sprouting": "Dissemination",
    "polysemy": "Dissemination",
    "ambiguity": "Dissemination",
    "equivocation": "Dissemination",
    "equivocal": "Dissemination",
    "multiplicity": "Dissemination",
    "plurality": "Dissemination",
    "refraction": "Dissemination",
    "scatter": "Dissemination",
    "spreading": "Dissemination",
    "propagation": "Dissemination",
    "relay": "Dissemination",
    "absence": "Dissemination",
    "permutation": "Dissemination",

    # Signature phrase labels you started with
    "play": "Structure, Sign, and Play in the Discourse of the Human Sciences",
    "structure, sign, and play in the discourse of the human sciences": "Structure, Sign, and Play in the Discourse of the Human Sciences",
    "center": "Structure, Sign, and Play in the Discourse of the Human Sciences",
    "decentering": "Structure, Sign, and Play in the Discourse of the Human Sciences",
    "event": "Structure, Sign, and Play in the Discourse of the Human Sciences",
    "bricolage": "Structure, Sign, and Play in the Discourse of the Human Sciences",
    "structure": "Writing and Difference",  # note: overwrites above if you kept both
    "sign": "Writing and Difference",       # note: overwrites above if you kept both
    "text": "Writing and Difference",

    # Glas
    "glas": "Glas",
    "glasses": "Glas",
    "margins": "Glas",
    "margin": "Glas",
    "page": "Glas",
    "colophon": "Glas",
    "column": "Glas",
    "columns": "Glas",
    "name": "Glas",
    "names": "Glas",
    "proper name": "Glas",
    "monument": "Glas",
    "epitaph": "Glas",
    "eulogy": "Glas",
    "father": "Glas",
    "son": "Glas",
    "Hegel": "Glas",
    "Genet": "Glas",
    "blanchot": "Glas",
    "mourning": "Glas",
    "death": "Glas",  # if you want “death” to hit Glas too; otherwise remove

    # Margins of Philosophy
    "margins of philosophy": "Margins of Philosophy",
    "margins": "Margins of Philosophy",
    "margin": "Margins of Philosophy",
    "philosophy": "Margins of Philosophy",
    "outside": "Margins of Philosophy",
    "outside the text": "Margins of Philosophy",
    "edge": "Margins of Philosophy",
    "border": "Margins of Philosophy",
    "threshold": "Margins of Philosophy",
    "limit": "Margins of Philosophy",
    "supplement": "Margins of Philosophy",
    "writing": "Margins of Philosophy",
    "text": "Margins of Philosophy",
    "commentary": "Margins of Philosophy",
    "comment": "Margins of Philosophy",
    "gloss": "Margins of Philosophy",
    "translation": "Margins of Philosophy",
    "method": "Margins of Philosophy",
    "metaphysics": "Margins of Philosophy",
    "deconstruction": "Margins of Philosophy",
    "deconstruct": "Margins of Philosophy",
    "interruption": "Margins of Philosophy",
    "rupture": "Margins of Philosophy",
    "rhetoric": "Margins of Philosophy",
    "style": "Margins of Philosophy"
}