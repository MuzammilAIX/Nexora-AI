"""
Symmetric encryption for stored integration credentials.
"""
from cryptography.fernet import Fernet

from .config import settings


def _fernet() -> Fernet:
    if not settings.FERNET_KEY:
        raise RuntimeError("FERNET_KEY is not set in .env")
    return Fernet(settings.FERNET_KEY.encode())


def encrypt_token(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_token(ciphertext: str) -> str:
    return _fernet().decrypt(ciphertext.encode()).decode()
