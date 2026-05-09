import argparse
import sys

from shodoukan.db.connection import resolve_path
from shodoukan.db.download import download


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
