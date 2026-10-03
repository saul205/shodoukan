from fastapi.testclient import TestClient
from tokens import TokenFactory, bearer

from shodoukan_practice.infrastructure.db.orm import UserORM


def test_search_is_public(client: TestClient) -> None:
    response = client.get("/dictionary/search", params={"q": "食べる"})

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"entries", "kanji"}
    assert set(body["entries"]) == {"items", "total", "limit", "offset"}
    entry = body["entries"]["items"][0]
    assert entry["id"] == 1000001
    assert [g["text"] for g in entry["senses"][0]["glosses"]] == [
        "to eat",
        "to have a meal",
    ]


def test_search_paginates(client: TestClient) -> None:
    body = client.get(
        "/dictionary/search", params={"q": "taberu", "limit": 1, "offset": 0}
    ).json()

    assert body["entries"]["limit"] == 1
    assert body["entries"]["offset"] == 0
    assert len(body["entries"]["items"]) <= 1


def test_search_validates_its_parameters(client: TestClient) -> None:
    assert client.get("/dictionary/search").status_code == 422
    assert client.get("/dictionary/search", params={"q": ""}).status_code == 422
    too_many = client.get("/dictionary/search", params={"q": "a", "limit": 101})
    assert too_many.status_code == 422


def test_search_results_can_be_imported(
    client: TestClient, make_token: TokenFactory, user: UserORM
) -> None:
    headers = bearer(make_token())
    found = client.get("/dictionary/search", params={"q": "water"}).json()
    entry_id = found["entries"]["items"][0]["id"]

    imported = client.post(
        "/library/entries", json={"entry_id": entry_id}, headers=headers
    )
    status = client.get(
        "/library/imported", params={"entry_ids": [entry_id]}, headers=headers
    )

    assert imported.status_code == 201
    assert status.json()["entries"] == [
        {"source_entry_id": entry_id, "id": imported.json()["id"]}
    ]
