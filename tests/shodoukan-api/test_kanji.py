def test_search_by_meaning(client):
    r = client.get("/kanji/search", params={"q": "water"})
    assert r.status_code == 200
    assert any(k["literal"] == "水" for k in r.json()["items"])


def test_search_by_grade(client):
    r = client.get("/kanji/search", params={"grade": 1})
    assert r.status_code == 200
    assert all(k["grade"] == 1 for k in r.json()["items"])


def test_search_no_params(client):
    r = client.get("/kanji/search")
    assert r.status_code == 422


def test_get_kanji(client):
    r = client.get("/kanji/食")
    assert r.status_code == 200
    data = r.json()
    assert data["literal"] == "食"
    assert data["grade"] == 2
    assert "ショク" in data["on_readings"]
    assert any(m["text"] == "eat" for m in data["meanings"])


def test_get_kanji_not_found(client):
    r = client.get("/kanji/X")
    assert r.status_code == 404


def test_search_by_character(client):
    r = client.get("/kanji/search", params={"q": "食"})
    assert r.status_code == 200
    assert r.json()["items"][0]["literal"] == "食"


def test_search_by_reading(client):
    r = client.get("/kanji/search", params={"q": "スイ"})
    assert r.status_code == 200
    assert any(k["literal"] == "水" for k in r.json()["items"])
