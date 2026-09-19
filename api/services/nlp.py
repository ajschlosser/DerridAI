from __future__ import annotations

import logging
import os
import time
from functools import cached_property

import dl_translate as dlt
import nltk
import spacy
from fast_langdetect import detect
from keybert import KeyBERT
from sentence_transformers import SentenceTransformer, util
from spacy.tokens import Doc
from textblob import TextBlob

LOG = logging.getLogger(__name__)

DEFAULT_SENTENCE_TRANSFORMER_MODEL = os.getenv(
    "DERRIDAI_SENTENCE_TRANSFORMER_MODEL",
    "paraphrase-multilingual-MiniLM-L12-v2",
)


class NLPService:
    """
    Lightweight-at-startup NLP facade.

    Expensive NLP/translation models are loaded only by the methods that need
    them. This keeps API startup independent of untracked api/data assets and
    avoids failing the health check simply because a local model cache has not
    been created yet.
    """

    def __init__(self) -> None:
        self.sentence_transformer_model = DEFAULT_SENTENCE_TRANSFORMER_MODEL
        LOG.info(
            "Initialized NLPService with lazy model loading (sentence transformer: %s)",
            self.sentence_transformer_model,
        )

    @cached_property
    def nlp_models(self) -> dict[str, spacy.language.Language]:
        LOG.info("Loading spaCy language models")
        return {
            "en": spacy.load("en_core_web_lg"),
            "fr": spacy.load("fr_core_news_lg"),
        }

    @cached_property
    def sentence_transformer(self) -> SentenceTransformer:
        cache_folder = os.getenv("HF_HOME") or None
        LOG.info(
            "Loading sentence-transformer model %s (cache=%s)",
            self.sentence_transformer_model,
            cache_folder or "default",
        )
        return SentenceTransformer(
            self.sentence_transformer_model,
            cache_folder=cache_folder,
        )

    @cached_property
    def km_model(self) -> KeyBERT:
        # Reuse the same sentence-transformer instance rather than maintaining
        # a second copy in memory/cache.
        return KeyBERT(model=self.sentence_transformer)

    @cached_property
    def mt(self) -> dlt.TranslationModel:
        LOG.info("Loading translation model on first translation request")
        return dlt.TranslationModel()

    def extract_keywords(
        self,
        text: str,
        threshold: float = 0.425,
        keyphrase_ngram_range: tuple[int, int] = (1, 1),
        stop_words: list[str] | None = None,
    ) -> list[str]:
        default_stop_words = [
            "french",
            "english",
            "français",
            "anglais",
            "derrida",
            "jacques",
            "philosophy",
        ]
        try:
            keywords = self.km_model.extract_keywords(
                text,
                keyphrase_ngram_range=keyphrase_ngram_range,
                stop_words=default_stop_words + (stop_words or []),
            )
            normalized = [(str(key), float(score)) for key, score in keywords]
            return [key for key, score in normalized if score >= threshold]
        except Exception:
            LOG.exception("Could not extract keywords")
            return []

    def extract_likeness(
        self,
        target: str | list[str] | tuple[str, ...],
        text: str | list[str],
        threshold: float = 0.55,
    ) -> list[tuple[str, float]]:
        phrases = text if isinstance(text, list) else [str(x) for x in TextBlob(text).sentences]
        target_embedding = self.sentence_transformer.encode(target, convert_to_tensor=True)
        likeness_scores: list[tuple[str, float]] = []

        for phrase in phrases:
            sentence_embedding = self.sentence_transformer.encode(
                str(phrase),
                convert_to_tensor=True,
            )
            similarity = (
                util.pytorch_cos_sim(target_embedding, sentence_embedding)
                .max()
                .item()
            )
            if similarity >= threshold:
                likeness_scores.append((str(phrase), float(similarity)))

        return likeness_scores

    def detect_phrasing(
        self,
        text: str,
        instructions: str | list[str] | tuple[str, ...],
        language: str = "en",
    ) -> bool:
        model = self.nlp_models[language]
        doc: Doc = model(text)
        phrases: list[str] = []
        current_phrase: list[str] = []

        for token in doc:
            if token.pos_ in {"NOUN", "PROPN", "PRON", "ADP", "DET"}:
                current_phrase.append(token.text_with_ws)
            elif current_phrase:
                phrases.append("".join(current_phrase).strip())
                current_phrase = []

        if current_phrase:
            phrases.append("".join(current_phrase).strip())

        phrases = [
            phrase
            for phrase in phrases
            if len(phrase) > 2
            and any(
                token.pos_ in {"NOUN", "PROPN", "PRON", "ADP", "DET"}
                for token in model(phrase)
            )
        ]

        return bool(
            self.extract_likeness(
                target=instructions,
                text=phrases,
            )
        )

    def detect_languages(self, text: str, threshold: float = 0.4) -> list[str]:
        languages: list[str] = []
        try:
            results = detect(text)
        except Exception:
            LOG.exception("Language detection failed")
            return languages

        for result in results:
            language = str(result.get("lang", "")).strip().lower()
            score = float(result.get("score", 0.0))
            if language and language not in languages and score > threshold:
                languages.append(language)
        return languages

    def translate(
        self,
        text: str,
        from_lang: str = "en",
        to_lang: str = "fr",
    ) -> str:
        if not text or from_lang == to_lang:
            return text

        try:
            translated = self.mt.translate(
                text,
                source=from_lang,
                target=to_lang,
            )
            return str(translated)
        except Exception:
            # Retrieval can still proceed with the original query. Do not make
            # translation availability a hard dependency for the research API.
            LOG.exception("Could not translate text from %s to %s", from_lang, to_lang)
            return text


def _ensure_nltk_basics() -> None:
    """
    Preserve the legacy TextBlob/NLTK support without blocking normal API
    startup on downloads. The resources are fetched only when they are absent.
    """

    try:
        nltk.data.find("tokenizers/punkt")
        return
    except LookupError:
        pass

    start = time.perf_counter()
    LOG.info("NLTK punkt data not found; downloading baseline tokenizers")
    for package in ("punkt", "punkt_tab"):
        try:
            nltk.download(package, quiet=True)
        except Exception:
            LOG.exception("Could not download NLTK package %s", package)
    LOG.info("NLTK baseline setup completed in %.2f seconds", time.perf_counter() - start)


_ensure_nltk_basics()
