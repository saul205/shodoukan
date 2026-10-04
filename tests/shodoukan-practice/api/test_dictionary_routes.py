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


def test_entry_details_are_public(client: TestClient) -> None:
    entry = client.get("/dictionary/entries/1000001")
    kanji = client.get("/dictionary/entries/1000001/kanji")

    assert entry.status_code == 200
    assert entry.json()["kanji_readings"][0]["kanji"] == "食べる"
    assert [k["literal"] for k in kanji.json()] == ["食"]


def test_kanji_details_are_public(client: TestClient) -> None:
    kanji = client.get("/dictionary/kanji/食")
    words = client.get("/dictionary/kanji/食/entries", params={"limit": 5})

    assert kanji.status_code == 200
    assert kanji.json()["on_readings"] == ["ショク", "ジキ"]
    assert words.status_code == 200
    body = words.json()
    assert [e["id"] for e in body["items"]] == [1000001]
    assert (body["total"], body["limit"], body["offset"]) == (1, 5, 0)


def test_unknown_details_are_404(client: TestClient) -> None:
    assert client.get("/dictionary/entries/999").status_code == 404
    assert client.get("/dictionary/entries/999/kanji").status_code == 404
    assert client.get("/dictionary/kanji/龘").status_code == 404
    assert client.get("/dictionary/kanji/龘/entries").status_code == 404


def test_kanji_detail_validates_its_parameters(client: TestClient) -> None:
    assert client.get("/dictionary/kanji/食べ").status_code == 422
    assert (
        client.get("/dictionary/kanji/食/entries", params={"limit": 0}).status_code
        == 422
    )
