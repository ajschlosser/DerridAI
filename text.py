from textblob import TextBlob
import json
import re
from defaults import PHILOSOPHY_STOPWORD_EXCEPTIONS_EN, PHILOSOPHY_STOPWORD_EXCEPTIONS_FR
from logger import Logger
from multi_rake import Rake
from keybert import KeyBERT
from langdetect import detect
from fast_langdetect import detect

from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
from sumy.nlp.stemmers import Stemmer

from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

from sentence_transformers import SentenceTransformer, util
import spacy
import dl_translate as dlt

nlps = {
    "en": spacy.load("en_core_web_trf"),
    "fr": spacy.load("fr_dep_news_trf") # GPU accelerated RoBERTa-based transformer model
}

LOG = Logger.setup("text")

rake = Rake()
km_model = KeyBERT()

sentence_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

def detect_phrasing(text: str, instructions):
    t = extract_likeness(
        target=instructions,
        text=text
    )
    if len(t) > 0:
        return True
    return False

def extract_query_and_flters(text: str, lang: str):
    doc = nlps[lang](text)

    filters = {
        "canonical_work_ids": [],
        "works_referenced": [],
        "materials_languages": [],
        "institutions_referenced": [],
        "locations_referenced": [],
        "persons_referenced": [],
        "events_referenced": [],
        "groups_referenced": [],
        "limit": 10,
        "response_language": "en"
    }

    def handle_work(work: str):
        if detect_phrasing(work, "Monolingualism of the Other; or The Prosthesis of Origin"):
            filters["canonical_work_ids"].append("derrida-le_monolinguisme_de_l_autre_ou_la_prothese_d_origine-1996")
            filters["canonical_work_ids"].append("derrida-monolingualism_of_the_other_or_the_prosthesis_of_origin-1998")
        if detect_phrasing(work, ["Specters", "Spectres", "Marx", "Marxism"]):
            filters["canonical_work_ids"].append("derrida-spectres_de_marx-1993")
            filters["canonical_work_ids"].append("derrida-specters_of_marx_the_state_of_the_debt_the_work_of_mourning_and_the_new_international-2006")
        if detect_phrasing(work, "Of Grammatology"):
            filters["canonical_work_ids"].append("derrida-de_la_grammatologie-1967")
        if detect_phrasing(work, "Writing and Difference"):
            filters["canonical_work_ids"].append("derrida-l_ecriture_et_la_difference-1967")
            filters["canonical_work_ids"].append("derrida-writing_and_difference-1978")
        if detect_phrasing(work, "Dissemination"):
            filters["canonical_work_ids"].append("derrida-dissemination-1981")
            filters["canonical_work_ids"].append("derrida-dissemination-1972")
        if detect_phrasing(work, "Gift of Death"):
            filters["canonical_work_ids"].append("derrida-the_gift_of_death-1995")
            filters["canonical_work_ids"].append("derrida-donner_la_mort-1999")

    def handle_location(location: str):
        if detect_phrasing(location, ["Algeria", "North Africa", "Maghreb", "Algiers"]):
            filters["canonical_work_ids"].append("derrida-le_monolinguisme_de_l_autre_ou_la_prothese_d_origine-1996")
            filters["canonical_work_ids"].append("derrida-monolingualism_of_the_other_or_the_prosthesis_of_origin-1998")

    def handle_person(person: str):
        if detect_phrasing(person, "Martin Heidegger"):
            filters["canonical_work_ids"].append("derrida-l_oreille_de_heidegger-1994")
            filters["canonical_work_ids"].append("derrida-of_spirit_heidegger_and_the_question-1989")
            filters["canonical_work_ids"].append("derrida-de_l_esprit_heidegger_et_la_question-1987")
            filters["canonical_work_ids"].append("derrida-l_oreille_de_heidegger-1994")
        if detect_phrasing(person, ["Francis Fukuyama", "Emmanuel Levinas"]):
            filters["canonical_work_ids"].append("derrida-spectres_de_marx-1993")
            filters["canonical_work_ids"].append("derrida-specters_of_marx_the_state_of_the_debt_the_work_of_mourning_and_the_new_international-2006")
        if detect_phrasing(person, "Emmanuel Levinas"):
            filters["canonical_work_ids"].append("derrida-adieu_a_emmanuel_levinas-1997")
            filters["canonical_work_ids"].append("derrida-adieu_to_emmanuel_levinas-1999")

    def handle_event(event: str):
        if detect_phrasing(event, ["World War II", "Second World War", "WWII", "WW2", "World War 2", "Vichy", "German occupation", "under the occupation", "Nazi"]):
            filters["canonical_work_ids"].append("derrida-le_monolinguisme_de_l_autre_ou_la_prothese_d_origine-1996")
            filters["canonical_work_ids"].append("derrida-monolingualism_of_the_other_or_the_prosthesis_of_origin-1998")
            filters["canonical_work_ids"].append("derrida-of_spirit_heidegger_and_the_question-1989")
            filters["canonical_work_ids"].append("derrida-de_l_esprit_heidegger_et_la_question-1987")
            filters["canonical_work_ids"].append("derrida-on_cosmopolitanism_and_forgiveness-2005-dooley_hughes")

    for ent in doc.ents:
        if ent.label_ == "NORP":
            filters["groups_referenced"].append(ent.text)
        if ent.label_ == "EVENT":
            filters["events_referenced"].append(ent.text)
            handle_event(ent.text)
        if ent.label_ == "ORG":
            filters["institutions_referenced"].append(ent.text)
        if ent.label_ == "GPE":
            filters["locations_referenced"].append(ent.text)
            handle_location(ent.text)
        if ent.label_ == "PERSON":
            filters["persons_referenced"].append(ent.text)
            handle_person(ent.text)
        if ent.label_ == "WORK_OF_ART":
            filters["works_referenced"].append(ent.text)
            handle_work(ent.text)
        if ent.label_ == "LANGUAGE":
            filters["materials_languages"].append(ent.text)
        if ent.label_ == "CARDINAL":
            filters["limit"] = int(ent.text)
    
    return filters

