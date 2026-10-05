from typing import Any

import pytest
from fastapi.testclient import TestClient
from tokens import TokenFactory, bearer

from shodoukan_practice.infrastructure.db.orm import UserORM

WORD_SETTINGS = {
    "type": "card.choice",
    "directions": [
        {"prompt": ["meaning"], "answer": "writing"},
        {"prompt": ["writing"], "answer": "meaning"},
    ],
    "back_fields": ["reading"],
}
KANJI_SETTINGS = {
    "type": "card.choice",
    "directions": [
        {"prompt": ["literal"], "answer": "kunyomi"},
        {"prompt": ["literal"], "answer": "onyomi"},
        {"prompt": ["kunyomi"], "answer": "literal"},
    ],
    "back_fields": ["meaning"],
    "option_count": 4,
}


@pytest.fixture
def headers(make_token: TokenFactory, user: UserORM) -> dict[str, str]:
    return bearer(make_token())


def _collection(
    client: TestClient, headers: dict[str, str], kind: str, name: str
) -> int:
    response = client.post(f"/collections/{kind}", json={"name": name}, headers=headers)
    collection_id: int = response.json()["id"]
    return collection_id


def _body(collection_ids: list[int], **overrides: Any) -> dict[str, Any]:
    return {
        "item_kind": "entries",
        "name": "Verbs",
        "collection_ids": collection_ids,
        "settings": WORD_SETTINGS,
        **overrides,
    }


def _create(
    client: TestClient, headers: dict[str, str], body: dict[str, Any]
) -> dict[str, Any]:
    response = client.post("/exercises", json=body, headers=headers)
    assert response.status_code == 201, response.json()
    result: dict[str, Any] = response.json()
    return result


def test_create_and_get(client: TestClient, headers: dict[str, str]) -> None:
    verbs = _collection(client, headers, "entries", "verbs")

    created = _create(client, headers, _body([verbs], name="  Verbs  "))

    assert created["name"] == "Verbs"
    assert created["item_kind"] == "entries"
    assert created["collection_ids"] == [verbs]
    assert created["settings"] == {
        **WORD_SETTINGS,
        "option_count": 4,
        "distractor_source": "collection",
    }
    assert created["created_at"].endswith("Z")
    assert "user_id" not in created
    fetched = client.get(f"/exercises/{created['id']}", headers=headers)
    assert fetched.json() == created


def test_kanji_exercise(client: TestClient, headers: dict[str, str]) -> None:
    n5 = _collection(client, headers, "kanji", "N5")
    created = _create(
        client,
        headers,
        _body([n5], item_kind="kanji", name="N5", settings=KANJI_SETTINGS),
    )
    assert created["item_kind"] == "kanji"
    assert created["settings"]["directions"][2] == {
        "prompt": ["kunyomi"],
        "answer": "literal",
    }


def test_list_is_by_name(client: TestClient, headers: dict[str, str]) -> None:
    verbs = _collection(client, headers, "entries", "verbs")
    _create(client, headers, _body([verbs], name="b"))
    _create(client, headers, _body([verbs], name="a"))

    listed = client.get("/exercises", headers=headers).json()

    assert [e["name"] for e in listed] == ["a", "b"]


@pytest.mark.parametrize(
    "overrides",
    [
        {"name": ""},
        {"collection_ids": []},
        {"item_kind": "sentences"},
        {"settings": {**WORD_SETTINGS, "type": "card.unknown"}},
        {"settings": {**WORD_SETTINGS, "directions": []}},
        {"settings": {**WORD_SETTINGS, "option_count": 9}},
        {
            "settings": {
                **WORD_SETTINGS,
                "directions": [{"prompt": ["reading"], "answer": "reading"}],
            }
        },
    ],
)
def test_invalid_requests_are_422(
    client: TestClient, headers: dict[str, str], overrides: dict[str, Any]
) -> None:
    verbs = _collection(client, headers, "entries", "verbs")
    response = client.post(
        "/exercises", json={**_body([verbs]), **overrides}, headers=headers
    )
    assert response.status_code == 422


def test_fields_of_the_other_kind_are_422(
    client: TestClient, headers: dict[str, str]
) -> None:
    n5 = _collection(client, headers, "kanji", "N5")
    response = client.post(
        "/exercises",
        json=_body([n5], item_kind="kanji", settings=WORD_SETTINGS),
        headers=headers,
    )
    assert response.status_code == 422
    assert "writing" in response.json()["detail"][0]["msg"]


def test_unknown_or_foreign_collection_is_404(
    client: TestClient,
    headers: dict[str, str],
    make_token: TokenFactory,
    other_user: UserORM,
) -> None:
    other = bearer(make_token(str(other_user.id)))
    theirs = _collection(client, other, "entries", "theirs")

    for collection_id in (theirs, theirs + 100):
        response = client.post(
            "/exercises", json=_body([collection_id]), headers=headers
        )
        assert response.status_code == 404


def test_another_users_exercise_is_404(
    client: TestClient,
    headers: dict[str, str],
    make_token: TokenFactory,
    other_user: UserORM,
) -> None:
    verbs = _collection(client, headers, "entries", "verbs")
    exercise = _create(client, headers, _body([verbs]))
    other = bearer(make_token(str(other_user.id)))
    url = f"/exercises/{exercise['id']}"

    assert client.get(url, headers=other).status_code == 404
    assert client.put(url, json=_body([verbs]), headers=other).status_code == 404
    assert client.delete(url, headers=other).status_code == 404
    assert client.get("/exercises", headers=other).json() == []


def test_update_replaces_but_keeps_the_kind(
    client: TestClient, headers: dict[str, str]
) -> None:
    verbs = _collection(client, headers, "entries", "verbs")
    nouns = _collection(client, headers, "entries", "nouns")
    exercise = _create(client, headers, _body([verbs]))
    settings = {
        "type": "card.choice",
        "directions": [{"prompt": ["reading"], "answer": "meaning"}],
        "option_count": 6,
    }

    response = client.put(
        f"/exercises/{exercise['id']}",
        json={
            "item_kind": "kanji",  # ignored: the kind can't change
            "name": "Words",
            "collection_ids": [nouns, verbs],
            "settings": settings,
        },
        headers=headers,
    )

    assert response.status_code == 200
    updated = response.json()
    assert updated["item_kind"] == "entries"
    assert updated["name"] == "Words"
    assert updated["description"] is None
    assert updated["collection_ids"] == [nouns, verbs]
    assert updated["settings"]["option_count"] == 6
    assert updated["settings"]["back_fields"] == []


def test_delete(client: TestClient, headers: dict[str, str]) -> None:
    verbs = _collection(client, headers, "entries", "verbs")
    exercise = _create(client, headers, _body([verbs]))
    url = f"/exercises/{exercise['id']}"

    assert client.delete(url, headers=headers).status_code == 204
    assert client.get(url, headers=headers).status_code == 404
    assert client.get("/collections/entries", headers=headers).json()[0]["id"] == verbs


def test_deleted_collection_leaves_the_exercise(
    client: TestClient, headers: dict[str, str]
) -> None:
    verbs = _collection(client, headers, "entries", "verbs")
    exercise = _create(client, headers, _body([verbs]))

    client.delete(f"/collections/entries/{verbs}", headers=headers)

    fetched = client.get(f"/exercises/{exercise['id']}", headers=headers).json()
    assert fetched["collection_ids"] == []


def test_requires_a_token(client: TestClient) -> None:
    assert client.get("/exercises").status_code == 401
