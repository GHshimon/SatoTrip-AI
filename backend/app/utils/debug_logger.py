"""
デバッグログユーティリティ
YouTube検索からデータベース追加までの各処理ステップをJSON形式で記録
"""
import os
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from threading import Lock

# ログディレクトリ
LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

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


def finalize_debug_log(summary: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """
    ログセッションを終了してファイルに保存
    
    Args:
        summary: サマリー情報
    
    Returns:
        保存されたファイルパス（セッションがない場合はNone）
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
            
            # ファイル名を生成（YYYYMMDD_HHMMSS形式）
            now = datetime.now()
            filename = f"debug_{now.strftime('%Y%m%d_%H%M%S')}.json"
            filepath = os.path.join(LOGS_DIR, filename)
            
            # JSONファイルに保存
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(_current_session, f, ensure_ascii=False, indent=2)
                
                saved_path = filepath
            except Exception as e:
                # エラーが発生してもセッションはクリア
                saved_path = None
            
            # セッションをクリア
            _current_session = None
            
            return saved_path
    
    return None


def get_current_session() -> Optional[Dict[str, Any]]:
    """
    現在のセッション情報を取得（デバッグ用）
    
    Returns:
        現在のセッション情報（セッションがない場合はNone）
    """
    return _current_session