def extract_likeness(target: str, text: str, threshold: float = 0.55):
    sentences = TextBlob(text).sentences
    LOG.info("sentences extracted: %d", len(sentences))
    target_embedding = sentence_model.encode(target, convert_to_tensor=True)
    likeness_scores = []
    for sentence in sentences:
        sentence_embedding = sentence_model.encode(str(sentence), convert_to_tensor=True)
        similarity = util.pytorch_cos_sim(target_embedding, sentence_embedding).max().item()
        if similarity >= threshold:
            likeness_scores.append((str(sentence), similarity))
    return likeness_scores


def remove_stopwords(text: str, language: str = "en"):
    language = "english" if language == "en" else "french" if language == "fr" else language
    stop_words = set(stopwords.words(language))
    if language == "english":
        stop_words = stop_words - PHILOSOPHY_STOPWORD_EXCEPTIONS_EN
    elif language == "french":
        stop_words = stop_words - PHILOSOPHY_STOPWORD_EXCEPTIONS_FR | {"l'", "L'"}
    
    # Tokenize the sentence (splits words and punctuation cleanly)
    words = word_tokenize(text)
    
    # Filter out grammatical filler words
    filtered_words = [word for word in words if word.lower() not in stop_words]
    
    # Rejoin the words back into a sentence
    return " ".join(filtered_words)


def summarize_text(text: str, language: str = "en", num_sentences: int = 3) -> str:
    """Summarizes the given text using the Edmundson summarizer."""
    lang = "english" if language[0] in ["en", "en_us"] else "french" if language[0] in ["fr", "fr_fr"] else language
    LOG.info("Summarizing text in language: %s", language)
    stemmer = Stemmer(lang)
    summarizer = LsaSummarizer(stemmer)
    try:
        parser = PlaintextParser.from_string(text, Tokenizer(lang))
        summary = summarizer(parser.document, num_sentences)
        return " [...] ".join(str(sentence) for sentence in summary)
    except Exception as e:
        LOG.error("Could not summarize text!", e)
        return text
 
def extract_keywords(
        text: str,
        threshold: float = 0.425,
        keyphrase_ngram_range: tuple[int, int] = (1, 1),
        stop_words: list[str] = []
    ) -> list[str]:
    """Extracts keywords from the given text using MultiRake."""
    default_stop_words = ["french","english","français","anglais","derrida","jacques","philosophy"]
    try:
        keywords = km_model.extract_keywords(
            text,
            keyphrase_ngram_range=keyphrase_ngram_range,
            stop_words=default_stop_words + (stop_words or [])
        )
        keywords = [(remove_stopwords(key), score) for key, score in keywords]
        return [key for key, _ in keywords if _ >= threshold]
    except Exception as e:
        LOG.error("Could not extract keywords!", e)
        return []

def correct_spelling(text: str) -> str:
    """Corrects the spelling of the given text using TextBlob."""
    try:
        return str(TextBlob(text).correct())
    except Exception as e:
        LOG.error("Could not correct spelling!", e)
        return text

def get_language_status(languages: list[str]) -> tuple[bool, bool]:
    """Returns a tuple indicating whether English and French are present in the list of languages."""
    return ("en" in languages, "fr" in languages)

def detect_languages(text: str, threshold: float = 0.4) -> list[str]:
    languages = []
    results = detect(text)
    for result in results:
        if result["lang"] not in languages and result["score"] > threshold:
            languages.append(result["lang"])
    return languages

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

def strip_code_fence(text: str, extract_json: bool = False) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:toon|json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    if extract_json:
        LOG.info("Extracting JSON...")
        extracted_text = list(extract_json_objects(text))
        text = extracted_text[0] if extracted_text else text  # Get the first JSON object found, or empty string if none
    return text

mt = dlt.TranslationModel() 
def translate(text: str, from_lang:str = "en", to_lang: str = "fr") -> str:
    """Translates the given text to the target language using DeepL Translate."""
    try:
        t = mt.translate(text, source=from_lang, target=to_lang)
        LOG.info("Translating text from %s to %s: %s --> %s", from_lang, to_lang, text, t)
        return t
    except Exception as e:
        LOG.error("Could not translate text!", e)
        return text