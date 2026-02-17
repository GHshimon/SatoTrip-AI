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
        
        # 二日目以降の場合、最初のスポットが宿泊施設（出発）かどうかを確認
        hotel_to_first_spot_duration = 0
        first_spot_is_hotel = False
        if day > 1 and day_spots:
            first_spot = day_spots[0]
            # 最初のスポットのカテゴリを取得
            category = None
            if "spot" in first_spot and isinstance(first_spot["spot"], dict):
                category = first_spot["spot"].get("category")
            if not category:
                category = first_spot.get("category")
            note = first_spot.get("note", "")
            
            # 最初のスポットが宿泊施設（出発）の場合
            if category == "Hotel" and note == "出発":
                first_spot_is_hotel = True
                # 宿泊施設から次のスポット（観光スポット）への移動時間を計算
                if len(day_spots) > 1:
                    next_spot = day_spots[1]
                    hotel_location = {}
                    if "spot" in first_spot and isinstance(first_spot["spot"], dict):
                        hotel_location = first_spot["spot"].get("location", {})
                    if not hotel_location:
                        hotel_location = first_spot.get("location", {})
                    
                    next_spot_location = {}
                    if "spot" in next_spot and isinstance(next_spot["spot"], dict):
                        next_spot_location = next_spot["spot"].get("location", {})
                    if not next_spot_location:
                        next_spot_location = next_spot.get("location", {})
                    
                    # 位置情報から緯度経度を取得
                    hotel_lat = hotel_location.get("lat") or hotel_location.get("latitude")
                    hotel_lng = hotel_location.get("lng") or hotel_location.get("longitude")
                    next_lat = next_spot_location.get("lat") or next_spot_location.get("latitude")
                    next_lng = next_spot_location.get("lng") or next_spot_location.get("longitude")
                    
                    # 位置情報がある場合は実際の移動時間を計算
                    if hotel_lat and hotel_lng and next_lat and next_lng:
                        # 交通手段をプロファイルに変換
                        profile_map = {
                            "車": "driving",
                            "公共交通機関": "transit",
                            "電車": "transit",
                            "バス": "transit",
                            "徒歩": "walking",
                            "その他": "driving"
                        }
                        # 移動手段を決定（全体 > デフォルト）
                        day_transportation = transportation
                        profile = profile_map.get(day_transportation, "driving")
                        
                        try:
                            route_info = get_route_info(
                                coordinates=[(hotel_lat, hotel_lng), (next_lat, next_lng)],
                                profile=profile
                            )
                            
                            if route_info:
                                hotel_to_first_spot_duration = int(route_info.get("duration_minutes", 20))
                        except Exception:
                            # エラー時はデフォルト値を使用
                            hotel_to_first_spot_duration = 20
                    else:
                        # 位置情報がない場合はデフォルト値
                        hotel_to_first_spot_duration = 20
                    
                    # 最初のスポット（宿泊施設）から次のスポットへの移動時間を設定
                    first_spot["transportDuration"] = hotel_to_first_spot_duration
            else:
                # 最初のスポットが宿泊施設でない場合、前日の宿泊施設から最初のスポットへの移動時間を計算
                prev_day = day - 1
                prev_day_spots = spots_by_day.get(prev_day, [])
                
                # 前日の最後のスポットが宿泊施設か確認
                hotel_spot = None
                for spot in reversed(prev_day_spots):
                    # スポットのカテゴリを取得（spotオブジェクト内または直接）
                    category = None
                    if "spot" in spot and isinstance(spot["spot"], dict):
                        category = spot["spot"].get("category")
                    if not category:
                        category = spot.get("category")
                    
                    if category == "Hotel":
                        hotel_spot = spot
                        break
                
                # 宿泊施設が見つかった場合、その位置から最初のスポットへの移動時間を計算
                # hotel_locationを初期化（if文の外側で定義）
                hotel_location = {}
                if hotel_spot:
                    # 宿泊施設の位置情報を取得
                    if "spot" in hotel_spot and isinstance(hotel_spot["spot"], dict):
                        hotel_location = hotel_spot["spot"].get("location", {})
                    if not hotel_location:
                        hotel_location = hotel_spot.get("location", {})
                
                # 最初のスポットの位置情報を取得
                first_spot = day_spots[0]
                first_spot_location = {}
                if "spot" in first_spot and isinstance(first_spot["spot"], dict):
                    first_spot_location = first_spot["spot"].get("location", {})
                if not first_spot_location:
                    first_spot_location = first_spot.get("location", {})
                
                # 位置情報から緯度経度を取得
                hotel_lat = hotel_location.get("lat") or hotel_location.get("latitude") if hotel_location else None
                hotel_lng = hotel_location.get("lng") or hotel_location.get("longitude") if hotel_location else None
                first_lat = first_spot_location.get("lat") or first_spot_location.get("latitude")
                first_lng = first_spot_location.get("lng") or first_spot_location.get("longitude")
                
                # 位置情報がある場合は実際の移動時間を計算
                if hotel_lat and hotel_lng and first_lat and first_lng:
                    # 交通手段をプロファイルに変換
                    profile_map = {
                        "車": "driving",
                        "公共交通機関": "transit",
                        "電車": "transit",
                        "バス": "transit",
                        "徒歩": "walking",
                        "その他": "driving"
                    }
                    # 移動手段を決定（全体 > デフォルト）
                    day_transportation = transportation
                    profile = profile_map.get(day_transportation, "driving")
                    
                    try:
                        route_info = get_route_info(
                            coordinates=[(hotel_lat, hotel_lng), (first_lat, first_lng)],
                            profile=profile
                        )
                        
                        if route_info:
                            hotel_to_first_spot_duration = int(route_info.get("duration_minutes", 20))
                    except Exception:
                        # エラー時はデフォルト値を使用
                        hotel_to_first_spot_duration = 20
                else:
                    # 位置情報がない場合はデフォルト値
                    hotel_to_first_spot_duration = 20
                
                # 最初のスポットのtransportDurationに設定（宿泊施設からの移動時間）
                if day_spots:
                    day_spots[0]["transportDuration"] = hotel_to_first_spot_duration
        
        # 終了時刻をパース（オプション）
        end_dt = None
        if end_time:
            end_hour, end_minute = map(int, end_time.split(":"))
            end_dt = dt(2000, 1, 1, end_hour, end_minute)
        
        for i, spot in enumerate(day_spots):
            # 最初のスポットが宿泊施設（出発）の場合は、開始時刻をそのまま使用
            if i == 0 and first_spot_is_hotel:
                # 宿泊施設（出発）の開始時刻はそのまま使用
                current_time = dt(2000, 1, 1, start_hour, start_minute)
            # 最初のスポットで、宿泊施設からの移動時間がある場合は考慮
            elif i == 0 and hotel_to_first_spot_duration > 0:
                # 宿泊施設からの移動時間を考慮して開始時刻を計算
                # 開始時刻は通常のstart_timeから、移動時間を加算
                current_time = dt(2000, 1, 1, start_hour, start_minute) + timedelta(minutes=hotel_to_first_spot_duration)
            # 最初のスポットが宿泊施設（出発）の次のスポットの場合
            elif i == 1 and first_spot_is_hotel and hotel_to_first_spot_duration > 0:
                # 宿泊施設からの移動時間を考慮して開始時刻を計算
                current_time = dt(2000, 1, 1, start_hour, start_minute) + timedelta(minutes=hotel_to_first_spot_duration)
            # 最初のスポットで、前のスポットからの移動時間を考慮
            elif i > 0:
                # 前のスポットの終了時刻に移動時間を加算
                prev_spot = day_spots[i - 1]
                prev_duration = prev_spot.get("durationMinutes", 60)
                prev_transport = prev_spot.get("transportDuration", 20)
                # current_timeは前のループで前のスポットの開始時刻+滞在時間+移動時間になっている
                # これが現在のスポットの開始時刻になる
                pass  # current_timeは既に前のループで更新されている
            
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
                            "公共交通機関": "transit",
                            "電車": "transit",
                            "バス": "transit",
                            "徒歩": "walking",
                            "その他": "driving"
                        }
                        # 移動手段を決定（全体 > デフォルト）
                        day_transportation = transportation
                        profile = profile_map.get(day_transportation, "driving")
                        
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

