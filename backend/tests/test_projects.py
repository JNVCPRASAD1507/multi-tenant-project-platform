def test_project_crud_and_tenant_isolation(client, auth_headers, registered_user, second_user):
    org1 = registered_user[1]["organization_id"]
    org2 = second_user[1]["organization_id"]

    create1 = client.post(
        f"/api/v1/organizations/{org1}/projects",
        headers=auth_headers,
        json={"name": "Tenant One Project", "description": "Private"},
    )
    assert create1.status_code == 201, create1.text
    project = create1.json()
    assert project["organization_id"] == org1

    own = client.get(f"/api/v1/organizations/{org1}/projects", headers=auth_headers)
    assert own.status_code == 200
    assert own.json()["total"] == 1

    foreign = client.get(f"/api/v1/organizations/{org2}/projects", headers=auth_headers)
    assert foreign.status_code == 404

    foreign_project = client.get(
        f"/api/v1/organizations/{org2}/projects/{project['id']}",
        headers=auth_headers,
    )
    assert foreign_project.status_code == 404


def test_project_update_and_soft_delete(client, auth_headers, registered_user):
    org_id = registered_user[1]["organization_id"]
    create = client.post(
        f"/api/v1/organizations/{org_id}/projects",
        headers=auth_headers,
        json={"name": "Original"},
    )
    project_id = create.json()["id"]

    update = client.put(
        f"/api/v1/organizations/{org_id}/projects/{project_id}",
        headers=auth_headers,
        json={"name": "Updated", "status": "completed"},
    )
    assert update.status_code == 200
    assert update.json()["name"] == "Updated"
    assert update.json()["status"] == "completed"

    delete = client.delete(
        f"/api/v1/organizations/{org_id}/projects/{project_id}",
        headers=auth_headers,
    )
    assert delete.status_code == 200
    assert delete.json()["is_active"] is False
    assert delete.json()["status"] == "archived"
