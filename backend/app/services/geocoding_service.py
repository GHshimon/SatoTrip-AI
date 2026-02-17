"""
位置情報取得サービス
既存のadd_location_data.pyから移植
"""
import time
from typing import Optional, Tuple, Dict, Any, List
from opencage.geocoder import OpenCageGeocode
from app.config import settings
from app.utils.error_handler import log_error


# 都道府県の境界データ（必要に応じて拡張）
PREFECTURE_BOUNDS: Dict[str, Dict[str, float]] = {
    "鹿児島県": {
        "lat_min": 31.0,
        "lat_max": 32.5,
        "lng_min": 129.5,
        "lng_max": 131.5
    },
    # 他の都道府県も必要に応じて追加可能
}


def is_in_prefecture(lat: float, lng: float, prefecture: str) -> bool:
    """
    緯度経度が指定都道府県内か判定
    
    Args:
        lat: 緯度
        lng: 経度
        prefecture: 都道府県名
    
    Returns:
        都道府県内の場合True
    """
    if prefecture not in PREFECTURE_BOUNDS:
        # 境界データがない場合は判定をスキップ
        return True
    
    bounds = PREFECTURE_BOUNDS[prefecture]
    return (
        bounds["lat_min"] <= lat <= bounds["lat_max"]
        and bounds["lng_min"] <= lng <= bounds["lng_max"]
    )


def get_geo(place_name: str, area: str, prefecture: str = "鹿児島県") -> Tuple[Optional[float], Optional[float]]:
    """
    地名から緯度経度を取得。県名固定・信頼度確認・県内判定を実施
    
    Args:
        place_name: 場所名
        area: エリア名
        prefecture: 都道府県名
    
    Returns:
        (緯度, 経度) のタプル。取得失敗時は (None, None)
    """
    if not settings.OPENCAGE_API_KEY:
        log_error("OPENCAGE_API_KEY_NOT_SET", "OPENCAGE_API_KEYが設定されていません")
        return None, None
    
    try:
        geocoder = OpenCageGeocode(settings.OPENCAGE_API_KEY)
    except Exception as e:
        log_error("OPENCAGE_INIT_ERROR", f"OpenCage Geocoder初期化エラー: {e}")
        return None, None
    
    # クエリリスト（優先度順）
    queries = [
        f"{prefecture} {area} {place_name}",      # 最優先: 県+エリア+場所名
        f"{prefecture} {place_name}",              # 県+場所名
        f"{area} {place_name}",                    # エリア+場所名
        f"{place_name}, {area}, {prefecture}, Japan",  # 英語形式
    ]

    for q in queries:
        try:
            result = geocoder.geocode(q)
            if result and len(result) > 0:
                lat = result[0]["geometry"]["lat"]
                lng = result[0]["geometry"]["lng"]
                
                # 信頼度スコア確認
                confidence = result[0].get("confidence", 10)
                if confidence < 6:
                    log_error("LOW_CONFIDENCE", f"低信頼度検出 ({place_name}): confidence={confidence}")
                    continue
                
                # 県内判定
                if not is_in_prefecture(lat, lng, prefecture):
                    log_error("OUT_OF_PREFECTURE", f"{prefecture}外位置検出 ({place_name}): ({lat}, {lng})")
                    continue
                
                return lat, lng
        except Exception as e:
            log_error("GEOCODING_ERROR", f"位置情報取得エラー ({q}): {e}")
        time.sleep(1)  # レート制限回避

    # 最終手段：area単体から住所レベルで近似（県名付き）
    try:
        area_queries = [
            f"{prefecture} {area}",
            area
        ]
        for aq in area_queries:
            area_result = geocoder.geocode(aq)
            if area_result and len(area_result) > 0:
                lat = area_result[0]["geometry"]["lat"]
                lng = area_result[0]["geometry"]["lng"]
                
                # 県内判定
                if is_in_prefecture(lat, lng, prefecture):
                    return lat, lng
    except Exception as e:
        log_error("AREA_GEOCODING_ERROR", f"エリア位置情報取得エラー ({place_name}): {e}")

    # 全て失敗
    log_error("GEOCODING_FAILED", f"位置情報取得失敗: {place_name} ({area})")
    return None, None


def add_location_to_places(
    places_data: List[Dict[str, Any]],
    prefecture: str = "鹿児島県"
) -> List[Dict[str, Any]]:
    """
    スポットリストに位置情報を付与
    
    Args:
        places_data: スポットデータのリスト（各要素に "name" と "area" が必要）
        prefecture: 都道府県名
    
    Returns:
        位置情報が付与されたスポットデータのリスト
    """
    result = []
    for place in places_data:
        place_name = place.get("name", "")
        area = place.get("area", "")
        
        if not place_name:
            continue
        
        lat, lng = get_geo(place_name, area, prefecture)
        
        # 位置情報を追加
        place_with_location = place.copy()
        place_with_location["latitude"] = lat
        place_with_location["longitude"] = lng
        
        # 位置精度メタデータ
        if lat and lng:
            if is_in_prefecture(lat, lng, prefecture):
                place_with_location["location_status"] = "ok"
            else:
                place_with_location["location_status"] = "out_of_prefecture"
        else:
            place_with_location["location_status"] = "failed"
        
        result.append(place_with_location)
        time.sleep(1)  # レート制限回避
    
    return result

