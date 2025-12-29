"""
時刻計算ユーティリティ
プランのタイムスケジュールの時刻を正確に計算・再計算する
"""
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from app.utils.route_service import get_route_info


def calculate_spot_distances(
    spots: List[Dict[str, Any]],
    transportation: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    スポット間の距離・移動時間を計算
    
    Args:
        spots: スポットリスト（location情報を含む）
        transportation: 交通手段（driving, walking, transit）
    
    Returns:
        距離・時間情報のリスト
    """
    distances = []
    
    # 交通手段をプロファイルに変換
    profile_map = {
        "車": "driving",
        "電車": "transit",
        "バス": "transit",
        "徒歩": "walking",
        "その他": "driving"
    }
    profile = profile_map.get(transportation, "driving") if transportation else "driving"
    
    for i in range(len(spots) - 1):
        spot1 = spots[i]
        spot2 = spots[i + 1]
        
        loc1 = spot1.get("location", {})
        loc2 = spot2.get("location", {})
        
        lat1 = loc1.get("lat") or loc1.get("latitude")
        lng1 = loc1.get("lng") or loc1.get("longitude")
        lat2 = loc2.get("lat") or loc2.get("latitude")
        lng2 = loc2.get("lng") or loc2.get("longitude")
        
        if lat1 and lng1 and lat2 and lng2:
            try:
                route_info = get_route_info(
                    coordinates=[(lat1, lng1), (lat2, lng2)],
                    profile=profile
                )
                
                if route_info:
                    distances.append({
                        "from": spot1.get("name", ""),
                        "to": spot2.get("name", ""),
                        "distance_km": route_info.get("distance_km", 0),
                        "duration_minutes": route_info.get("duration_minutes", 0)
                    })
            except Exception:
                # エラー時はスキップ
                pass
    
    return distances


def recalculate_spot_times(
    spots: List[Dict[str, Any]],
    start_time: str = "09:00",
    end_time: Optional[str] = None,
    transportation: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    スポットの開始時刻を再計算
    
    Args:
        spots: スポットリスト（day, durationMinutes, transportDurationを含む）
        start_time: 1日の開始時間（HH:MM形式）
        end_time: 1日の終了時間（HH:MM形式、オプション）
        transportation: 交通手段
    
    Returns:
        時刻を再計算したスポットリスト
    """
    from datetime import datetime as dt
    
    # 日ごとにグループ化
    spots_by_day = {}
    for spot in spots:
        day = spot.get("day", 1)
        if day not in spots_by_day:
            spots_by_day[day] = []
        spots_by_day[day].append(spot)
    
    recalculated_spots = []
    
    for day in sorted(spots_by_day.keys()):
        day_spots = spots_by_day[day]
        
        # 開始時刻をパース
        start_hour, start_minute = map(int, start_time.split(":"))
        current_time = dt(2000, 1, 1, start_hour, start_minute)
        
        # 終了時刻をパース（オプション）
        end_dt = None
        if end_time:
            end_hour, end_minute = map(int, end_time.split(":"))
            end_dt = dt(2000, 1, 1, end_hour, end_minute)
        
        for i, spot in enumerate(day_spots):
            # 開始時刻を設定
            spot["startTime"] = current_time.strftime("%H:%M")
            
            # 滞在時間を取得
            duration_minutes = spot.get("durationMinutes", 60)
            
            # 終了時刻を計算
            end_spot_time = current_time + timedelta(minutes=duration_minutes)
            
            # 次のスポットへの移動時間を計算
            if i < len(day_spots) - 1:
                next_spot = day_spots[i + 1]
                
                # 既存の移動時間を使用、または計算
                transport_duration = spot.get("transportDuration", 0)
                
                # 位置情報がある場合は実際の移動時間を計算
                if not transport_duration or transport_duration == 0:
                    loc1 = spot.get("location", {})
                    loc2 = next_spot.get("location", {})
                    
                    lat1 = loc1.get("lat") or loc1.get("latitude")
                    lng1 = loc1.get("lng") or loc1.get("longitude")
                    lat2 = loc2.get("lat") or loc2.get("latitude")
                    lng2 = loc2.get("lng") or loc2.get("longitude")
                    
                    if lat1 and lng1 and lat2 and lng2:
                        # 交通手段をプロファイルに変換
                        profile_map = {
                            "車": "driving",
                            "電車": "transit",
                            "バス": "transit",
                            "徒歩": "walking",
                            "その他": "driving"
                        }
                        profile = profile_map.get(transportation, "driving") if transportation else "driving"
                        
                        try:
                            route_info = get_route_info(
                                coordinates=[(lat1, lng1), (lat2, lng2)],
                                profile=profile
                            )
                            
                            if route_info:
                                transport_duration = int(route_info.get("duration_minutes", 20))
                        except Exception:
                            # エラー時はデフォルト値を使用
                            transport_duration = 20
                    else:
                        # 位置情報がない場合はデフォルト値
                        transport_duration = 20
                
                spot["transportDuration"] = transport_duration
                
                # 次のスポットの開始時刻を計算
                current_time = end_spot_time + timedelta(minutes=transport_duration)
            else:
                # 最後のスポット
                current_time = end_spot_time
            
            # 終了時間の制約チェック
            if end_dt and current_time > end_dt:
                # 終了時間を超える場合は調整
                # 最後のスポットの滞在時間を短縮
                if i == len(day_spots) - 1:
                    max_duration = (end_dt - (current_time - timedelta(minutes=duration_minutes))).total_seconds() / 60
                    if max_duration > 0:
                        spot["durationMinutes"] = int(max_duration)
            
            recalculated_spots.append(spot)
    
    return recalculated_spots

