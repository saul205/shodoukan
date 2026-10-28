"""Port for splitting a Japanese sentence into morphemes.

Sentences propose their words and link them to the library from this: each
morpheme's dictionary form finds the library word even when the sentence
inflects it (引かれた → 引く) or spells it in kana, and its part of speech and
conjugation give the form of a gap (`domain/services/inflection_service.py`).
Only used when sentences are added or edited; the morphemes aren't stored.
"""

from typing import NamedTuple, Protocol


class Morpheme(NamedTuple):
    surface: str
    # Dictionary form: 引く for 引か, た for た.
    lemma: str
    # Reading of the surface, in katakana as the analyzer gives it (ヒカ).
    reading: str
    # Part of speech, most general first: ("動詞", "一般"), ("助詞", "格助詞").
    pos: tuple[str, ...]
    # Conjugation type and form (活用型, 活用形), `None` when it doesn't
    # inflect: "五段-カ行", "未然形-一般".
    conjugation_type: str | None
    conjugation_form: str | None
    # Offsets of the surface in the sentence, in characters.
    start: int
    end: int


class MorphologyGateway(Protocol):
    def morphemes(self, text: str) -> list[Morpheme]:
        """The morphemes of `text`, in order, covering all of it."""
        ...
