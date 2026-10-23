from shodoukan.db.download import _api_headers


def test_api_headers_without_token(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    assert _api_headers() == {}


def test_api_headers_with_token(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "abc")
    assert _api_headers() == {"Authorization": "Bearer abc"}
