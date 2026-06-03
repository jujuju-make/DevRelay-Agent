"""用户认证服务：密码哈希、JWT 签发与验证。"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import jose.jwt as jose_jwt
from jose.exceptions import JWTError

from app.config import get_settings


def hash_password(password: str) -> str:
    """对明文密码进行 bcrypt 哈希（使用 hashlib + 随机盐）。"""
    salt = secrets.token_hex(16)  # 32 字符十六进制盐
    pwd_hash = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt.encode("utf-8"),
        n=16384,
        r=8,
        p=1,
        dklen=64,
    )
    return f"scrypt$:{salt}:{pwd_hash.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """校验明文密码与哈希值是否匹配。"""
    try:
        _, salt, stored_hash = hashed_password.split(":", 2)
        pwd_hash = hashlib.scrypt(
            plain_password.encode("utf-8"),
            salt=salt.encode("utf-8"),
            n=16384,
            r=8,
            p=1,
            dklen=64,
        )
        return pwd_hash.hex() == stored_hash
    except (ValueError, AttributeError):
        return False


def create_access_token(data: dict) -> str:
    """生成 JWT access_token。

    注意：python-jose 要求 sub 字段必须为字符串。
    """
    settings = get_settings()
    to_encode = data.copy()
    # 确保 sub 为字符串类型（python-jose 要求）
    if "sub" in to_encode:
        to_encode["sub"] = str(to_encode["sub"])
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    to_encode.update({"exp": expire})
    return jose_jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict | None:
    """解码 JWT token，失败返回 None。"""
    settings = get_settings()
    try:
        payload = jose_jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError:
        return None
