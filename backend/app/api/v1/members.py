
from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.api.deps import get_current_membership 
from app.db.session import get_db
from app.models.organization_member import OrganizationMember
from app.models.role import Role
from app.models.user import User
from app.schemas.member import (
    MemberCreateRequest,
    MemberListResponse,
    MemberResponse,
    MemberUpdateRequest,
)
from app.services.organization_service import (
    add_organization_member,
    get_organization_members,
    update_organization_member,
    remove_organization_member,
)

router = APIRouter(
    prefix="/organizations/{organization_id}/members",
    tags=["Organization Members"],
)


@router.get(
    "",
    response_model=MemberListResponse,
    status_code=status.HTTP_200_OK,
)
def get_organization_members_api(
    organization_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    role: Role = Depends(require_permission("member:read")),
    db: Session = Depends(get_db),
):
    members = get_organization_members(
        db=db,
        user_id=current_user.id,
        organization_id=organization_id,
    )

    if not members:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "ORGANIZATION_NOT_FOUND",
                "message": "Organization not found or you are not a member of this organization.",
            },
        )

    return MemberListResponse(
        items=[MemberResponse(**member) for member in members],
        total=len(members),
    )
    
@router.post(
    "",
    response_model=MemberResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_organization_member_api(
    data: MemberCreateRequest,
    organization_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    role: Role = Depends(require_permission("member:create")),
    db: Session = Depends(get_db),
):
    organization_membership = db.scalar(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.is_active.is_(True),
        )
    )

    if organization_membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "ORGANIZATION_NOT_FOUND",
                "message": "Organization not found or you are not a member of this organization.",
            },
        )

    try:
        membership = add_organization_member(
            db=db,
            organization_id=organization_id,
            user_id=data.user_id,
            role_id=data.role_id,
        )
    except ValueError as exc:
        error_code = str(exc)

        error_map = {
            "ORGANIZATION_NOT_FOUND": (
                status.HTTP_404_NOT_FOUND,
                "Organization not found.",
            ),
            "USER_NOT_FOUND": (
                status.HTTP_404_NOT_FOUND,
                "User not found or inactive.",
            ),
            "ROLE_NOT_FOUND": (
                status.HTTP_404_NOT_FOUND,
                "Role not found.",
            ),
            "USER_ALREADY_MEMBER": (
                status.HTTP_409_CONFLICT,
                "User is already an active member of this organization.",
            ),
        }

        status_code, message = error_map.get(
            error_code,
            (
                status.HTTP_400_BAD_REQUEST,
                "Unable to add organization member.",
            ),
        )

        raise HTTPException(
            status_code=status_code,
            detail={
                "code": error_code,
                "message": message,
            },
        )

    member_data = db.execute(
        select(
            User.id.label("user_id"),
            User.email,
            User.full_name,
            Role.name.label("role"),
            OrganizationMember.is_active,
            OrganizationMember.joined_at,
        )
        .join(
            OrganizationMember,
            OrganizationMember.user_id == User.id,
        )
        .join(
            Role,
            Role.id == OrganizationMember.role_id,
        )
        .where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == membership.user_id,
        )
    ).mappings().first()

    return MemberResponse(**dict(member_data))

@router.put(
    "/{user_id}",
    response_model=MemberResponse,
    status_code=status.HTTP_200_OK,
)
def update_organization_member_api(
    data: MemberUpdateRequest,
    organization_id: int = Path(..., ge=1),
    user_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    role: Role = Depends(require_permission("member:update")),
    db: Session = Depends(get_db),
):
    current_membership = db.scalar(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.is_active.is_(True),
        )
    )

    if current_membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "ORGANIZATION_NOT_FOUND",
                "message": "Organization not found or you are not a member of this organization.",
            },
        )

    try:
        membership = update_organization_member(
            db=db,
            organization_id=organization_id,
            user_id=user_id,
            role_id=data.role_id,
            is_active=data.is_active,
        )
    except ValueError as exc:
        error_code = str(exc)

        if error_code == "MEMBER_NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "MEMBER_NOT_FOUND",
                    "message": "The user is not a member of this organization.",
                },
            )

        if error_code == "ROLE_NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "ROLE_NOT_FOUND",
                    "message": "The requested role does not exist.",
                },
            )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "MEMBER_UPDATE_FAILED",
                "message": "Unable to update organization member.",
            },
        )

    member_data = db.execute(
        select(
            User.id.label("user_id"),
            User.email,
            User.full_name,
            Role.name.label("role"),
            OrganizationMember.is_active,
            OrganizationMember.joined_at,
        )
        .join(
            OrganizationMember,
            OrganizationMember.user_id == User.id,
        )
        .join(
            Role,
            Role.id == OrganizationMember.role_id,
        )
        .where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == user_id,
        )
    ).mappings().first()

    return MemberResponse(**dict(member_data))

@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_organization_member_api(
    organization_id: int = Path(..., ge=1),
    user_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    role: Role = Depends(require_permission("member:delete")),
    db: Session = Depends(get_db),
):
    current_membership = db.scalar(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.is_active.is_(True),
        )
    )

    if current_membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "ORGANIZATION_NOT_FOUND",
                "message": "Organization not found or you are not a member of this organization.",
            },
        )

    try:
        remove_organization_member(
            db=db,
            organization_id=organization_id,
            user_id=user_id,
        )
    except ValueError as exc:
        if str(exc) == "MEMBER_NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "MEMBER_NOT_FOUND",
                    "message": "The user is not an active member of this organization.",
                },
            )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "MEMBER_REMOVAL_FAILED",
                "message": "Unable to remove organization member.",
            },
        )

    return None

