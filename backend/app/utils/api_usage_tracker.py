"""
API使用回数管理機能
各APIの呼び出し回数を記録・管理
"""
import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from collections import defaultdict

API_USAGE_FILE = "data/api_usage.json"


def load_api_usage() -> Dict[str, Dict[str, Any]]:
    """API使用量を読み込み"""
    if not os.path.exists(API_USAGE_FILE):
        return {}
    try:
        with open(API_USAGE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


def save_api_usage(usage: Dict[str, Dict[str, Any]]):
    """API使用量を保存"""
    os.makedirs(os.path.dirname(API_USAGE_FILE), exist_ok=True)
    with open(API_USAGE_FILE, "w", encoding="utf-8") as f:
        json.dump(usage, f, ensure_ascii=False, indent=2)


def record_api_call(api_name: str, endpoint: Optional[str] = None, success: bool = True, metadata: Optional[Dict[str, Any]] = None):
    """
    API呼び出しを記録
    
    Args:
        api_name: API名（例: "yahoo_local_search", "gemini", "google_places"）
        endpoint: エンドポイント名（例: "LocalSearch", "geocode"）
        success: 成功したかどうか
        metadata: 追加メタデータ
    """
    usage = load_api_usage()
    
    now = datetime.now()
    date_key = now.strftime("%Y-%m-%d")
    month_key = now.strftime("%Y-%m")
    
    # API名とエンドポイントの組み合わせ
    api_key = f"{api_name}" + (f":{endpoint}" if endpoint else "")
    
    if api_key not in usage:
        usage[api_key] = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "daily": {},
            "monthly": {},
            "last_updated": None,
        }
    
    usage[api_key]["total_calls"] += 1
    if success:
        usage[api_key]["successful_calls"] += 1
    else:
        usage[api_key]["failed_calls"] += 1
    
    # 日別統計
    if date_key not in usage[api_key]["daily"]:
        usage[api_key]["daily"][date_key] = {"calls": 0, "success": 0, "failed": 0}
    usage[api_key]["daily"][date_key]["calls"] += 1
    if success:
        usage[api_key]["daily"][date_key]["success"] += 1
    else:
        usage[api_key]["daily"][date_key]["failed"] += 1
    
    # 月別統計
    if month_key not in usage[api_key]["monthly"]:
        usage[api_key]["monthly"][month_key] = {"calls": 0, "success": 0, "failed": 0}
    usage[api_key]["monthly"][month_key]["calls"] += 1
    if success:
        usage[api_key]["monthly"][month_key]["success"] += 1
    else:
        usage[api_key]["monthly"][month_key]["failed"] += 1
    
    usage[api_key]["last_updated"] = now.isoformat()
    
    save_api_usage(usage)


def get_api_usage_stats(api_name: Optional[str] = None, days: int = 30) -> Dict[str, Any]:
    """
    API使用統計を取得
    
    Args:
        api_name: API名でフィルタ（Noneの場合は全て）
        days: 過去何日分のデータを取得するか
    
    Returns:
        統計情報
    """
    usage = load_api_usage()
    
    if api_name:
        # 特定のAPIのみ
        api_key = api_name
        if api_key in usage:
            return {
                api_key: usage[api_key]
            }
        return {}
    
    # 全てのAPI
    result = {}
    cutoff_date = (datetime.now().timestamp() - (days * 24 * 60 * 60))
    
    for api_key, data in usage.items():
        # 日別データをフィルタ
        filtered_daily = {}
        for date_key, daily_data in data.get("daily", {}).items():
            try:
                date_timestamp = datetime.strptime(date_key, "%Y-%m-%d").timestamp()
                if date_timestamp >= cutoff_date:
                    filtered_daily[date_key] = daily_data
            except:
                pass
        
        result[api_key] = {
            **data,
            "daily": filtered_daily,
        }
    
    return result


def get_api_usage_summary() -> Dict[str, Any]:
    """API使用量のサマリーを取得"""
    usage = load_api_usage()
    
    summary = {
        "total_apis": len(usage),
        "total_calls": 0,
        "total_successful": 0,
        "total_failed": 0,
        "apis": [],
    }
    
    for api_key, data in usage.items():
        summary["total_calls"] += data.get("total_calls", 0)
        summary["total_successful"] += data.get("successful_calls", 0)
        summary["total_failed"] += data.get("failed_calls", 0)
        
        success_rate = 0
        if data.get("total_calls", 0) > 0:
            success_rate = (data.get("successful_calls", 0) / data.get("total_calls", 0)) * 100
        
        summary["apis"].append({
            "name": api_key,
            "total_calls": data.get("total_calls", 0),
            "successful_calls": data.get("successful_calls", 0),
            "failed_calls": data.get("failed_calls", 0),
            "success_rate": round(success_rate, 2),
            "last_updated": data.get("last_updated"),
        })
    
    # 使用回数でソート
    summary["apis"].sort(key=lambda x: x["total_calls"], reverse=True)
    
    return summary

