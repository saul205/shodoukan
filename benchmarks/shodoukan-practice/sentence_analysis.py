"""Benchmark the morphological analyzer on JMDict example sentences.

Takes a random sample of the dictionary's example sentences of JLPT words and
runs them through `SudachiMorphologyGateway`, for each Sudachi dictionary and
split mode asked, to see how well it does what sentences need:

- aligned: the word's form in the sentence (`examples.text`, the gap) starts
  and ends on morpheme boundaries, so it can be picked as whole morphemes; a gap
  that isn't (心地 inside 使い心地) is analyzed on its own for the rest;
- linked: one of the gap's dictionary forms (`gap_dictionary_forms`) is a
  spelling or reading of its entry, so the word would be found in the library;
- reading: for gaps not inflected, the analyzer's reading is a reading of the
  entry;
- inflections: how many distinct forms the inflected gaps fall into.

It isn't a test: it prints figures and a few misses, to choose the dictionary
and mode and to check them after an upgrade.

    python benchmarks/shodoukan-practice/sentence_analysis.py
    python benchmarks/shodoukan-practice/sentence_analysis.py --sentences 500 \\
        --dictionaries small core --modes B C

Needs the dictionary database (`shodoukan-setup`) and the Sudachi dictionaries
asked for (`pip install sudachidict_core sudachidict_small`).
"""

import argparse
import random
import sqlite3
import time
from collections import Counter
from dataclasses import dataclass
from typing import Literal, cast

from shodoukan.db.connection import resolve_path
from shodoukan.utils.kana import katakana_to_hiragana
from shodoukan_practice.domain.gateways import Morpheme
from shodoukan_practice.domain.services import (
    gap_dictionary_forms,
    gap_head,
    gap_inflection,
)
from shodoukan_practice.infrastructure.morphology import (
    SudachiDictionary,
    SudachiMorphologyGateway,
)

SplitModeName = Literal["A", "B", "C"]


@dataclass(frozen=True)
class Sample:
    sentence: str
    gap: str
    forms: frozenset[str]  # the entry's spellings and readings, readings in hiragana
    readings: frozenset[str]


def load_samples(count: int, seed: int) -> list[Sample]:
    connection = sqlite3.connect(resolve_path(None))
    rows = connection.execute(
        """
        SELECT s.entry_id, x.text, es.text
        FROM examples x
        JOIN senses s ON s.id = x.sense_id
        JOIN entries e ON e.id = s.entry_id
        JOIN example_sentences es ON es.example_id = x.id AND es.lang = 'jpn'
        WHERE e.jlpt IS NOT NULL
        """
    ).fetchall()
    chosen = random.Random(seed).sample(rows, min(count, len(rows)))
    samples = []
    for entry_id, gap, sentence in chosen:
        spellings = {
            k
            for (k,) in connection.execute(
                "SELECT kanji FROM kanji_readings WHERE entry_id = ?", (entry_id,)
            )
        }
        readings = {
            katakana_to_hiragana(r)
            for (r,) in connection.execute(
                "SELECT text FROM readings WHERE entry_id = ?", (entry_id,)
            )
        }
        samples.append(
            Sample(sentence, gap, frozenset(spellings | readings), frozenset(readings))
        )
    return samples


def gap_morphemes(morphemes: list[Morpheme], start: int, end: int) -> list[Morpheme]:
    """The morphemes exactly covering `start` to `end`, or [] if it isn't aligned."""
    inside = [m for m in morphemes if m.start < end and m.end > start]
    if inside and inside[0].start == start and inside[-1].end == end:
        return inside
    return []


def run(gateway: SudachiMorphologyGateway, samples: list[Sample]) -> dict[str, object]:
    unaligned = linked = reading_checked = reading_right = 0
    inflections: Counter[str] = Counter()
    misses: dict[str, list[str]] = {"aligned": [], "linked": [], "reading": []}
    started = time.perf_counter()
    for sample in samples:
        morphemes = gateway.morphemes(sample.sentence)
        start = sample.sentence.index(sample.gap)
        span = gap_morphemes(morphemes, start, start + len(sample.gap))
        if not span:
            # Part of a longer unit (心地 in 使い心地): analyze the gap alone.
            alone = gateway.morphemes(sample.gap)
            span = [m._replace(start=m.start + start, end=m.end + start) for m in alone]
            unaligned += 1
            around = " | ".join(
                m.surface
                for m in morphemes
                if m.end > start - 2 and m.start < start + len(sample.gap) + 2
            )
            misses["aligned"].append(f"{sample.gap}: {around}")
        forms = gap_dictionary_forms(span)
        if any(
            f in sample.forms or katakana_to_hiragana(f) in sample.forms for f in forms
        ):
            linked += 1
        else:
            head = gap_head(span)
            misses["linked"].append(
                f"{sample.gap}: {' / '.join(forms)} ({head.pos if head else '-'})"
            )
        inflection = gap_inflection(span)
        if inflection and (inflection.endings or sample.gap not in sample.forms):
            inflections[f"{'+'.join(inflection.endings)}·{inflection.form}"] += 1
        elif sample.gap in sample.forms:
            reading_checked += 1
            reading = katakana_to_hiragana("".join(m.reading for m in span))
            if reading in sample.readings:
                reading_right += 1
            else:
                misses["reading"].append(f"{sample.gap}: {reading}")
    elapsed = time.perf_counter() - started
    return {
        "aligned": len(samples) - unaligned,
        "linked": linked,
        "reading_checked": reading_checked,
        "reading_right": reading_right,
        "inflections": inflections,
        "misses": misses,
        "ms_per_sentence": elapsed * 1000 / len(samples),
    }


def percent(part: int, whole: int) -> str:
    return f"{part}/{whole} ({part * 100 / whole:.0f} %)" if whole else "0/0"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sentences", type=int, default=200)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--dictionaries", nargs="+", default=["small", "core"])
    parser.add_argument("--modes", nargs="+", default=["B", "C"])
    parser.add_argument("--misses", type=int, default=5, help="misses shown per kind")
    args = parser.parse_args()

    samples = load_samples(args.sentences, args.seed)
    print(f"{len(samples)} sentences, seed {args.seed}\n")
    for dictionary in args.dictionaries:
        for mode in args.modes:
            started = time.perf_counter()
            gateway = SudachiMorphologyGateway(
                cast(SudachiDictionary, dictionary), cast(SplitModeName, mode)
            )
            load_ms = (time.perf_counter() - started) * 1000
            result = run(gateway, samples)
            total = len(samples)
            aligned = cast(int, result["aligned"])
            inflections = cast(Counter[str], result["inflections"])
            print(f"== {dictionary}, mode {mode}")
            print(f"  load        {load_ms:.0f} ms")
            print(f"  per sentence {result['ms_per_sentence']:.2f} ms")
            print(f"  aligned     {percent(aligned, total)}")
            print(f"  linked      {percent(cast(int, result['linked']), total)}")
            print(
                "  reading     "
                + percent(
                    cast(int, result["reading_right"]),
                    cast(int, result["reading_checked"]),
                )
            )
            print(
                f"  inflected   {sum(inflections.values())} gaps in "
                f"{len(inflections)} forms; most common: "
                + ", ".join(f"{k} ({v})" for k, v in inflections.most_common(6))
            )
            misses = cast(dict[str, list[str]], result["misses"])
            for kind, items in misses.items():
                for item in items[: args.misses]:
                    print(f"  miss {kind:8} {item}")
            print()


if __name__ == "__main__":
    main()
