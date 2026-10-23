import sqlite3
from pathlib import Path
from typing import Any

import pytest
from db_helpers import kanjivg_svg  # type: ignore[import-not-found]
from factories import make_kanji_collection, make_kanji_with, make_word
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from tokens import TokenFactory, bearer

from shodoukan_practice.domain.entities import EntryCollection
from shodoukan_practice.infrastructure.db.orm import UserORM
from shodoukan_practice.infrastructure.repositories import (
    SqlAlchemyEntryCollectionRepository,
    SqlAlchemyKanjiCollectionRepository,
    SqlAlchemyPracticeEntryRepository,
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
        f"/exercise-sessions/{session_id}/answer",
        json={
            "question_id": question_id,
            "answer": {"type": "option", "option": option},
            "response_ms": 1500,
        },
        headers=headers,
    )


def _right_option(question: dict[str, Any]) -> int:
    kun = {k[0]: k[2] for k in KANJI}[question["prompt"][0]["values"][0]]
    return [o["text"] for o in question["options"]].index(kun)


def _assert_hidden(question: dict[str, Any]) -> None:
    assert question["answered"] is False
    for hidden in ("item_id", "correct_option", "back", "answer", "is_correct"):
        assert question[hidden] is None
    assert all(option["item_id"] is None for option in question["options"])


def test_start_returns_the_first_question_without_its_solution(
    client: TestClient, headers: dict[str, str], exercise_id: int
) -> None:
    started = _start(client, headers, exercise_id)

    assert started["exercise_id"] == exercise_id
    assert started["exercise_name"] == "N5"
    assert started["item_kind"] == "kanji"
    assert started["meaning_lang"] == "en"
    assert started["started_at"].endswith("Z")
    assert started["finished_at"] is None
    assert (started["answered"], started["score"], started["history"]) == (0, 0, [])
    current = started["current"]
    assert current["prompt_fields"] == ["literal"]
    assert current["answer_field"] == "kunyomi"
    assert len(current["options"]) == 4
    _assert_hidden(current)


def test_answering_returns_the_solution_and_the_next_question(
    client: TestClient, headers: dict[str, str], exercise_id: int
) -> None:
    started = _start(client, headers, exercise_id)
    session_id, current = started["id"], started["current"]

    for i in range(7):
        right = _right_option(current)
        response = _answer(client, headers, session_id, current["id"], right)
        assert response.status_code == 200
        body = response.json()
        graded = body["answered"]
        assert graded["id"] == current["id"]
        assert graded["is_correct"] is True
        assert graded["correct_option"] == right
        assert graded["item_id"] is not None
        assert graded["response_ms"] == 1500
        assert [f["field"] for f in graded["back"]] == [
            "literal",
            "kunyomi",
            "meaning",
        ]
        assert all(o["item_id"] is not None for o in graded["options"])
        assert (body["answered_count"], body["score"]) == (i + 1, i + 1)
        assert body["finished_at"] is None
        current = body["next"]
        _assert_hidden(current)
        assert current["position"] == i + 1

    # Coming back shows the same active question, and the history.
    review = client.get(f"/exercise-sessions/{session_id}", headers=headers).json()
    assert review["current"] == current
    assert len(review["history"]) == 7
    assert all(q["correct_option"] is not None for q in review["history"])


def test_answer_errors(
    client: TestClient, headers: dict[str, str], exercise_id: int
) -> None:
    started = _start(client, headers, exercise_id)
    session_id = started["id"]
    question_id = started["current"]["id"]

    assert _answer(client, headers, session_id, question_id, 9).status_code == 422
    assert _answer(client, headers, 999999, question_id, 0).status_code == 404
    assert _answer(client, headers, session_id, question_id, 0).status_code == 200
    # The same question again (a double click): it isn't the active one any more.
    assert _answer(client, headers, session_id, question_id, 1).status_code == 409


