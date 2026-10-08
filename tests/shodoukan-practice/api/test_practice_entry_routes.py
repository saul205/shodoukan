from typing import Any

import pytest
from fastapi.testclient import TestClient
from tokens import TokenFactory, bearer

from shodoukan_practice.infrastructure.db.orm import UserORM


@pytest.fixture
def headers(make_token: TokenFactory, user: UserORM) -> dict[str, str]:
    return bearer(make_token())


@pytest.fixture
def entry(client: TestClient, headers: dict[str, str]) -> dict[str, Any]:
    response = client.post(
        "/library/entries", json={"entry_id": 1000001}, headers=headers
    )
    body: dict[str, Any] = response.json()
    return body


def test_get_returns_the_copy_with_notes(
    client: TestClient, headers: dict[str, str], entry: dict[str, Any]
) -> None:
    response = client.get(f"/library/entries/{entry['id']}", headers=headers)

    assert response.status_code == 200
    assert response.json() == entry
    assert entry["notes"] is None
    assert entry["senses"][0]["notes"] is None


def test_notes(
    client: TestClient, headers: dict[str, str], entry: dict[str, Any]
) -> None:
    url = f"/library/entries/{entry['id']}"
    sense_id = entry["senses"][0]["id"]

    general = client.put(f"{url}/notes", json={"notes": " ichidan "}, headers=headers)
    sense = client.put(
        f"{url}/senses/{sense_id}/notes", json={"notes": "casual"}, headers=headers
    )
    cleared = client.put(f"{url}/notes", json={"notes": None}, headers=headers)
    too_long = client.put(f"{url}/notes", json={"notes": "x" * 2001}, headers=headers)

    assert general.json()["notes"] == "ichidan"
    assert sense.json()["senses"][0]["notes"] == "casual"
    assert cleared.json()["notes"] is None
    assert too_long.status_code == 422


def test_active_and_enabled(
    client: TestClient, headers: dict[str, str], entry: dict[str, Any]
) -> None:
    url = f"/library/entries/{entry['id']}"
    gloss_id = entry["senses"][0]["glosses"][0]["id"]
    reading_id = entry["kanji_readings"][0]["id"]

    inactive = client.put(f"{url}/active", json={"active": False}, headers=headers)
    gloss = client.put(
        f"{url}/glosses/{gloss_id}/enabled", json={"enabled": False}, headers=headers
    )
    spelling = client.put(
        f"{url}/kanji-readings/{reading_id}/enabled",
        json={"enabled": False},
        headers=headers,
    )

    assert inactive.json()["is_active"] is False
    assert gloss.json()["senses"][0]["glosses"][0]["enabled"] is False
    assert spelling.json()["kanji_readings"][0]["enabled"] is False


def test_unknown_part_or_item(
    client: TestClient, headers: dict[str, str], entry: dict[str, Any]
) -> None:
    url = f"/library/entries/{entry['id']}"
    body = {"enabled": False}
    assert (
        client.put(f"{url}/notes/1/enabled", json=body, headers=headers).status_code
        == 422
    )
    assert (
        client.put(f"{url}/glosses/999/enabled", json=body, headers=headers).status_code
        == 404
    )


def test_own_meanings(
    client: TestClient, headers: dict[str, str], entry: dict[str, Any]
) -> None:
    url = f"/library/entries/{entry['id']}"
    sense_id = entry["senses"][0]["id"]

    added = client.post(
        f"{url}/senses/{sense_id}/glosses",
        json={"text": " to scoff ", "lang": "eng"},
        headers=headers,
    )
    assert added.status_code == 201
    gloss = added.json()["senses"][0]["glosses"][-1]
    assert (gloss["text"], gloss["origin"]) == ("to scoff", "added")

    edited = client.put(
        f"{url}/glosses/{gloss['id']}", json={"text": "to gobble"}, headers=headers
    )
    assert edited.json()["senses"][0]["glosses"][-1]["text"] == "to gobble"

    removed = client.delete(f"{url}/glosses/{gloss['id']}", headers=headers)
    assert removed.status_code == 200
    assert len(removed.json()["senses"][0]["glosses"]) == 2


