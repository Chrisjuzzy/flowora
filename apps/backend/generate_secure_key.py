
"""
Generate a cryptographically secure SECRET_KEY for JWT token signing
"""
import secrets

# Generate a 64-byte (512-bit) random key
secure_key = secrets.token_urlsafe(64)

print("Generated secure SECRET_KEY:")
print(secure_key)
print("
Add this to your .env file:")
print(f"SECRET_KEY={secure_key}")
