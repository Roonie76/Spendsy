from __future__ import annotations

import base64
import logging
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.fernet import Fernet
from app.core.config import settings

logger = logging.getLogger("finance.crypto")

_aesgcm: AESGCM | None = None
_fernet_fallback: Fernet | None = None

def _get_key_bytes(key_str: str) -> bytes:
    try:
        # Try to decode as base64
        key_bytes = base64.b64decode(key_str)
        # Pad or truncate to 32 bytes (256 bits) for AES-256
        if len(key_bytes) < 32:
            key_bytes = key_bytes.ljust(32, b'\0')
        elif len(key_bytes) > 32:
            key_bytes = key_bytes[:32]
        return key_bytes
    except Exception:
        # If not valid base64, grab raw bytes and pad/truncate
        key_bytes = key_str.encode()
        if len(key_bytes) < 32:
            key_bytes = key_bytes.ljust(32, b'\0')
        elif len(key_bytes) > 32:
            key_bytes = key_bytes[:32]
        return key_bytes

def get_aesgcm() -> tuple[AESGCM, Fernet | None]:
    global _aesgcm, _fernet_fallback
    if _aesgcm is None:
        if not settings.encryption_key:
            logger.warning("ENCRYPTION_KEY not set. Generating temporary key.")
            key_bytes = AESGCM.generate_key(bit_length=256)
            _aesgcm = AESGCM(key_bytes)
            _fernet_fallback = Fernet(Fernet.generate_key())
        else:
            try:
                # Primary AES-256-GCM cipher
                key_bytes = _get_key_bytes(settings.encryption_key)
                _aesgcm = AESGCM(key_bytes)
                
                # Fallback Fernet cipher
                try:
                    _fernet_fallback = Fernet(settings.encryption_key.encode())
                except Exception:
                    _fernet_fallback = None

            except Exception as exc:
                logger.error("invalid_encryption_key: %s", str(exc))
                raise ValueError("INVALID_ENCRYPTION_KEY: Could not initialize AES-256-GCM.") from exc
    return _aesgcm, _fernet_fallback


def encrypt_string(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        aesgcm, _ = get_aesgcm()
        nonce = os.urandom(12)
        encrypted_data = aesgcm.encrypt(nonce, value.encode(), None)
        return base64.b64encode(nonce + encrypted_data).decode()
    except Exception as exc:
        logger.error("encryption_failed: %s", str(exc))
        return value


def decrypt_string(encrypted_value: str | None) -> str | None:
    if encrypted_value is None:
        return None
    try:
        aesgcm, fernet_fallback = get_aesgcm()
        
        # 1. Try generic Base64 decode for AES-256-GCM
        try:
            data = base64.b64decode(encrypted_value)
            if len(data) >= 12:
                nonce = data[:12]
                ciphertext = data[12:]
                # Will raise exception if tag doesn't match or not GCM
                return aesgcm.decrypt(nonce, ciphertext, None).decode()
        except Exception:
            logger.debug("AES-GCM decryption failed, trying Fernet fallback")
            
        # 2. Try Fernet fallback for legacy data
        if fernet_fallback:
            return fernet_fallback.decrypt(encrypted_value.encode()).decode()
            
        return encrypted_value
    except Exception:
        return encrypted_value
