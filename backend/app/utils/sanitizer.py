"""入力サニタイゼーション"""
import re
import html
from typing import Any, Dict, List


def sanitize_string(value: str, max_length: int = 1000) -> str:
    """文字列をサニタイズ"""
    if not isinstance(value, str):
        return ""
    value = html.escape(value)
    value = value.strip()
    if len(value) > max_length:
        value = value[:max_length]
    return value


def sanitize_username(username: str) -> str:
    """ユーザー名をサニタイズ（英数字とアンダースコアのみ）"""
    if not isinstance(username, str):
        return ""
    username = re.sub(r'[^a-zA-Z0-9_]', '', username)
    return username[:50]


def sanitize_email(email: str) -> str:
    """メールアドレスをサニタイズ"""
    if not isinstance(email, str):
        return ""
    email = email.strip().lower()
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if re.match(email_pattern, email):
        return email
    return ""


def sanitize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """辞書を再帰的にサニタイズ"""
    sanitized = {}
    for key, value in data.items():
        sanitized_key = sanitize_string(str(key), max_length=100)
        if isinstance(value, str):
            sanitized[sanitized_key] = sanitize_string(value)
        elif isinstance(value, dict):
            sanitized[sanitized_key] = sanitize_dict(value)
        elif isinstance(value, list):
            sanitized[sanitized_key] = [sanitize_string(str(item)) if isinstance(item, str) else item for item in value]
        else:
            sanitized[sanitized_key] = value
    return sanitized


def sanitize_sql_input(value: str) -> str:
    """SQLインジェクション対策"""
    if not isinstance(value, str):
        return ""
    value = value.replace("'", "''")
    value = value.replace(";", "")
    value = value.replace("--", "")
    return value

