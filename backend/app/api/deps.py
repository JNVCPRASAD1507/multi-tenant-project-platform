

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.permissions import has_permission
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.organization import Organization
from app.models.organization_member import OrganizationMember
from app.models.role import Role
from app.models.user import User


# ============================================================
# JWT BEARER AUTHENTICATION
# ============================================================

bearer_scheme = HTTPBearer(
    auto_error=True,
)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(
        bearer_scheme
    ),
    db: Session = Depends(get_db),
) -> User:

    token = credentials.credentials

    try:
        payload = decode_access_token(token)

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "INVALID_ACCESS_TOKEN",
                "message": "Invalid or expired access token.",
            },
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    # --------------------------------------------------------
    # Get user ID from JWT
    # --------------------------------------------------------

    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "INVALID_ACCESS_TOKEN",
                "message": "Access token does not contain a user ID.",
            },
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    try:
        user_id = int(user_id)

    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "INVALID_ACCESS_TOKEN",
                "message": "Invalid user ID in access token.",
            },
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    # --------------------------------------------------------
    # Find user
    # --------------------------------------------------------

    user = db.scalar(
        select(User).where(
            User.id == user_id
        )
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "USER_NOT_FOUND",
                "message": "Authenticated user no longer exists.",
            },
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    # --------------------------------------------------------
    # Check user status
    # --------------------------------------------------------

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "USER_INACTIVE",
                "message": "Your account is inactive.",
            },
        )

    return user


# ============================================================
# ORGANIZATION MEMBERSHIP
# ============================================================

def get_current_membership(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OrganizationMember:

    membership = db.scalar(
        select(OrganizationMember).where(
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.is_active.is_(True),
        )
    )

    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "ORGANIZATION_MEMBERSHIP_REQUIRED",
                "message": (
                    "You are not an active member "
                    "of an organization."
                ),
            },
        )

    organization = db.scalar(
        select(Organization).where(
            Organization.id == membership.organization_id,
            Organization.is_active.is_(True),
        )
    )

    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "ORGANIZATION_INACTIVE",
                "message": "Your organization is inactive.",
            },
        )

    return membership


# ============================================================
# CURRENT ROLE
# ============================================================

def get_current_role(
    membership: OrganizationMember = Depends(
        get_current_membership
    ),
    db: Session = Depends(get_db),
) -> Role:

    role = db.scalar(
        select(Role).where(
            Role.id == membership.role_id
        )
    )

    if role is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "ROLE_NOT_FOUND",
                "message": (
                    "The user's role is not "
                    "configured correctly."
                ),
            },
        )

    return role


# ============================================================
# RBAC PERMISSION CHECK
# ============================================================

def require_permission(permission: str):

    def permission_dependency(
        role: Role = Depends(get_current_role),
    ) -> Role:

        if not has_permission(
            role.name,
            permission,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "PERMISSION_DENIED",
                    "message": (
                        "You do not have permission "
                        "to perform this action."
                    ),
                },
            )

        return role

    return permission_dependency



# from fastapi import Depends, HTTPException, status
# from fastapi.security import OAuth2PasswordBearer
# from sqlalchemy import select
# from sqlalchemy.orm import Session

# from app.db.session import get_db
# from app.models.user import User
# from app.core.security import decode_access_token

# from app.models.organization import Organization
# from app.models.organization_member import OrganizationMember
# from app.models.role import Role

# from app.core.permissions import has_permission


# oauth2_scheme = OAuth2PasswordBearer(
#     tokenUrl="/api/v1/auth/login"
# )


# def get_current_user(
#     token: str = Depends(oauth2_scheme),
#     db: Session = Depends(get_db),
# ) -> User:
#     try:
#         payload = decode_access_token(token)
#     except Exception:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail={
#                 "code": "INVALID_ACCESS_TOKEN",
#                 "message": "Invalid or expired access token.",
#             },
#             headers={"WWW-Authenticate": "Bearer"},
#         )

#     user_id = payload.get("sub")

#     if not user_id:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail={
#                 "code": "INVALID_ACCESS_TOKEN",
#                 "message": "Access token does not contain a user ID.",
#             },
#             headers={"WWW-Authenticate": "Bearer"},
#         )

#     try:
#         user_id = int(user_id)
#     except (TypeError, ValueError):
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail={
#                 "code": "INVALID_ACCESS_TOKEN",
#                 "message": "Invalid user ID in access token.",
#             },
#             headers={"WWW-Authenticate": "Bearer"},
#         )

#     user = db.scalar(
#         select(User).where(User.id == user_id)
#     )

#     if user is None:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail={
#                 "code": "USER_NOT_FOUND",
#                 "message": "Authenticated user no longer exists.",
#             },
#             headers={"WWW-Authenticate": "Bearer"},
#         )

#     if not user.is_active:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail={
#                 "code": "USER_INACTIVE",
#                 "message": "Your account is inactive.",
#             },
#         )

#     return user

# #================================================

# def get_current_membership(
#     current_user: User = Depends(get_current_user),
#     db: Session = Depends(get_db),
# ) -> OrganizationMember:
#     membership = db.scalar(
#         select(OrganizationMember).where(
#             OrganizationMember.user_id == current_user.id,
#             OrganizationMember.is_active.is_(True),
#         )
#     )

#     if membership is None:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail={
#                 "code": "ORGANIZATION_MEMBERSHIP_REQUIRED",
#                 "message": "You are not an active member of an organization.",
#             },
#         )

#     organization = db.scalar(
#         select(Organization).where(
#             Organization.id == membership.organization_id,
#             Organization.is_active.is_(True),
#         )
#     )

#     if organization is None:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail={
#                 "code": "ORGANIZATION_INACTIVE",
#                 "message": "Your organization is inactive.",
#             },
#         )

#     return membership

# #================================================

# def get_current_role(
#     membership: OrganizationMember = Depends(
#         get_current_membership
#     ),
#     db: Session = Depends(get_db),
# ) -> Role:
#     role = db.scalar(
#         select(Role).where(
#             Role.id == membership.role_id
#         )
#     )

#     if role is None:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail={
#                 "code": "ROLE_NOT_FOUND",
#                 "message": "The user's role is not configured correctly.",
#             },
#         )

#     return role

# #================================================

# def require_permission(permission: str):
#     def permission_dependency(
#         role: Role = Depends(get_current_role),
#     ) -> Role:
#         if not has_permission(
#             role.name,
#             permission,
#         ):
#             raise HTTPException(
#                 status_code=status.HTTP_403_FORBIDDEN,
#                 detail={
#                     "code": "PERMISSION_DENIED",
#                     "message": "You do not have permission to perform this action.",
#                 },
#             )

#         return role

#     return permission_dependency

