from fastapi import APIRouter, Depends, HTTPException, Query

from shodoukan import Dictionary, Kanji, Page
from shodoukan_api.deps import dictionary_dep

router = APIRouter()


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
