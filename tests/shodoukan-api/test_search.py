def test_search_single_kanji(client):
    r = client.get("/search", params={"q": "食"})
    assert r.status_code == 200
    data = r.json()
    assert any(k["literal"] == "食" for k in data["kanji"])
    assert any(e["id"] == 1000001 for e in data["entries"]["items"])


def test_search_kana(client):
    r = client.get("/search", params={"q": "みず"})
    assert r.status_code == 200
    data = r.json()
    assert any(e["id"] == 1000002 for e in data["entries"]["items"])
    assert any(k["literal"] == "水" for k in data["kanji"])


def test_search_translation(client):
    r = client.get("/search", params={"q": "water"})
    assert r.status_code == 200
    data = r.json()
    assert any(e["id"] == 1000002 for e in data["entries"]["items"])
    assert any(k["literal"] == "水" for k in data["kanji"])


def test_search_missing_q(client):
    r = client.get("/search")
    assert r.status_code == 422


def test_search_limit_max(client):
    r = client.get("/search", params={"q": "eat", "limit": 200})
    assert r.status_code == 422
