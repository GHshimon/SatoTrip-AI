"""
Google Places API (New) 連携サービス

Text Search で店舗候補を絞り、Place Details で住所・緯度経度・画像・電話・URL を取得する。

参考:
- https://developers.google.com/maps/documentation/places/web-service/text-search
- https://developers.google.com/maps/documentation/places/web-service/place-details

レスポンスから取り出す主なフィールド:
- id (place_id)
- formattedAddress
- location.latitude / location.longitude
- displayName.text
- internationalPhoneNumber
- websiteUri
- rating
- priceLevel
- types
- photos[].name (photo resource name)

呼び出し側は ``enrich_spot_with_places(name, area, prefecture)`` を使う。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from difflib import SequenceMatcher

import requests

from app.config import settings
from app.utils.error_handler import log_error


PLACES_TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
PLACES_DETAILS_URL = "https://places.googleapis.com/v1/places/{place_id}"
PLACE_PHOTO_URL = "https://places.googleapis.com/v1/{photo_name}/media"

_TEXT_SEARCH_FIELD_MASK = ",".join([
    "places.id",
    "places.displayName",
    "places.formattedAddress",
    "places.location",
    "places.types",
    "places.rating",
    "places.priceLevel",
])

_DETAILS_FIELD_MASK = ",".join([
    "id",
    "displayName",
    "formattedAddress",
    "shortFormattedAddress",
    "location",
    "internationalPhoneNumber",
    "nationalPhoneNumber",
    "websiteUri",
    "rating",
    "userRatingCount",
    "priceLevel",
    "types",
    "photos",
    "regularOpeningHours",
])


# Google Places の priceLevel 列挙を概算金額に変換（日本円ざっくり想定）
_PRICE_LEVEL_TO_YEN: Dict[str, float] = {
    "PRICE_LEVEL_FREE": 0.0,
    "PRICE_LEVEL_INEXPENSIVE": 1000.0,
    "PRICE_LEVEL_MODERATE": 3000.0,
    "PRICE_LEVEL_EXPENSIVE": 8000.0,
    "PRICE_LEVEL_VERY_EXPENSIVE": 15000.0,
}

# 都道府県ごとの検索制限（B1: locationRestriction）
# 必要になったら順次追加
_PREFECTURE_BOUNDS: Dict[str, Dict[str, float]] = {
    "北海道": {"lat_min": 41.3, "lat_max": 45.6, "lng_min": 139.3, "lng_max": 145.8},
    "青森県": {"lat_min": 40.2, "lat_max": 41.6, "lng_min": 139.4, "lng_max": 141.7},
    "岩手県": {"lat_min": 38.9, "lat_max": 40.5, "lng_min": 140.7, "lng_max": 142.1},
    "宮城県": {"lat_min": 37.8, "lat_max": 39.0, "lng_min": 140.5, "lng_max": 141.7},
    "秋田県": {"lat_min": 39.2, "lat_max": 40.5, "lng_min": 139.5, "lng_max": 141.0},
    "山形県": {"lat_min": 37.8, "lat_max": 39.2, "lng_min": 139.5, "lng_max": 140.9},
    "福島県": {"lat_min": 36.8, "lat_max": 37.9, "lng_min": 139.3, "lng_max": 141.2},
    "茨城県": {"lat_min": 35.7, "lat_max": 36.9, "lng_min": 139.7, "lng_max": 140.9},
    "栃木県": {"lat_min": 36.2, "lat_max": 37.2, "lng_min": 139.4, "lng_max": 140.3},
    "群馬県": {"lat_min": 35.9, "lat_max": 37.1, "lng_min": 138.4, "lng_max": 139.7},
    "埼玉県": {"lat_min": 35.7, "lat_max": 36.3, "lng_min": 138.7, "lng_max": 139.9},
    "千葉県": {"lat_min": 34.9, "lat_max": 36.1, "lng_min": 139.8, "lng_max": 140.9},
    "東京都": {"lat_min": 35.5, "lat_max": 35.9, "lng_min": 139.3, "lng_max": 139.95},
    "神奈川県": {"lat_min": 35.1, "lat_max": 35.7, "lng_min": 139.0, "lng_max": 139.9},
    "新潟県": {"lat_min": 36.9, "lat_max": 38.7, "lng_min": 137.6, "lng_max": 139.9},
    "富山県": {"lat_min": 36.2, "lat_max": 37.0, "lng_min": 136.7, "lng_max": 137.8},
    "石川県": {"lat_min": 36.1, "lat_max": 37.6, "lng_min": 136.1, "lng_max": 137.4},
    "福井県": {"lat_min": 35.3, "lat_max": 36.3, "lng_min": 135.3, "lng_max": 136.8},
    "山梨県": {"lat_min": 35.2, "lat_max": 36.0, "lng_min": 138.2, "lng_max": 139.2},
    "長野県": {"lat_min": 35.2, "lat_max": 37.1, "lng_min": 137.3, "lng_max": 138.9},
    "岐阜県": {"lat_min": 35.1, "lat_max": 36.5, "lng_min": 136.3, "lng_max": 137.7},
    "静岡県": {"lat_min": 34.6, "lat_max": 35.7, "lng_min": 137.5, "lng_max": 139.2},
    "愛知県": {"lat_min": 34.5, "lat_max": 35.4, "lng_min": 136.7, "lng_max": 137.9},
    "三重県": {"lat_min": 33.7, "lat_max": 35.3, "lng_min": 135.8, "lng_max": 137.5},
    "滋賀県": {"lat_min": 34.8, "lat_max": 35.7, "lng_min": 135.8, "lng_max": 136.5},
    "京都府": {"lat_min": 34.9, "lat_max": 35.8, "lng_min": 134.3, "lng_max": 136.1},
    "大阪府": {"lat_min": 34.3, "lat_max": 34.9, "lng_min": 135.1, "lng_max": 135.7},
    "兵庫県": {"lat_min": 34.1, "lat_max": 35.7, "lng_min": 134.2, "lng_max": 135.9},
    "奈良県": {"lat_min": 33.8, "lat_max": 34.8, "lng_min": 135.5, "lng_max": 136.3},
    "和歌山県": {"lat_min": 33.4, "lat_max": 34.4, "lng_min": 135.0, "lng_max": 136.1},
    "鳥取県": {"lat_min": 35.1, "lat_max": 35.6, "lng_min": 133.2, "lng_max": 134.8},
    "島根県": {"lat_min": 34.7, "lat_max": 35.7, "lng_min": 131.6, "lng_max": 133.4},
    "岡山県": {"lat_min": 34.3, "lat_max": 35.4, "lng_min": 133.2, "lng_max": 134.4},
    "広島県": {"lat_min": 34.0, "lat_max": 35.1, "lng_min": 132.0, "lng_max": 133.4},
    "山口県": {"lat_min": 33.7, "lat_max": 34.5, "lng_min": 130.5, "lng_max": 132.2},
    "徳島県": {"lat_min": 33.5, "lat_max": 34.4, "lng_min": 133.5, "lng_max": 134.8},
    "香川県": {"lat_min": 34.0, "lat_max": 34.6, "lng_min": 133.4, "lng_max": 134.4},
    "愛媛県": {"lat_min": 32.9, "lat_max": 34.4, "lng_min": 132.0, "lng_max": 133.6},
    "高知県": {"lat_min": 32.7, "lat_max": 33.9, "lng_min": 132.3, "lng_max": 134.3},
    "福岡県": {"lat_min": 33.2, "lat_max": 34.2, "lng_min": 129.9, "lng_max": 131.2},
    "佐賀県": {"lat_min": 32.9, "lat_max": 33.7, "lng_min": 129.7, "lng_max": 130.6},
    "長崎県": {"lat_min": 32.5, "lat_max": 34.7, "lng_min": 128.5, "lng_max": 130.4},
    "熊本県": {"lat_min": 32.1, "lat_max": 33.3, "lng_min": 129.9, "lng_max": 131.3},
    "大分県": {"lat_min": 32.7, "lat_max": 33.8, "lng_min": 130.8, "lng_max": 132.1},
    "宮崎県": {"lat_min": 31.3, "lat_max": 32.9, "lng_min": 130.7, "lng_max": 131.9},
    "鹿児島県": {"lat_min": 30.9, "lat_max": 32.6, "lng_min": 129.2, "lng_max": 131.6},
    "沖縄県": {"lat_min": 24.0, "lat_max": 27.9, "lng_min": 122.7, "lng_max": 131.5},
}

# B2: カテゴリごとの Places 型ヒント
_CATEGORY_TO_INCLUDED_TYPE: Dict[str, str] = {
    "Food": "restaurant",
    "Cafe": "cafe",
    "Drink": "bar",
    "Tourism": "tourist_attraction",
    "Nature": "park",
    "History": "museum",
    "Art": "museum",
    "Shopping": "shopping_mall",
    "Hotel": "lodging",
    "HotSpring": "spa",
    "Culture": "tourist_attraction",
    "Experience": "tourist_attraction",
    "Event": "event_venue",
    "ScenicView": "tourist_attraction",
    "Drive": "tourist_attraction",
}


def _api_key_or_none() -> Optional[str]:
    """API キーが空なら警告ログを出して None を返す"""
    key = settings.GOOGLE_MAPS_API_KEY
    if not key:
        return None
    return key


def _build_location_restriction(prefecture: Optional[str]) -> Optional[Dict[str, Any]]:
    """都道府県境界から Places API の rectangle を作る"""
    if not prefecture:
        return None
    b = _PREFECTURE_BOUNDS.get(prefecture)
    if not b:
        return None
    return {
        "rectangle": {
            "low": {"latitude": b["lat_min"], "longitude": b["lng_min"]},
            "high": {"latitude": b["lat_max"], "longitude": b["lng_max"]},
        }
    }


def _build_included_type(category: Optional[str]) -> Optional[str]:
    """カテゴリから Places includedType を解決"""
    if not category:
        return None
    return _CATEGORY_TO_INCLUDED_TYPE.get(category)


def _query_candidates(name: str, area: Optional[str], prefecture: Optional[str]) -> List[str]:
    """
    B3: 段階的クエリ
      1) name + area + prefecture
      2) name + area
      3) name + prefecture
      4) name
    """
    raw = [
        " ".join([p for p in [name, area, prefecture] if p and str(p).strip()]),
        " ".join([p for p in [name, area] if p and str(p).strip()]),
        " ".join([p for p in [name, prefecture] if p and str(p).strip()]),
        (name or "").strip(),
    ]
    seen = set()
    out: List[str] = []
    for q in raw:
        qq = q.strip()
        if qq and qq not in seen:
            out.append(qq)
            seen.add(qq)
    return out


def _normalize_name(value: Optional[str]) -> str:
    """名称比較用の簡易正規化"""
    if not value:
        return ""
    s = value.strip().lower()
    for token in ["株式会社", "(株)", "有限会社", "本店", "支店", "店", " ", "　"]:
        s = s.replace(token, "")
    return s


def _name_similarity(a: Optional[str], b: Optional[str]) -> float:
    """0.0-1.0 の名称類似度"""
    na = _normalize_name(a)
    nb = _normalize_name(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    if na in nb or nb in na:
        return 0.9
    return SequenceMatcher(None, na, nb).ratio()


def _build_candidate_score(
    candidate: Dict[str, Any],
    *,
    target_name: str,
    area: Optional[str],
    prefecture: Optional[str],
    category: Optional[str],
) -> Dict[str, Any]:
    """
    Places候補をスコアリング（cheap-first）
    score: 0.0-1.0
    """
    display_name = ((candidate.get("displayName") or {}).get("text") or "").strip()
    formatted_address = (candidate.get("formattedAddress") or "").strip()
    types = candidate.get("types") or []

    name_score = _name_similarity(target_name, display_name)

    prefecture_score = 0.0
    if prefecture:
        prefecture_score = 1.0 if prefecture in formatted_address else 0.0
    else:
        prefecture_score = 0.5

    area_score = 0.5
    if area:
        area_tokens = [t for t in str(area).replace("　", " ").split(" ") if t]
        if area_tokens:
            hits = sum(1 for t in area_tokens if t in formatted_address)
            area_score = min(1.0, hits / max(len(area_tokens), 1))

    type_score = 0.5
    expected_type = _build_included_type(category)
    if expected_type:
        type_score = 1.0 if expected_type in types else 0.0

    # 重み合成
    score = (
        name_score * 0.45
        + prefecture_score * 0.25
        + area_score * 0.15
        + type_score * 0.15
    )

    return {
        "score": round(float(score), 4),
        "name_score": round(float(name_score), 4),
        "prefecture_score": round(float(prefecture_score), 4),
        "area_score": round(float(area_score), 4),
        "type_score": round(float(type_score), 4),
        "display_name": display_name,
        "formatted_address": formatted_address,
        "types": types,
        "id": candidate.get("id"),
        "raw": candidate,
    }


def text_search(
    query: str,
    max_results: int = 1,
    *,
    prefecture: Optional[str] = None,
    category: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Places API (New) Text Search を実行して候補を返す

    Args:
        query: 検索クエリ（例: "寿庵 鹿児島市 鹿児島県"）
        max_results: 最大件数

    Returns:
        places の配列（取得失敗時は空配列）
    """
    api_key = _api_key_or_none()
    if api_key is None:
        log_error("PLACES_API_KEY_NOT_SET", "GOOGLE_MAPS_API_KEY が未設定のため Places を呼び出せません")
        return []

    if not query or not query.strip():
        return []

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": _TEXT_SEARCH_FIELD_MASK,
    }
    body = {
        "textQuery": query,
        "languageCode": settings.PLACES_LANGUAGE,
        "regionCode": settings.PLACES_REGION,
        "maxResultCount": max(1, min(int(max_results or 1), 20)),
    }
    location_restriction = _build_location_restriction(prefecture)
    if location_restriction:
        body["locationRestriction"] = location_restriction

    included_type = _build_included_type(category)
    if included_type:
        body["includedType"] = included_type

    try:
        res = requests.post(
            PLACES_TEXT_SEARCH_URL,
            headers=headers,
            json=body,
            timeout=settings.PLACES_API_TIMEOUT_SEC,
        )
        if res.status_code == 403:
            log_error(
                "PLACES_API_403",
                f"Places API 403: {res.text[:300]}",
                {"query": query},
            )
            return []
        res.raise_for_status()
        data = res.json() or {}
        places = data.get("places", []) or []
        return places
    except requests.exceptions.HTTPError as e:
        body_text = ""
        try:
            body_text = e.response.text[:300]
        except Exception:
            pass
        log_error(
            "PLACES_API_HTTP_ERROR",
            f"Places API HTTPエラー: {e} {body_text}",
            {"query": query},
        )
        return []
    except Exception as e:
        log_error("PLACES_API_ERROR", f"Places API 呼び出し失敗: {e}", {"query": query})
        return []


