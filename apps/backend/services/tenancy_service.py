from sqlalchemy.orm import Session
from models import Organization, Workspace, User


def ensure_tenant(db: Session, user: User) -> None:
    """
    Ensure a user has an organization and default workspace.
    """
    if user.organization_id:
        return

    org_base = user.email.split("@")[0]
    org_name = f"{org_base}-org"
    existing = db.query(Organization).filter(Organization.name == org_name).first()
    if existing:
        org_name = f"{org_base}-org-{user.id}"

    org = Organization(name=org_name, owner_id=user.id)
    db.add(org)
    db.commit()
    db.refresh(org)

    org.tenant_id = org.id
    db.commit()

    user.organization_id = org.id
    user.tenant_id = org.id
    db.commit()

    workspace = Workspace(
        name=f"{org_base} Workspace",
        owner_id=user.id,
        organization_id=org.id,
        tenant_id=org.id
    )
    db.add(workspace)
    db.commit()
