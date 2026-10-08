def test_cross_organization_chat_is_allowed_by_design(client, auth_headers, second_user):
    other_id = second_user[1]["user"]["id"]

    search = client.get(
        "/api/v1/chat/users/search",
        headers=auth_headers,
        params={"q": "Tenant Member"},
    )
    assert search.status_code == 200
    assert any(user["id"] == other_id for user in search.json())

    room = client.post(
        "/api/v1/chat/rooms",
        headers=auth_headers,
        json={"participant_user_id": other_id},
    )
    assert room.status_code == 201, room.text
    room_id = room.json()["id"]

    rooms = client.get("/api/v1/chat/rooms", headers=auth_headers)
    assert rooms.status_code == 200
    assert any(item["id"] == room_id for item in rooms.json()["items"])

    message = client.post(
        f"/api/v1/chat/rooms/{room_id}/messages",
        headers=auth_headers,
        json={"body": "Hello"},
    )
    assert message.status_code == 201, message.text
    assert message.json()["body"] == "Hello"


def test_chat_rejects_self_chat(client, auth_headers, registered_user):
    user_id = registered_user[1]["user"]["id"]
    response = client.post(
        "/api/v1/chat/rooms",
        headers=auth_headers,
        json={"participant_user_id": user_id},
    )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "INVALID_PARTICIPANT"


def test_non_participant_cannot_read_chat(client, auth_headers, second_user):
    other_id = second_user[1]["user"]["id"]
    room = client.post(
        "/api/v1/chat/rooms",
        headers=auth_headers,
        json={"participant_user_id": other_id},
    )
    room_id = room.json()["id"]

    # The current user is a participant; create a third user who is not.
    third = client.post(
        "/api/v1/auth/register",
        json={
            "email": "third@example.com",
            "password": "StrongPass123!",
            "full_name": "Third User",
            "organization_name": "Tenant Three",
        },
    )
    assert third.status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "third@example.com", "password": "StrongPass123!"},
    )
    third_token = login.json()["tokens"]["access_token"]

    response = client.get(
        f"/api/v1/chat/rooms/{room_id}/messages",
        headers={"Authorization": f"Bearer {third_token}"},
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "ROOM_ACCESS_DENIED"
