from fastapi import APIRouter, Depends, Query

from shodoukan import Dictionary, SearchResult
from shodoukan_api.deps import dictionary_dep

router = APIRouter()


@router.get("", response_model=SearchResult)
def search(
    q: str = Query(min_length=1),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    d: Dictionary = Depends(dictionary_dep),
) -> SearchResult:
    return d.search(q, limit=limit, offset=offset)