def test_own_senses(
    client: TestClient, headers: dict[str, str], entry: dict[str, Any]
) -> None:
    url = f"/library/entries/{entry['id']}"
    imported_id = entry["senses"][0]["id"]
    assert (entry["senses"][0]["enabled"], entry["senses"][0]["origin"]) == (
        True,
        "imported",
    )

    added = client.post(
        f"{url}/senses", json={"text": " to dine ", "lang": "eng"}, headers=headers
    )
    assert added.status_code == 201
    sense = added.json()["senses"][-1]
    assert sense["origin"] == "added"
    assert [g["text"] for g in sense["glosses"]] == ["to dine"]

    hidden = client.put(
        f"{url}/senses/{imported_id}/enabled", json={"enabled": False}, headers=headers
    )
    assert hidden.json()["senses"][0]["enabled"] is False

    removed = client.delete(f"{url}/senses/{sense['id']}", headers=headers)
    assert removed.status_code == 200
    assert [s["id"] for s in removed.json()["senses"]] == [imported_id]
    assert (
        client.delete(f"{url}/senses/{imported_id}", headers=headers).status_code == 409
    )
    assert (
        client.post(
            f"{url}/senses", json={"text": " ", "lang": "eng"}, headers=headers
        ).status_code
        == 422
    )


def test_own_spellings_and_readings(
    client: TestClient, headers: dict[str, str], entry: dict[str, Any]
) -> None:
    url = f"/library/entries/{entry['id']}"
    imported_reading = entry["readings"][0]["id"]

    spelling = client.post(
        f"{url}/kanji-readings", json={"kanji": "喰べる"}, headers=headers
    )
    reading = client.post(f"{url}/readings", json={"text": "クウ"}, headers=headers)
    assert (spelling.status_code, reading.status_code) == (201, 201)
    own_spelling = spelling.json()["kanji_readings"][-1]
    own_reading = reading.json()["readings"][-1]
    assert (own_spelling["origin"], own_reading["origin"]) == ("added", "added")

    assert (
        client.post(
            f"{url}/readings", json={"text": "kuu"}, headers=headers
        ).status_code
        == 422
    )
    assert (
        client.delete(f"{url}/readings/{imported_reading}", headers=headers).status_code
        == 409
    )
    client.delete(f"{url}/kanji-readings/{own_spelling['id']}", headers=headers)
    removed = client.delete(f"{url}/readings/{own_reading['id']}", headers=headers)
    assert removed.status_code == 200
    assert all(r["origin"] == "imported" for r in removed.json()["readings"])
    assert all(k["origin"] == "imported" for k in removed.json()["kanji_readings"])


def test_an_own_word_keeps_its_last_reading(
    client: TestClient, headers: dict[str, str]
) -> None:
    own = client.post(
        "/library/entries/own",
        json={"readings": ["ねこ"], "meaning": "cat", "lang": "eng"},
        headers=headers,
    ).json()
    reading_id = own["readings"][0]["id"]

    response = client.delete(
        f"/library/entries/{own['id']}/readings/{reading_id}", headers=headers
    )

    assert response.status_code == 409


def test_meaning_validation(
    client: TestClient, headers: dict[str, str], entry: dict[str, Any]
) -> None:
    url = f"/library/entries/{entry['id']}/senses/{entry['senses'][0]['id']}/glosses"
    for body in ({"text": "  ", "lang": "eng"}, {"text": "x", "lang": "en"}):
        assert client.post(url, json=body, headers=headers).status_code == 422


def test_dictionary_meanings_are_409(
    client: TestClient, headers: dict[str, str], entry: dict[str, Any]
) -> None:
    gloss_id = entry["senses"][0]["glosses"][0]["id"]
    url = f"/library/entries/{entry['id']}/glosses/{gloss_id}"

    edited = client.put(url, json={"text": "x"}, headers=headers)
    removed = client.delete(url, headers=headers)

    assert (edited.status_code, removed.status_code) == (409, 409)


def test_collections_and_remove(
    client: TestClient, headers: dict[str, str], entry: dict[str, Any]
) -> None:
    url = f"/library/entries/{entry['id']}"
    verbs = client.post(
        "/collections/entries", json={"name": "verbs"}, headers=headers
    ).json()
    client.put(
        f"/collections/entries/{verbs['id']}/items/{entry['id']}", headers=headers
    )

    tags = client.get(f"{url}/collections", headers=headers).json()
    assert [c["name"] for c in tags] == ["verbs"]

    assert client.delete(url, headers=headers).status_code == 204
    assert client.get(url, headers=headers).status_code == 404
    items = client.get(
        f"/collections/entries/{verbs['id']}/items", headers=headers
    ).json()
    assert items["total"] == 0


def test_another_users_entry_is_404(
    client: TestClient,
    entry: dict[str, Any],
    make_token: TokenFactory,
    other_user: UserORM,
) -> None:
    theirs = bearer(make_token(str(other_user.id)))
    url = f"/library/entries/{entry['id']}"

    assert client.get(url, headers=theirs).status_code == 404
    assert (
        client.put(f"{url}/notes", json={"notes": "x"}, headers=theirs).status_code
        == 404
    )
    assert client.delete(url, headers=theirs).status_code == 404


def test_requires_a_token(client: TestClient, entry: dict[str, Any]) -> None:
    assert client.get(f"/library/entries/{entry['id']}").status_code == 401
