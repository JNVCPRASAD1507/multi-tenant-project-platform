
ROLE_PERMISSIONS = {
    "Super Admin": {
        "organization:read",
        "organization:create",
        "organization:update",
        "organization:delete",
        "member:read",
        "member:create",
        "member:update",
        "member:delete",
        "project:read",
        "project:create",
        "project:update",
        "project:delete",
        "task:read",
        "task:create",
        "task:update",
        "task:delete",
    },

    "Organization Admin": {
        "organization:read",
        "organization:update",
        "member:read",
        "member:create",
        "member:update",
        "member:delete",
        "project:read",
        "project:create",
        "project:update",
        "project:delete",
        "task:read",
        "task:create",
        "task:update",
        "task:delete",
    },

    "Project Manager": {
        "organization:read",
        "member:read",
        "project:read",
        "project:create",
        "project:update",
        "project:delete",
        "task:read",
        "task:create",
        "task:update",
        "task:delete",
    },

    "Team Member": {
        "organization:read",
        "member:read",
        "project:read",
        "task:read",
        "task:create",
        "task:update",
    },

    "Viewer": {
        "organization:read",
        "member:read",
        "project:read",
        "task:read",
    },
}


def has_permission(
    role_name: str,
    permission: str,
) -> bool:
    return permission in ROLE_PERMISSIONS.get(
        role_name,
        set(),
    )
    
    
    