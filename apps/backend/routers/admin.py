from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from database_production import get_db
from models import User, AuditLog
from schemas import User as UserSchema
from security import RoleChecker, get_current_active_user
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(RoleChecker(["admin"]))]
)

class AuditLogSchema(BaseModel):
    id: int
    user_id: int
    action: str
    resource_type: str
    resource_id: str
    timestamp: datetime
    details: str = None
    ip_address: str = None
    
    class Config:
        from_attributes = True

@router.get("/users", response_model=List[UserSchema])
def list_all_users(db: Session = Depends(get_db)):
    """List all users (Admin only)"""
    return db.query(User).all()

@router.get("/audit-logs", response_model=List[AuditLogSchema])
def view_audit_logs(limit: int = 100, db: Session = Depends(get_db)):
    """View system audit logs (Admin only)"""
    return db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit).all()

@router.post("/promote/{user_id}")
def promote_user(user_id: int, role: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    """Promote a user to a specific role (Admin only)"""
    if role not in ["admin", "developer", "user", "viewer"]:
        raise HTTPException(status_code=400, detail="Invalid role")
        
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    user.role = role
    db.commit()
    return {"message": f"User {user.email} promoted to {role}"}
