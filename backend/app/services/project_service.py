
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.organization_member import OrganizationMember
from app.models.project import Project
from app.schemas.project import ProjectCreateRequest, ProjectUpdateRequest


def create_project(
    db: Session,
    organization_id: int,
    data: ProjectCreateRequest,
) -> Project:
    project = Project(
        organization_id=organization_id,
        name=data.name.strip(),
        description=data.description.strip() if data.description else None,
        status=data.status,
        is_active=True,
    )

    db.add(project)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(project)

    return project


def get_organization_projects(
    db: Session,
    organization_id: int,
) -> list[Project]:
    projects = db.scalars(
        select(Project)
        .where(
            Project.organization_id == organization_id,
            Project.is_active.is_(True),
        )
        .order_by(Project.created_at.desc())
    ).all()

    return list(projects)


def get_project(
    db: Session,
    organization_id: int,
    project_id: int,
) -> Project | None:
    return db.scalar(
        select(Project).where(
            Project.id == project_id,
            Project.organization_id == organization_id,
            Project.is_active.is_(True),
        )
    )


def update_project(
    db: Session,
    organization_id: int,
    project_id: int,
    data: ProjectUpdateRequest,
) -> Project | None:
    project = get_project(
        db=db,
        organization_id=organization_id,
        project_id=project_id,
    )

    if project is None:
        return None

    update_data = data.model_dump(exclude_unset=True)

    if "name" in update_data and update_data["name"] is not None:
        project.name = update_data["name"].strip()

    if "description" in update_data:
        description = update_data["description"]
        project.description = (
            description.strip()
            if description is not None
            else None
        )

    if "status" in update_data and update_data["status"] is not None:
        project.status = update_data["status"]

    if "is_active" in update_data and update_data["is_active"] is not None:
        project.is_active = update_data["is_active"]

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(project)

    return project


def delete_project(
    db: Session,
    organization_id: int,
    project_id: int,
) -> Project | None:
    project = get_project(
        db=db,
        organization_id=organization_id,
        project_id=project_id,
    )

    if project is None:
        return None

    project.is_active = False
    project.status = "archived"

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(project)

    return project


def is_active_organization_member(
    db: Session,
    user_id: int,
    organization_id: int,
) -> bool:
    membership = db.scalar(
        select(OrganizationMember.id).where(
            OrganizationMember.user_id == user_id,
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.is_active.is_(True),
        )
    )

    return membership is not None

