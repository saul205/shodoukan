from typing import Any

import pytest
from factories import make_kanji_collection, make_kanji_with
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from tokens import TokenFactory, bearer

from shodoukan_practice.infrastructure.db.orm import UserORM
from shodoukan_practice.infrastructure.repositories import (
    SqlAlchemyKanjiCollectionRepository,
    SqlAlchemyPracticeKanjiRepository,
)

# literal, kun'yomi: one exercise asks the kun'yomi of each.
KANJI = [("食", "た.べる"), ("水", "みず"), ("火", "ひ"), ("木", "き"), ("山", "やま")]


@pytest.fixture
def headers(make_token: TokenFactory, user: UserORM) -> dict[str, str]:
    return bearer(make_token())


@pytest.fixture
def exercise_id(
    client: TestClient, headers: dict[str, str], session: Session, user: UserORM
) -> int:
    collections = SqlAlchemyKanjiCollectionRepository(session)
    kanji = SqlAlchemyPracticeKanjiRepository(session)
    n5 = collections.add(make_kanji_collection(user.id, "N5"))
    for literal, kun in KANJI:
        collections.add_item(
            n5, kanji.add(make_kanji_with(user.id, literal, kun=[kun]))
        )
    session.commit()
    settings = {
        "type": "card.choice",
        "directions": [{"prompt": ["literal"], "answer": "kunyomi"}],
    }
    response = client.post(
        "/exercises",
        json={
            "item_kind": "kanji",
            "name": "N5",
            "collection_ids": [n5.id],
            "settings": settings,
        },
        headers=headers,
    )
    created: int = response.json()["id"]
    return created


def _play(
    client: TestClient, headers: dict[str, str], exercise_id: int, rights: list[bool]
) -> dict[str, Any]:
    """Start a session and answer right or wrong, as `rights` says."""
    started = client.post(
        f"/exercises/{exercise_id}/sessions",
        json={"meaning_lang": "en"},
        headers=headers,
    ).json()
    current = started["current"]
    kun = dict(KANJI)
    for right in rights:
        texts = [option["text"] for option in current["options"]]
        option = texts.index(kun[current["prompt"][0]["values"][0]])
        if not right:
            option = (option + 1) % len(texts)
        body = {
            "question_id": current["id"],
            "answer": {"type": "option", "option": option},
            "response_ms": 1500,
        }
        response = client.post(
            f"/exercise-sessions/{started['id']}/answer", json=body, headers=headers
        )
        current = response.json()["next"]
    result: dict[str, Any] = started
    return result


def test_exercise_statistics(
    client: TestClient, headers: dict[str, str], exercise_id: int
) -> None:
    _play(client, headers, exercise_id, [True, False, True])

    response = client.get(f"/exercises/{exercise_id}/statistics", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["exercise_id"] == exercise_id
    assert body["item_kind"] == "kanji"
    totals = body["totals"]
    assert (totals["sessions"], totals["answered"], totals["correct"]) == (1, 3, 2)
    assert totals["accuracy"] == 2 / 3
    assert totals["mean_response_ms"] == 1500
    assert body["directions"] == [
        {
            "prompt_fields": ["literal"],
            "answer_field": "kunyomi",
            "answered": 3,
            "correct": 2,
            "accuracy": 2 / 3,
        }
    ]
    [missed] = body["most_missed"]
    assert (missed["answered"], missed["wrong"], missed["reading"]) == (1, 1, None)
    assert len(missed["label"]) == 1  # the kanji


def test_exercise_statistics_of_an_unknown_exercise(
    client: TestClient, headers: dict[str, str]
) -> None:
    response = client.get("/exercises/999/statistics", headers=headers)
    assert response.status_code == 404


def test_practice_statistics(
    client: TestClient, headers: dict[str, str], exercise_id: int
) -> None:
    _play(client, headers, exercise_id, [False, True])

    response = client.get("/statistics?days=7&tz=Europe/Madrid", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["totals"]["answered"] == 2
    assert len(body["activity"]) == 7
    assert body["activity"][-1]["answered"] == 2  # today, in Madrid
    assert sum(day["answered"] for day in body["activity"]) == 2
    [exercise] = body["exercises"]
    assert (exercise["exercise_id"], exercise["exercise_name"]) == (exercise_id, "N5")
    assert exercise["accuracy"] == 0.5
    assert len(body["most_missed_kanji"]) == 1
    assert body["most_missed_entries"] == []


def test_practice_statistics_with_nothing_answered(
    client: TestClient, headers: dict[str, str]
) -> None:
    body = client.get("/statistics", headers=headers).json()
    assert body["totals"] == {
        "sessions": 0,
        "answered": 0,
        "correct": 0,
        "accuracy": None,
        "mean_response_ms": None,
    }
    assert len(body["activity"]) == 30


def test_practice_statistics_rejects_bad_parameters(
    client: TestClient, headers: dict[str, str]
) -> None:
    for query in ("tz=Mars/Olympus", "tz=../etc", "days=0", "days=366"):
        response = client.get(f"/statistics?{query}", headers=headers)
        assert response.status_code == 422, query
