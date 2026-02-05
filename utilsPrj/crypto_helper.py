# utils/crypto_helper.py
import base64
from django.conf import settings

def encrypt_value(value: str) -> str:
    """문자열 → Fernet 암호화 → Base64 문자열"""
    encrypted_bytes = settings.FERNET.encrypt(value.encode())
    return base64.b64encode(encrypted_bytes).decode()

def decrypt_value(encrypted_base64: str) -> str:
    """Base64 문자열 → Fernet 복호화 → 평문"""
    encrypted_bytes = base64.b64decode(encrypted_base64.encode())
    return settings.FERNET.decrypt(encrypted_bytes).decode()
