
import logging
from schemas.schemas import DerridAIQueryMetadata
from data.knowledge_base import (
    DERRIDA_CANONICAL_WORKS,
    DERRIDA_CANONICAL_LOCATIONS,
    DERRIDA_CANONICAL_PERSONS,
    DERRIDA_CANONICAL_EVENTS,
    CANONICAL_IDS_TO_TITLES
)

from services.nlp import NLPService
from utils.get_language_status import get_language_status

LOG = logging.getLogger(__name__)

class QueryMetadataExtractor:
    def __init__(self, nlp_service: NLPService):
        self.nlp_service = nlp_service

    def extract(self, text: str, lang: str) -> DerridAIQueryMetadata:
        doc = self.nlp_service.nlp_models[lang](text)
        metadata: DerridAIQueryMetadata = {
            "canonical_work_ids": [],
            "works_referenced": [],
            "canonical_work_ids_works_referenced": [],
            "institutions_referenced": [],
            "locations_referenced": [],
            "persons_referenced": [],
            "events_referenced": [],
            "groups_referenced": [],
            "languages_referenced": [],
            "limit": 10,
            "response_language": "en",
            "materials_languages": ["en", "fr"],
            "document_languages": ["en", "fr"],
            "prompt_languages": self.nlp_service.detect_languages(text)
        }

        def append_canonical_work_ids(ids: list[str], references: bool = False):
            for id in ids:
                if id not in metadata["canonical_work_ids"]:
                    metadata["canonical_work_ids"].append(id)
                if id not in metadata["canonical_work_ids_works_referenced"] and references:
                    metadata["canonical_work_ids_works_referenced"].append(id)

        def append_with_translation(key: str, text: str):
            if not metadata["materials_languages"] or len(metadata["materials_languages"]) < 2:
                metadata[key].append(text)
                return
            else:
                metadata[key].append(text)
                for i in range(1, len(metadata["materials_languages"]) - 1):
                    text_translated = self.nlp_service.translate(text=text, from_lang=metadata["materials_languages"][0], to_lang=metadata["prompt_languages"][i])
                    metadata[key].append(text_translated)
        
        def handle_work(work: str) -> None | list[str]:
            for work_phrase, canonical_ids in DERRIDA_CANONICAL_WORKS.items():
                if self.nlp_service.detect_phrasing(work, work_phrase):
                    ids = []
                    for id in canonical_ids:
                        ids.append(id)
                        append_canonical_work_ids([id], references=True)
                    return ids
            return None


        def handle_location(location: str):
            for location_phrases, canonical_ids in DERRIDA_CANONICAL_LOCATIONS.items():
                if self.nlp_service.detect_phrasing(location, location_phrases):
                    append_canonical_work_ids(canonical_ids)

        def handle_person(person: str):
            for person_names, canonical_ids in DERRIDA_CANONICAL_PERSONS.items():
                if self.nlp_service.detect_phrasing(person, person_names):
                    append_canonical_work_ids(canonical_ids)

        def handle_event(event: str):
            for event_phrases, canonical_ids in DERRIDA_CANONICAL_EVENTS.items():
                if self.nlp_service.detect_phrasing(event, event_phrases):
                    append_canonical_work_ids(canonical_ids)

        for ent in doc.ents:
            LOG.debug(f"Processing entity: label={ent.label_}, text={ent.text}")
            l, t = ent.label_, ent.text
            if l == "NORP":
                append_with_translation("groups_referenced", t)
            if l == "EVENT":
                append_with_translation("events_referenced", t)
                handle_event(t)
            if l == "ORG":
                append_with_translation("institutions_referenced", t)
            if l == "GPE":
                append_with_translation("locations_referenced", t)
                handle_location(t)
            if l == "PERSON":
                append_with_translation("persons_referenced", t)
                handle_person(t)
            if l == "WORK_OF_ART":
                canonical_ids = handle_work(t)
                if canonical_ids:
                    for id in canonical_ids:
                        metadata["works_referenced"].append(CANONICAL_IDS_TO_TITLES.get(id, t))
                else:
                    metadata["works_referenced"].append(t)
            if l == "LANGUAGE":
                metadata["languages_referenced"].append(t)
            if l == "CARDINAL":
                limit_n = self.nlp_service.detect_phrasing(
                    ent.text,
                    [
                        f"return top {ent.text} results",
                        f"only the top {ent.text}",
                        f"limit to top {ent.text}",
                        f"fetch the top {ent.text}",
                        f"limit sources to {ent.text}",
                        f"only consider {ent.text} results",
                        f"maximum of {ent.text} results",
                    ]
                )
                if limit_n:
                    metadata["limit"] = int(ent.text)

            limit_fr = self.nlp_service.detect_phrasing(
                text=text,
                instructions=["only check French sources", "consult only French", "only look at French texts", "use French resources only"]
            )
            if limit_fr:
                metadata["document_languages"] = ["fr"]
            else:
                limit_en = self.nlp_service.detect_phrasing(
                    text=text,
                    instructions=["only check English sources", "consult only English", "only look at English texts", "use English resources only"]
                )
                if limit_en:
                    metadata["document_languages"] = ["en"]

            # Translate the prompt
            en, fr = get_language_status(metadata["prompt_languages"])

            # Prompt is in English; translate to French
            if en:
                text_fr = self.nlp_service.translate(text, from_lang="en", to_lang="fr")
                metadata["prompt_fr"] = text_fr
                metadata["keywords_fr"] = self.nlp_service.extract_keywords(text_fr)

            # Prompt is in French; translate to English
            elif fr:
                text_en = self.nlp_service.translate(text, from_lang="fr", to_lang="en")
                metadata["prompt"] = text_en
                metadata["keywords"] = self.nlp_service.extract_keywords(text_en)

        return DerridAIQueryMetadata(**metadata)