from textblob import TextBlob
from polyglot.detect import Detector
from logger import Logger
import argostranslate.package
import argostranslate.translate
from multi_rake import Rake
from keybert import KeyBERT
from langdetect import detect
import pycld2 as cld2
from fast_langdetect import detect

LOG = Logger.setup("text")

# Download and install language models
argostranslate.package.update_package_index()
available_packages = argostranslate.package.get_available_packages()
package_to_install = next(
    filter(
        lambda x: ((x.from_code == "en" and x.to_code == "fr") or (x.from_code == "fr" and x.to_code == "en")),
        available_packages
    )
)
argostranslate.package.install_from_path(package_to_install.download())

rake = Rake()
km_model = KeyBERT()

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

def translate(text: str, from_code: str, to_code: str) -> str:
    """Translates the given text from the source language to the target language using Argos Translate."""
    try:
        installed_languages = argostranslate.translate.get_installed_languages()
        from_lang = next(filter(lambda x: x.code == from_code, installed_languages))
        to_lang = next(filter(lambda x: x.code == to_code, installed_languages))
        translation = from_lang.get_translation(to_lang)
        return translation.translate(text)
    except Exception as e:
        LOG.error("Could not translate text!", e)
        return text