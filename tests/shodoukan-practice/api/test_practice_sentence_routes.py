from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from tokens import TokenFactory, bearer

from shodoukan_practice.domain.entities import PracticeSentence
from shodoukan_practice.infrastructure.db.orm import UserORM
from shodoukan_practice.infrastructure.repositories import (
    SqlAlchemyPracticeSentenceRepository,
)

URL = "/library/sentences"
ATE = "昨日パンを食べた。"


@pytest.fixture
def headers(make_token: TokenFactory, user: UserORM) -> dict[str, str]:
    return bearer(make_token())


@pytest.fixture
def entry(client: TestClient, headers: dict[str, str]) -> dict[str, Any]:
    """食べる, from the test dictionary."""
    response = client.post(
        "/library/entries", json={"entry_id": 1000001}, headers=headers
    )
    body: dict[str, Any] = response.json()
    return body


def add(
    client: TestClient, headers: dict[str, str], japanese: str, **extra: Any
) -> dict[str, Any]:
    response = client.post(
        URL,
        json={"japanese": japanese, "translation": "I ate.", "lang": "eng", **extra},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


def test_add_a_sentence_linked_to_a_word(
    client: TestClient, headers: dict[str, str], entry: dict[str, Any]
) -> None:
    sentence = add(client, headers, ATE, entry_id=entry["id"])

    [word] = sentence["words"]
    assert sentence["origin"] == "added"
    assert sentence["translations"] == [{"lang": "eng", "text": "I ate."}]
    # The gap is where the word is, inflected: 食べた.
    assert ATE[word["start"] : word["end"]] == "食べた"
    assert word["entry_id"] == entry["id"]
    assert word["lemma"] == "食べる"
    assert word["reading"] == "たべた"
    assert word["inflection"] == {"endings": ["た"], "form": "終止形"}


def test_the_sentences_of_a_word_and_searching(
    client: TestClient, headers: dict[str, str], entry: dict[str, Any]
) -> None:
    linked = add(client, headers, ATE, entry_id=entry["id"])
    unlinked = add(client, headers, "雨が降った。")

    by_word = client.get(URL, params={"entry_id": entry["id"]}, headers=headers)
    alone = client.get(URL, params={"linked": False}, headers=headers)
    by_text = client.get(URL, params={"q": "パン"}, headers=headers)
    by_translation = client.get(URL, params={"q": "ATE"}, headers=headers)

    assert [s["id"] for s in by_word.json()["items"]] == [linked["id"]]
    assert [s["id"] for s in alone.json()["items"]] == [unlinked["id"]]
    assert by_text.json()["total"] == 1
    assert by_translation.json()["total"] == 2  # "I ate.", any case
    everything = client.get(URL, headers=headers).json()
    assert [s["id"] for s in everything["items"]] == [unlinked["id"], linked["id"]]


def test_analyze_then_add_in_bulk(
    client: TestClient, headers: dict[str, str], entry: dict[str, Any]
) -> None:
    analyzed = client.post(
        f"{URL}/analyze", json={"texts": [ATE, "猫がいる。"]}, headers=headers
    )

    assert analyzed.status_code == 200
    ate, cat = analyzed.json()
    [word] = ate["words"]
    assert ATE[word["start"] : word["end"]] == "食べた"
    assert (word["form"], word["entry_ids"], word["certain"]) == (
        "食べる",
        [entry["id"]],
        True,
    )
    assert "".join(m["surface"] for m in ate["morphemes"]) == ATE
    assert cat["words"] == []

    saved = client.post(
        f"{URL}/batch",
        json={
            "sentences": [
                {
                    "japanese": ATE,
                    "translation": None,
                    "lang": "eng",
                    "words": [
                        {
                            "start": word["start"],
                            "end": word["end"],
                            "entry_id": entry["id"],
                        }
                    ],
                },
                {"japanese": "猫がいる。", "lang": "eng"},
            ]
        },
        headers=headers,
    )

    assert saved.status_code == 201, saved.text
    first, second = saved.json()
    assert first["words"][0]["lemma"] == "食べる"  # analyzed when stored
    assert second["words"] == []


def test_a_bulk_add_with_a_foreign_word_stores_nothing(
    client: TestClient, headers: dict[str, str]
) -> None:
    response = client.post(
        f"{URL}/batch",
        json={
            "sentences": [
                {"japanese": ATE, "lang": "eng", "words": [{"entry_id": 999}]}
            ]
        },
        headers=headers,
    )

    assert response.status_code == 404
    assert client.get(URL, headers=headers).json()["total"] == 0


def test_rewrite_and_words(
    client: TestClient, headers: dict[str, str], entry: dict[str, Any]
) -> None:
    sentence = add(client, headers, ATE, entry_id=entry["id"])
    url = f"{URL}/{sentence['id']}"
    word_id = sentence["words"][0]["id"]

    rewritten = client.put(
        url,
        json={"japanese": "今日もパンを食べた。", "translation": None, "lang": "eng"},
        headers=headers,
    ).json()
    [moved] = rewritten["words"]
    assert rewritten["text"][moved["start"] : moved["end"]] == "食べた"
    assert rewritten["translations"] == []

    bread = client.post(
        f"{url}/words", json={"start": 3, "end": 5}, headers=headers
    ).json()
    assert [w["start"] for w in bread["words"]] == [6, 3]
    bread_id = bread["words"][1]["id"]
    assert bread["words"][1]["lemma"] == "パン"  # analyzed, not linked

    overlapping = client.post(
        f"{url}/words", json={"start": 4, "end": 8}, headers=headers
    )
    corrected = client.put(
        f"{url}/words/{word_id}/correction",
        json={"lemma": "食べる", "reading": "くった"},
        headers=headers,
    )
    unlinked = client.put(
        f"{url}/words/{word_id}/link", json={"entry_id": None}, headers=headers
    )
    removed = client.delete(f"{url}/words/{bread_id}", headers=headers)

    assert overlapping.status_code == 422
    assert corrected.json()["words"][0]["reading"] == "くった"
    assert unlinked.json()["words"][0]["entry_id"] is None
    assert [w["id"] for w in removed.json()["words"]] == [word_id]


def test_active_notes_and_removal(client: TestClient, headers: dict[str, str]) -> None:
    sentence = add(client, headers, ATE)
    url = f"{URL}/{sentence['id']}"

    inactive = client.put(f"{url}/active", json={"active": False}, headers=headers)
    noted = client.put(f"{url}/notes", json={"notes": " casual "}, headers=headers)
    deleted = client.delete(url, headers=headers)

    assert inactive.json()["is_active"] is False
    assert noted.json()["notes"] == "casual"
    assert deleted.status_code == 204
    assert client.get(url, headers=headers).status_code == 404


def test_a_dictionary_sentence_is_only_deactivated(
    client: TestClient,
    headers: dict[str, str],
    session: Session,
    user: UserORM,
) -> None:
    sentence = SqlAlchemyPracticeSentenceRepository(session).add(
        PracticeSentence.from_dictionary(
            user.id, ATE, [], word="", entry_id=None, sense_id=None
        )
    )
    session.commit()

    response = client.delete(f"{URL}/{sentence.id}", headers=headers)

    assert response.status_code == 409


def test_another_users_sentence_is_not_found(
    client: TestClient,
    headers: dict[str, str],
    make_token: TokenFactory,
    other_user: UserORM,
) -> None:
    sentence = add(client, headers, ATE)
    theirs = bearer(make_token(sub=str(other_user.id)))

    assert client.get(f"{URL}/{sentence['id']}", headers=theirs).status_code == 404
    assert client.delete(f"{URL}/{sentence['id']}", headers=theirs).status_code == 404


def test_a_word_of_another_user_cant_be_linked(
    client: TestClient,
    headers: dict[str, str],
    make_token: TokenFactory,
    other_user: UserORM,
    entry: dict[str, Any],
) -> None:
    theirs = bearer(make_token(sub=str(other_user.id)))

    response = client.post(
        URL,
        json={"japanese": ATE, "lang": "eng", "entry_id": entry["id"]},
        headers=theirs,
    )

    assert response.status_code == 404
