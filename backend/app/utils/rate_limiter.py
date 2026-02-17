"""
レート制限機能
API呼び出しの制限、不正アクセス防止
"""
from sqlalchemy.orm import Session
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta

# レート制限設定
RATE_LIMITS = {
    "free": {
        "requests_per_minute": 5,
        "requests_per_hour": 20,
        "requests_per_day": 50,
    },
    "basic": {
        "requests_per_minute": 20,
        "requests_per_hour": 100,
        "requests_per_day": 500,
    },
    "premium": {
        "requests_per_minute": 60,
        "requests_per_hour": 500,
        "requests_per_day": -1,  # unlimited
    }
}


class RateLimiter:
    def __init__(self):
        # メモリベースのリクエスト履歴（高速化のため）
        # 本番環境では Redis などの使用を推奨
        self.requests: Dict[str, list] = {}
    
    def check_limit(self, db: Session, user_id: str, plan: str = "free") -> Tuple[bool, Optional[str]]:
        """
        レート制限をチェック
        Returns: (allowed, error_message)
        """
        now = datetime.now()
        limits = RATE_LIMITS.get(plan, RATE_LIMITS["free"])
        
        # ユーザーのリクエスト履歴を取得（メモリから）
        user_requests = self.requests.get(user_id, [])
        
        # 古いリクエストを削除（24時間以上前）
        cutoff = now - timedelta(hours=24)
        user_requests = [req for req in user_requests if req > cutoff]
        self.requests[user_id] = user_requests
        
        # 1分間の制限
        minute_ago = now - timedelta(minutes=1)
        recent_minute = [r for r in user_requests if r > minute_ago]
        if len(recent_minute) >= limits["requests_per_minute"]:
            return False, f"1分間に{limits['requests_per_minute']}回まで。しばらくお待ちください。"
        
        # 1時間の制限
        hour_ago = now - timedelta(hours=1)
        recent_hour = [r for r in user_requests if r > hour_ago]
        if limits["requests_per_hour"] > 0 and len(recent_hour) >= limits["requests_per_hour"]:
            return False, f"1時間に{limits['requests_per_hour']}回まで。しばらくお待ちください。"
        
        # 1日の制限
        day_ago = now - timedelta(days=1)
        recent_day = [r for r in user_requests if r > day_ago]
        if limits["requests_per_day"] > 0 and len(recent_day) >= limits["requests_per_day"]:
            return False, f"1日に{limits['requests_per_day']}回まで。明日またお試しください。"
        
        # リクエストを記録
        user_requests.append(now)
        self.requests[user_id] = user_requests
        
        return True, None
    
    def check_limit_by_api_key(
        self,
        db: Session,
        api_key_id: str,
        rate_limit_per_minute: int,
        rate_limit_per_hour: int,
        rate_limit_per_day: int
    ) -> Tuple[bool, Optional[str]]:
        """
        APIキー単位のレート制限をチェック
        Returns: (allowed, error_message)
        """
        now = datetime.now()
        
        # APIキーのリクエスト履歴を取得（メモリから）
        key = f"api_key_{api_key_id}"
        key_requests = self.requests.get(key, [])
        
        # 古いリクエストを削除（24時間以上前）
        cutoff = now - timedelta(hours=24)
        key_requests = [req for req in key_requests if req > cutoff]
        self.requests[key] = key_requests
        
        # 1分間の制限
        minute_ago = now - timedelta(minutes=1)
        recent_minute = [r for r in key_requests if r > minute_ago]
        if len(recent_minute) >= rate_limit_per_minute:
            return False, f"1分間に{rate_limit_per_minute}回まで。しばらくお待ちください。"
        
        # 1時間の制限
        hour_ago = now - timedelta(hours=1)
        recent_hour = [r for r in key_requests if r > hour_ago]
        if rate_limit_per_hour > 0 and len(recent_hour) >= rate_limit_per_hour:
            return False, f"1時間に{rate_limit_per_hour}回まで。しばらくお待ちください。"
        
        # 1日の制限
        day_ago = now - timedelta(days=1)
        recent_day = [r for r in key_requests if r > day_ago]
        if rate_limit_per_day > 0 and len(recent_day) >= rate_limit_per_day:
            return False, f"1日に{rate_limit_per_day}回まで。明日またお試しください。"
        
        # リクエストを記録
        key_requests.append(now)
        self.requests[key] = key_requests
        
        return True, None


# グローバルインスタンス
rate_limiter = RateLimiter()

