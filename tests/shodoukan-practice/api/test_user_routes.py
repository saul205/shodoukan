from uuid import uuid4

from fastapi.testclient import TestClient
from tokens import TokenFactory, bearer

from shodoukan_practice.infrastructure.db.orm import UserORM


def test_me_returns_the_current_user(
    client: TestClient, make_token: TokenFactory, user: UserORM
) -> None:
    response = client.get("/users/me", headers=bearer(make_token()))

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(user.id)
    assert body["username"] == "saul"
    assert body["created_at"].endswith("Z")


def test_me_creates_the_user_on_first_request(
    client: TestClient, make_token: TokenFactory
) -> None:
    provider_id = uuid4()
    headers = bearer(make_token(str(provider_id), preferred_username="newbie"))

    first = client.get("/users/me", headers=headers)
    again = client.get("/users/me", headers=headers)

    assert first.status_code == 200
    assert first.json()["id"] == str(provider_id)
    assert first.json()["username"] == "newbie"
    assert again.json()["id"] == first.json()["id"]


def test_non_uuid_subject_is_401(client: TestClient, make_token: TokenFactory) -> None:
    response = client.get("/users/me", headers=bearer(make_token("auth0|abc123")))
    assert response.status_code == 401


def test_me_requires_a_token(client: TestClient) -> None:
    response = client.get("/users/me")

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_openapi_declares_the_keycloak_login(client: TestClient) -> None:
    schemes = client.get("/openapi.json").json()["components"]["securitySchemes"]
    flow = next(iter(schemes.values()))["flows"]["authorizationCode"]

    assert flow["authorizationUrl"].endswith("/protocol/openid-connect/auth")
    assert flow["tokenUrl"].endswith("/protocol/openid-connect/token")
