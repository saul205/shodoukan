import sys
from pathlib import Path

import httpx

_RELEASES_URL = "https://api.github.com/repos/saul205/shodoukan-db/releases/latest"
_ASSET_NAME = "shodoukan.sqlite"


def download(dest: Path, force: bool = False) -> None:
    if dest.exists() and not force:
        return

    dest.parent.mkdir(parents=True, exist_ok=True)

    print("Fetching latest release info...", file=sys.stderr)
    response = httpx.get(_RELEASES_URL, follow_redirects=True)
    response.raise_for_status()
    release = response.json()

    asset_url = next(
        (
            a["browser_download_url"]
            for a in release["assets"]
            if a["name"] == _ASSET_NAME
        ),
        None,
    )
    if asset_url is None:
        raise FileNotFoundError(
            f"Asset '{_ASSET_NAME}' not found in latest release of shodoukan-db"
        )

    tmp = dest.parent / f"{_ASSET_NAME}.tmp"
    print(f"Downloading {_ASSET_NAME}...", file=sys.stderr)
    with httpx.stream("GET", asset_url, follow_redirects=True) as r:
        r.raise_for_status()
        with tmp.open("wb") as f:
            for chunk in r.iter_bytes(chunk_size=8192):
                f.write(chunk)

    tmp.rename(dest)
    print(f"Database saved to {dest}", file=sys.stderr)
