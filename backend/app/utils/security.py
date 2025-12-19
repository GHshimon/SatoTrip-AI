"""
セキュリティ機能
パスワード強度チェック、ログイン試行回数制限など
既存のSatoTripプロジェクトの実装を参考
"""
import re
import bcrypt
from typing import Tuple, Optional
import json
import os
from datetime import datetime, timedelta

LOGIN_ATTEMPTS_FILE = "data/login_attempts.json"
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15


def hash_password(password: str) -> str:
    """パスワードをハッシュ化"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """パスワードを検証"""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def validate_password(password: str) -> Tuple[bool, str]:
    """パスワード強度をチェック"""
    if len(password) < 8:
        return False, "パスワードは8文字以上である必要があります"
    if not re.search(r'[A-Z]', password):
        return False, "大文字を含めてください"
    if not re.search(r'[a-z]', password):
        return False, "小文字を含めてください"
    if not re.search(r'\d', password):
        return False, "数字を含めてください"
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "記号を含めてください"
    return True, ""


def load_login_attempts() -> dict:
    """ログイン試行履歴を読み込み"""
    if not os.path.exists(LOGIN_ATTEMPTS_FILE):
        return {}
    try:
        with open(LOGIN_ATTEMPTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


def save_login_attempts(attempts: dict):
    """ログイン試行履歴を保存"""
    os.makedirs(os.path.dirname(LOGIN_ATTEMPTS_FILE), exist_ok=True)
    with open(LOGIN_ATTEMPTS_FILE, "w", encoding="utf-8") as f:
        json.dump(attempts, f, ensure_ascii=False, indent=2)


def check_login_lockout(username: str) -> Tuple[bool, Optional[str]]:
    """
    ログインロックアウトをチェック
    Returns: (is_locked, message)
    """
    attempts = load_login_attempts()
    user_attempts = attempts.get(username, {})
    
    if not user_attempts:
        return False, None
    
    failed_count = user_attempts.get("failed_count", 0)
    locked_until = user_attempts.get("locked_until")
    
    # ロックアウト期間チェック
    if locked_until:
        locked_time = datetime.fromisoformat(locked_until)
        if datetime.now() < locked_time:
            remaining = int((locked_time - datetime.now()).total_seconds() / 60)
            return True, f"アカウントがロックされています。{remaining}分後に再試行できます。"
        else:
            # ロックアウト期間終了
            attempts[username] = {"failed_count": 0}
            save_login_attempts(attempts)
    
    # 試行回数チェック
    if failed_count >= MAX_LOGIN_ATTEMPTS:
        lockout_time = datetime.now() + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
        attempts[username] = {
            "failed_count": failed_count,
            "locked_until": lockout_time.isoformat(),
        }
        save_login_attempts(attempts)
        return True, f"ログイン試行回数の上限に達しました。{LOCKOUT_DURATION_MINUTES}分後に再試行できます。"
    
    return False, None


def record_login_attempt(username: str, success: bool):
    """ログイン試行を記録"""
    attempts = load_login_attempts()
    
    if username not in attempts:
        attempts[username] = {"failed_count": 0}
    
    if success:
        attempts[username] = {"failed_count": 0}
    else:
        attempts[username]["failed_count"] = attempts[username].get("failed_count", 0) + 1
    
    save_login_attempts(attempts)

