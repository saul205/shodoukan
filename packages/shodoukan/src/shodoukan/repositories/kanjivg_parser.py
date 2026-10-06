"""Reads the strokes out of a KanjiVG drawing (https://kanjivg.tagaini.net/)."""

import re
from xml.etree import ElementTree

from shodoukan.models.kanji import KanjiStroke

_SVG = "{http://www.w3.org/2000/svg}"
# Stroke paths are "kvg:<codepoint>-s<n>"; stroke number labels are placed with
# "matrix(1 0 0 1 <x> <y>)".
_STROKE_ID = re.compile(r"-s(\d+)$")
_LABEL_TRANSFORM = re.compile(r"matrix\(1 0 0 1 ([\d.]+) ([\d.]+)\)")


def parse_kanjivg(svg: str) -> list[KanjiStroke]:
    """The strokes of a KanjiVG SVG, in writing order.

    Strokes are ordered by the number in their id, not by where they sit in the
    document. Only `id`, `d` and `transform` are read, since KanjiVG's own `kvg:`
    attributes declare their namespace inconsistently.
    """
    root = ElementTree.fromstring(svg)
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
    return [KanjiStroke(path=paths[n], label=labels.get(n)) for n in sorted(paths)]
