import logging
import json
import sys
from datetime import datetime
from config import settings

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if hasattr(record, "props"):
            log_record.update(record.props)
        return json.dumps(log_record)

def setup_logger(name="ai_agent_builder"):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO if not settings.DEBUG else logging.DEBUG)
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    
    logger.addHandler(handler)
    return logger

logger = setup_logger()