def test_response_ms_must_fit_the_database(
    client: TestClient, headers: dict[str, str], exercise_id: int
) -> None:
    started = _start(client, headers, exercise_id)
    url = f"/exercise-sessions/{started['id']}/answer"
    body = {
        "question_id": started["current"]["id"],
        "answer": {"type": "option", "option": 0},
    }

    for too_much in (-1, 2_147_483_648):
        response = client.post(
            url, json={**body, "response_ms": too_much}, headers=headers
        )
        assert response.status_code == 422
    response = client.post(
        url, json={**body, "response_ms": 2_147_483_647}, headers=headers
    )
    assert response.status_code == 200


def test_finish(client: TestClient, headers: dict[str, str], exercise_id: int) -> None:
    started = _start(client, headers, exercise_id)
    session_id, current = started["id"], started["current"]
    _answer(client, headers, session_id, current["id"], _right_option(current))

    response = client.post(f"/exercise-sessions/{session_id}/finish", headers=headers)

    assert response.status_code == 200
    finished = response.json()
    assert finished["finished_at"] is not None
    assert finished["current"] is None
    assert finished["answered"] == 1
    again = client.post(f"/exercise-sessions/{session_id}/finish", headers=headers)
    assert again.json() == finished
    assert _answer(client, headers, session_id, current["id"], 0).status_code == 409


def test_starting_again_finishes_the_previous_session(
    client: TestClient, headers: dict[str, str], exercise_id: int
) -> None:
    first = _start(client, headers, exercise_id)
    _start(client, headers, exercise_id)

    old = client.get(f"/exercise-sessions/{first['id']}", headers=headers).json()

    assert old["finished_at"] is not None
    assert old["current"] is None


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
    url = f"/exercise-sessions/{started['id']}"

    assert client.get(url, headers=other).status_code == 404
    assert client.post(f"{url}/finish", headers=other).status_code == 404
    question_id = started["current"]["id"]
    assert _answer(client, other, started["id"], question_id, 0).status_code == 404
    response = client.post(
        f"/exercises/{exercise_id}/sessions",
        json={"meaning_lang": "en"},
        headers=other,
    )
    assert response.status_code == 404


def test_requires_a_token(client: TestClient) -> None:
    assert client.get("/exercise-sessions/1").status_code == 401
    assert client.post("/exercise-sessions/1/finish").status_code == 401
    response = client.post("/exercises/1/sessions", json={"meaning_lang": "en"})
    assert response.status_code == 401


def test_questions_carry_their_type(
    client: TestClient, headers: dict[str, str], exercise_id: int
) -> None:
    started = _start(client, headers, exercise_id)
    assert started["current"]["type"] == "card.choice"


def test_list_sessions_finds_the_open_one_and_the_history(
    client: TestClient, headers: dict[str, str], exercise_id: int
) -> None:
    first = _start(client, headers, exercise_id)
    current = first["current"]
    _answer(client, headers, first["id"], current["id"], _right_option(current))
    client.post(f"/exercise-sessions/{first['id']}/finish", headers=headers)
    second = _start(client, headers, exercise_id)

    listed = client.get("/exercise-sessions", headers=headers).json()
    assert listed["total"] == 2
    assert [s["id"] for s in listed["items"]] == [second["id"], first["id"]]
    assert (listed["items"][1]["answered"], listed["items"][1]["score"]) == (1, 1)
    assert "history" not in listed["items"][0]

    open_ = client.get("/exercise-sessions?status=open&limit=1", headers=headers)
    assert [s["id"] for s in open_.json()["items"]] == [second["id"]]
    assert open_.json()["items"][0]["finished_at"] is None
    ended = client.get(
        f"/exercise-sessions?status=finished&exercise_id={exercise_id}", headers=headers
    ).json()
    assert [s["id"] for s in ended["items"]] == [first["id"]]
    assert ended["items"][0]["finished_at"].endswith("Z")


