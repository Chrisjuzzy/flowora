from sqlalchemy.orm import Session
from models import AuditLog
from datetime import datetime
import json

class AuditService:
    def log_action(
        self, 
        db: Session, 
        user_id: int, 
        action: str, 
        resource_type: str, 
        resource_id: str, 
        details: dict = None,
        ip_address: str = None
    ):
        log_entry = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=json.dumps(details) if details else None,
            ip_address=ip_address,
            timestamp=datetime.utcnow()
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        return log_entry

audit_service = AuditService()
