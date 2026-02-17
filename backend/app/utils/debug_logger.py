"""
デバッグログユーティリティ
YouTube検索からデータベース追加までの各処理ステップをJSON形式で記録
"""
import os
import json
import uuid
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
from threading import Lock

# デバッグログファイルパス
DEBUG_LOG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs', 'debug.log')
# ディレクトリが存在しない場合は作成
log_dir = os.path.dirname(DEBUG_LOG_PATH)
os.makedirs(log_dir, exist_ok=True)

# スレッドセーフなログ管理
_log_lock = Lock()
_current_session: Optional[Dict[str, Any]] = None


def init_debug_log(prefecture: str, **kwargs) -> str:
    """
    デバッグログセッションを開始
    
    Args:
        prefecture: 都道府県名
        **kwargs: 追加情報（max_keywords, max_total_videos等）
    
    Returns:
        セッションID
    """
    global _current_session
    
    session_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()
    
    with _log_lock:
        _current_session = {
            "session_id": session_id,
            "prefecture": prefecture,
            "started_at": timestamp,
            "config": kwargs,
            "steps": [],
            "summary": {}
        }
        
        # セッション開始を1行JSON形式でdebug.logに追記
        try:
            log_entry = {
                "location": "debug_logger.py:init_debug_log",
                "message": "Debug session started",
                "data": {
                    "session_id": session_id,
                    "prefecture": prefecture,
                    "config": kwargs
                },
                "timestamp": int(time.time() * 1000),
                "sessionId": session_id,
                "runId": "run1",
                "hypothesisId": "SESSION_START"
            }
            with open(DEBUG_LOG_PATH, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
        except Exception:
            pass  # ログ書き込みエラーは無視
    
    return session_id


def log_debug_step(
    step: str,
    status: str,
    data: Optional[Dict[str, Any]] = None,
    keyword: Optional[str] = None,
    video_title: Optional[str] = None,
    error: Optional[str] = None
) -> None:
    """
    各処理ステップのログを記録
    
    Args:
        step: ステップ名（keyword_generation, youtube_search, gemini_summary, spot_import, location_assignment）
        status: ステータス（started, completed, error）
        data: 追加データ
        keyword: キーワード（youtube_searchの場合）
        video_title: 動画タイトル（gemini_summaryの場合）
        error: エラーメッセージ（エラー時）
    """
    global _current_session
    
    if _current_session is None:
        return  # セッションが開始されていない場合は何もしない
    
    timestamp = datetime.now().isoformat()
    
    step_entry: Dict[str, Any] = {
        "step": step,
        "timestamp": timestamp,
        "status": status
    }
    
    if keyword:
        step_entry["keyword"] = keyword
    
    if video_title:
        step_entry["video_title"] = video_title
    
    if data:
        step_entry["data"] = data
    
    if error:
        step_entry["error"] = error
    
    with _log_lock:
        if _current_session:
            _current_session["steps"].append(step_entry)
            
            # 各ステップを1行JSON形式でdebug.logにリアルタイム追記
            try:
                log_data = {
                    "step": step,
                    "status": status
                }
                if keyword:
                    log_data["keyword"] = keyword
                if video_title:
                    log_data["video_title"] = video_title
                if data:
                    log_data.update(data)
                if error:
                    log_data["error"] = error
                
                log_entry = {
                    "location": f"debug_logger.py:log_debug_step",
                    "message": f"{step} - {status}",
                    "data": log_data,
                    "timestamp": int(time.time() * 1000),
                    "sessionId": _current_session.get("session_id", "unknown"),
                    "runId": "run1",
                    "hypothesisId": step.upper()
                }
                with open(DEBUG_LOG_PATH, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
            except Exception:
                pass  # ログ書き込みエラーは無視


def finalize_debug_log(summary: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """
    ログセッションを終了してdebug.logに記録
    
    Args:
        summary: サマリー情報
    
    Returns:
        常にNone（以前の互換性のため）
    """
    global _current_session
    
    if _current_session is None:
        return None
    
    timestamp = datetime.now().isoformat()
    
    with _log_lock:
        if _current_session:
            _current_session["completed_at"] = timestamp
            
            if summary:
                _current_session["summary"] = summary
            
            # セッション終了を1行JSON形式でdebug.logに追記
            try:
                log_data = {
                    "session_id": _current_session.get("session_id"),
                    "prefecture": _current_session.get("prefecture"),
                    "started_at": _current_session.get("started_at"),
                    "completed_at": timestamp,
                    "total_steps": len(_current_session.get("steps", []))
                }
                if summary:
                    log_data["summary"] = summary
                
                log_entry = {
                    "location": "debug_logger.py:finalize_debug_log",
                    "message": "Debug session completed",
                    "data": log_data,
                    "timestamp": int(time.time() * 1000),
                    "sessionId": _current_session.get("session_id", "unknown"),
                    "runId": "run1",
                    "hypothesisId": "SESSION_END"
                }
                with open(DEBUG_LOG_PATH, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
            except Exception:
                pass  # ログ書き込みエラーは無視
            
            # セッションをクリア
            _current_session = None
            
            return None
    
    return None


def get_current_session() -> Optional[Dict[str, Any]]:
    """
    現在のセッション情報を取得（デバッグ用）
    
    Returns:
        現在のセッション情報（セッションがない場合はNone）
    """
    return _current_session

