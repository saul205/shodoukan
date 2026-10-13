from typing import Any

import pytest
from fastapi.testclient import TestClient
from tokens import TokenFactory, bearer

from shodoukan_practice.infrastructure.db.orm import UserORM


@pytest.fixture
def headers(make_token: TokenFactory, user: UserORM) -> dict[str, str]:
    return bearer(make_token())


@pytest.fixture
def theirs(make_token: TokenFactory, other_user: UserORM) -> dict[str, str]:
    return bearer(make_token(str(other_user.id)))


def published_words(client: TestClient, headers: dict[str, str]) -> dict[str, Any]:
    """The user's public "verbs" with 食べる."""
    collection = client.post(
        "/collections/entries", json={"name": "verbs"}, headers=headers
    ).json()
    entry = client.post(
        "/library/entries",
        json={"entry_id": 1000001, "collection_ids": [collection["id"]]},
        headers=headers,
    )
    assert entry.status_code in (200, 201)
    response = client.put(
        f"/collections/entries/{collection['id']}/publication",
        json={"include_notes": False},
        headers=headers,
    )
    assert response.status_code == 200
    body: dict[str, Any] = response.json()
    return body


def test_publish_list_preview_and_import(
    client: TestClient, headers: dict[str, str], theirs: dict[str, str]
) -> None:
    collection = published_words(client, headers)
    assert (collection["is_public"], collection["published_version"]) == (True, 1)
    base = f"/public-collections/entries/{collection['id']}"

    listing = client.get(
        "/public-collections/entries", params={"q": "VERB"}, headers=theirs
    ).json()
    assert listing["total"] == 1
    card = listing["items"][0]
    assert (card["owner"], card["is_mine"], card["item_count"]) == ("saul", False, 1)
    assert (
        client.get(
            "/public-collections/entries", params={"owner": "mine"}, headers=theirs
        ).json()["items"]
        == []
    )

    preview = client.get(f"{base}/items", headers=theirs).json()
    assert preview["total"] == 1
    word = preview["items"][0]
    assert word["source_entry_id"] == 1000001
    assert isinstance(word["id"], int)
    assert all(isinstance(s["id"], int) for s in word["senses"])

    imported = client.post(f"{base}/import", headers=theirs)
    assert imported.status_code == 201
    body = imported.json()
    assert body["created"] == 1
    assert body["collection"]["source_collection_id"] == collection["id"]
    assert body["collection"]["source_version"] == 1
    detail = client.get(base, headers=theirs).json()
    assert (detail["downloads"], detail["imported_version"]) == (1, 1)


def test_private_collections_are_not_found(
    client: TestClient, headers: dict[str, str], theirs: dict[str, str]
) -> None:
    collection = published_words(client, headers)
    base = f"/public-collections/entries/{collection['id']}"
    unpublished = client.delete(
        f"/collections/entries/{collection['id']}/publication", headers=headers
    )
    assert unpublished.json()["is_public"] is False

    assert client.get(base, headers=theirs).status_code == 404
    assert client.get(f"{base}/items", headers=theirs).status_code == 404
    assert client.post(f"{base}/import", headers=theirs).status_code == 404
    # Only its owner can publish it.
    again = client.put(
        f"/collections/entries/{collection['id']}/publication",
        json={},
        headers=theirs,
    )
    assert again.status_code == 404


def test_kanji_collections_are_shared_too(
    client: TestClient, headers: dict[str, str], theirs: dict[str, str]
) -> None:
    collection = client.post(
        "/collections/kanji", json={"name": "N4"}, headers=headers
    ).json()
    client.post(
        "/library/kanji",
        json={"literal": "食", "collection_ids": [collection["id"]]},
        headers=headers,
    )
    client.put(
        f"/collections/kanji/{collection['id']}/publication", json={}, headers=headers
    )
    base = f"/public-collections/kanji/{collection['id']}"

    preview = client.get(f"{base}/items", headers=theirs).json()
    assert [k["literal"] for k in preview["items"]] == ["食"]
    imported = client.post(f"{base}/import", headers=theirs).json()
    assert (imported["created"], imported["missing"]) == (1, [])


def test_a_copy_shows_and_applies_its_sources_new_version(
    client: TestClient, headers: dict[str, str], theirs: dict[str, str]
) -> None:
    source = published_words(client, headers)
    copy = client.post(
        f"/public-collections/entries/{source['id']}/import", headers=theirs
    ).json()["collection"]
    assert copy["latest_source_version"] is None  # only lists and gets fill it

    client.put(
        f"/collections/entries/{source['id']}/publication", json={}, headers=headers
    )
    fetched = client.get(f"/collections/entries/{copy['id']}", headers=theirs).json()
    assert (fetched["source_version"], fetched["latest_source_version"]) == (1, 2)
    listed = client.get("/collections/entries", headers=theirs).json()
    assert [c["latest_source_version"] for c in listed] == [2]

    updated = client.post(f"/collections/entries/{copy['id']}/update", headers=theirs)
    assert updated.status_code == 200
    body = updated.json()
    assert (body["existing"], body["removed"]) == (1, 0)
    assert body["collection"]["source_version"] == 2

    client.delete(f"/collections/entries/{source['id']}/publication", headers=headers)
    gone = client.post(f"/collections/entries/{copy['id']}/update", headers=theirs)
    assert gone.status_code == 404
