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
    DictionaryKanjiStroke,
    DictionaryKanjiStrokes,
    DictionaryReading,
    DictionarySearchResult,
    DictionarySense,
)
from .kana_gateway import KanaForms, KanaGateway

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
    "DictionaryKanjiStroke",
    "DictionaryKanjiStrokes",
    "DictionaryReading",
    "DictionarySearchResult",
    "DictionarySense",
    "KanaForms",
    "KanaGateway",
]
