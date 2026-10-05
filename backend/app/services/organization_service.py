
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.models.organization_member import OrganizationMember
from app.models.role import Role
from app.models.user import User
from app.schemas.organization import OrganizationCreateRequest


def create_organization(
    db: Session,
    user: User,
    data: OrganizationCreateRequest,
) -> Organization:
    # Find the Organization Admin role
    admin_role = db.scalar(
        select(Role).where(
            Role.name == "Organization Admin"
        )
    )

    if admin_role is None:
        raise RuntimeError(
            "Organization Admin role is not configured."
        )

    # Generate a unique organization slug
    slug = _generate_unique_slug(
        db=db,
        name=data.name,
    )

    # Create organization
    organization = Organization(
        name=data.name.strip(),
        slug=slug,
        is_active=True,
    )

    db.add(organization)
    db.flush()

    # Make requesting user an Organization Admin
    membership = OrganizationMember(
        user_id=user.id,
        organization_id=organization.id,
        role_id=admin_role.id,
        is_active=True,
    )

    db.add(membership)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(organization)

    return organization


def get_user_organizations(
    db: Session,
    user_id: int,
) -> list[Organization]:
    organizations = db.scalars(
        select(Organization)
        .join(
            OrganizationMember,
            OrganizationMember.organization_id == Organization.id,
        )
        .where(
            OrganizationMember.user_id == user_id,
            OrganizationMember.is_active.is_(True),
            Organization.is_active.is_(True),
        )
        .order_by(Organization.name)
    ).all()

    return list(organizations)


def get_user_organization(
    db: Session,
    user_id: int,
    organization_id: int,
) -> Organization | None:
    return db.scalar(
        select(Organization)
        .join(
            OrganizationMember,
            OrganizationMember.organization_id == Organization.id,
        )
        .where(
            Organization.id == organization_id,
            OrganizationMember.user_id == user_id,
            OrganizationMember.is_active.is_(True),
            Organization.is_active.is_(True),
        )
    )
    
def update_organization(
    db: Session,
    user_id: int,
    organization_id: int,
    name: str,
) -> Organization | None:
    organization = get_user_organization(
        db=db,
        user_id=user_id,
        organization_id=organization_id,
    )

    if organization is None:
        return None

    organization.name = name.strip()

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(organization)

    return organization


def _generate_unique_slug(
    db: Session,
    name: str,
) -> str:
    base_slug = _slugify(name)

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

    characters = []

    for character in value:
        if character.isalnum():
            characters.append(character)
        elif character in {" ", "-", "_"}:
            characters.append("-")

    slug = "".join(characters)

    while "--" in slug:
        slug = slug.replace("--", "-")

    return slug.strip("-")

