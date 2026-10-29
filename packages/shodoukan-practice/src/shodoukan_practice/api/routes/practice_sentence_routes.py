"""The sentences of the user's library: listing, adding (one, or many after
reviewing their analysis), rewriting, and marking and linking their words.

Every change returns the whole sentence as it is now. A sentence from the
dictionary can't be rewritten (409), only deactivated. A word over another
or outside the sentence is a 422.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status

from ...application.commands import (
    AddSentence,
    AddSentences,
    AddSentenceWord,
    CorrectSentenceWord,
    LinkSentenceWord,
    MarkSentenceWord,
    RemoveSentence,
    RemoveSentenceWord,
    RewriteSentence,
    SentenceDraft,
    SetSentenceActive,
    SetSentenceNotes,
    WordDraft,
)
from ...application.queries import AnalyzeSentenceTexts, GetSentence, SearchSentences
from ...domain.repositories import SentenceSearch
from ..deps import (
    CurrentUserDep,
    SessionDep,
    get_add_sentence,
    get_add_sentence_word,
    get_add_sentences,
    get_analyze_sentence_texts,
    get_correct_sentence_word,
    get_get_sentence,
    get_link_sentence_word,
    get_mark_sentence_word,
    get_remove_sentence,
    get_remove_sentence_word,
    get_rewrite_sentence,
    get_search_sentences,
    get_set_sentence_active,
    get_set_sentence_notes,
)
from ..schemas import (
    ActiveRequest,
    AnalyzeRequest,
    CorrectionRequest,
    LinkRequest,
    NewSentenceRequest,
    NotesRequest,
    SentenceBatchRequest,
    SentencePageResponse,
    SentenceProposalResponse,
    SentenceRequest,
    SentenceResponse,
    SpanRequest,
    WordRequest,
)

_RESPONSES: dict[int | str, dict[str, Any]] = {
    status.HTTP_401_UNAUTHORIZED: {"description": "Missing or invalid token."},
    status.HTTP_404_NOT_FOUND: {
        "description": "Not in the user's library: the sentence, one of its "
        "words, or the library word or sense to link."
    },
    status.HTTP_422_UNPROCESSABLE_CONTENT: {
        "description": "A word over another, outside the sentence, or a "
        "reading that isn't kana."
    },
}

router = APIRouter(
    prefix="/library/sentences", tags=["sentences"], responses=_RESPONSES
)


@router.get("", response_model=SentencePageResponse)
def list_sentences(
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[SearchSentences, Depends(get_search_sentences)],
    q: Annotated[
        str | None, Query(max_length=100, description="In the text or a translation.")
    ] = None,
    entry_id: Annotated[
        int | None, Query(description="With a word linked to this entry.")
    ] = None,
    linked: Annotated[
        bool | None, Query(description="false: sentences with no linked word.")
    ] = None,
    active: bool | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> SentencePageResponse:
    """The user's sentences, newest first."""
    search = SentenceSearch(text=q, entry_id=entry_id, linked=linked, active=active)
    page = use_case.execute(user.id, search, limit, offset)
    session.commit()  # persists the user if this request created it
    return SentencePageResponse.model_validate(page)


@router.post("", response_model=SentenceResponse, status_code=status.HTTP_201_CREATED)
def add_sentence(
    body: NewSentenceRequest,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[AddSentence, Depends(get_add_sentence)],
) -> SentenceResponse:
    """Add a sentence of the user's own, linked to one of their words if
    `entry_id` is given (its gap is found where it is, inflected or not)."""
    sentence = use_case.execute(
        user.id,
        body.japanese,
        body.translation,
        body.lang,
        entry_id=body.entry_id,
        sense_id=body.sense_id,
    )
    session.commit()
    return SentenceResponse.model_validate(sentence)


@router.post(
    "/batch",
    response_model=list[SentenceResponse],
    status_code=status.HTTP_201_CREATED,
)
def add_sentences(
    body: SentenceBatchRequest,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[AddSentences, Depends(get_add_sentences)],
) -> list[SentenceResponse]:
    """Store several reviewed sentences at once, each with its words (what
    `/analyze` proposed, as the user left it). All or nothing."""
    sentences = use_case.execute(
        user.id,
        [
            SentenceDraft(
                text=draft.japanese,
                translation=draft.translation,
                lang=draft.lang,
                words=[
                    WordDraft(w.start, w.end, w.entry_id, w.sense_id)
                    for w in draft.words
                ],
            )
            for draft in body.sentences
        ],
    )
    session.commit()
    return [SentenceResponse.model_validate(s) for s in sentences]


