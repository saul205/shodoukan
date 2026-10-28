from typing import Literal

from sudachipy.sudachipy import Dictionary, SplitMode

from ...domain.gateways import Morpheme, MorphologyGateway

SudachiDictionary = Literal["small", "core", "full"]

_SPLIT_MODES = {"A": SplitMode.A, "B": SplitMode.B, "C": SplitMode.C}
_NONE = "*"


class SudachiMorphologyGateway(MorphologyGateway):
    """Morphemes from SudachiPy.

    Long units (mode C) by default: they match dictionary words best (日本語,
    not 日本 + 語). The dictionary is loaded once; a tokenizer is created per
    call, since tokenizers aren't safe to share between threads.
    """

    def __init__(
        self,
        dictionary: SudachiDictionary = "core",
        split_mode: Literal["A", "B", "C"] = "C",
    ) -> None:
        self._dictionary = Dictionary(dict=dictionary)
        self._split_mode = _SPLIT_MODES[split_mode]

    def morphemes(self, text: str) -> list[Morpheme]:
        tokenizer = self._dictionary.tokenizer(mode=self._split_mode)
        result = []
        for m in tokenizer.tokenize(text):
            pos = m.part_of_speech()
            result.append(
                Morpheme(
                    surface=m.surface(),
                    lemma=m.dictionary_form(),
                    reading=m.reading_form(),
                    pos=tuple(p for p in pos[:4] if p != _NONE),
                    conjugation_type=_value(pos[4]),
                    conjugation_form=_value(pos[5]),
                    start=m.begin(),
                    end=m.end(),
                )
            )
        return result


def _value(field: str) -> str | None:
    return None if field == _NONE else field