def get_place_details(place_id: str) -> Optional[Dict[str, Any]]:
    """
    Places API (New) Place Details で詳細情報を取得

    Args:
        place_id: Places の id

    Returns:
        詳細レスポンス辞書、失敗時は None
    """
    api_key = _api_key_or_none()
    if api_key is None or not place_id:
        return None

    headers = {
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": _DETAILS_FIELD_MASK,
    }
    params = {
        "languageCode": settings.PLACES_LANGUAGE,
        "regionCode": settings.PLACES_REGION,
    }

    url = PLACES_DETAILS_URL.format(place_id=place_id)
    try:
        res = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=settings.PLACES_API_TIMEOUT_SEC,
        )
        res.raise_for_status()
        return res.json()
    except Exception as e:
        log_error(
            "PLACES_DETAILS_ERROR",
            f"Place Details 取得失敗: {e}",
            {"place_id": place_id},
        )
        return None


def build_photo_url(photo_resource_name: str, max_width_px: Optional[int] = None) -> Optional[str]:
    """
    Places の photo resource name から表示用 URL を組み立てる
    （API キーをクエリに含める形式）

    Args:
        photo_resource_name: ``places/<id>/photos/<token>``
        max_width_px: 最大幅

    Returns:
        画像 URL
    """
    api_key = _api_key_or_none()
    if api_key is None or not photo_resource_name:
        return None

    width = max_width_px or settings.PLACES_PHOTO_MAX_WIDTH_PX
    return (
        f"{PLACE_PHOTO_URL.format(photo_name=photo_resource_name)}"
        f"?maxWidthPx={int(width)}&key={api_key}"
    )


