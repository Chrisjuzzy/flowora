from cryptography.fernet import Fernet
import base64
import json
import os
from typing import Dict, Any, Union

# Use a derived key or a fixed one for demo. In prod, this should be in env.
# We'll derive a 32-byte key from SECRET_KEY if available, or generate one.
# For stability across restarts in this dev environment without persistent env vars,
# we'll use a hardcoded fallback if SECRET_KEY is not sufficient, but best practice is env.

# We will try to use the SECRET_KEY from security module if possible.
try:
    from security import SECRET_KEY
except ImportError:
    SECRET_KEY = "super-secret-key-for-dev-environment-only"

def get_fernet_key():
    # Ensure key is 32 url-safe base64-encoded bytes
    # We can hash the SECRET_KEY to get 32 bytes, then base64 encode it.
    import hashlib
    key_bytes = hashlib.sha256(SECRET_KEY.encode()).digest()
    return base64.urlsafe_b64encode(key_bytes)

_fernet = Fernet(get_fernet_key())

import logging

logger = logging.getLogger(__name__)

class EncryptionService:
    @staticmethod
    def encrypt_data(data: Union[Dict, str]) -> str:
        """Encrypts a dictionary or string into a fernet token string."""
        if isinstance(data, dict):
            text = json.dumps(data)
        else:
            text = str(data)
        
        encrypted = _fernet.encrypt(text.encode())
        return encrypted.decode()

    @staticmethod
    def decrypt_data(token: str) -> Union[Dict, str]:
        """Decrypts a fernet token string back to data."""
        if not token:
            return {}
            
        try:
            decrypted = _fernet.decrypt(token.encode()).decode()
            try:
                return json.loads(decrypted)
            except json.JSONDecodeError:
                return decrypted
        except Exception as e:
            # Fallback for unencrypted data (e.g. legacy data)
            logger.warning(f"Decryption failed, assuming plain text or error: {e}")
            try:
                # If it's a JSON string, try to parse it
                return json.loads(token)
            except:
                return token

encryption_service = EncryptionService()
