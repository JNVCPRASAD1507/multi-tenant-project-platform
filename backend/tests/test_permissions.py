from app.core.permissions import has_permission


def test_role_permission_matrix():
    assert has_permission("Organization Admin", "project:create")
    assert has_permission("Project Manager", "task:create")
    assert has_permission("Team Member", "task:update")
    assert has_permission("Viewer", "task:read")
    assert not has_permission("Viewer", "task:create")
    assert not has_permission("Team Member", "project:delete")
    assert not has_permission("Unknown", "project:read")
