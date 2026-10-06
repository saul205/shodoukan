"""Mapping functions from SQLAlchemy ORM objects to Pydantic domain models."""

import json
import re
from xml.etree import ElementTree

from shodoukan.db.orm import EntryORM, KanjiORM, KanjiSvgORM
from shodoukan.models.entry import (
    CrossReference,
    Entry,
    Example,
    ExampleSentence,
    Gloss,
    KanjiReading,
    Reading,
    Sense,
)
from shodoukan.models.kanji import Kanji, KanjiMeaning, KanjiStroke, KanjiStrokes


def _json(value: str) -> list[str]:
    return json.loads(value) if value else []


def entry_to_domain(e: EntryORM) -> Entry:
    return Entry(
        id=e.id,
        jlpt=e.jlpt,
        is_common=bool(e.has_common),
        kanji_readings=[
            KanjiReading(
                id=kr.id,
                kanji=kr.kanji,
                priority=_json(kr.priority),
                info=_json(kr.info),
            )
            for kr in e.kanji_readings
        ],
        readings=[
            Reading(
                id=r.id,
                text=r.text,
                no_kanji=bool(r.no_kanji),
                priority=_json(r.priority),
                info=_json(r.info),
                restricted_to=[kr.kanji for kr in r.restrictions],
            )
            for r in e.readings
        ],
        senses=[
            Sense(
                id=s.id,
                pos=_json(s.pos),
                misc=_json(s.misc),
                dialects=_json(s.dialects),
                info=_json(s.info),
                glosses=[
                    Gloss(id=g.id, text=g.text, type=g.type, lang=g.lang)
                    for g in s.glosses
                ],
                cross_references=[
                    CrossReference(
                        reference=x.reference,
                        reading=x.reading,
                        sense_idx=x.sense_idx,
                    )
                    for x in s.cross_references
                ],
                examples=[
                    Example(
                        id=ex.id,
                        source_name=ex.source_name,
                        source_id=ex.source_id,
                        text=ex.text,
                        sentences=[
                            ExampleSentence(lang=sent.lang, text=sent.text)
                            for sent in ex.sentences
                        ],
                    )
                    for ex in s.examples
                ],
            )
            for s in e.senses
        ],
    )


def kanji_to_domain(k: KanjiORM) -> Kanji:
    return Kanji(
        literal=k.literal,
        grade=k.grade,
        stroke_count=k.stroke_count,
        freq=k.freq,
        jlpt=k.jlpt,
        on_readings=_json(k.on_readings),
        kun_readings=_json(k.kun_readings),
        nanori=_json(k.nanori),
        meanings=[KanjiMeaning(text=m.text, lang=m.lang) for m in k.meanings],
    )


_SVG = "{http://www.w3.org/2000/svg}"
# Stroke paths are "kvg:<codepoint>-s<n>"; stroke number labels are placed with
# "matrix(1 0 0 1 <x> <y>)".
_STROKE_ID = re.compile(r"-s(\d+)$")
_LABEL_TRANSFORM = re.compile(r"matrix\(1 0 0 1 ([\d.]+) ([\d.]+)\)")


def kanji_strokes_to_domain(literal: str, k: KanjiSvgORM) -> KanjiStrokes:
    """The strokes of a KanjiVG drawing, in writing order.

    `literal` is the character that was asked for, which may differ from the
    drawing's own (a compatibility ideograph is drawn with its canonical form).
    Strokes are ordered by the number in their id, not by where they sit in the
    document; only `id`, `d` and `transform` are read, since KanjiVG's own
    `kvg:` attributes declare their namespace inconsistently.
    """
    root = ElementTree.fromstring(k.svg)
    paths: dict[int, str] = {}
    for path in root.iter(f"{_SVG}path"):
        match = _STROKE_ID.search(path.get("id", ""))
        if match and (d := path.get("d")):
            paths[int(match.group(1))] = d
    labels: dict[int, tuple[float, float]] = {}
    for label in root.iter(f"{_SVG}text"):
        match = _LABEL_TRANSFORM.fullmatch(label.get("transform", ""))
        number = (label.text or "").strip()
        if match and number.isdigit():
            labels[int(number)] = (float(match.group(1)), float(match.group(2)))
    return KanjiStrokes(
        literal=literal,
        strokes=[
            KanjiStroke(path=paths[n], label=labels.get(n)) for n in sorted(paths)
        ],
    )
