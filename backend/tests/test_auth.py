def test_register_login_and_me(client, registered_user):
    payload, registered = registered_user
    assert registered["user"]["email"] == payload["email"]
    assert registered["role"] == "Organization Admin"

    login = client.post(
        "/api/v1/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    assert login.status_code == 200
    body = login.json()
    assert body["tokens"]["access_token"]
    assert body["tokens"]["refresh_token"]

    me = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {body['tokens']['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["email"] == payload["email"]


def test_duplicate_registration_is_rejected(client, registered_user):
    payload, _ = registered_user
    duplicate = dict(payload)
    duplicate["organization_name"] = "Another Organization"
    response = client.post("/api/v1/auth/register", json=duplicate)
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "REGISTRATION_CONFLICT"


def test_invalid_login_is_rejected(client, registered_user):
    payload, _ = registered_user
    response = client.post(
        "/api/v1/auth/login",
        json={"email": payload["email"], "password": "WrongPassword!"},
    )
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "INVALID_CREDENTIALS"


def test_protected_endpoint_requires_authentication(client):
    response = client.get("/api/v1/organizations")
    assert response.status_code == 401


def test_refresh_rotates_refresh_token(client, registered_user):
    payload, _ = registered_user
    login = client.post(
        "/api/v1/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    refresh = login.json()["tokens"]["refresh_token"]
    response = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert response.status_code == 200
    assert response.json()["access_token"]
    assert response.json()["refresh_token"] != refresh


def test_logout_revokes_refresh_token(client, registered_user):
    payload, _ = registered_user
    login = client.post(
        "/api/v1/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    refresh = login.json()["tokens"]["refresh_token"]
    logout = client.post("/api/v1/auth/logout", json={"refresh_token": refresh})
    assert logout.status_code == 200
    again = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert again.status_code == 401