@router.post("/analyze", response_model=list[SentenceProposalResponse])
def analyze(
    body: AnalyzeRequest,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[AnalyzeSentenceTexts, Depends(get_analyze_sentence_texts)],
) -> list[SentenceProposalResponse]:
    """Analyze sentences before adding them: their morphemes and the user's
    words each one uses. Nothing is stored."""
    proposals = use_case.execute(user.id, body.texts)
    session.commit()
    return [SentenceProposalResponse.model_validate(p) for p in proposals]


@router.get("/{sentence_id}", response_model=SentenceResponse)
def get_sentence(
    sentence_id: int,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[GetSentence, Depends(get_get_sentence)],
) -> SentenceResponse:
    sentence = use_case.execute(user.id, sentence_id)
    session.commit()
    return SentenceResponse.model_validate(sentence)


@router.put(
    "/{sentence_id}",
    response_model=SentenceResponse,
    responses={status.HTTP_409_CONFLICT: {"description": "A dictionary sentence."}},
)
def rewrite_sentence(
    sentence_id: int,
    body: SentenceRequest,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[RewriteSentence, Depends(get_rewrite_sentence)],
) -> SentenceResponse:
    """Rewrite one of the user's own sentences and its translation in `lang`;
    its words keep their gap where their text still is."""
    sentence = use_case.execute(
        user.id, sentence_id, body.japanese, body.translation, body.lang
    )
    session.commit()
    return SentenceResponse.model_validate(sentence)


@router.delete("/{sentence_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_sentence(
    sentence_id: int,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[RemoveSentence, Depends(get_remove_sentence)],
) -> None:
    """Remove the sentence from the library."""
    use_case.execute(user.id, sentence_id)
    session.commit()


@router.put("/{sentence_id}/active", response_model=SentenceResponse)
def set_active(
    sentence_id: int,
    body: ActiveRequest,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[SetSentenceActive, Depends(get_set_sentence_active)],
) -> SentenceResponse:
    """Activate or deactivate it (inactive sentences aren't practised)."""
    sentence = use_case.execute(user.id, sentence_id, body.active)
    session.commit()
    return SentenceResponse.model_validate(sentence)


@router.put("/{sentence_id}/notes", response_model=SentenceResponse)
def set_notes(
    sentence_id: int,
    body: NotesRequest,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[SetSentenceNotes, Depends(get_set_sentence_notes)],
) -> SentenceResponse:
    sentence = use_case.execute(user.id, sentence_id, body.notes)
    session.commit()
    return SentenceResponse.model_validate(sentence)


@router.post("/{sentence_id}/words", response_model=SentenceResponse)
def add_word(
    sentence_id: int,
    body: WordRequest,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[AddSentenceWord, Depends(get_add_sentence_word)],
) -> SentenceResponse:
    """Mark a word (`start`/`end`) and link it to one of the user's words, or
    link a word without a span (its gap is found where it is)."""
    sentence = use_case.execute(
        user.id, sentence_id, body.start, body.end, body.entry_id, body.sense_id
    )
    session.commit()
    return SentenceResponse.model_validate(sentence)


@router.put("/{sentence_id}/words/{word_id}/span", response_model=SentenceResponse)
def mark_word(
    sentence_id: int,
    word_id: int,
    body: SpanRequest,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[MarkSentenceWord, Depends(get_mark_sentence_word)],
) -> SentenceResponse:
    """Move a word's gap; it's analyzed again."""
    sentence = use_case.execute(user.id, sentence_id, word_id, body.start, body.end)
    session.commit()
    return SentenceResponse.model_validate(sentence)


@router.put("/{sentence_id}/words/{word_id}/link", response_model=SentenceResponse)
def link_word(
    sentence_id: int,
    word_id: int,
    body: LinkRequest,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[LinkSentenceWord, Depends(get_link_sentence_word)],
) -> SentenceResponse:
    """Link the word to one of the user's words and senses, or unlink it."""
    sentence = use_case.execute(
        user.id, sentence_id, word_id, body.entry_id, body.sense_id
    )
    session.commit()
    return SentenceResponse.model_validate(sentence)


@router.put(
    "/{sentence_id}/words/{word_id}/correction", response_model=SentenceResponse
)
def correct_word(
    sentence_id: int,
    word_id: int,
    body: CorrectionRequest,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[CorrectSentenceWord, Depends(get_correct_sentence_word)],
) -> SentenceResponse:
    """The user's lemma and reading (kana) for the word."""
    sentence = use_case.execute(user.id, sentence_id, word_id, body.lemma, body.reading)
    session.commit()
    return SentenceResponse.model_validate(sentence)


@router.delete("/{sentence_id}/words/{word_id}", response_model=SentenceResponse)
def remove_word(
    sentence_id: int,
    word_id: int,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[RemoveSentenceWord, Depends(get_remove_sentence_word)],
) -> SentenceResponse:
    sentence = use_case.execute(user.id, sentence_id, word_id)
    session.commit()
    return SentenceResponse.model_validate(sentence)
