from pydantic import BaseModel

from shodoukan.models.entry import Entry, Page
from shodoukan.models.kanji import Kanji


class SearchResult(BaseModel):
    entries: Page[Entry]
    kanji: list[Kanji]
