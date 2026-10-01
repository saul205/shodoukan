"""Ports for external, read-only sources the domain depends on."""

from .dictionary_gateway import (
    DictionaryCrossReference,
    DictionaryEntry,
    DictionaryEntryPage,
    DictionaryExample,
    DictionaryExampleSentence,
    DictionaryGateway,
    DictionaryGloss,
    DictionaryKanji,
    DictionaryKanjiMeaning,
    DictionaryKanjiReading,
    DictionaryReading,
    DictionarySearchResult,
    DictionarySense,
)

__all__ = [
    "DictionaryCrossReference",
    "DictionaryEntry",
    "DictionaryEntryPage",
    "DictionaryExample",
    "DictionaryExampleSentence",
    "DictionaryGateway",
    "DictionaryGloss",
    "DictionaryKanji",
    "DictionaryKanjiMeaning",
    "DictionaryKanjiReading",
    "DictionaryReading",
    "DictionarySearchResult",
    "DictionarySense",
]