def test_list_sessions_rejects_an_unknown_status(
    client: TestClient, headers: dict[str, str]
) -> None:
    response = client.get("/exercise-sessions?status=idle", headers=headers)
    assert response.status_code == 422


def test_skipping_shows_the_solution_and_counts_as_a_miss(
    client: TestClient, headers: dict[str, str], exercise_id: int
) -> None:
    started = _start(client, headers, exercise_id)
    current = started["current"]

    response = client.post(
        f"/exercise-sessions/{started['id']}/answer",
        json={"question_id": current["id"], "answer": {"type": "skip"}},
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    graded = body["answered"]
    assert graded["answer"] == {"type": "skip"}
    assert graded["is_correct"] is False
    assert graded["correct_option"] == _right_option(current)
    assert graded["back"] is not None
    assert body["next"] is not None
    assert (body["answered_count"], body["score"]) == (1, 0)


def test_an_unknown_answer_type_is_rejected(
    client: TestClient, headers: dict[str, str], exercise_id: int
) -> None:
    started = _start(client, headers, exercise_id)

    response = client.post(
        f"/exercise-sessions/{started['id']}/answer",
        json={"question_id": started["current"]["id"], "answer": {"type": "guess"}},
        headers=headers,
    )

    assert response.status_code == 422


@pytest.fixture
def handwriting_exercise_id(
    client: TestClient,
    headers: dict[str, str],
    session: Session,
    exercise_id: int,
    tmp_path: Path,
) -> int:
    """A handwriting exercise on the same collection; 食, 水 and 火 can be
    drawn (the test dictionary has 食's strokes; 水 and 火 are added)."""
    with sqlite3.connect(tmp_path / "dictionary.sqlite") as conn:
        conn.executemany(
            "INSERT INTO kanji_svg VALUES (?, ?)",
            [
                ("水", kanjivg_svg("水", [(1, "M54,10c0,30,0,60,0,90")])),
                ("火", kanjivg_svg("火", [(1, "M20,30c10,20,20,40,30,60")])),
            ],
        )
    collection_ids = client.get(f"/exercises/{exercise_id}", headers=headers).json()[
        "collection_ids"
    ]
    response = client.post(
        "/exercises",
        json={
            "item_kind": "kanji",
            "name": "Write N5",
            "collection_ids": collection_ids,
            "settings": {
                "type": "card.handwriting",
                "directions": [{"prompt": ["meaning"], "answer": "literal"}],
                "back_fields": ["onyomi"],
            },
        },
        headers=headers,
    )
    assert response.status_code == 201, response.json()
    created: int = response.json()["id"]
    return created


def test_a_handwriting_question_hides_its_kanji_until_drawn(
    client: TestClient, headers: dict[str, str], handwriting_exercise_id: int
) -> None:
    started = _start(client, headers, handwriting_exercise_id)
    question = started["current"]

    assert question["type"] == "card.handwriting"
    assert question["answer_field"] == "literal"
    assert (question["references"], question["grade"], question["back"]) == (
        None,
        None,
        None,
    )
    assert "options" not in question

    response = client.post(
        f"/exercise-sessions/{started['id']}/answer",
        json={
            "question_id": question["id"],
            "answer": {"type": "strokes", "strokes": [[[54, 10], [54, 60], [54, 100]]]},
            "response_ms": 5000,
        },
        headers=headers,
    )

    assert response.status_code == 200, response.json()
    graded = response.json()["answered"]
    assert graded["references"][0]["literal"] in {"食", "水", "火"}
    assert set(graded["references"][0]["strokes"][0]) == {"path", "label"}
    assert graded["grade"]["verdict"] in {"correct", "close", "wrong"}
    assert graded["answer"]["type"] == "strokes"
    assert response.json()["next"]["type"] == "card.handwriting"


@pytest.mark.parametrize(
    "answer",
    [
        {"type": "strokes", "strokes": [[[500, 10]]]},  # off the canvas
        {"type": "strokes", "strokes": []},
        {"type": "option", "option": 0},  # not a choice card
    ],
)
def test_a_drawing_that_doesnt_fit_is_refused(
    client: TestClient,
    headers: dict[str, str],
    handwriting_exercise_id: int,
    answer: dict[str, Any],
) -> None:
    started = _start(client, headers, handwriting_exercise_id)

    response = client.post(
        f"/exercise-sessions/{started['id']}/answer",
        json={"question_id": started["current"]["id"], "answer": answer},
        headers=headers,
    )

    assert response.status_code == 422


@pytest.fixture
def word_exercise_id(
    client: TestClient,
    headers: dict[str, str],
    session: Session,
    user: UserORM,
    tmp_path: Path,
) -> int:
    """Write the reading of みず and ひ, whose kana get strokes here."""
    with sqlite3.connect(tmp_path / "dictionary.sqlite") as conn:
        conn.executemany(
            "INSERT INTO kanji_svg VALUES (?, ?)",
            [
                (kana, kanjivg_svg(kana, [(1, "M20,30c10,20,20,40,30,60")]))
                for kana in "みずひ"
            ],
        )
    collections = SqlAlchemyEntryCollectionRepository(session)
    entries = SqlAlchemyPracticeEntryRepository(session)
    words = collections.add(EntryCollection(id=None, user_id=user.id, name="words"))
    for i, (writing, reading, meaning) in enumerate(
        [("水", "みず", "water"), ("火", "ひ", "fire")]
    ):
        entry = make_word(user.id, i + 1, writing, reading, [(meaning, "eng")])
        collections.add_item(words, entries.add(entry))
    session.commit()
    response = client.post(
        "/exercises",
        json={
            "item_kind": "entries",
            "name": "Write readings",
            "collection_ids": [words.id],
            "settings": {
                "type": "card.handwriting",
                "directions": [{"prompt": ["meaning"], "answer": "reading"}],
            },
        },
        headers=headers,
    )
    assert response.status_code == 201, response.json()
    created: int = response.json()["id"]
    return created


def test_a_word_question_shows_its_cells_but_not_its_words_until_written(
    client: TestClient, headers: dict[str, str], word_exercise_id: int
) -> None:
    response = client.post(
        f"/exercises/{word_exercise_id}/sessions",
        json={"meaning_lang": "eng"},
        headers=headers,
    )
    assert response.status_code == 201, response.json()
    started = response.json()
    question = started["current"]

    assert question["type"] == "card.handwriting_word"
    assert question["answer_field"] == "reading"
    assert question["cell_count"] in {1, 2}
    assert (question["words"], question["grade"]) == (None, None)

    cells = [[[[20, 30], [40, 70]]]] * question["cell_count"]
    response = client.post(
        f"/exercise-sessions/{started['id']}/answer",
        json={
            "question_id": question["id"],
            "answer": {"type": "cells", "cells": cells},
        },
        headers=headers,
    )

    assert response.status_code == 200, response.json()
    graded = response.json()["answered"]
    assert graded["words"][0]["text"] in {"みず", "ひ"}
    assert len(graded["grade"]["cells"]) == question["cell_count"]
    assert graded["answer"]["type"] == "cells"


def test_a_word_in_the_wrong_number_of_cells_is_422(
    client: TestClient, headers: dict[str, str], word_exercise_id: int
) -> None:
    started = client.post(
        f"/exercises/{word_exercise_id}/sessions",
        json={"meaning_lang": "eng"},
        headers=headers,
    ).json()
    question = started["current"]
    cells = [[[[20, 30], [40, 70]]]] * (question["cell_count"] + 1)

    response = client.post(
        f"/exercise-sessions/{started['id']}/answer",
        json={
            "question_id": question["id"],
            "answer": {"type": "cells", "cells": cells},
        },
        headers=headers,
    )

    assert response.status_code == 422