def enrich_spot_with_places(
    name: str,
    area: Optional[str] = None,
    prefecture: Optional[str] = None,
    category: Optional[str] = None,
    extra_query: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    スポット名 + エリアを使って Places API で詳細を取得し、
    Spot モデルに保存可能な辞書を返す。

    Returns:
        ``{
            "place_id": str,
            "name": str,                       # Places の正規名称
            "address": str | None,
            "latitude": float | None,
            "longitude": float | None,
            "phone": str | None,
            "website": str | None,
            "rating": float | None,
            "price": float | None,             # 円換算
            "image": str | None,
            "types": list[str],
        }``
        ヒットなしや API キー未設定時は ``None``。
    """
    if not name or not name.strip():
        return None

    # B3: 段階的クエリで順に試す
    queries = _query_candidates(name=name, area=area, prefecture=prefecture)
    if extra_query and isinstance(extra_query, str) and extra_query.strip():
        queries.insert(0, extra_query.strip())

    top: Optional[Dict[str, Any]] = None
    top_score: float = 0.0
    candidate_count = 0
    search_attempts = 0
    matched_query: Optional[str] = None
    for q in queries:
        search_attempts += 1
        candidates = text_search(
            q,
            max_results=5,
            prefecture=prefecture,
            category=category,
        )
        if candidates:
            candidate_count += len(candidates)
            scored = [
                _build_candidate_score(
                    c,
                    target_name=name,
                    area=area,
                    prefecture=prefecture,
                    category=category,
                )
                for c in candidates
            ]
            scored.sort(key=lambda x: x["score"], reverse=True)
            best = scored[0]
            top = best["raw"]
            top_score = float(best["score"])
            matched_query = q
            break
    if not top:
        log_error(
            "PLACES_NO_HIT",
            "Places で候補が見つかりませんでした",
            {"name": name, "area": area, "prefecture": prefecture, "queries": queries[:4]},
        )
        return None

    place_id = top.get("id")
    if not place_id:
        return None

    details = get_place_details(place_id) or top
    details_called = True

    location = details.get("location") or {}
    latitude = location.get("latitude")
    longitude = location.get("longitude")

    display_name = (details.get("displayName") or {}).get("text")
    address = details.get("formattedAddress") or details.get("shortFormattedAddress")

    phone = details.get("internationalPhoneNumber") or details.get("nationalPhoneNumber")
    website = details.get("websiteUri")

    rating = details.get("rating")

    price_level = details.get("priceLevel")
    price_yen = _PRICE_LEVEL_TO_YEN.get(price_level) if isinstance(price_level, str) else None

    image_url: Optional[str] = None
    photos = details.get("photos") or []
    if photos:
        first_photo_name = photos[0].get("name")
        if first_photo_name:
            image_url = build_photo_url(first_photo_name)

    return {
        "place_id": place_id,
        "name": display_name or name,
        "address": address,
        "latitude": float(latitude) if latitude is not None else None,
        "longitude": float(longitude) if longitude is not None else None,
        "phone": phone,
        "website": website,
        "rating": float(rating) if rating is not None else None,
        "price": price_yen,
        "image": image_url,
        "types": details.get("types") or [],
        "matched_query": matched_query,
        "matched_score": top_score,
        "search_attempts": search_attempts,
        "candidate_count": candidate_count,
        "details_called": details_called,
    }
