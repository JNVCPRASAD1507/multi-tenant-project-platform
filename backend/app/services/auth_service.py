
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_refresh_token_expiry,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models.organization import Organization
from app.models.organization_member import OrganizationMember
from app.models.role import Role
from app.models.user import User
from app.schemas.auth import RegisterRequest
from app.models.refresh_token import RefreshToken


def register_user(
    db: Session,
    data: RegisterRequest,
) -> tuple[User, Organization, Role]:
    # 1. Check whether email already exists
    existing_user = db.scalar(
        select(User).where(
            User.email == data.email.lower()
        )
    )

    if existing_user:
        raise ValueError("An account with this email already exists.")

    # 2. Find the Organization Admin role
    organization_admin_role = db.scalar(
        select(Role).where(
            Role.name == "Organization Admin"
        )
    )

    if organization_admin_role is None:
        raise RuntimeError(
            "Organization Admin role is not configured."
        )

    # 3. Create the user
    user = User(
        email=data.email.lower(),
        password_hash=hash_password(data.password),
        full_name=data.full_name.strip(),
        is_active=True,
        is_verified=False,
    )

    db.add(user)
    db.flush()

    # 4. Create the organization
    organization = Organization(
        name=data.organization_name.strip(),
        slug=_generate_unique_slug(
            db,
            data.organization_name,
        ),
        is_active=True,
    )

    db.add(organization)
    db.flush()

    # 5. Add the registering user as Organization Admin
    membership = OrganizationMember(
        user_id=user.id,
        organization_id=organization.id,
        role_id=organization_admin_role.id,
        is_active=True,
    )

    db.add(membership)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError(
            "Registration could not be completed because "
            "the email or organization slug already exists."
        )

    db.refresh(user)
    db.refresh(organization)

    return user, organization, organization_admin_role


def _generate_unique_slug(
    db: Session,
    organization_name: str,
) -> str:
    base_slug = _slugify(organization_name)

    if not base_slug:
        base_slug = "organization"

    slug = base_slug
    counter = 2

    while db.scalar(
        select(Organization.id).where(
            Organization.slug == slug
        )
    ):
        slug = f"{base_slug}-{counter}"
        counter += 1

    return slug


def _slugify(value: str) -> str:
    value = value.strip().lower()

    result = []

    for character in value:
        if character.isalnum():
            result.append(character)
        elif character in {" ", "-", "_"}:
            result.append("-")

    slug = "".join(result)

    while "--" in slug:
        slug = slug.replace("--", "-")

    return slug.strip("-")


#=========================================================================

def login_user(
    db: Session,
    email: str,
    password: str,
) -> tuple[User, OrganizationMember, Role, str, str]:
    # 1. Find user
    user = db.scalar(
        select(User).where(
            User.email == email.lower()
        )
    )

    if user is None:
        raise ValueError("Invalid email or password.")

    # 2. Check account status
    if not user.is_active:
        raise PermissionError("Your account is inactive.")

    # 3. OAuth-only users do not have a password
    if not user.password_hash:
        raise ValueError(
            "This account does not have a password. "
            "Please sign in using your OAuth provider."
        )

    # 4. Verify password
    if not verify_password(
        password,
        user.password_hash,
    ):
        raise ValueError("Invalid email or password.")

    # 5. Find active organization membership
    membership = db.scalar(
        select(OrganizationMember).where(
            OrganizationMember.user_id == user.id,
            OrganizationMember.is_active.is_(True),
        )
    )

    if membership is None:
        raise PermissionError(
            "You are not an active member of any organization."
        )

    # 6. Load organization
    organization = db.scalar(
        select(Organization).where(
            Organization.id == membership.organization_id,
            Organization.is_active.is_(True),
        )
    )

    if organization is None:
        raise PermissionError(
            "Your organization is inactive or unavailable."
        )

    # 7. Load role
    role = db.scalar(
        select(Role).where(
            Role.id == membership.role_id
        )
    )

    if role is None:
        raise RuntimeError(
            "User role is not configured correctly."
        )

    # 8. Create access token
    access_token = create_access_token(
        user_id=user.id,
        organization_id=organization.id,
        role=role.name,
    )

    # 9. Create opaque refresh token
    refresh_token = create_refresh_token()

    # 10. Store only its hash
    refresh_token_record = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token(refresh_token),
        expires_at=get_refresh_token_expiry(),
    )

    db.add(refresh_token_record)
    db.commit()

    return (
        user,
        membership,
        role,
        access_token,
        refresh_token,
    )
    
    