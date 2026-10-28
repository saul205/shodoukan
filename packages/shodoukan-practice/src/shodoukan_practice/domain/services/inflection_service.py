"""The form of a word in a sentence, from its morphemes.

A gap covers one or more morphemes: the word itself (its head) and whatever
inflects it (引か + れ + た). Two gaps are in the same form when they have the
same inflection: the lemmas of the morphemes after the head, in order, and the
form of the last one. 引かれた and 飲まれた are both (れる, た · 終止形);
食べた and 飲んだ both (た · 終止形). Fill-the-gap options are other words in
the same form, so an ending never gives the answer away.

Variants that only depend on the verb's class are merged: past だ is た
(飲んだ), te-form で is て (読んで), られる is れる and させる is せる.

See docs/practice/proposals/sentences.md.
"""

from collections.abc import Sequence

from ..entities import Inflection
from ..gateways import Morpheme

# Parts of speech a gap can be made of: words worth studying, not particles,
# auxiliaries, prefixes or symbols.
CONTENT_POS = frozenset(
    {"名詞", "代名詞", "動詞", "形容詞", "形状詞", "副詞", "連体詞", "感動詞"}
)

_PAST = "助動詞-タ"
_LEMMA_VARIANTS = {"られる": "れる", "させる": "せる"}


def is_content_word(morpheme: Morpheme) -> bool:
    """Whether the morpheme can be the head of a gap."""
    return bool(morpheme.pos) and morpheme.pos[0] in CONTENT_POS


def gap_head(morphemes: Sequence[Morpheme]) -> Morpheme | None:
    """The word a gap is about: its first content morpheme (after お, ご...)."""
    return next((m for m in morphemes if is_content_word(m)), None)


def gap_inflection(morphemes: Sequence[Morpheme]) -> Inflection | None:
    """The inflection of a gap made of `morphemes`; `None` without a head."""
    head = gap_head(morphemes)
    if head is None:
        return None
    tail = list(morphemes[morphemes.index(head) + 1 :])
    last = tail[-1] if tail else head
    return Inflection(
        endings=tuple(_ending(m) for m in tail),
        form=_main_form(last.conjugation_form),
    )


def gap_dictionary_forms(morphemes: Sequence[Morpheme]) -> list[str]:
    """How the gap's word may be written in the dictionary, best guess first.

    The head's lemma (引かれた → 引く), then the gap as written (共に, a word
    of several morphemes), then the gap with its last morpheme in dictionary
    form (いけない from いけ + ない, a whole expression).
    """
    if not morphemes:
        return []
    head = gap_head(morphemes)
    surface = "".join(m.surface for m in morphemes)
    expression = "".join(m.surface for m in morphemes[:-1]) + morphemes[-1].lemma
    forms = [head.lemma] if head else []
    forms += [surface, expression]
    return list(dict.fromkeys(forms))


def _ending(morpheme: Morpheme) -> str:
    if morpheme.conjugation_type == _PAST:
        return "た"
    if morpheme.pos[:2] == ("助詞", "接続助詞") and morpheme.lemma == "で":
        return "て"
    return _LEMMA_VARIANTS.get(morpheme.lemma, morpheme.lemma)


def _main_form(conjugation_form: str | None) -> str | None:
    if conjugation_form is None:
        return None
    return conjugation_form.split("-", 1)[0]
