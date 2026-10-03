from fastapi import APIRouter, Depends, HTTPException, Query

from shodoukan import Dictionary, Entry, EntryKanjiLink, Page
from shodoukan_api.deps import dictionary_dep

router = APIRouter()


@router.get("/search", response_model=Page[Entry])
def search_entries(
    q: str = Query(min_length=1),
    lang: str = Query(default="en"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    d: Dictionary = Depends(dictionary_dep),
) -> Page[Entry]:
    return d.search_entries(q, lang=lang, limit=limit, offset=offset)


@router.get("/by-kanji/{literal}", response_model=Page[Entry])
def entries_for_kanji(
    literal: str,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    d: Dictionary = Depends(dictionary_dep),
) -> Page[Entry]:
    return d.get_entries_for_kanji(literal, limit=limit, offset=offset)


@router.get("/{entry_id}/kanji", response_model=list[EntryKanjiLink])
def get_entry_kanji(
    entry_id: int,
    d: Dictionary = Depends(dictionary_dep),
) -> list[EntryKanjiLink]:
    return d.get_kanji_for_entry(entry_id)


@router.get("/{entry_id}", response_model=Entry)
def get_entry(
    entry_id: int,
    d: Dictionary = Depends(dictionary_dep),
) -> Entry:
    entry = d.get_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Entry not found")
    return entry
