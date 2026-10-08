from sqlalchemy import select

from app.models.organization_member import OrganizationMember
from app.models.role import Role


def test_user_can_list_own_organization(client, auth_headers, registered_user):
    org_id = registered_user[1]["organization_id"]
    response = client.get("/api/v1/organizations", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["id"] == org_id


def test_user_cannot_read_another_organization(client, auth_headers, second_user):
    other_org_id = second_user[1]["organization_id"]
    response = client.get(
        f"/api/v1/organizations/{other_org_id}",
        headers=auth_headers,
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "ORGANIZATION_NOT_FOUND"


def test_owner_can_add_user_to_organization(client, db, auth_headers, registered_user, second_user):
    role_id = db.scalar(select(Role.id).where(Role.name == "Team Member"))
    org_id = registered_user[1]["organization_id"]
    member_user_id = second_user[1]["user"]["id"]
    response = client.post(
        f"/api/v1/organizations/{org_id}/members",
        headers=auth_headers,
        json={"user_id": member_user_id, "role_id": role_id},
    )
    assert response.status_code == 201, response.text
    assert response.json()["user_id"] == member_user_id
    assert response.json()["role"] == "Team Member"


def test_viewer_cannot_create_project(client, db, registered_user, second_user):
    owner_payload, owner_data = registered_user
    viewer_id = second_user[1]["user"]["id"]
    org_id = owner_data["organization_id"]
    viewer_role_id = db.scalar(select(Role.id).where(Role.name == "Viewer"))

    # The second registration creates its own organization. Deactivate that
    # membership first so login has exactly one active organization/role.
    db.query(OrganizationMember).filter(
        OrganizationMember.user_id == viewer_id
    ).update({"is_active": False})
    db.commit()

    add = client.post(
        f"/api/v1/organizations/{org_id}/members",
        headers={"Authorization": f"Bearer {client.post('/api/v1/auth/login', json={'email': owner_payload['email'], 'password': owner_payload['password']}).json()['tokens']['access_token']}"},
        json={"user_id": viewer_id, "role_id": viewer_role_id},
    )
    assert add.status_code == 201

    viewer_login = client.post(
        "/api/v1/auth/login",
        json={"email": "member@example.com", "password": "StrongPass123!"},
    )
    token = viewer_login.json()["tokens"]["access_token"]
    response = client.post(
        f"/api/v1/organizations/{org_id}/projects",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Should Fail"},
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "PERMISSION_DENIED"
