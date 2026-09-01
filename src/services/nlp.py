import os
import time
from textblob import TextBlob
from keybert import KeyBERT
from fast_langdetect import detect
import nltk
from spacy.tokens import Doc
from sentence_transformers import SentenceTransformer, util
import spacy
import logging
import dl_translate as dlt
from data.knowledge_base import DERRIDA_CANONICAL_LOCATIONS, DERRIDA_CANONICAL_EVENTS, DERRIDA_CANONICAL_PERSONS, DERRIDA_CANONICAL_WORKS, CANONICAL_IDS_TO_TITLES
from schemas.schemas import DerridAIQueryMetadata
LOG = logging.getLogger(__name__)

DEFAULT_SENTENCE_TRANSFORMER_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

"""
NLPService provides various natural language processing functionalities including:
- Extracting semantic likeness between text and target phrases.
- Detecting specific phrasings within text.
- Identifying languages present in a text.
- Extracting structured metadata from queries related to Derrida's works.
"""
class NLPService:
    nlp_models: dict[str, spacy.language.Language]
    km_model: KeyBERT
    sentence_transformer: SentenceTransformer
    sentence_transformer_model: str
    mt: dlt.TranslationModel
    def __init__(self): 
        LOG.debug("Loading spaCy models...")
        self.nlp_models = {
            "en": spacy.load("en_core_web_lg"),
            "fr": spacy.load("fr_core_news_lg")
        }
        LOG.debug("Initializing KeyBERT...")
        self.sentence_transformer_model = DEFAULT_SENTENCE_TRANSFORMER_MODEL
        self.km_model = KeyBERT(model=self.sentence_transformer_model)
        LOG.debug(f"Initializing sentence transformer model: {self.sentence_transformer_model}")
        local_sentence_transformer_model_path = f"./data/models/{self.sentence_transformer_model.replace('/', '_')}"
        if not os.path.exists(local_sentence_transformer_model_path):
            self.sentence_transformer.save(local_sentence_transformer_model_path)
        self.sentence_transformer = SentenceTransformer(local_sentence_transformer_model_path, local_files_only=True)
        LOG.debug("Initializing translation model...")
        self.mt = dlt.TranslationModel()
    def extract_keywords(
            self,
            text: str,
            threshold: float = 0.425,
            keyphrase_ngram_range: tuple[int, int] = (1, 1),
            stop_words: list[str] = []
        ) -> list[str]:
        default_stop_words = ["french","english","français","anglais","derrida","jacques","philosophy"]
        try:
            keywords = self.km_model.extract_keywords(
                text,
                keyphrase_ngram_range=keyphrase_ngram_range,
                stop_words=default_stop_words + (stop_words or [])
            )
            keywords = [(str(key), float(score)) for key, score in keywords]  # type: ignore[misc]
            return [key for key, score in keywords if score >= threshold]
        except Exception as e:
            LOG.error("Could not extract keywords!", e)
            return []

    def extract_likeness(self, target: str | list[str] | tuple[str, ...], text: str | list[str], threshold: float = 0.55):
        if isinstance(text, list):
            phrases = text
        else:
            phrases = list(TextBlob(text).sentences)  # type: ignore[arg-type]
        target_embedding = self.sentence_transformer.encode(target, convert_to_tensor=True)
        likeness_scores = []
        for phrase in phrases:
            LOG.debug(f"Processing phrase: {phrase}")
            sentence_embedding = self.sentence_transformer.encode(str(phrase), convert_to_tensor=True)
            similarity = util.pytorch_cos_sim(target_embedding, sentence_embedding).max().item()
            LOG.debug(f"Similarity for phrase '{phrase}' to target '{target}': {similarity}")
            if similarity >= threshold:
                likeness_scores.append((str(phrase), similarity))
        return likeness_scores

    def detect_phrasing(self, text: str, instructions: str | list[str] | tuple[str, ...], language: str = "en"):
        doc: Doc = self.nlp_models[language](text)
        
        phrases = []
        current_phrase = []
        
        for token in doc:
            # Group Nouns, Proper Nouns, Pronouns, Prepositions (ADP), and Determiners/Articles (DET)
            if token.pos_ in {"NOUN", "PROPN", "PRON", "ADP", "DET"}:
                current_phrase.append(token.text_with_ws)
            else:
                if current_phrase:
                    phrases.append("".join(current_phrase).strip())
                    current_phrase = []
        if current_phrase:
            phrases.append("".join(current_phrase).strip())
            
        # Filter out empty strings or isolated lone prepositions/determiners
        phrases = [p for p in phrases if len(p) > 2 and any(t.pos_ in {"NOUN", "PROPN", "PRON", "ADP", "DET"} for t in self.nlp_models[language](p))]

        LOG.debug(f"Extracted noun chunk phrases: {phrases}")
        
        t = self.extract_likeness(
            target=instructions,
            text=phrases
        )
        
        return len(t) > 0


    def detect_languages(self, text: str, threshold: float = 0.4) -> list[str]:
        languages = []
        results = detect(text)
        for result in results:
            if result["lang"] not in languages and float(result["score"]) > threshold:
                languages.append(result["lang"])
        return languages

    def translate(self, text: str, from_lang:str = "en", to_lang: str = "fr") -> str:
        """Translates the given text to the target language using DeepL Translate."""
        try:
            t = self.mt.translate(text, source=from_lang, target=to_lang)
            LOG.debug("Translating text from %s to %s: %s --> %s", from_lang, to_lang, text, t)
            return str(t)
        except Exception as e:
            LOG.error("Could not translate text!", e)
            return text


LOG.debug("Checking for existing local nltk data...")
if not nltk.download('punkt', quiet=True):
    start = time.perf_counter()
    LOG.debug(" - None found. Downloading necessary nltk data...")
    nltk.download('punkt')
    nltk.download('punkt_tab')
    nltk.download('stopwords')
    nltk.download('wordnet')
    elapsed = time.perf_counter() - start
    LOG.debug(f" - NLTK data download completed in {elapsed:.2f} seconds.")
else:
    LOG.debug("Local nltk data already present.")