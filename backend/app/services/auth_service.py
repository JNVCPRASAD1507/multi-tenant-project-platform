
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

from datetime import datetime, timezone


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
    
def refresh_access_token(
    db: Session,
    refresh_token: str,
) -> tuple[str, str]:
    token_hash = hash_refresh_token(refresh_token)

    stored_token = db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash
        )
    )

    if stored_token is None:
        raise ValueError("Invalid refresh token.")

    if stored_token.revoked_at is not None:
        raise ValueError("Refresh token has been revoked.")

    if stored_token.expires_at <= datetime.now(timezone.utc):
        raise ValueError("Refresh token has expired.")

    user = db.scalar(
        select(User).where(
            User.id == stored_token.user_id
        )
    )

    if user is None:
        raise ValueError("User no longer exists.")

    if not user.is_active:
        raise PermissionError("Your account is inactive.")

    membership = db.scalar(
        select(OrganizationMember).where(
            OrganizationMember.user_id == user.id,
            OrganizationMember.is_active.is_(True),
        )
    )

    if membership is None:
        raise PermissionError(
            "You are not an active organization member."
        )

    organization = db.scalar(
        select(Organization).where(
            Organization.id == membership.organization_id,
            Organization.is_active.is_(True),
        )
    )

    if organization is None:
        raise PermissionError(
            "Your organization is inactive."
        )

    role = db.scalar(
        select(Role).where(
            Role.id == membership.role_id
        )
    )

    if role is None:
        raise RuntimeError(
            "User role is not configured correctly."
        )

    # Create new access JWT
    access_token = create_access_token(
        user_id=user.id,
        organization_id=organization.id,
        role=role.name,
    )

    # Rotate refresh token
    new_refresh_token = create_refresh_token()

    stored_token.revoked_at = datetime.now(timezone.utc)

    new_refresh_token_record = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token(
            new_refresh_token
        ),
        expires_at=get_refresh_token_expiry(),
    )

    db.add(new_refresh_token_record)
    db.commit()

    return access_token, new_refresh_token

#=========================================================================

def logout_user(
    db: Session,
    refresh_token: str,
) -> None:
    token_hash = hash_refresh_token(refresh_token)

    stored_token = db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash
        )
    )

    if stored_token is None:
        raise ValueError("Invalid refresh token.")

    if stored_token.revoked_at is not None:
        return

    stored_token.revoked_at = datetime.now(timezone.utc)

    db.commit()
    
    

#=========================================================================
# GitHub OAuth
#=========================================================================

import httpx
from app.models.oauth_account import OAuthAccount
from app.core.config import settings


async def exchange_github_code(code: str) -> dict:
    """Exchange authorization code for GitHub access token + user info."""
    async with httpx.AsyncClient() as client:
        # 1. Exchange code for access token
        token_resp = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": settings.GITHUB_REDIRECT_URI,
            },
        )
        token_data = token_resp.json()
        if "access_token" not in token_data:
            raise ValueError(
                token_data.get("error_description")
                or token_data.get("error")
                or "Failed to obtain GitHub access token"
            )

        gh_token = token_data["access_token"]

        # 2. Fetch user profile
        user_resp = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {gh_token}",
                "Accept": "application/vnd.github+json",
            },
        )
        if user_resp.status_code != 200:
            raise ValueError("Failed to fetch GitHub user profile")

        gh_user = user_resp.json()

        # 3. Fetch primary email if not public
        email = gh_user.get("email")
        if not email:
            emails_resp = await client.get(
                "https://api.github.com/user/emails",
                headers={
                    "Authorization": f"Bearer {gh_token}",
                    "Accept": "application/vnd.github+json",
                },
            )
            if emails_resp.status_code == 200:
                for e in emails_resp.json():
                    if e.get("primary") and e.get("verified"):
                        email = e["email"]
                        break
                if not email and emails_resp.json():
                    email = emails_resp.json()[0]["email"]

        if not email:
            raise ValueError(
                "GitHub account has no accessible email. "
                "Make sure your email is public or grant the user:email scope."
            )

        return {
            "provider_user_id": str(gh_user["id"]),
            "email": email.lower(),
            "full_name": gh_user.get("name") or gh_user.get("login") or email,
            "login": gh_user.get("login"),
            "avatar_url": gh_user.get("avatar_url"),
        }


def login_or_register_github_user(
    db: Session,
    github_data: dict,
) -> tuple[User, Organization | None, Role | None, str, str]:
    """
    Find or create user from GitHub data.
    Returns (user, organization, role, access_token, refresh_token)
    """
    provider = "github"
    provider_user_id = github_data["provider_user_id"]
    email = github_data["email"]

    # 1. Look for existing OAuth link
    oauth = db.scalar(
        select(OAuthAccount).where(
            OAuthAccount.provider == provider,
            OAuthAccount.provider_user_id == provider_user_id,
        )
    )

    if oauth:
        user = db.get(User, oauth.user_id)
        if not user or not user.is_active:
            raise PermissionError("User account is inactive.")
    else:
        # 2. Look for existing user by email
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            # Create new user (no password)
            user = User(
                email=email,
                password_hash=None,
                full_name=github_data["full_name"][:150],
                is_active=True,
                is_verified=True,
            )
            db.add(user)
            db.flush()

        # Link OAuth account
        oauth = OAuthAccount(
            user_id=user.id,
            provider=provider,
            provider_user_id=provider_user_id,
            email=email,
        )
        db.add(oauth)
        db.commit()
        db.refresh(user)

    if not user.is_active:
        raise PermissionError("User account is inactive.")

    # Find primary membership (first active org)
    membership = db.scalar(
        select(OrganizationMember)
        .where(
            OrganizationMember.user_id == user.id,
            OrganizationMember.is_active == True,  # noqa: E712
        )
        .limit(1)
    )

    organization = None
    role = None
    organization_id = None
    role_name = None

    if membership:
        organization = db.get(Organization, membership.organization_id)
        role = db.get(Role, membership.role_id)
        organization_id = membership.organization_id
        role_name = role.name if role else None

    access_token = create_access_token(
        user_id=user.id,
        organization_id=organization_id,
        role=role_name,
    )
    refresh_token = create_refresh_token()

    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(refresh_token),
            expires_at=get_refresh_token_expiry(),
        )
    )
    db.commit()

    return user, organization, role, access_token, refresh_token
