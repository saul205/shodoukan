def test_search_japanese(client):
    r = client.get("/entries/search", params={"q": "食べる"})
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 1
    assert any(e["id"] == 1000001 for e in data["items"])


def test_search_english(client):
    r = client.get("/entries/search", params={"q": "to eat"})
    assert r.status_code == 200
    assert any(e["id"] == 1000001 for e in r.json()["items"])


def test_search_missing_q(client):
    r = client.get("/entries/search")
    assert r.status_code == 422


def test_get_entry(client):
    r = client.get("/entries/1000001")
    assert r.status_code == 200
    assert r.json()["id"] == 1000001


def test_get_entry_not_found(client):
    r = client.get("/entries/9999999")
    assert r.status_code == 404


def test_get_entry_kanji(client):
    r = client.get("/entries/1000001/kanji")
    assert r.status_code == 200
    assert any(lk["literal"] == "食" for lk in r.json())


def test_entries_by_kanji(client):
    r = client.get("/entries/by-kanji/食")
    assert r.status_code == 200
    assert any(e["id"] == 1000001 for e in r.json()["items"])


def test_pagination(client):
    r = client.get("/entries/search", params={"q": "eat", "limit": 1, "offset": 0})
    assert r.status_code == 200
    assert len(r.json()["items"]) <= 1


def test_limit_max(client):
    r = client.get("/entries/search", params={"q": "eat", "limit": 200})
    assert r.status_code == 422
