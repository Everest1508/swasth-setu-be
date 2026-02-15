"""
ZEGOCLOUD Token04 Generation
Generates authentication tokens for ZEGOCLOUD video calls.
"""
import hashlib
import hmac
import json
import os
import struct
import time
import base64


def _pkcs5_padding(text, block_size=16):
    """PKCS5 padding for AES encryption"""
    padding_len = block_size - len(text.encode('utf-8')) % block_size
    return text + chr(padding_len) * padding_len


def _aes_cbc_encrypt(key, iv, plain_text):
    """AES CBC encryption using PyCryptodome or fallback"""
    try:
        from Crypto.Cipher import AES
        cipher = AES.new(key, AES.MODE_CBC, iv)
        return cipher.encrypt(plain_text)
    except ImportError:
        try:
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            from cryptography.hazmat.backends import default_backend
            cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
            encryptor = cipher.encryptor()
            return encryptor.update(plain_text) + encryptor.finalize()
        except ImportError:
            raise ImportError(
                "Either 'pycryptodome' or 'cryptography' package is required. "
                "Install with: pip install cryptography"
            )


def generate_token04(app_id, user_id, server_secret, effective_time_in_seconds=3600, payload=''):
    """
    Generate ZEGOCLOUD Token04 for authentication.
    
    Args:
        app_id (int): Your Zego App ID
        user_id (str): The user ID to generate token for
        server_secret (str): Your Zego Server Secret (32 characters)
        effective_time_in_seconds (int): Token validity in seconds (default 3600 = 1 hour)
        payload (str): Optional payload string
    
    Returns:
        str: Generated token string
    
    Raises:
        ValueError: If parameters are invalid
    """
    if not app_id:
        raise ValueError("app_id is required")
    if not user_id:
        raise ValueError("user_id is required")
    if not server_secret or len(server_secret) != 32:
        raise ValueError("server_secret must be a 32-character string")
    if effective_time_in_seconds <= 0:
        raise ValueError("effective_time_in_seconds must be positive")
    
    # Generate random values
    nonce = int.from_bytes(os.urandom(4), byteorder='big')
    create_time = int(time.time())
    expire_time = create_time + effective_time_in_seconds
    
    # Build token info JSON
    token_info = {
        'app_id': app_id,
        'user_id': user_id,
        'nonce': nonce,
        'ctime': create_time,
        'expire': expire_time,
        'payload': payload
    }
    
    plain_text = json.dumps(token_info, separators=(',', ':'), ensure_ascii=False)
    
    # PKCS5 padding
    padded_text = _pkcs5_padding(plain_text)
    
    # Generate IV
    iv = os.urandom(16)
    
    # AES CBC encrypt
    key = server_secret.encode('utf-8')
    encrypted = _aes_cbc_encrypt(key, iv, padded_text.encode('utf-8'))
    
    # Build binary token
    buf = bytearray()
    buf.extend(struct.pack('>q', expire_time))      # 8 bytes - expire time (big-endian)
    buf.extend(struct.pack('>H', len(iv)))           # 2 bytes - IV length
    buf.extend(iv)                                    # IV
    buf.extend(struct.pack('>H', len(encrypted)))     # 2 bytes - encrypted data length
    buf.extend(encrypted)                             # encrypted data
    
    # Token = "04" + base64(binary_data)
    token = '04' + base64.b64encode(bytes(buf)).decode('utf-8')
    
    return token
