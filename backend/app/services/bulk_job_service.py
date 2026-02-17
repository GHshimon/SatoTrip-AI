"""
一括追加ジョブ管理（簡易版）

- FastAPI BackgroundTasks で実行
- 進捗/結果はインメモリに保持（プロセス再起動で失われる）
"""
from __future__ import annotations

import threading
import uuid
from typing import Dict, Any, Optional

from app.utils.database import SessionLocal
from app.utils.error_handler import log_error
from app.services.spot_bulk_service import bulk_add_spots_by_prefecture


_lock = threading.Lock()
_jobs: Dict[str, Dict[str, Any]] = {}


def create_job(payload: Dict[str, Any]) -> str:
    job_id = str(uuid.uuid4())
    with _lock:
        _jobs[job_id] = {
            "job_id": job_id,
            "job_status": "queued",
            "payload": payload,
            "result": None,
            "error": None,
        }
    return job_id


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    with _lock:
        return _jobs.get(job_id)


def _update_job(job_id: str, **updates: Any) -> None:
    with _lock:
        if job_id not in _jobs:
            return
        _jobs[job_id].update(updates)


def run_bulk_add_job(job_id: str) -> None:
    """
    BackgroundTasks から呼ばれる実行関数
    """
    job = get_job(job_id)
    if not job:
        return

    payload = job.get("payload") or {}
    prefecture = payload.get("prefecture", "")

    _update_job(job_id, job_status="running")
    db = SessionLocal()
    try:
        _update_job(job_id, job_status="collecting")
        result = bulk_add_spots_by_prefecture(
            prefecture=prefecture,
            db=db,
            max_results_per_keyword=payload.get("max_results_per_keyword"),
            max_keywords=payload.get("max_keywords"),
            max_total_videos=payload.get("max_total_videos"),
            add_location=payload.get("add_location", True),
            category=payload.get("category")
        )
        # bulk_add_spots_by_prefecture内でインポート/位置情報まで完結するため、ここではstageだけ更新
        _update_job(job_id, job_status="succeeded", result=result, error=None)
    except Exception as e:
        log_error("BULK_ADD_JOB_ERROR", f"一括追加ジョブ失敗: {str(e)}", {"job_id": job_id, "prefecture": prefecture})
        _update_job(job_id, job_status="failed", result=None, error=str(e))
    finally:
        try:
            db.close()
        except Exception:
            pass


