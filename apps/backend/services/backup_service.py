import shutil
import os
from datetime import datetime
from config import settings
import logging

logger = logging.getLogger(__name__)

class BackupService:
    def __init__(self, db_path: str = "app.db", backup_dir: str = "backups"):
        self.db_path = db_path
        self.backup_dir = backup_dir
        
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)

    def create_snapshot(self) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"backup_{timestamp}.db"
        backup_path = os.path.join(self.backup_dir, backup_filename)
        
        try:
            # Simple file copy for SQLite
            # In production with Postgres, use pg_dump
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"Database snapshot created at {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            raise e

    def list_snapshots(self):
        files = [f for f in os.listdir(self.backup_dir) if f.endswith(".db")]
        files.sort(reverse=True) # Newest first
        return files

    def restore_snapshot(self, snapshot_filename: str):
        backup_path = os.path.join(self.backup_dir, snapshot_filename)
        if not os.path.exists(backup_path):
            raise FileNotFoundError(f"Snapshot {snapshot_filename} not found")
        
        try:
            # Create a safety backup of current state before restore
            self.create_snapshot()
            
            shutil.copy2(backup_path, self.db_path)
            logger.info(f"Database restored from {backup_path}")
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            raise e

backup_service = BackupService()
