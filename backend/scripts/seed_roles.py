import sys
from pathlib import Path

# Add the backend directory to Python's import path.
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.role import Role


SYSTEM_ROLES = [
    {
        "name": "Super Admin",
        "description": "Platform-level administrator with system-wide access.",
    },
    {
        "name": "Organization Admin",
        "description": "Administrator responsible for an organization.",
    },
    {
        "name": "Project Manager",
        "description": "Manages projects, tasks, assignments, and workflows.",
    },
    {
        "name": "Team Member",
        "description": "Works on assigned projects and tasks.",
    },
    {
        "name": "Viewer",
        "description": "Read-only access to permitted organization resources.",
    },
]


def seed_roles() -> None:
    db = SessionLocal()

    try:
        for role_data in SYSTEM_ROLES:
            existing_role = db.scalar(
                select(Role).where(Role.name == role_data["name"])
            )

            if existing_role:
                print(f"Already exists: {role_data['name']}")
                continue

            role = Role(**role_data)
            db.add(role)

            print(f"Created: {role_data['name']}")

        db.commit()
        print("\nRole seeding completed.")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed_roles()
    
    