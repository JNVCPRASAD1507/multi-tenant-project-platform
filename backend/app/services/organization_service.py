
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
    
def get_organization_members(
    db: Session,
    user_id: int,
    organization_id: int,
) -> list[dict]:
    organization = get_user_organization(
        db=db,
        user_id=user_id,
        organization_id=organization_id,
    )

    if organization is None:
        return []

    members = db.execute(
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
            OrganizationMember.is_active.is_(True),
        )
        .order_by(User.full_name)
    ).mappings().all()

    return [dict(member) for member in members]
    
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

def add_organization_member(
    db: Session,
    organization_id: int,
    user_id: int,
    role_id: int,
) -> OrganizationMember:
    organization = db.scalar(
        select(Organization).where(
            Organization.id == organization_id,
            Organization.is_active.is_(True),
        )
    )

    if organization is None:
        raise ValueError("ORGANIZATION_NOT_FOUND")

    user = db.scalar(
        select(User).where(
            User.id == user_id,
            User.is_active.is_(True),
        )
    )

    if user is None:
        raise ValueError("USER_NOT_FOUND")

    role = db.scalar(
        select(Role).where(Role.id == role_id)
    )

    if role is None:
        raise ValueError("ROLE_NOT_FOUND")

    existing_member = db.scalar(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == user_id,
        )
    )

    if existing_member is not None:
        if existing_member.is_active:
            raise ValueError("USER_ALREADY_MEMBER")

        existing_member.role_id = role_id
        existing_member.is_active = True

        try:
            db.commit()
        except Exception:
            db.rollback()
            raise

        db.refresh(existing_member)
        return existing_member

    membership = OrganizationMember(
        organization_id=organization_id,
        user_id=user_id,
        role_id=role_id,
        is_active=True,
    )

    db.add(membership)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(membership)

    return membership

def update_organization_member(
    db: Session,
    organization_id: int,
    user_id: int,
    role_id: int,
    is_active: bool,
) -> OrganizationMember:
    membership = db.scalar(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == user_id,
        )
    )

    if membership is None:
        raise ValueError("MEMBER_NOT_FOUND")

    role = db.scalar(
        select(Role).where(Role.id == role_id)
    )

    if role is None:
        raise ValueError("ROLE_NOT_FOUND")

    membership.role_id = role_id
    membership.is_active = is_active

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(membership)

    return membership


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

def remove_organization_member(
    db: Session,
    organization_id: int,
    user_id: int,
) -> OrganizationMember:
    membership = db.scalar(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == user_id,
            OrganizationMember.is_active.is_(True),
        )
    )

    if membership is None:
        raise ValueError("MEMBER_NOT_FOUND")

    membership.is_active = False

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(membership)

    return membership

