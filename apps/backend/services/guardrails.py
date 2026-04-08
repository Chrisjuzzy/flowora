from sqlalchemy.orm import Session
from models import EthicalLog
import re

class EthicalGuardrailsService:
    @staticmethod
    def check_input(db: Session, execution_id: int, content: str) -> bool:
        # 1. Basic Keyword Check (Toxicity)
        toxic_keywords = ["hate", "violence", "kill", "attack", "illegal", "exploit"]
        for word in toxic_keywords:
            if word in content.lower():
                EthicalGuardrailsService._log_violation(db, execution_id, "toxicity", f"Found keyword: {word}")
                return False
                
        # 2. PII Check (Simple regex for email/phone)
        # Note: This is very basic. Real PII detection is complex.
        # email_regex = r"[^@]+@[^@]+\.[^@]+"
        # if re.search(email_regex, content):
        #     EthicalGuardrailsService._log_violation(db, execution_id, "pii", "Possible email address found")
        #     return False
            
        return True

    @staticmethod
    def check_output(db: Session, execution_id: int, content: str) -> bool:
        # Similar checks for output
        toxic_keywords = ["hate", "violence", "kill", "attack"]
        for word in toxic_keywords:
            if word in content.lower():
                EthicalGuardrailsService._log_violation(db, execution_id, "toxicity_output", f"Found keyword: {word}")
                return False
        
        return True

    @staticmethod
    def _log_violation(db: Session, execution_id: int, check_type: str, details: str):
        log = EthicalLog(
            execution_id=execution_id,
            check_type=check_type,
            passed=False,
            details=details
        )
        db.add(log)
        db.commit()
        print(f"⚠️ Ethical Guardrail Violation: {check_type} - {details}")
