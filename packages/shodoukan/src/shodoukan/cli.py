import argparse
import sys

from shodoukan.db.connection import resolve_path
from shodoukan.db.download import download

# ── Formatting helpers ────────────────────────────────────────────────────────

def _fmt_entry(entry) -> str:
    kanji = ", ".join(kr.kanji for kr in entry.kanji_readings)
    readings = ", ".join(r.text for r in entry.readings)
    header = f"[{entry.id}]"
    if kanji:
        header += f" {kanji} ({readings})"
    else:
        header += f" {readings}"

    lines = [header]
    for sense in entry.senses:
        pos = ", ".join(sense.pos) if sense.pos else ""
        glosses = "; ".join(g.text for g in sense.glosses if g.lang == "eng")
        tag = f"  [{pos}]" if pos else " "
        lines.append(f"{tag} {glosses}")
    return "\n".join(lines)


def _fmt_kanji(k) -> str:
    grade = str(k.grade) if k.grade is not None else "—"
    jlpt = str(k.jlpt) if k.jlpt is not None else "—"
    freq = str(k.freq) if k.freq is not None else "—"
    on = ", ".join(k.on_readings) if k.on_readings else "—"
    kun = ", ".join(k.kun_readings) if k.kun_readings else "—"
    meanings = ", ".join(
        m.text for m in k.meanings if m.lang == "en"
    )
    return (
        f"{k.literal}\n"
        f"  Grade: {grade}  JLPT: {jlpt}  Strokes: {k.stroke_count}  Freq: {freq}\n"
        f"  On:  {on}\n"
        f"  Kun: {kun}\n"
        f"  Meanings: {meanings}"
    )


def _fmt_page_header(label: str, page) -> str:
    return f"=== {label} ({len(page.items)} of {page.total}) ==="


# ── Sub-command handlers ──────────────────────────────────────────────────────

def _cmd_search(args, d) -> None:
    result = d.search(args.query, limit=args.limit, offset=args.offset)

    print(_fmt_page_header("Entries", result.entries))
    for entry in result.entries.items:
        print(_fmt_entry(entry))
        print()

    if result.kanji:
        print("=== Kanji ===")
        for k in result.kanji:
            print(_fmt_kanji(k))
            print()


def _cmd_entry(args, d) -> None:
    entry = d.get_entry(args.id)
    if entry is None:
        print(f"Entry {args.id} not found.", file=sys.stderr)
        sys.exit(1)
    print(_fmt_entry(entry))


def _cmd_entry_search(args, d) -> None:
    page = d.search_entries(args.query, limit=args.limit, offset=args.offset)
    print(_fmt_page_header("Entries", page))
    for entry in page.items:
        print(_fmt_entry(entry))
        print()


def _cmd_entry_kanji(args, d) -> None:
    links = d.get_kanji_for_entry(args.id)
    if not links:
        print(f"No kanji found for entry {args.id}.", file=sys.stderr)
        return
    for lk in links:
        print(f"  {lk.literal}")


def _cmd_entries_for_kanji(args, d) -> None:
    page = d.get_entries_for_kanji(args.literal, limit=args.limit, offset=args.offset)
    print(_fmt_page_header("Entries", page))
    for entry in page.items:
        print(_fmt_entry(entry))
        print()


def _cmd_kanji(args, d) -> None:
    k = d.get_kanji(args.literal)
    if k is None:
        print(f"Kanji '{args.literal}' not found.", file=sys.stderr)
        sys.exit(1)
    print(_fmt_kanji(k))


def _cmd_kanji_search(args, d) -> None:
    page = d.search_kanji(
        query=args.query or None,
        grade=args.grade,
        jlpt=args.jlpt,
        limit=args.limit,
        offset=args.offset,
    )
    print(_fmt_page_header("Kanji", page))
    for k in page.items:
        print(_fmt_kanji(k))
        print()


# ── Entry points ──────────────────────────────────────────────────────────────

def setup(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="shodoukan-setup",
        description="Download the shodoukan database to the local data directory.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download even if the database already exists.",
    )
    parser.add_argument(
        "--path",
        default=None,
        metavar="PATH",
        help="Destination path (default: ~/.local/share/shodoukan/shodoukan.sqlite).",
    )
    args = parser.parse_args(argv)

    dest = resolve_path(args.path)
    print(f"Destination: {dest}", file=sys.stderr)
    download(dest, force=args.force)
    print("Done.", file=sys.stderr)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="shodoukan",
        description="Japanese-English dictionary lookup.",
    )
    parser.add_argument(
        "--db",
        default=None,
        metavar="PATH",
        help="Path to the SQLite database (overrides SHODOUKAN_DB_PATH env var).",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # search
    p_search = sub.add_parser("search", help="Generic search: entries + kanji.")
    p_search.add_argument("query")
    p_search.add_argument("--limit", type=int, default=10, metavar="N")
    p_search.add_argument("--offset", type=int, default=0, metavar="N")

    # entry
    p_entry = sub.add_parser("entry", help="Look up a single entry by ID.")
    p_entry.add_argument("id", type=int)

    # entry-search
    p_es = sub.add_parser("entry-search", help="Search entries by reading or English.")
    p_es.add_argument("query")
    p_es.add_argument("--limit", type=int, default=10, metavar="N")
    p_es.add_argument("--offset", type=int, default=0, metavar="N")

    # entry-kanji
    p_ek = sub.add_parser("entry-kanji", help="List kanji contained in an entry.")
    p_ek.add_argument("id", type=int)

    # entries-for-kanji
    p_efk = sub.add_parser(
        "entries-for-kanji", help="List entries that contain a kanji."
    )
    p_efk.add_argument("literal")
    p_efk.add_argument("--limit", type=int, default=10, metavar="N")
    p_efk.add_argument("--offset", type=int, default=0, metavar="N")

    # kanji
    p_kanji = sub.add_parser("kanji", help="Look up a single kanji by character.")
    p_kanji.add_argument("literal")

    # kanji-search
    p_ks = sub.add_parser(
        "kanji-search", help="Search kanji by meaning, reading, or filters."
    )
    p_ks.add_argument("query", nargs="?", default=None)
    p_ks.add_argument("--grade", type=int, default=None, metavar="N")
    p_ks.add_argument("--jlpt", type=int, default=None, metavar="N")
    p_ks.add_argument("--limit", type=int, default=10, metavar="N")
    p_ks.add_argument("--offset", type=int, default=0, metavar="N")

    args = parser.parse_args(argv)

    from shodoukan.dictionary import Dictionary

    with Dictionary(db_path=args.db) as d:
        dispatch = {
            "search": _cmd_search,
            "entry": _cmd_entry,
            "entry-search": _cmd_entry_search,
            "entry-kanji": _cmd_entry_kanji,
            "entries-for-kanji": _cmd_entries_for_kanji,
            "kanji": _cmd_kanji,
            "kanji-search": _cmd_kanji_search,
        }
        dispatch[args.command](args, d)
