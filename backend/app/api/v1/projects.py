
from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.db.session import get_db
from app.models.organization_member import OrganizationMember
from app.models.role import Role
from app.models.user import User
from app.schemas.project import (
    ProjectCreateRequest,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdateRequest,
)
from app.services.project_service import (
    create_project,
    delete_project,
    get_organization_projects,
    get_project,
    update_project,
)

router = APIRouter(
    prefix="/organizations/{organization_id}/projects",
    tags=["Projects"],
)


def verify_organization_membership(
    db: Session,
    user_id: int,
    organization_id: int,
) -> None:
    membership = db.scalar(
        select(OrganizationMember).where(
            OrganizationMember.user_id == user_id,
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.is_active.is_(True),
        )
    )

    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "ORGANIZATION_NOT_FOUND",
                "message": (
                    "Organization not found or you are not "
                    "a member of this organization."
                ),
            },
        )


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_project_api(
    organization_id: int = Path(..., ge=1),
    data: ProjectCreateRequest = ...,
    current_user: User = Depends(get_current_user),
    role: Role = Depends(require_permission("project:create")),
    db: Session = Depends(get_db),
):
    verify_organization_membership(
        db=db,
        user_id=current_user.id,
        organization_id=organization_id,
    )

    return create_project(
        db=db,
        organization_id=organization_id,
        data=data,
    )


@router.get(
    "",
    response_model=ProjectListResponse,
    status_code=status.HTTP_200_OK,
)
def get_projects_api(
    organization_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    role: Role = Depends(require_permission("project:read")),
    db: Session = Depends(get_db),
):
    verify_organization_membership(
        db=db,
        user_id=current_user.id,
        organization_id=organization_id,
    )

    projects = get_organization_projects(
        db=db,
        organization_id=organization_id,
    )

    return ProjectListResponse(
        items=projects,
        total=len(projects),
    )


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    status_code=status.HTTP_200_OK,
)
def get_project_api(
    organization_id: int = Path(..., ge=1),
    project_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    role: Role = Depends(require_permission("project:read")),
    db: Session = Depends(get_db),
):
    verify_organization_membership(
        db=db,
        user_id=current_user.id,
        organization_id=organization_id,
    )

    project = get_project(
        db=db,
        organization_id=organization_id,
        project_id=project_id,
    )

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "PROJECT_NOT_FOUND",
                "message": (
                    "Project not found or does not belong "
                    "to this organization."
                ),
            },
        )

    return project


@router.put(
    "/{project_id}",
    response_model=ProjectResponse,
    status_code=status.HTTP_200_OK,
)
def update_project_api(
    organization_id: int = Path(..., ge=1),
    project_id: int = Path(..., ge=1),
    data: ProjectUpdateRequest = ...,
    current_user: User = Depends(get_current_user),
    role: Role = Depends(require_permission("project:update")),
    db: Session = Depends(get_db),
):
    verify_organization_membership(
        db=db,
        user_id=current_user.id,
        organization_id=organization_id,
    )

    project = update_project(
        db=db,
        organization_id=organization_id,
        project_id=project_id,
        data=data,
    )

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "PROJECT_NOT_FOUND",
                "message": (
                    "Project not found or does not belong "
                    "to this organization."
                ),
            },
        )

    return project


@router.delete(
    "/{project_id}",
    response_model=ProjectResponse,
    status_code=status.HTTP_200_OK,
)
def delete_project_api(
    organization_id: int = Path(..., ge=1),
    project_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    role: Role = Depends(require_permission("project:delete")),
    db: Session = Depends(get_db),
):
    verify_organization_membership(
        db=db,
        user_id=current_user.id,
        organization_id=organization_id,
    )

    project = delete_project(
        db=db,
        organization_id=organization_id,
        project_id=project_id,
    )

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "PROJECT_NOT_FOUND",
                "message": (
                    "Project not found or does not belong "
                    "to this organization."
                ),
            },
        )

    return project

