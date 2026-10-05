
from fastapi import APIRouter, Depends, HTTPException, status , Path
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.db.session import get_db
from app.models.role import Role
from app.models.user import User
from app.schemas.organization import (
    OrganizationCreateRequest,
    OrganizationListResponse,
    OrganizationResponse,
    OrganizationUpdateRequest,
)
from app.services.organization_service import (
    create_organization,
    get_user_organization,
    get_user_organizations,
    update_organization,
)

router = APIRouter(prefix="/organizations", tags=["Organizations"])


@router.post(
    "",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_organization_api(
    data: OrganizationCreateRequest,
    current_user: User = Depends(get_current_user),
    role: Role = Depends(require_permission("organization:create")),
    db: Session = Depends(get_db),
):
    try:
        organization = create_organization(
            db=db,
            user=current_user,
            data=data,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "ORGANIZATION_CONFIGURATION_ERROR",
                "message": str(exc),
            },
        )

    return organization


@router.get(
    "",
    response_model=OrganizationListResponse,
    status_code=status.HTTP_200_OK,
)
def get_organizations_api(
    current_user: User = Depends(get_current_user),
    role: Role = Depends(require_permission("organization:read")),
    db: Session = Depends(get_db),
):
    organizations = get_user_organizations(
        db=db,
        user_id=current_user.id,
    )

    return OrganizationListResponse(
        items=organizations,
        total=len(organizations),
    )
    

@router.get(
    "/{organization_id}",
    response_model=OrganizationResponse,
    status_code=status.HTTP_200_OK,
)
def get_organization_api(
    organization_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    role: Role = Depends(require_permission("organization:read")),
    db: Session = Depends(get_db),
):
    organization = get_user_organization(
        db=db,
        user_id=current_user.id,
        organization_id=organization_id,
    )

    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "ORGANIZATION_NOT_FOUND",
                "message": "Organization not found or you are not a member of this organization.",
            },
        )

    return organization

@router.put(
    "/{organization_id}",
    response_model=OrganizationResponse,
    status_code=status.HTTP_200_OK,
)
def update_organization_api(
    organization_id: int = Path(..., ge=1),
    data: OrganizationUpdateRequest = ...,
    current_user: User = Depends(get_current_user),
    role: Role = Depends(require_permission("organization:update")),
    db: Session = Depends(get_db),
):
    organization = update_organization(
        db=db,
        user_id=current_user.id,
        organization_id=organization_id,
        name=data.name,
    )

    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "ORGANIZATION_NOT_FOUND",
                "message": "Organization not found or you are not a member of this organization.",
            },
        )

    return organization


