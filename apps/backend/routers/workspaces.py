from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from database_production import get_db
from models import Workspace, WorkspaceMember, User
from pydantic import BaseModel
from datetime import datetime
from security import get_current_user
from services.audit_service import audit_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workspaces", tags=["workspaces"])

# --- Schemas ---
class WorkspaceBase(BaseModel):
    name: str
    type: str = "general"  # Default workspace type

class WorkspaceCreate(WorkspaceBase):
    pass

class WorkspaceSchema(WorkspaceBase):
    id: int
    owner_id: int
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True

class MemberSchema(BaseModel):
    id: int
    user_id: int
    role: str
    joined_at: Optional[datetime] = None
    class Config:
        from_attributes = True

class MemberAddRequest(BaseModel):
    user_id: int
    role: str = "member"

# --- Endpoints ---

@router.post("/", response_model=WorkspaceSchema)
def create_workspace(workspace: WorkspaceCreate, request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_workspace = Workspace(
        name=workspace.name,
        type=workspace.type,
        owner_id=current_user.id,
        organization_id=current_user.organization_id
    )
    db.add(db_workspace)
    db.commit()
    db.refresh(db_workspace)
    
    # Add owner as admin member
    member = WorkspaceMember(workspace_id=db_workspace.id, user_id=current_user.id, role="admin")
    db.add(member)
    db.commit()
    
    # Audit Log
    audit_service.log_action(
        db, current_user.id, "create_workspace", "workspace", str(db_workspace.id), 
        details={"name": workspace.name, "type": workspace.type}, ip_address=request.client.host
    )
    
    return db_workspace

@router.get("/", response_model=List[WorkspaceSchema])
def list_workspaces(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """List all workspaces for current user"""
    # Filter by current user membership
    memberships = db.query(WorkspaceMember).filter(WorkspaceMember.user_id == current_user.id).all()
    workspace_ids = [m.workspace_id for m in memberships]
    
    return db.query(Workspace).filter(Workspace.id.in_(workspace_ids)).all()

@router.get("/{workspace_id}/members", response_model=List[MemberSchema])
def list_members(workspace_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Check if user is member
    membership = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == current_user.id
    ).first()
    
    if not membership and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not a member of this workspace")

    return db.query(WorkspaceMember).filter(WorkspaceMember.workspace_id == workspace_id).all()

@router.post("/{workspace_id}/members")
def add_member(workspace_id: int, member_req: MemberAddRequest, request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Check if user is workspace admin
    membership = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == current_user.id
    ).first()
    
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of this workspace")
        
    if membership.role != "admin" and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only workspace admins can add members")

    # Check if user exists
    user = db.query(User).filter(User.id == member_req.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Check if already member
    existing = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == member_req.user_id
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="User already a member")
        
    new_member = WorkspaceMember(workspace_id=workspace_id, user_id=member_req.user_id, role=member_req.role)
    db.add(new_member)
    db.commit()
    
    # Audit Log
    audit_service.log_action(
        db, current_user.id, "add_workspace_member", "workspace", str(workspace_id), 
        details={"added_user_id": member_req.user_id, "role": member_req.role}, ip_address=request.client.host
    )
    
    return {"status": "success", "message": f"User {user.email} added to workspace"}
