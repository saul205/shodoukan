from fastapi import APIRouter, Depends, HTTPException, Query, Response

from shodoukan import Dictionary, Kanji, KanjiStrokes, Page
from shodoukan_api.deps import dictionary_dep

router = APIRouter()

# Stroke order only changes with a new database release.
_STROKES_CACHE_CONTROL = "public, max-age=86400"


@router.get("/search", response_model=Page[Kanji])
def search_kanji(
    q: str | None = Query(default=None),
    lang: str = Query(default="en"),
    grade: int | None = Query(default=None, ge=1, le=10),
    jlpt: int | None = Query(default=None, ge=1, le=5),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    d: Dictionary = Depends(dictionary_dep),
) -> Page[Kanji]:
    if q is None and grade is None and jlpt is None:
        raise HTTPException(
            status_code=422,
            detail="At least one of 'q', 'grade', or 'jlpt' is required",
        )
    return d.search_kanji(
        query=q, grade=grade, jlpt=jlpt, lang=lang, limit=limit, offset=offset
    )


@router.get("/{literal}", response_model=Kanji)
def get_kanji(
    literal: str,
    d: Dictionary = Depends(dictionary_dep),
) -> Kanji:
    kanji = d.get_kanji(literal)
    if kanji is None:
        raise HTTPException(status_code=404, detail="Kanji not found")
    return kanji


@router.get("/{literal}/strokes", response_model=KanjiStrokes)
def get_kanji_strokes(
    literal: str,
    response: Response,
    d: Dictionary = Depends(dictionary_dep),
) -> KanjiStrokes:
    """Stroke order (KanjiVG), for any character with a drawing."""
    strokes = d.get_kanji_strokes(literal)
    if strokes is None:
        raise HTTPException(status_code=404, detail="Stroke order not available")
    response.headers["Cache-Control"] = _STROKES_CACHE_CONTROL
    return strokes
