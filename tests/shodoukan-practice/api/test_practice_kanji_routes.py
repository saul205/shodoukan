from typing import Any

import pytest
from fastapi.testclient import TestClient
from tokens import TokenFactory, bearer

from shodoukan_practice.infrastructure.db.orm import UserORM


@pytest.fixture
def headers(make_token: TokenFactory, user: UserORM) -> dict[str, str]:
    return bearer(make_token())


@pytest.fixture
def kanji(client: TestClient, headers: dict[str, str]) -> dict[str, Any]:
    response = client.post("/library/kanji", json={"literal": "食"}, headers=headers)
    body: dict[str, Any] = response.json()
    return body


def test_get_notes_active_and_enabled(
    client: TestClient, headers: dict[str, str], kanji: dict[str, Any]
) -> None:
    url = f"/library/kanji/{kanji['id']}"
    kun_id = kanji["kun_readings"][0]["id"]
    meaning_id = kanji["meanings"][0]["id"]

    assert client.get(url, headers=headers).json() == kanji
    noted = client.put(f"{url}/notes", json={"notes": "radical"}, headers=headers)
    inactive = client.put(f"{url}/active", json={"active": False}, headers=headers)
    kun = client.put(
        f"{url}/readings/{kun_id}/enabled", json={"enabled": False}, headers=headers
    )
    meaning = client.put(
        f"{url}/meanings/{meaning_id}/enabled", json={"enabled": False}, headers=headers
    )

    assert noted.json()["notes"] == "radical"
    assert inactive.json()["is_active"] is False
    assert kun.json()["kun_readings"][0]["enabled"] is False
    assert meaning.json()["meanings"][0]["enabled"] is False


def test_own_meanings(
    client: TestClient, headers: dict[str, str], kanji: dict[str, Any]
) -> None:
    url = f"/library/kanji/{kanji['id']}"

    added = client.post(
        f"{url}/meanings", json={"text": "meal", "lang": "en"}, headers=headers
    )
    assert added.status_code == 201
    meaning = added.json()["meanings"][-1]
    assert meaning["origin"] == "added"

    edited = client.put(
        f"{url}/meanings/{meaning['id']}", json={"text": "dish"}, headers=headers
    )
    removed = client.delete(f"{url}/meanings/{meaning['id']}", headers=headers)

    assert edited.json()["meanings"][-1]["text"] == "dish"
    assert [m["text"] for m in removed.json()["meanings"]] == ["eat", "food"]
    bad_lang = client.post(
        f"{url}/meanings", json={"text": "x", "lang": "eng"}, headers=headers
    )
    assert bad_lang.status_code == 422


def test_dictionary_meanings_are_409(
    client: TestClient, headers: dict[str, str], kanji: dict[str, Any]
) -> None:
    url = f"/library/kanji/{kanji['id']}/meanings/{kanji['meanings'][0]['id']}"
    assert client.put(url, json={"text": "x"}, headers=headers).status_code == 409
    assert client.delete(url, headers=headers).status_code == 409


def test_collections_and_remove(
    client: TestClient, headers: dict[str, str], kanji: dict[str, Any]
) -> None:
    url = f"/library/kanji/{kanji['id']}"
    n5 = client.post("/collections/kanji", json={"name": "N5"}, headers=headers).json()
    client.put(f"/collections/kanji/{n5['id']}/items/{kanji['id']}", headers=headers)

    assert [
        c["name"] for c in client.get(f"{url}/collections", headers=headers).json()
    ] == ["N5"]
    assert client.delete(url, headers=headers).status_code == 204
    assert client.get(url, headers=headers).status_code == 404


def test_another_users_kanji_is_404(
    client: TestClient,
    kanji: dict[str, Any],
    make_token: TokenFactory,
    other_user: UserORM,
) -> None:
    theirs = bearer(make_token(str(other_user.id)))
    assert (
        client.get(f"/library/kanji/{kanji['id']}", headers=theirs).status_code == 404
    )
