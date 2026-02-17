"""
処理時間計測機能
ソース単位で処理時間を計測し、後で分析できるようにする
"""
import time
import json
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
from contextlib import contextmanager
from functools import wraps

PERFORMANCE_LOG_FILE = "data/performance_logs.json"


def load_performance_logs() -> List[Dict[str, Any]]:
    """パフォーマンスログを読み込み"""
    if not os.path.exists(PERFORMANCE_LOG_FILE):
        return []
    try:
        with open(PERFORMANCE_LOG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []


def save_performance_logs(logs: List[Dict[str, Any]]):
    """パフォーマンスログを保存"""
    os.makedirs(os.path.dirname(PERFORMANCE_LOG_FILE), exist_ok=True)
    # 最新1000件のみ保持
    logs = logs[-1000:]
    with open(PERFORMANCE_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)


@contextmanager
def track_performance(source: str, task: str, metadata: Optional[Dict[str, Any]] = None):
    """
    処理時間を計測するコンテキストマネージャー
    
    Args:
        source: ソースファイル名（例: "app/pages/2_AI旅行プラン生成.py"）
        task: タスク名（例: "generate_travel_plan"）
        metadata: 追加メタデータ（例: {"user_id": "user123", "plan_days": 2}）
    
    Usage:
        with track_performance("app/pages/2_AI旅行プラン生成.py", "generate_travel_plan", {"days": 2}):
            # 処理
            result = generate_plan()
    """
    start_time = time.time()
    start_timestamp = datetime.now().isoformat()
    
    try:
        yield
        success = True
        error = None
    except Exception as e:
        success = False
        error = str(e)
        raise
    finally:
        end_time = time.time()
        duration = end_time - start_time
        
        log_entry = {
            "timestamp": start_timestamp,
            "source": source,
            "task": task,
            "duration_seconds": round(duration, 4),
            "success": success,
            "error": error,
            "metadata": metadata or {},
        }
        
        logs = load_performance_logs()
        logs.append(log_entry)
        save_performance_logs(logs)


def track_function(source: str, task: Optional[str] = None):
    """
    関数の処理時間を計測するデコレータ
    
    Args:
        source: ソースファイル名
        task: タスク名（Noneの場合は関数名を使用）
    
    Usage:
        @track_function("app/utils/api_clients.py", "get_place_details")
        def get_place_details(place_name: str):
            # 処理
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            task_name = task or func.__name__
            metadata = {
                "function": func.__name__,
                "args_count": len(args),
                "kwargs_keys": list(kwargs.keys()),
            }
            with track_performance(source, task_name, metadata):
                return func(*args, **kwargs)
        return wrapper
    return decorator


def get_performance_stats(source: Optional[str] = None, task: Optional[str] = None, days: int = 30) -> Dict[str, Any]:
    """
    パフォーマンス統計を取得
    
    Args:
        source: ソースファイルでフィルタ（Noneの場合は全て）
        task: タスク名でフィルタ（Noneの場合は全て）
        days: 過去何日分のデータを取得するか
    
    Returns:
        統計情報（平均時間、最大時間、最小時間、実行回数など）
    """
    logs = load_performance_logs()
    
    # 日付フィルタ
    cutoff_date = datetime.now().timestamp() - (days * 24 * 60 * 60)
    
    filtered_logs = []
    for log in logs:
        try:
            log_time = datetime.fromisoformat(log["timestamp"]).timestamp()
            if log_time < cutoff_date:
                continue
        except:
            continue
        
        if source and log.get("source") != source:
            continue
        if task and log.get("task") != task:
            continue
        
        filtered_logs.append(log)
    
    if not filtered_logs:
        return {
            "count": 0,
            "avg_duration": 0,
            "min_duration": 0,
            "max_duration": 0,
            "success_rate": 0,
        }
    
    durations = [log["duration_seconds"] for log in filtered_logs]
    successes = [log for log in filtered_logs if log.get("success", True)]
    
    return {
        "count": len(filtered_logs),
        "avg_duration": round(sum(durations) / len(durations), 4),
        "min_duration": round(min(durations), 4),
        "max_duration": round(max(durations), 4),
        "success_rate": round(len(successes) / len(filtered_logs) * 100, 2),
        "total_duration": round(sum(durations), 4),
    }


def get_performance_by_source(days: int = 30) -> Dict[str, Dict[str, Any]]:
    """ソース単位でパフォーマンス統計を取得"""
    logs = load_performance_logs()
    
    cutoff_date = datetime.now().timestamp() - (days * 24 * 60 * 60)
    
    source_stats = {}
    
    for log in logs:
        try:
            log_time = datetime.fromisoformat(log["timestamp"]).timestamp()
            if log_time < cutoff_date:
                continue
        except:
            continue
        
        source = log.get("source", "unknown")
        if source not in source_stats:
            source_stats[source] = {
                "count": 0,
                "total_duration": 0,
                "tasks": {},
            }
        
        source_stats[source]["count"] += 1
        source_stats[source]["total_duration"] += log.get("duration_seconds", 0)
        
        task = log.get("task", "unknown")
        if task not in source_stats[source]["tasks"]:
            source_stats[source]["tasks"][task] = {
                "count": 0,
                "total_duration": 0,
            }
        
        source_stats[source]["tasks"][task]["count"] += 1
        source_stats[source]["tasks"][task]["total_duration"] += log.get("duration_seconds", 0)
    
    # 平均時間を計算
    for source in source_stats:
        if source_stats[source]["count"] > 0:
            source_stats[source]["avg_duration"] = round(
                source_stats[source]["total_duration"] / source_stats[source]["count"],
                4
            )
        for task in source_stats[source]["tasks"]:
            task_data = source_stats[source]["tasks"][task]
            if task_data["count"] > 0:
                task_data["avg_duration"] = round(
                    task_data["total_duration"] / task_data["count"],
                    4
                )
    
    return source_stats

