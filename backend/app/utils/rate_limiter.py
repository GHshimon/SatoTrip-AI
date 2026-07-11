"""
レート制限機能
API呼び出しの制限、不正アクセス防止

REDIS_URL が設定されていれば Redis を共有ストアとして使い、複数ワーカー/インスタンス
間で一貫したレート制限を行う。未設定または接続失敗時はプロセス内メモリにフォールバック
する（単一ワーカー向け。従来挙動）。
"""
import time
import logging
import secrets
from sqlalchemy.orm import Session
from typing import Dict, Optional, Tuple, List
from datetime import datetime, timedelta

from app.config import settings

logger = logging.getLogger(__name__)

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

# 各ウィンドウの秒数
_WINDOWS = {
    "minute": 60,
    "hour": 3600,
    "day": 86400,
}

# Redis クライアントの初期化（任意）
_redis = None
if settings.REDIS_URL:
    try:
        import redis as _redis_lib
        _redis = _redis_lib.from_url(settings.REDIS_URL, decode_responses=True)
        _redis.ping()
        logger.info("レート制限: Redis を使用します")
    except Exception as e:
        logger.warning("レート制限: Redis 接続に失敗したためメモリにフォールバックします: %s", str(e))
        _redis = None


class RateLimiter:
    def __init__(self):
        # メモリベースのリクエスト履歴（Redis未使用時のフォールバック）
        self.requests: Dict[str, list] = {}

    # ---- 共通ロジック ----

    def _limits_to_windows(self, limits: dict) -> List[Tuple[str, int, str]]:
        """(window名, 上限, エラーメッセージ) のリストを返す。上限<=0は無制限で除外。"""
        specs = [
            ("minute", limits["requests_per_minute"], "1分間に{n}回まで。しばらくお待ちください。"),
            ("hour", limits["requests_per_hour"], "1時間に{n}回まで。しばらくお待ちください。"),
            ("day", limits["requests_per_day"], "1日に{n}回まで。明日またお試しください。"),
        ]
        return [(w, lim, msg.format(n=lim)) for (w, lim, msg) in specs if lim and lim > 0]

    def _check_and_record(self, key: str, limits: dict) -> Tuple[bool, Optional[str]]:
        """バックエンド（Redis or メモリ）を選んでレート制限を判定・記録する。"""
        windows = self._limits_to_windows(limits)
        if _redis is not None:
            try:
                return self._check_redis(key, windows)
            except Exception as e:
                logger.warning("レート制限: Redis エラーのためメモリにフォールバック: %s", str(e))
        return self._check_memory(key, windows)

    def _check_redis(self, key: str, windows: List[Tuple[str, int, str]]) -> Tuple[bool, Optional[str]]:
        now = time.time()
        redis_key = f"ratelimit:{key}"
        max_window = max((_WINDOWS[w] for (w, _, _) in windows), default=86400)

        # 最大ウィンドウより古いエントリを削除
        _redis.zremrangebyscore(redis_key, 0, now - max_window)

        # 各ウィンドウで件数を確認
        for (w, lim, msg) in windows:
            count = _redis.zcount(redis_key, now - _WINDOWS[w], now)
            if count >= lim:
                return False, msg

        # 記録（スコア=時刻、メンバーは一意にする）
        member = f"{now}:{secrets.token_hex(4)}"
        _redis.zadd(redis_key, {member: now})
        _redis.expire(redis_key, max_window)
        return True, None

    def _check_memory(self, key: str, windows: List[Tuple[str, int, str]]) -> Tuple[bool, Optional[str]]:
        now = datetime.now()
        reqs = self.requests.get(key, [])
        cutoff = now - timedelta(seconds=86400)
        reqs = [r for r in reqs if r > cutoff]
        self.requests[key] = reqs

        for (w, lim, msg) in windows:
            window_start = now - timedelta(seconds=_WINDOWS[w])
            count = len([r for r in reqs if r > window_start])
            if count >= lim:
                return False, msg

        reqs.append(now)
        self.requests[key] = reqs
        return True, None

    # ---- 公開API（従来と同一シグネチャ） ----

    def check_limit(self, db: Session, user_id: str, plan: str = "free") -> Tuple[bool, Optional[str]]:
        """レート制限をチェック。Returns: (allowed, error_message)"""
        limits = RATE_LIMITS.get(plan, RATE_LIMITS["free"])
        return self._check_and_record(f"user:{user_id}", limits)

    def check_limit_by_api_key(
        self,
        db: Session,
        api_key_id: str,
        rate_limit_per_minute: int,
        rate_limit_per_hour: int,
        rate_limit_per_day: int
    ) -> Tuple[bool, Optional[str]]:
        """APIキー単位のレート制限をチェック。Returns: (allowed, error_message)"""
        limits = {
            "requests_per_minute": rate_limit_per_minute,
            "requests_per_hour": rate_limit_per_hour,
            "requests_per_day": rate_limit_per_day,
        }
        return self._check_and_record(f"api_key:{api_key_id}", limits)


# グローバルインスタンス
rate_limiter = RateLimiter()
