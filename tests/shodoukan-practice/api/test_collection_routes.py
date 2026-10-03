from typing import Any

import pytest
from fastapi.testclient import TestClient
from tokens import TokenFactory, bearer

from shodoukan_practice.infrastructure.db.orm import UserORM


@pytest.fixture
def headers(make_token: TokenFactory, user: UserORM) -> dict[str, str]:
    return bearer(make_token())


def _create(
    client: TestClient, headers: dict[str, str], kind: str = "entries", **body: Any
) -> dict[str, Any]:
    response = client.post(
        f"/collections/{kind}", json={"name": "verbs", **body}, headers=headers
    )
    assert response.status_code == 201
    result: dict[str, Any] = response.json()
    return result


def _import_entry(client: TestClient, headers: dict[str, str], entry_id: int) -> int:
    response = client.post(
        "/library/entries", json={"entry_id": entry_id}, headers=headers
    )
    practice_id: int = response.json()["id"]
    return practice_id


def test_create_and_get(client: TestClient, headers: dict[str, str]) -> None:
    created = _create(client, headers, name="  verbs  ", description="Godan")

    assert created["name"] == "verbs"  # stripped
    assert created["description"] == "Godan"
    assert created["created_at"].endswith("Z")
    assert "user_id" not in created
    fetched = client.get(f"/collections/entries/{created['id']}", headers=headers)
    assert fetched.json() == created


def test_create_validates_the_name(client: TestClient, headers: dict[str, str]) -> None:
    for name in ("", "   ", "x" * 101):
        response = client.post(
            "/collections/entries", json={"name": name}, headers=headers
        )
        assert response.status_code == 422


def test_duplicate_name_is_409(client: TestClient, headers: dict[str, str]) -> None:
    _create(client, headers)
    response = client.post(
        "/collections/entries", json={"name": "verbs"}, headers=headers
    )
    assert response.status_code == 409


def test_list_is_by_name_and_per_kind(
    client: TestClient, headers: dict[str, str]
) -> None:
    _create(client, headers, name="verbs")
    _create(client, headers, name="adjectives")
    _create(client, headers, kind="kanji", name="N5")

    entries = client.get("/collections/entries", headers=headers).json()
    kanji = client.get("/collections/kanji", headers=headers).json()

    assert [c["name"] for c in entries] == ["adjectives", "verbs"]
    assert [c["name"] for c in kanji] == ["N5"]


def test_update_replaces_name_and_description(
    client: TestClient, headers: dict[str, str]
) -> None:
    created = _create(client, headers, description="old")

    response = client.put(
        f"/collections/entries/{created['id']}",
        json={"name": "godan"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["name"] == "godan"
    assert response.json()["description"] is None  # omitted means cleared


def test_update_to_a_taken_name_is_409(
    client: TestClient, headers: dict[str, str]
) -> None:
    _create(client, headers, name="verbs")
    nouns = _create(client, headers, name="nouns")

    response = client.put(
        f"/collections/entries/{nouns['id']}", json={"name": "verbs"}, headers=headers
    )
    assert response.status_code == 409


def test_delete(client: TestClient, headers: dict[str, str]) -> None:
    created = _create(client, headers)
    url = f"/collections/entries/{created['id']}"

    assert client.delete(url, headers=headers).status_code == 204
    assert client.get(url, headers=headers).status_code == 404
    assert client.delete(url, headers=headers).status_code == 404


def test_add_list_and_remove_items(client: TestClient, headers: dict[str, str]) -> None:
    collection = _create(client, headers)
    first = _import_entry(client, headers, 1000001)
    second = _import_entry(client, headers, 1000002)
    items = f"/collections/entries/{collection['id']}/items"

    for entry_id in (first, second, first):
        response = client.put(f"{items}/{entry_id}", headers=headers)
        assert response.status_code == 204

    listed = client.get(items, headers=headers).json()
    assert [item["id"] for item in listed] == [first, second]
    page = client.get(items, params={"limit": 1, "offset": 1}, headers=headers)
    assert [item["id"] for item in page.json()] == [second]

    for _ in range(2):
        response = client.delete(f"{items}/{first}", headers=headers)
        assert response.status_code == 204
    assert [i["id"] for i in client.get(items, headers=headers).json()] == [second]


def test_kanji_items(client: TestClient, headers: dict[str, str]) -> None:
    collection = _create(client, headers, kind="kanji", name="N5")
    kanji = client.post("/library/kanji", json={"literal": "食"}, headers=headers)
    items = f"/collections/kanji/{collection['id']}/items"

    added = client.put(f"{items}/{kanji.json()['id']}", headers=headers)

    assert added.status_code == 204
    listed = client.get(items, headers=headers).json()
    assert [item["literal"] for item in listed] == ["食"]


def test_unknown_item_is_404(client: TestClient, headers: dict[str, str]) -> None:
    collection = _create(client, headers)
    response = client.put(
        f"/collections/entries/{collection['id']}/items/999", headers=headers
    )
    assert response.status_code == 404


def test_items_page_is_validated(client: TestClient, headers: dict[str, str]) -> None:
    collection = _create(client, headers)
    response = client.get(
        f"/collections/entries/{collection['id']}/items",
        params={"limit": 101},
        headers=headers,
    )
    assert response.status_code == 422


def test_another_users_collection_is_404(
    client: TestClient,
    headers: dict[str, str],
    make_token: TokenFactory,
    other_user: UserORM,
) -> None:
    collection = _create(client, headers)
    entry_id = _import_entry(client, headers, 1000001)
    theirs = bearer(make_token(str(other_user.id)))
    url = f"/collections/entries/{collection['id']}"

    assert client.get(url, headers=theirs).status_code == 404
    assert client.put(url, json={"name": "mine"}, headers=theirs).status_code == 404
    assert client.delete(url, headers=theirs).status_code == 404
    assert client.get(f"{url}/items", headers=theirs).status_code == 404
    assert client.put(f"{url}/items/{entry_id}", headers=theirs).status_code == 404


def test_requires_a_token(client: TestClient) -> None:
    assert client.get("/collections/entries").status_code == 401
    assert client.post("/collections/kanji", json={"name": "N5"}).status_code == 401


def test_cors_allows_delete(client: TestClient) -> None:
    response = client.options(
        "/collections/entries/1",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "DELETE",
            "Access-Control-Request-Headers": "Authorization",
        },
    )
    assert response.status_code == 200
