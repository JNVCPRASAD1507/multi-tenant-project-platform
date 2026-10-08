def _create_project(client, headers, org_id):
    response = client.post(
        f"/api/v1/organizations/{org_id}/projects",
        headers=headers,
        json={"name": "Task Project"},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _create_task(client, headers, org_id, project_id, **extra):
    payload = {"title": "Task One", **extra}
    response = client.post(
        f"/api/v1/organizations/{org_id}/projects/{project_id}/tasks",
        headers=headers,
        json=payload,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_task_crud_and_status_workflow(client, auth_headers, registered_user):
    org_id = registered_user[1]["organization_id"]
    project_id = _create_project(client, auth_headers, org_id)
    task = _create_task(client, auth_headers, org_id, project_id)
    task_id = task["id"]
    assert task["status"] == "backlog"

    invalid = client.post(
        f"/api/v1/organizations/{org_id}/projects/{project_id}/tasks/{task_id}/status",
        headers=auth_headers,
        json={"status": "done"},
    )
    assert invalid.status_code == 409
    assert invalid.json()["detail"]["code"] == "INVALID_STATUS_TRANSITION"

    todo = client.post(
        f"/api/v1/organizations/{org_id}/projects/{project_id}/tasks/{task_id}/status",
        headers=auth_headers,
        json={"status": "todo"},
    )
    assert todo.status_code == 200
    assert todo.json()["status"] == "todo"

    update = client.patch(
        f"/api/v1/organizations/{org_id}/projects/{project_id}/tasks/{task_id}",
        headers=auth_headers,
        json={"priority": "high", "description": "Updated"},
    )
    assert update.status_code == 200
    assert update.json()["priority"] == "high"

    listing = client.get(
        f"/api/v1/organizations/{org_id}/projects/{project_id}/tasks",
        headers=auth_headers,
    )
    assert listing.status_code == 200
    assert listing.json()["total"] == 1


def test_task_dependency_rejects_self_and_duplicate(client, auth_headers, registered_user):
    org_id = registered_user[1]["organization_id"]
    project_id = _create_project(client, auth_headers, org_id)
    first = _create_task(client, auth_headers, org_id, project_id)
    second = _create_task(client, auth_headers, org_id, project_id, title="Task Two")

    self_dep = client.post(
        f"/api/v1/organizations/{org_id}/projects/{project_id}/tasks/{first['id']}/dependencies",
        headers=auth_headers,
        params={"depends_on_task_id": first["id"]},
    )
    assert self_dep.status_code == 400
    assert self_dep.json()["detail"]["code"] == "INVALID_DEPENDENCY"

    dep = client.post(
        f"/api/v1/organizations/{org_id}/projects/{project_id}/tasks/{second['id']}/dependencies",
        headers=auth_headers,
        params={"depends_on_task_id": first["id"]},
    )
    assert dep.status_code == 201

    duplicate = client.post(
        f"/api/v1/organizations/{org_id}/projects/{project_id}/tasks/{second['id']}/dependencies",
        headers=auth_headers,
        params={"depends_on_task_id": first["id"]},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"]["code"] == "DEPENDENCY_EXISTS"
