from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from tokens import TokenFactory, bearer

from shodoukan_practice.infrastructure.db.orm import UserORM
from shodoukan_practice.infrastructure.repositories import (
    SqlAlchemyPracticeEntryRepository,
)


def test_import_entry_creates_it(
    client: TestClient, make_token: TokenFactory, user: UserORM, session: Session
) -> None:
    response = client.post(
        "/library/entries", json={"entry_id": 1000001}, headers=bearer(make_token())
    )

    assert response.status_code == 201
    body = response.json()
    assert body["source_entry_id"] == 1000001
    assert [g["text"] for g in body["senses"][0]["glosses"]] == [
        "to eat",
        "to have a meal",
    ]
    assert body["created_at"].endswith("Z")
    assert "user_id" not in body
    stored = SqlAlchemyPracticeEntryRepository(session).get(body["id"], user.id)
    assert stored is not None


def test_import_entry_again_returns_200_with_the_same_item(
    client: TestClient, make_token: TokenFactory, user: UserORM
) -> None:
    headers = bearer(make_token())
    first = client.post("/library/entries", json={"entry_id": 1000001}, headers=headers)
    again = client.post("/library/entries", json={"entry_id": 1000001}, headers=headers)

    assert first.status_code == 201
    assert again.status_code == 200
    assert again.json()["id"] == first.json()["id"]


def test_import_unknown_entry_is_404(
    client: TestClient, make_token: TokenFactory, user: UserORM
) -> None:
    response = client.post(
        "/library/entries", json={"entry_id": 999}, headers=bearer(make_token())
    )
    assert response.status_code == 404


def test_import_kanji_creates_then_returns_it(
    client: TestClient, make_token: TokenFactory, user: UserORM
) -> None:
    headers = bearer(make_token())
    first = client.post("/library/kanji", json={"literal": "食"}, headers=headers)
    again = client.post("/library/kanji", json={"literal": "食"}, headers=headers)

    assert first.status_code == 201
    assert [r["text"] for r in first.json()["on_readings"]] == ["ショク", "ジキ"]
    assert again.status_code == 200
    assert again.json()["id"] == first.json()["id"]


def test_import_unknown_kanji_is_404(
    client: TestClient, make_token: TokenFactory, user: UserORM
) -> None:
    response = client.post(
        "/library/kanji", json={"literal": "龘"}, headers=bearer(make_token())
    )
    assert response.status_code == 404


def test_kanji_literal_must_be_one_character(
    client: TestClient, make_token: TokenFactory, user: UserORM
) -> None:
    response = client.post(
        "/library/kanji", json={"literal": "食べ"}, headers=bearer(make_token())
    )
    assert response.status_code == 422


def test_missing_token_is_401(client: TestClient, user: UserORM) -> None:
    response = client.post("/library/entries", json={"entry_id": 1000001})

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_invalid_token_is_401(client: TestClient, user: UserORM) -> None:
    response = client.post(
        "/library/entries", json={"entry_id": 1000001}, headers=bearer("not-a-jwt")
    )
    assert response.status_code == 401


def test_unregistered_user_is_403(
    client: TestClient, make_token: TokenFactory, user: UserORM
) -> None:
    response = client.post(
        "/library/entries",
        json={"entry_id": 1000001},
        headers=bearer(make_token("sub-nobody")),
    )
    assert response.status_code == 403
