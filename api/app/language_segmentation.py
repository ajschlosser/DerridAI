# Copyright 2026 Aaron John Schlosser, PhD.
"""Language-aware deterministic text-boundary helpers.

This module deliberately separates orthographic sentence evidence from source
structure and semantic/discourse segmentation. It is dependency-free so the
Corpus Builder can always conserve source text, even when optional NLP models
are unavailable. Language metadata selects a profile when known; otherwise a
bounded Unicode-script detector chooses a conservative fallback profile.

The helpers never translate or rewrite source text. Sentence splitting is
lossless: concatenating the returned pieces reproduces the input exactly.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass

_COMMON_TERMINATORS = frozenset(".!?…。！？؟۔։;।॥။።།༎༏༐༑")
_SPACELESS_TERMINATORS = frozenset("。！？؟۔։;।॥။።།༎༏༐༑")
_CLOSERS = frozenset("\"'’”»›」』】〕〉》）)]}〗〙〛❯❱")
_CONTINUATION_PUNCTUATION = frozenset(",;:،؛)]}»”’」』】〉》）")


@dataclass(frozen=True)
class LanguageSegmentationProfile:
    """Deterministic orthographic conventions for one language/script family."""

    code: str
    sentence_terminators: frozenset[str] = _COMMON_TERMINATORS
    spaceless_terminators: frozenset[str] = _SPACELESS_TERMINATORS
    abbreviations: frozenset[str] = frozenset()
    continuation_words: frozenset[str] = frozenset()
    heading_terms: tuple[str, ...] = ()
    uses_case: bool = True
    script: str = "unknown"
    engine_version: str = "unicode-sentence-rules-v1"


_BASE_ABBREVIATIONS = frozenset(
    {
        "mr", "mrs", "ms", "dr", "prof", "st", "sr", "jr", "vs", "cf", "etc",
        "eg", "ie", "fig", "no", "vol", "pp", "p", "ch", "ed", "eds", "trans",
        "op", "cit", "ibid", "viz", "al", "ca", "approx", "dept", "gen", "col",
        "rev", "hon", "n", "nn", "v",
    }
)

_PROFILES: dict[str, LanguageSegmentationProfile] = {
    "und": LanguageSegmentationProfile(
        code="und",
        script="unknown",
        abbreviations=_BASE_ABBREVIATIONS,
        # Unknown-language Latin text still needs a conservative guard against
        # treating obvious connective fragments as headings. This union is
        # deliberately small and can only prevent a split; it cannot create one.
        continuation_words=frozenset(
            {
                "a", "an", "and", "as", "at", "but", "by", "for", "from", "in",
                "into", "is", "of", "on", "or", "that", "the", "to", "was",
                "with", "à", "au", "aux", "de", "des", "du", "en", "est", "et",
                "la", "le", "les", "mais", "ou", "par", "pour", "que", "qui",
                "sur", "un", "une", "der", "die", "das", "und", "zu",
            }
        ),
    ),
    "en": LanguageSegmentationProfile(
        code="en",
        script="Latin",
        abbreviations=_BASE_ABBREVIATIONS,
        continuation_words=frozenset(
            {
                "a", "an", "and", "as", "at", "but", "by", "for", "from", "in",
                "into", "is", "of", "on", "or", "that", "the", "to", "was",
                "were", "with",
            }
        ),
        heading_terms=(
            "chapter", "part", "session", "section", "book", "introduction",
            "preface", "foreword", "conclusion", "epilogue", "notes",
            "bibliography", "works cited",
        ),
    ),
    "fr": LanguageSegmentationProfile(
        code="fr",
        script="Latin",
        abbreviations=_BASE_ABBREVIATIONS
        | frozenset({"m", "mme", "mlle", "mm", "me", "cie", "éd", "trad", "sq", "sqq"}),
        continuation_words=frozenset(
            {
                "à", "au", "aux", "avec", "de", "des", "du", "en", "est", "et",
                "la", "le", "les", "mais", "ou", "par", "pour", "que", "qui",
                "sur", "un", "une",
            }
        ),
        heading_terms=(
            "chapitre", "partie", "séance", "section", "livre", "introduction",
            "préface", "avant-propos", "conclusion", "épilogue", "notes",
            "bibliographie",
        ),
    ),
    "de": LanguageSegmentationProfile(
        code="de",
        script="Latin",
        abbreviations=_BASE_ABBREVIATIONS | frozenset({"bzw", "d.h", "u.a", "z.b", "nr", "s"}),
        continuation_words=frozenset(
            {
                "der", "die", "das", "den", "dem", "des", "ein", "eine", "einer",
                "eines", "und", "oder", "aber", "mit", "von", "zu", "für", "ist",
                "war", "als",
            }
        ),
        heading_terms=(
            "kapitel", "teil", "sitzung", "abschnitt", "buch", "einleitung",
            "vorwort", "schluss", "nachwort", "anmerkungen", "literatur",
            "bibliographie",
        ),
    ),
    "es": LanguageSegmentationProfile(
        code="es",
        script="Latin",
        abbreviations=_BASE_ABBREVIATIONS | frozenset({"sra", "srta", "dra", "núm", "pág"}),
        continuation_words=frozenset(
            {"de", "del", "la", "las", "el", "los", "y", "o", "pero", "que", "con", "por", "para", "en"}
        ),
        heading_terms=(
            "capítulo", "parte", "sección", "libro", "introducción", "prefacio",
            "prólogo", "conclusión", "epílogo", "notas", "bibliografía",
        ),
    ),
    "it": LanguageSegmentationProfile(
        code="it",
        script="Latin",
        abbreviations=_BASE_ABBREVIATIONS | frozenset({"sig", "sig.ra", "dott", "pag"}),
        continuation_words=frozenset(
            {"di", "del", "della", "il", "lo", "la", "i", "gli", "le", "e", "o", "ma", "che", "con", "per", "in"}
        ),
        heading_terms=(
            "capitolo", "parte", "sezione", "libro", "introduzione", "prefazione",
            "conclusione", "epilogo", "note", "bibliografia",
        ),
    ),
    "pt": LanguageSegmentationProfile(
        code="pt",
        script="Latin",
        abbreviations=_BASE_ABBREVIATIONS | frozenset({"sra", "dra", "pág", "cap"}),
        continuation_words=frozenset(
            {"de", "do", "da", "dos", "das", "o", "a", "os", "as", "e", "ou", "mas", "que", "com", "por", "para", "em"}
        ),
        heading_terms=(
            "capítulo", "parte", "seção", "secção", "livro", "introdução",
            "prefácio", "conclusão", "epílogo", "notas", "bibliografia",
        ),
    ),
    "ru": LanguageSegmentationProfile(
        code="ru",
        script="Cyrillic",
        abbreviations=frozenset({"г", "гг", "др", "проф", "стр", "т", "т.е", "т.к", "см", "рис", "им"}),
        continuation_words=frozenset(
            {"и", "или", "но", "а", "что", "как", "с", "со", "в", "во", "на", "по", "к", "из", "для"}
        ),
        heading_terms=(
            "глава", "часть", "раздел", "книга", "введение", "предисловие",
            "заключение", "эпилог", "примечания", "библиография",
        ),
    ),
    "el": LanguageSegmentationProfile(
        code="el",
        script="Greek",
        continuation_words=frozenset({"και", "ή", "αλλά", "που", "με", "σε", "από", "για"}),
        heading_terms=(
            "κεφάλαιο", "μέρος", "ενότητα", "εισαγωγή", "πρόλογος", "συμπέρασμα",
            "σημειώσεις", "βιβλιογραφία",
        ),
    ),
    "ar": LanguageSegmentationProfile(
        code="ar",
        script="Arabic",
        uses_case=False,
        heading_terms=(
            "الفصل", "الباب", "القسم", "المقدمة", "مقدمة", "تمهيد", "الخاتمة",
            "خاتمة", "المراجع", "الفهرس",
        ),
    ),
    "he": LanguageSegmentationProfile(
        code="he",
        script="Hebrew",
        uses_case=False,
        heading_terms=("פרק", "חלק", "מבוא", "הקדמה", "סיכום", "הערות", "ביבליוגרפיה"),
    ),
    "hi": LanguageSegmentationProfile(
        code="hi",
        script="Devanagari",
        uses_case=False,
        heading_terms=("अध्याय", "भाग", "अनुभाग", "प्रस्तावना", "भूमिका", "निष्कर्ष", "टिप्पणियाँ", "संदर्भ"),
    ),
    "zh": LanguageSegmentationProfile(
        code="zh",
        script="Han",
        uses_case=False,
        heading_terms=("引言", "前言", "序言", "序", "结论", "結論", "注释", "註釋", "参考文献", "參考文獻"),
    ),
    "ja": LanguageSegmentationProfile(
        code="ja",
        script="Japanese",
        uses_case=False,
        heading_terms=("序", "序文", "はじめに", "結論", "おわりに", "注", "参考文献"),
    ),
    "ko": LanguageSegmentationProfile(
        code="ko",
        script="Hangul",
        uses_case=False,
        heading_terms=("서론", "머리말", "결론", "주", "참고문헌"),
    ),
    "th": LanguageSegmentationProfile(code="th", script="Thai", uses_case=False),
    "my": LanguageSegmentationProfile(code="my", script="Myanmar", uses_case=False),
    "bo": LanguageSegmentationProfile(code="bo", script="Tibetan", uses_case=False),
    "am": LanguageSegmentationProfile(code="am", script="Ethiopic", uses_case=False),
    "hy": LanguageSegmentationProfile(code="hy", script="Armenian"),
    "ka": LanguageSegmentationProfile(code="ka", script="Georgian", uses_case=False),
}

_LANGUAGE_ALIASES = {
    "english": "en",
    "anglais": "en",
    "french": "fr",
    "français": "fr",
    "francais": "fr",
    "german": "de",
    "deutsch": "de",
    "spanish": "es",
    "español": "es",
    "espanol": "es",
    "italian": "it",
    "italiano": "it",
    "portuguese": "pt",
    "português": "pt",
    "portugues": "pt",
    "russian": "ru",
    "русский": "ru",
    "greek": "el",
    "ελληνικά": "el",
    "arabic": "ar",
    "العربية": "ar",
    "hebrew": "he",
    "עברית": "he",
    "hindi": "hi",
    "हिन्दी": "hi",
    "हिंदी": "hi",
    "chinese": "zh",
    "中文": "zh",
    "mandarin": "zh",
    "japanese": "ja",
    "日本語": "ja",
    "korean": "ko",
    "한국어": "ko",
    "thai": "th",
    "ไทย": "th",
    "burmese": "my",
    "myanmar": "my",
    "tibetan": "bo",
    "amharic": "am",
    "armenian": "hy",
    "georgian": "ka",
}


def normalize_language(value: str | None) -> str:
    """Return a stable language/profile code when the input is recognizable."""
    raw = unicodedata.normalize("NFC", str(value or "")).strip().casefold()
    if not raw:
        return ""
    if raw in _LANGUAGE_ALIASES:
        return _LANGUAGE_ALIASES[raw]
    head = re.split(r"[-_\s]", raw, maxsplit=1)[0]
    iso3 = {
        "eng": "en", "fra": "fr", "fre": "fr", "deu": "de", "ger": "de",
        "spa": "es", "ita": "it", "por": "pt", "rus": "ru", "ell": "el",
        "gre": "el", "ara": "ar", "heb": "he", "hin": "hi", "zho": "zh",
        "chi": "zh", "jpn": "ja", "kor": "ko", "tha": "th", "mya": "my",
        "bur": "my", "bod": "bo", "tib": "bo", "amh": "am", "hye": "hy",
        "arm": "hy", "kat": "ka", "geo": "ka",
    }
    if head in iso3:
        return iso3[head]
    if len(head) == 2 and head.isalpha():
        return head
    return _LANGUAGE_ALIASES.get(head, "")


def _script_counts(text: str) -> dict[str, int]:
    counts = {
        "kana": 0, "han": 0, "hangul": 0, "arabic": 0, "hebrew": 0,
        "devanagari": 0, "thai": 0, "myanmar": 0, "tibetan": 0,
        "ethiopic": 0, "cyrillic": 0, "greek": 0, "armenian": 0,
        "georgian": 0, "latin": 0,
    }
    for ch in text[:12000]:
        if ch.isspace() or ch.isdigit() or unicodedata.category(ch).startswith("P"):
            continue
        cp = ord(ch)
        name = unicodedata.name(ch, "")
        if 0x3040 <= cp <= 0x30FF or 0x31F0 <= cp <= 0x31FF:
            counts["kana"] += 1
        elif 0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF:
            counts["han"] += 1
        elif 0xAC00 <= cp <= 0xD7AF or 0x1100 <= cp <= 0x11FF:
            counts["hangul"] += 1
        elif "ARABIC" in name:
            counts["arabic"] += 1
        elif "HEBREW" in name:
            counts["hebrew"] += 1
        elif "DEVANAGARI" in name:
            counts["devanagari"] += 1
        elif "THAI" in name:
            counts["thai"] += 1
        elif "MYANMAR" in name:
            counts["myanmar"] += 1
        elif "TIBETAN" in name:
            counts["tibetan"] += 1
        elif "ETHIOPIC" in name:
            counts["ethiopic"] += 1
        elif "CYRILLIC" in name:
            counts["cyrillic"] += 1
        elif "GREEK" in name:
            counts["greek"] += 1
        elif "ARMENIAN" in name:
            counts["armenian"] += 1
        elif "GEORGIAN" in name:
            counts["georgian"] += 1
        elif "LATIN" in name:
            counts["latin"] += 1
    return counts


def infer_language_from_text(text: str) -> str:
    """Infer only a coarse profile from Unicode script, never metadata truth."""
    counts = _script_counts(text)
    if counts["kana"]:
        return "ja"
    if counts["hangul"]:
        return "ko"
    if counts["han"]:
        return "zh"
    script, count = max(counts.items(), key=lambda item: item[1])
    if count < 4:
        return ""
    return {
        "arabic": "ar",
        "hebrew": "he",
        "devanagari": "hi",
        "thai": "th",
        "myanmar": "my",
        "tibetan": "bo",
        "ethiopic": "am",
        "cyrillic": "ru",
        "greek": "el",
        "armenian": "hy",
        "georgian": "ka",
    }.get(script, "")


def resolve_profile(language: str | None = None, text: str = "") -> LanguageSegmentationProfile:
    """Resolve declared language first, then a conservative script fallback.

    A declared but unsupported language is never silently treated as a different
    language merely because it shares a script. It receives script-appropriate
    punctuation/case behavior without borrowing another language's abbreviations,
    continuation words, or heading vocabulary.
    """
    code = normalize_language(language)
    if code in _PROFILES:
        return _PROFILES[code]
    inferred = infer_language_from_text(text)
    if code:
        inferred_profile = _PROFILES.get(inferred)
        if inferred_profile is None:
            return LanguageSegmentationProfile(code=code)
        return LanguageSegmentationProfile(
            code=code,
            script=inferred_profile.script,
            uses_case=inferred_profile.uses_case,
        )
    if inferred in _PROFILES:
        return _PROFILES[inferred]
    return _PROFILES["und"]


def _last_word(text: str) -> str:
    match = re.search(r"([^\W\d_]+)$", text, re.UNICODE)
    return match.group(1).casefold() if match else ""


def _looks_like_initialism(text: str) -> bool:
    return bool(re.search(r"(?:\b[^\W\d_][.]){2,}$", text, re.UNICODE))


def _is_abbreviation(before_period: str, profile: LanguageSegmentationProfile) -> bool:
    token = _last_word(before_period)
    if not token:
        return False
    if token in profile.abbreviations or token in _BASE_ABBREVIATIONS:
        return True
    if len(token) == 1 and token.isalpha() and profile.uses_case:
        return True
    return _looks_like_initialism(before_period)


def _next_nonspace(text: str, start: int) -> tuple[str, int]:
    index = start
    while index < len(text) and text[index].isspace():
        index += 1
    return (text[index] if index < len(text) else ""), index


def split_sentences(text: str, language: str | None = None) -> list[str]:
    """Losslessly split text using language/script-aware punctuation rules."""
    if not text:
        return []
    profile = resolve_profile(language, text)
    pieces: list[str] = []
    start = 0
    index = 0
    while index < len(text):
        char = text[index]
        if char not in profile.sentence_terminators:
            index += 1
            continue
        end_punctuation = index + 1
        while end_punctuation < len(text) and text[end_punctuation] in profile.sentence_terminators:
            end_punctuation += 1
        while end_punctuation < len(text) and text[end_punctuation] in _CLOSERS:
            end_punctuation += 1
        next_char, next_index = _next_nonspace(text, end_punctuation)
        if char == ".":
            before = text[start:index]
            previous_char = text[index - 1] if index > 0 else ""
            if previous_char.isdigit() and next_char.isdigit():
                index = end_punctuation
                continue
            if _is_abbreviation(before, profile):
                index = end_punctuation
                continue
            if profile.uses_case and next_char and next_char.islower():
                index = end_punctuation
                continue
        has_space = next_index > end_punctuation
        if (
            end_punctuation < len(text)
            and not has_space
            and char not in profile.spaceless_terminators
        ):
            index = end_punctuation
            continue
        piece_end = next_index if has_space else end_punctuation
        if piece_end > start:
            pieces.append(text[start:piece_end])
            start = piece_end
        index = max(end_punctuation, piece_end)
    if start < len(text):
        pieces.append(text[start:])
    return [piece for piece in pieces if piece.strip()]


def ends_sentence_text(text: str, language: str | None = None) -> bool:
    """Whether running text ends with recognized terminal punctuation."""
    profile = resolve_profile(language, text)
    stripped = str(text or "").rstrip()
    while stripped and stripped[-1] in _CLOSERS:
        stripped = stripped[:-1].rstrip()
    return bool(stripped and stripped[-1] in profile.sentence_terminators)


def _first_word(text: str) -> str:
    match = re.search(r"[^\W\d_]+", text, re.UNICODE)
    return match.group(0).casefold() if match else ""


def starts_mid_sentence_text(text: str, language: str | None = None) -> bool:
    """Conservative continuation signal that does not mistake caseless scripts for lowercase."""
    profile = resolve_profile(language, text)
    stripped = str(text or "").lstrip()
    if not stripped:
        return False
    if stripped[0] in _CONTINUATION_PUNCTUATION:
        return True
    if profile.uses_case and stripped[0].isalpha() and stripped[0].islower():
        return True
    first = _first_word(stripped)
    return bool(first and first in profile.continuation_words)


def _normalized_heading(text: str) -> str:
    return unicodedata.normalize(
        "NFC", re.sub(r"\s+", " ", str(text or "")).strip()
    ).casefold()


def looks_like_strong_heading(text: str, language: str | None = None) -> bool:
    """Language-aware lexical/numbered heading signal for deterministic routing."""
    normalized = _normalized_heading(text)
    if not normalized:
        return False
    profile = resolve_profile(language, normalized)
    if any(
        normalized == term or normalized.startswith(term + " ")
        for term in profile.heading_terms
    ):
        return True
    if re.match(r"^(?:§|[ivxlcdm]+|\d+)\s*[.:：—-]\s+", normalized, re.I):
        return True
    if profile.code in {"zh", "ja"} and re.match(
        r"^第\s*[一二三四五六七八九十百千万零〇\d]+\s*[章节節部卷篇]",
        normalized,
    ):
        return True
    if profile.code == "ko" and re.match(r"^제\s*\d+\s*[장절부]", normalized):
        return True
    return False


def looks_like_heading_line(text: str, language: str | None = None) -> bool:
    """Safe short-line heading heuristic for running-text boundary repair."""
    stripped = str(text or "").strip()
    if not stripped or len(stripped) > 120:
        return False
    if ends_sentence_text(stripped, language) or any(char in stripped for char in ";:：؛"):
        return False
    if looks_like_strong_heading(stripped, language):
        return True
    profile = resolve_profile(language, stripped)
    if not profile.uses_case:
        return False
    first = next((char for char in stripped if char.isalpha() or char.isdigit()), "")
    if not first or not (first.isupper() or first.isdigit()):
        return False
    return _last_word(stripped) not in profile.continuation_words


def looks_like_speaker_start(text: str, language: str | None = None) -> bool:
    """Detect a short speaker label followed by a colon without assuming ASCII names."""
    stripped = str(text or "").lstrip()
    positions = [
        position
        for marker in (":", "：")
        if (position := stripped.find(marker)) > 0
    ]
    if not positions:
        return False
    colon = min(positions)
    label = stripped[:colon].strip()
    rest = stripped[colon + 1 :].strip()
    if not rest or not label or len(label) > 60 or "\n" in label:
        return False
    letters = [char for char in label if char.isalpha()]
    if not letters:
        return False
    words = re.findall(r"[^\W\d_]+", label, re.UNICODE)
    if len(words) > 6:
        return False
    profile = resolve_profile(language, label)
    if not profile.uses_case:
        return len(label) <= 30
    return all(char.isupper() for char in letters) or all(
        word[:1].isupper() for word in words if word
    )


def starts_quote(text: str) -> bool:
    return bool(
        str(text or "").lstrip().startswith(
            ("“", "\"", "‘", "'", "«", "‹", "「", "『", "《", "〈")
        )
    )


def ends_quote(text: str) -> bool:
    return bool(
        str(text or "").rstrip().endswith(
            ("”", "\"", "’", "'", "»", "›", "」", "』", "》", "〉")
        )
    )


def profile_metadata(
    language: str | None = None, text: str = ""
) -> dict[str, str | bool]:
    """Compact provenance for the deterministic language-boundary engine."""
    explicit = normalize_language(language)
    profile = resolve_profile(language, text)
    return {
        "language": explicit or profile.code,
        "profile": profile.code,
        "script": profile.script,
        "engine": profile.engine_version,
        "language_source": (
            "declared"
            if explicit
            else ("script_inference" if profile.code != "und" else "undetermined")
        ),
        "uses_case": profile.uses_case,
    }


def sentence_terminators(
    language: str | None = None, text: str = ""
) -> Iterable[str]:
    """Expose resolved terminal punctuation for callers that need it."""
    return resolve_profile(language, text).sentence_terminators
