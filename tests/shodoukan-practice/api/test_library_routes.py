from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from tokens import TokenFactory, bearer

from shodoukan_practice.infrastructure.db.orm import UserORM
from shodoukan_practice.infrastructure.repositories import (
    SqlAlchemyPracticeEntryRepository,
    SqlAlchemyUserRepository,
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


def test_first_request_of_a_new_identity_creates_its_user(
    client: TestClient, make_token: TokenFactory, session: Session
) -> None:
    provider_id = uuid4()
    response = client.post(
        "/library/entries",
        json={"entry_id": 1000001},
        headers=bearer(make_token(str(provider_id), preferred_username="newbie")),
    )

    assert response.status_code == 201
    created = SqlAlchemyUserRepository(session).get(provider_id)
    assert created is not None
    assert created.username == "newbie"


def test_imported_lists_what_the_user_has(
    client: TestClient, make_token: TokenFactory, user: UserORM
) -> None:
    headers = bearer(make_token())
    entry = client.post("/library/entries", json={"entry_id": 1000001}, headers=headers)
    kanji = client.post("/library/kanji", json={"literal": "食"}, headers=headers)

    response = client.get(
        "/library/imported",
        params={"entry_ids": [1000001, 1000002], "literals": ["食", "水"]},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json() == {
        "entries": [{"source_entry_id": 1000001, "id": entry.json()["id"]}],
        "kanji": [{"literal": "食", "id": kanji.json()["id"]}],
    }


def test_imported_ignores_other_users_imports(
    client: TestClient, make_token: TokenFactory, user: UserORM, other_user: UserORM
) -> None:
    client.post(
        "/library/entries",
        json={"entry_id": 1000001},
        headers=bearer(make_token(str(other_user.id))),
    )

    response = client.get(
        "/library/imported",
        params={"entry_ids": [1000001]},
        headers=bearer(make_token()),
    )

    assert response.json() == {"entries": [], "kanji": []}


def test_imported_validates_its_parameters(
    client: TestClient, make_token: TokenFactory, user: UserORM
) -> None:
    headers = bearer(make_token())

    too_many = client.get(
        "/library/imported", params={"entry_ids": list(range(101))}, headers=headers
    )
    not_a_kanji = client.get(
        "/library/imported", params={"literals": ["食べ"]}, headers=headers
    )

    assert too_many.status_code == 422
    assert not_a_kanji.status_code == 422


def test_imported_requires_a_token(client: TestClient) -> None:
    assert client.get("/library/imported").status_code == 401


def test_cors_allows_the_frontend(client: TestClient) -> None:
    response = client.options(
        "/library/imported",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
