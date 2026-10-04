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

KANJI = [
    ("食", "ショク", "た.べる", "eat"),
    ("水", "スイ", "みず", "water"),
    ("火", "カ", "ひ", "fire"),
    ("木", "モク", "き", "tree"),
    ("山", "サン", "やま", "mountain"),
]
SETTINGS = {
    "type": "card.choice",
    "directions": [{"prompt": ["literal"], "answer": "kunyomi"}],
    "back_fields": ["meaning"],
    "question_count": 3,
}


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
    for literal, on, kun, meaning in KANJI:
        item = kanji.add(
            make_kanji_with(
                user.id, literal, on=[on], kun=[kun], meanings=[(meaning, "en")]
            )
        )
        collections.add_item(n5, item)
    session.commit()
    response = client.post(
        "/exercises",
        json={
            "item_kind": "kanji",
            "name": "N5",
            "collection_ids": [n5.id],
            "settings": SETTINGS,
        },
        headers=headers,
    )
    exercise: int = response.json()["id"]
    return exercise


def _start(
    client: TestClient, headers: dict[str, str], exercise_id: int
) -> dict[str, Any]:
    response = client.post(
        f"/exercises/{exercise_id}/sessions",
        json={"meaning_lang": "en"},
        headers=headers,
    )
    assert response.status_code == 201, response.json()
    result: dict[str, Any] = response.json()
    return result


def _answer(
    client: TestClient,
    headers: dict[str, str],
    session_id: int,
    question_id: int,
    option: int,
) -> Any:
    return client.post(
        f"/exercise-sessions/{session_id}/questions/{question_id}/answer",
        json={"answer": {"type": "option", "option": option}, "response_ms": 1500},
        headers=headers,
    )


def test_start_hides_the_solutions(
    client: TestClient, headers: dict[str, str], exercise_id: int
) -> None:
    started = _start(client, headers, exercise_id)

    assert started["exercise_id"] == exercise_id
    assert started["exercise_name"] == "N5"
    assert started["item_kind"] == "kanji"
    assert started["meaning_lang"] == "en"
    assert started["started_at"].endswith("Z")
    assert started["finished_at"] is None
    assert started["score"] == 0
    assert len(started["questions"]) == 3
    question = started["questions"][0]
    assert question["prompt_fields"] == ["literal"]
    assert question["answer_field"] == "kunyomi"
    assert question["prompt"][0]["field"] == "literal"
    assert len(question["options"]) == 4
    assert question["answered"] is False
    for hidden in ("item_id", "correct_option", "back", "answer", "is_correct"):
        assert question[hidden] is None
    assert all(option["item_id"] is None for option in question["options"])


def test_answer_reveals_the_solution_and_finishes(
    client: TestClient, headers: dict[str, str], exercise_id: int
) -> None:
    started = _start(client, headers, exercise_id)
    session_id = started["id"]
    texts = {k[0]: k[2] for k in KANJI}

    for i, question in enumerate(started["questions"]):
        literal = question["prompt"][0]["values"][0]
        right = [o["text"] for o in question["options"]].index(texts[literal])
        response = _answer(client, headers, session_id, question["id"], right)
        assert response.status_code == 200
        body = response.json()
        graded = body["question"]
        assert graded["answered"] is True
        assert graded["is_correct"] is True
        assert graded["correct_option"] == right
        assert graded["item_id"] is not None
        assert graded["response_ms"] == 1500
        assert [f["field"] for f in graded["back"]] == ["literal", "kunyomi", "meaning"]
        assert all(o["item_id"] is not None for o in graded["options"])
        assert body["score"] == i + 1
        last = i == len(started["questions"]) - 1
        assert (body["finished_at"] is not None) == last

    review = client.get(f"/exercise-sessions/{session_id}", headers=headers).json()
    assert review["score"] == 3
    assert review["finished_at"] is not None
    assert all(q["correct_option"] is not None for q in review["questions"])


def test_answer_errors(
    client: TestClient, headers: dict[str, str], exercise_id: int
) -> None:
    started = _start(client, headers, exercise_id)
    session_id = started["id"]
    question_id = started["questions"][0]["id"]

    assert _answer(client, headers, session_id, question_id, 9).status_code == 422
    assert _answer(client, headers, session_id, 999999, 0).status_code == 404
    assert _answer(client, headers, session_id, question_id, 0).status_code == 200
    assert _answer(client, headers, session_id, question_id, 1).status_code == 409


def test_bad_meaning_lang_is_422(
    client: TestClient, headers: dict[str, str], exercise_id: int
) -> None:
    response = client.post(
        f"/exercises/{exercise_id}/sessions",
        json={"meaning_lang": "English"},
        headers=headers,
    )
    assert response.status_code == 422


def test_too_few_items_is_422(client: TestClient, headers: dict[str, str]) -> None:
    collection = client.post(
        "/collections/kanji", json={"name": "empty"}, headers=headers
    ).json()
    empty = client.post(
        "/exercises",
        json={
            "item_kind": "kanji",
            "name": "Empty",
            "collection_ids": [collection["id"]],
            "settings": SETTINGS,
        },
        headers=headers,
    ).json()

    response = client.post(
        f"/exercises/{empty['id']}/sessions",
        json={"meaning_lang": "en"},
        headers=headers,
    )

    assert response.status_code == 422
    assert "at least 2 items" in response.json()["detail"]


def test_another_users_session_is_404(
    client: TestClient,
    headers: dict[str, str],
    exercise_id: int,
    make_token: TokenFactory,
    other_user: UserORM,
) -> None:
    started = _start(client, headers, exercise_id)
    other = bearer(make_token(str(other_user.id)))
    question_id = started["questions"][0]["id"]

    assert (
        client.get(f"/exercise-sessions/{started['id']}", headers=other).status_code
        == 404
    )
    assert _answer(client, other, started["id"], question_id, 0).status_code == 404
    response = client.post(
        f"/exercises/{exercise_id}/sessions", json={"meaning_lang": "en"}, headers=other
    )
    assert response.status_code == 404


def test_requires_a_token(client: TestClient) -> None:
    assert client.get("/exercise-sessions/1").status_code == 401
    assert (
        client.post("/exercises/1/sessions", json={"meaning_lang": "en"}).status_code
        == 401
    )
