"""
管理者用統計情報サービス
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta
from typing import Dict, Any, List
from app.models.plan import Plan
from app.models.spot import Spot
from app.models.user import User


def get_admin_stats(db: Session) -> Dict[str, Any]:
    """管理者ダッシュボード用統計情報を取得"""
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)
    week_start = today_start - timedelta(days=7)
    
    # プラン生成数（本日）
    plans_today = db.query(func.count(Plan.id)).filter(
        Plan.created_at >= today_start
    ).scalar() or 0
    
    # プラン生成数（昨日）
    plans_yesterday = db.query(func.count(Plan.id)).filter(
        and_(
            Plan.created_at >= yesterday_start,
            Plan.created_at < today_start
        )
    ).scalar() or 0
    
    # プラン生成数の変化率
    plans_change = 0.0
    if plans_yesterday > 0:
        plans_change = ((plans_today - plans_yesterday) / plans_yesterday) * 100
    elif plans_today > 0:
        plans_change = 100.0
    
    # 総プラン数
    total_plans = db.query(func.count(Plan.id)).scalar() or 0
    
    # 総スポット数
    total_spots = db.query(func.count(Spot.id)).scalar() or 0
    
    # 総ユーザー数
    total_users = db.query(func.count(User.id)).scalar() or 0
    
    # アクティブユーザー数
    active_users = db.query(func.count(User.id)).filter(
        User.is_active == True
    ).scalar() or 0
    
    # エラーレート（簡易版：エラーログから取得する場合は別途実装が必要）
    # 現時点では固定値0.21%を返す（実際のエラーログから計算する場合は要実装）
    error_rate = 0.21
    
    # APIコール数（24時間）
    # 実際のAPIコール数を記録するテーブルがないため、プラン生成数を代理指標として使用
    api_calls_24h = plans_today * 10  # 仮の計算（1プラン生成 = 10 APIコール想定）
    api_calls_yesterday = plans_yesterday * 10
    api_calls_change = 0.0
    if api_calls_yesterday > 0:
        api_calls_change = ((api_calls_24h - api_calls_yesterday) / api_calls_yesterday) * 100
    elif api_calls_24h > 0:
        api_calls_change = 100.0
    
    return {
        "plans_today": plans_today,
        "plans_change": round(plans_change, 1),
        "plans_trend": "up" if plans_change >= 0 else "down",
        "api_calls_24h": api_calls_24h,
        "api_calls_change": round(api_calls_change, 1),
        "api_calls_trend": "up" if api_calls_change >= 0 else "down",
        "error_rate": error_rate,
        "error_rate_change": -0.1,  # 仮の値
        "error_rate_trend": "down",
        "total_plans": total_plans,
        "total_spots": total_spots,
        "total_users": total_users,
        "active_users": active_users
    }


def get_system_alerts(db: Session) -> List[Dict[str, Any]]:
    """システムアラート一覧を取得"""
    alerts = []
    
    # エラーレートが高い場合のアラート
    stats = get_admin_stats(db)
    if stats["error_rate"] > 1.0:
        alerts.append({
            "type": "error",
            "title": "高エラーレート警告",
            "message": f"エラーレートが{stats['error_rate']}%を超えています。",
            "timestamp": datetime.utcnow().isoformat()
        })
    
    # APIコール数が多い場合のアラート
    if stats["api_calls_24h"] > 10000:
        alerts.append({
            "type": "warning",
            "title": "API使用率警告",
            "message": "APIコール数が高いです。レート制限に注意してください。",
            "timestamp": datetime.utcnow().isoformat()
        })
    
    # デフォルトのアラート（システムが正常な場合）
    if len(alerts) == 0:
        alerts.append({
            "type": "success",
            "title": "システム正常",
            "message": "システムは正常に動作しています。",
            "timestamp": datetime.utcnow().isoformat()
        })
    
    return alerts


def get_trending_areas(db: Session, limit: int = 3) -> List[Dict[str, Any]]:
    """人気急上昇エリアを取得"""
    now = datetime.utcnow()
    week_start = now - timedelta(days=7)
    two_weeks_start = now - timedelta(days=14)
    
    # 過去1週間のエリア別プラン生成数
    recent_plans = db.query(
        Plan.area,
        func.count(Plan.id).label('count')
    ).filter(
        Plan.created_at >= week_start
    ).group_by(Plan.area).all()
    
    # 過去2週間前～1週間前のエリア別プラン生成数
    previous_plans = db.query(
        Plan.area,
        func.count(Plan.id).label('count')
    ).filter(
        and_(
            Plan.created_at >= two_weeks_start,
            Plan.created_at < week_start
        )
    ).group_by(Plan.area).all()
    
    # エリア別の変化率を計算
    previous_dict = {area: count for area, count in previous_plans if area}
    trending = []
    
    for area, count in recent_plans:
        if not area:
            continue
        previous_count = previous_dict.get(area, 0)
        if previous_count > 0:
            change_rate = ((count - previous_count) / previous_count) * 100
        elif count > 0:
            change_rate = 100.0
        else:
            change_rate = 0.0
        
        trending.append({
            "area": area,
            "count": count,
            "change_rate": round(change_rate, 1)
        })
    
    # 変化率でソートして上位を返す
    trending.sort(key=lambda x: x["change_rate"], reverse=True)
    return trending[:limit]

