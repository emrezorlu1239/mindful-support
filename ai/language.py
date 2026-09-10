"""Offline language guard. Statistical detection is not a semantic safety review."""
from functools import lru_cache

@lru_cache(maxsize=1)
def detector():
    from lingua import Language, LanguageDetectorBuilder
    return LanguageDetectorBuilder.from_languages(Language.ENGLISH, Language.TURKISH).with_minimum_relative_distance(0.15).build()

def matches_language(text, language):
    from lingua import Language
    expected = {"en": Language.ENGLISH, "tr": Language.TURKISH}[language]
    return detector().detect_language_of(text) == expected
