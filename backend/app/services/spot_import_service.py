"""
スポットインポートサービス
収集データをSpotモデルに変換してDB保存
"""
import json
import re
import csv
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.spot import Spot
from app.utils.error_handler import log_error


def parse_gemini_summary(summary_text: str) -> List[Dict[str, Any]]:
    """
    Gemini要約JSONをパースしてスポット情報を抽出
    SatoTrip/appの方式に統一
    
    Args:
        summary_text: Gemini要約テキスト（JSON形式を含む）
    
    Returns:
        スポット情報のリスト
    """
    if not summary_text or not summary_text.strip():
        return []
    
    # SatoTrip/appと同じ方式: 先頭/末尾のコードブロック記号を除去
    clean_json_str = re.sub(r"^```json\s*|\s*```$", "", summary_text.strip())
    
    # 空の配列をチェック
    if clean_json_str.strip() == "[]":
        return []
    
    try:
        summary_data = json.loads(clean_json_str)
        # 単一のdictの場合はリストに変換
        if isinstance(summary_data, dict):
            return [summary_data]
        elif isinstance(summary_data, list):
            return summary_data
        else:
            log_error("INVALID_SUMMARY_FORMAT", f"不正な要約形式: {type(summary_data)}")
            return []
    except json.JSONDecodeError as e:
        # エラーログに生データを保存（SatoTrip/appと同じ方式）
        log_error(
            "JSON_PARSE_ERROR", 
            f"JSON解析エラー: {e}", 
            {
                "error": str(e),
                "raw_summary": summary_text[:1000]  # 最初の1000文字を保存
            }
        )
        return []


def map_category_from_theme(theme: str) -> str:
    """
    テーマからSpotモデルのカテゴリにマッピング
    
    Args:
        theme: テーマ（例: "グルメ", "観光", "体験"）
    
    Returns:
        Spotモデルのカテゴリ（History, Nature, Food, Culture, Shopping, Art, Relax）
    """
    theme_lower = theme.lower()
    if "グルメ" in theme or "食べ" in theme or "料理" in theme or "レストラン" in theme:
        return "Food"
    elif "観光" in theme or "名所" in theme or "見学" in theme:
        return "Culture"
    elif "歴史" in theme or "史跡" in theme or "遺跡" in theme:
        return "History"
    elif "自然" in theme or "公園" in theme or "山" in theme or "海" in theme:
        return "Nature"
    elif "ショッピング" in theme or "買い物" in theme:
        return "Shopping"
    elif "アート" in theme or "美術" in theme or "芸術" in theme:
        return "Art"
    elif "温泉" in theme or "癒やし" in theme or "リラックス" in theme:
        return "Relax"
    else:
        return "Culture"  # デフォルト


def merge_spot_data(existing_spot: Spot, new_spot_data: Dict[str, Any]) -> None:
    """
    既存Spotと新しいデータをマージ（統合）
    
    Args:
        existing_spot: 既存のSpotオブジェクト（更新される）
        new_spot_data: 新しいSpotデータ
    """
    # description: 既存 + " | " + 新しい（重複除去）
    existing_desc = existing_spot.description or ""
    new_desc = new_spot_data.get("description", "")
    if new_desc and new_desc not in existing_desc:
        if existing_desc:
            existing_spot.description = f"{existing_desc} | {new_desc}"
        else:
            existing_spot.description = new_desc
    
    # tags: 既存タグと新しいタグを統合（重複除去）
    existing_tags = existing_spot.tags or []
    new_tags = new_spot_data.get("tags") or []
    if isinstance(existing_tags, list) and isinstance(new_tags, list):
        merged_tags = list(set(existing_tags + new_tags))
        existing_spot.tags = merged_tags if merged_tags else None
    elif new_tags and not existing_tags:
        existing_spot.tags = new_tags if isinstance(new_tags, list) else [new_tags]
    
    # image: 既存がない場合のみ新しい画像を設定
    if not existing_spot.image and new_spot_data.get("image"):
        existing_spot.image = new_spot_data["image"]
    
    # latitude/longitude: 既存がない場合のみ新しい位置情報を設定
    if not existing_spot.latitude and new_spot_data.get("latitude"):
        existing_spot.latitude = new_spot_data["latitude"]
    if not existing_spot.longitude and new_spot_data.get("longitude"):
        existing_spot.longitude = new_spot_data["longitude"]
    
    # category, rating, area等は既存を優先（変更しない）


def create_spot_from_data(place_data: Dict[str, Any], source_url: Optional[str] = None) -> Dict[str, Any]:
    """
    データからSpotオブジェクト作成用の辞書を生成
    
    Args:
        place_data: 場所データ（name, area, items, recommend等を含む）
        source_url: データソースURL（YouTube動画URL等）
    
    Returns:
        Spot作成用の辞書
    """
    name = place_data.get("name", "")
    area = place_data.get("area", "")
    items = place_data.get("items", [])
    recommend = place_data.get("recommend", "")
    theme = place_data.get("theme", "")
    mood = place_data.get("mood", "")
    latitude = place_data.get("latitude")
    longitude = place_data.get("longitude")
    
    # 説明文を生成（recommend + items）
    description_parts = []
    if recommend:
        description_parts.append(recommend)
    if items:
        items_str = "、".join(items) if isinstance(items, list) else str(items)
        description_parts.append(f"関連: {items_str}")
    description = " ".join(description_parts) if description_parts else ""
    
    # カテゴリをマッピング
    category = map_category_from_theme(theme)
    
    # タグを生成（items + mood）
    tags = []
    if isinstance(items, list):
        tags.extend(items)
    if mood:
        tags.append(mood)
    
    spot_data = {
        "name": name,
        "description": description,
        "area": area,
        "category": category,
        "duration_minutes": 60,  # デフォルト値
        "rating": 4.0,  # デフォルト値
        "image": "",  # 後で設定可能
        "price": None,
        "tags": tags if tags else None,
        "latitude": latitude,
        "longitude": longitude
    }
    
    return spot_data


def import_spots_from_youtube_data(
    db: Session,
    youtube_data: Dict[str, Any],
    prefecture: str = "鹿児島県"
) -> Dict[str, Any]:
    """
    YouTube収集データからSpotをインポート
    
    Args:
        db: データベースセッション
        youtube_data: YouTube収集データ（collect_youtube_dataの戻り値）
        prefecture: 都道府県名
    
    Returns:
        インポート結果（成功件数、失敗件数等）
    """
    results = youtube_data.get("results", [])
    imported_count = 0
    error_count = 0
    skipped_count = 0
    spot_ids: List[str] = []
    
    for entry in results:
        summary_text = entry.get("summary", "")
        source_url = entry.get("url", "")
        
        if not summary_text:
            skipped_count += 1
            continue
        
        # Gemini要約をパース
        place_data_list = parse_gemini_summary(summary_text)
        
        if not place_data_list:
            skipped_count += 1  # error_countからskipped_countに変更
            continue
        
        # 各場所データからSpotを作成
        for place_data in place_data_list:
            places = place_data.get("places", [])
            if not places:
                continue
            
            # 各場所名に対してSpotを作成
            for place_name in places:
                if not place_name:
                    continue
                
                # 場所データを準備
                spot_place_data = {
                    "name": place_name,
                    "area": place_data.get("area", ""),
                    "items": place_data.get("items", []),
                    "recommend": place_data.get("recommend", ""),
                    "theme": place_data.get("theme", ""),
                    "mood": place_data.get("mood", ""),
                    "latitude": None,  # 位置情報は別途付与
                    "longitude": None
                }
                
                # Spotデータを作成
                spot_data = create_spot_from_data(spot_place_data, source_url)
                
                # 重複チェック（名前とエリアで判定）
                existing_spot = db.query(Spot).filter(
                    Spot.name == spot_data["name"],
                    Spot.area == spot_data["area"]
                ).first()
                
                if existing_spot:
                    # 重複が見つかった場合、マージする
                    try:
                        merge_spot_data(existing_spot, spot_data)
                        db.commit()
                        db.refresh(existing_spot)
                        imported_count += 1  # マージもインポートとしてカウント
                        if existing_spot.id:
                            spot_ids.append(existing_spot.id)
                    except Exception as e:
                        db.rollback()
                        log_error("SPOT_MERGE_ERROR", f"Spotマージエラー ({place_name}): {e}")
                        error_count += 1
                    continue
                
                # Spotを作成
                try:
                    spot = Spot(
                        name=spot_data["name"],
                        description=spot_data.get("description"),
                        area=spot_data.get("area"),
                        category=spot_data.get("category"),
                        duration_minutes=spot_data.get("duration_minutes"),
                        rating=spot_data.get("rating"),
                        image=spot_data.get("image"),
                        price=spot_data.get("price"),
                        tags=spot_data.get("tags"),
                        latitude=spot_data.get("latitude"),
                        longitude=spot_data.get("longitude")
                    )
                    db.add(spot)
                    db.commit()
                    db.refresh(spot)
                    imported_count += 1
                    if spot.id:
                        spot_ids.append(spot.id)
                except Exception as e:
                    db.rollback()
                    log_error("SPOT_CREATE_ERROR", f"Spot作成エラー ({place_name}): {e}")
                    error_count += 1
    
    return {
        "imported": imported_count,
        "errors": error_count,
        "skipped": skipped_count,
        "total_processed": len(results),
        "spot_ids": list(set(spot_ids))
    }


def add_location_to_existing_spots(
    db: Session,
    spot_ids: Optional[List[str]] = None,
    prefecture: str = "鹿児島県"
) -> Dict[str, Any]:
    """
    既存のSpotに位置情報を付与
    
    Args:
        db: データベースセッション
        spot_ids: 処理対象のSpot IDリスト（Noneの場合は全件）
        prefecture: 都道府県名
    
    Returns:
        処理結果（成功件数、失敗件数等）
    """
    from app.services.geocoding_service import get_geo
    
    # 対象Spotを取得
    if spot_ids:
        spots = db.query(Spot).filter(Spot.id.in_(spot_ids)).all()
    else:
        spots = db.query(Spot).limit(10000).all()  # 全件取得
    
    updated_count = 0
    error_count = 0
    skipped_count = 0
    
    for spot in spots:
        # 既に位置情報がある場合はスキップ
        if spot.latitude and spot.longitude:
            skipped_count += 1
            continue
        
        if not spot.name or not spot.area:
            skipped_count += 1
            continue
        
        # 位置情報を取得
        lat, lng = get_geo(spot.name, spot.area, prefecture)
        
        if lat and lng:
            try:
                spot.latitude = lat
                spot.longitude = lng
                db.commit()
                db.refresh(spot)
                updated_count += 1
            except Exception as e:
                db.rollback()
                log_error("SPOT_UPDATE_ERROR", f"Spot更新エラー ({spot.name}): {e}")
                error_count += 1
        else:
            error_count += 1
    
    return {
        "updated": updated_count,
        "errors": error_count,
        "skipped": skipped_count,
        "total_processed": len(spots)
    }


def import_spots_from_sns_data(
    db: Session,
    sns_data: Dict[str, Any],
    prefecture: str = "鹿児島県"
) -> Dict[str, Any]:
    """
    SNS収集データからSpotをインポート
    
    Args:
        db: データベースセッション
        sns_data: SNS収集データ（collect_sns_data_with_summaryの戻り値）
        prefecture: 都道府県名
    
    Returns:
        インポート結果（成功件数、失敗件数等）
    """
    results = sns_data.get("results", [])
    imported_count = 0
    error_count = 0
    skipped_count = 0
    
    for entry in results:
        summary_text = entry.get("summary", "")
        source_url = entry.get("link", "")
        
        if not summary_text:
            skipped_count += 1
            continue
        
        # Gemini要約をパース
        place_data_list = parse_gemini_summary(summary_text)
        
        if not place_data_list:
            # JSONパースに失敗した場合、または空のリストの場合
            skipped_count += 1
            continue
        
        # 各場所データからSpotを作成
        places_found_in_entry = False
        for place_data in place_data_list:
            places = place_data.get("places", [])
            if not places:
                # placesが空の場合はスキップ（このエントリ内でplacesが見つからなかったことを記録）
                continue
            
            places_found_in_entry = True
            
            # 各場所名に対してSpotを作成
            for place_name in places:
                if not place_name:
                    continue
                
                # 場所データを準備
                spot_place_data = {
                    "name": place_name,
                    "area": place_data.get("area", ""),
                    "items": place_data.get("items", []),
                    "recommend": place_data.get("recommend", ""),
                    "theme": place_data.get("theme", ""),
                    "mood": place_data.get("mood", ""),
                    "latitude": None,  # 位置情報は別途付与
                    "longitude": None
                }
                
                # Spotデータを作成
                spot_data = create_spot_from_data(spot_place_data, source_url)
                
                # 重複チェック（名前とエリアで判定）
                existing_spot = db.query(Spot).filter(
                    Spot.name == spot_data["name"],
                    Spot.area == spot_data["area"]
                ).first()
                
                if existing_spot:
                    # 重複が見つかった場合、マージする
                    try:
                        merge_spot_data(existing_spot, spot_data)
                        db.commit()
                        db.refresh(existing_spot)
                        imported_count += 1  # マージもインポートとしてカウント
                    except Exception as e:
                        db.rollback()
                        log_error("SPOT_MERGE_ERROR", f"Spotマージエラー ({place_name}): {e}")
                        error_count += 1
                    continue
                
                # Spotを作成
                try:
                    spot = Spot(
                        name=spot_data["name"],
                        description=spot_data.get("description"),
                        area=spot_data.get("area"),
                        category=spot_data.get("category"),
                        duration_minutes=spot_data.get("duration_minutes"),
                        rating=spot_data.get("rating"),
                        image=spot_data.get("image"),
                        price=spot_data.get("price"),
                        tags=spot_data.get("tags"),
                        latitude=spot_data.get("latitude"),
                        longitude=spot_data.get("longitude")
                    )
                    db.add(spot)
                    db.commit()
                    db.refresh(spot)
                    imported_count += 1
                except Exception as e:
                    db.rollback()
                    log_error("SPOT_CREATE_ERROR", f"Spot作成エラー ({place_name}): {e}")
                    error_count += 1
        
        # このエントリでplacesが見つからなかった場合、スキップとしてカウント
        if not places_found_in_entry:
            skipped_count += 1
    
    return {
        "imported": imported_count,
        "errors": error_count,
        "skipped": skipped_count,
        "total_processed": len(results)
    }


def parse_csv_hashtags(hashtags_str: str) -> Optional[List[str]]:
    """
    CSVのhashtags文字列をJSON配列にパース
    
    Args:
        hashtags_str: CSVのhashtagsカラム（例: '["tag1", "tag2"]'）
    
    Returns:
        タグのリスト、またはNone
    """
    if not hashtags_str or not hashtags_str.strip():
        return None
    
    try:
        # JSON配列としてパース
        tags = json.loads(hashtags_str)
        if isinstance(tags, list):
            return tags
        elif isinstance(tags, str):
            return [tags]
        else:
            return None
    except json.JSONDecodeError:
        # JSONパースに失敗した場合、カンマ区切りとして扱う
        tags = [tag.strip().strip('"') for tag in hashtags_str.split(',')]
        return tags if tags else None


def extract_price_from_range(price_range: str) -> Optional[float]:
    """
    priceRange文字列から数値を抽出
    
    Args:
        price_range: 価格範囲文字列（例: "¥1,000", "¥2,100〜¥3,100"）
    
    Returns:
        抽出した数値（最初の数値）、またはNone
    """
    if not price_range or not price_range.strip():
        return None
    
    # 数値とカンマを抽出（¥、〜などの記号を除去）
    numbers = re.findall(r'[\d,]+', price_range.replace('¥', '').replace('円', ''))
    if numbers:
        try:
            # 最初の数値を取得（カンマを除去）
            first_number = numbers[0].replace(',', '')
            return float(first_number)
        except ValueError:
            return None
    return None


def parse_datetime(datetime_str: str) -> Optional[datetime]:
    """
    CSVの日時文字列をdatetimeオブジェクトに変換
    
    Args:
        datetime_str: 日時文字列（例: "2025-12-08 21:00:35"）
    
    Returns:
        datetimeオブジェクト、またはNone
    """
    if not datetime_str or not datetime_str.strip():
        return None
    
    # 複数の形式を試す
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%d"
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(datetime_str.strip(), fmt)
        except ValueError:
            continue
    
    return None


def map_category_from_csv(category: str) -> str:
    """
    CSVのカテゴリをSpotモデルのカテゴリにマッピング
    
    Args:
        category: CSVのカテゴリ（例: "観光スポット", "グルメ・食材"）
    
    Returns:
        Spotモデルのカテゴリ（History, Nature, Food, Culture, Shopping, Art, Relax）
    """
    if not category:
        return "Culture"  # デフォルト
    
    category_lower = category.lower()
    
    # 既存のmap_category_from_themeを参考にマッピング
    if "グルメ" in category or "食べ" in category or "料理" in category or "レストラン" in category or "食材" in category:
        return "Food"
    elif "観光" in category or "名所" in category or "見学" in category or "スポット" in category:
        return "Culture"
    elif "歴史" in category or "史跡" in category or "遺跡" in category or "文化" in category:
        return "History"
    elif "自然" in category or "公園" in category or "山" in category or "海" in category:
        return "Nature"
    elif "ショッピング" in category or "買い物" in category:
        return "Shopping"
    elif "アート" in category or "美術" in category or "芸術" in category:
        return "Art"
    elif "温泉" in category or "癒やし" in category or "リラックス" in category or "リラクゼーション" in category or "宿泊" in category:
        return "Relax"
    else:
        return "Culture"  # デフォルト


def import_spots_from_csv_file(
    db: Session,
    csv_file_path: str
) -> Dict[str, Any]:
    """
    CSVファイルからSpotをインポート
    
    Args:
        db: データベースセッション
        csv_file_path: CSVファイルのパス
    
    Returns:
        インポート結果（成功件数、失敗件数等）
    """
    imported_count = 0
    error_count = 0
    skipped_count = 0
    total_processed = 0
    
    try:
        with open(csv_file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                total_processed += 1
                
                try:
                    # CSVカラムから値を取得
                    csv_id = row.get("id", "").strip()
                    title = row.get("title", "").strip()
                    description = row.get("description", "").strip()
                    prefecture = row.get("prefecture", "").strip()
                    address = row.get("address", "").strip()
                    lat_str = row.get("lat", "").strip()
                    lng_str = row.get("lng", "").strip()
                    category = row.get("category", "").strip()
                    hashtags_str = row.get("hashtags", "").strip()
                    image_url = row.get("imageUrl", "").strip()
                    price_range = row.get("priceRange", "").strip()
                    created_at_str = row.get("createdAt", "").strip()
                    updated_at_str = row.get("updatedAt", "").strip()
                    
                    # 必須フィールドのチェック
                    if not title:
                        skipped_count += 1
                        continue
                    
                    # areaの構築（prefecture + address）
                    area_parts = []
                    if prefecture:
                        area_parts.append(prefecture)
                    if address:
                        area_parts.append(address)
                    area = " ".join(area_parts) if area_parts else None
                    
                    # 位置情報の変換
                    latitude = None
                    longitude = None
                    if lat_str:
                        try:
                            latitude = float(lat_str)
                        except ValueError:
                            pass
                    if lng_str:
                        try:
                            longitude = float(lng_str)
                        except ValueError:
                            pass
                    
                    # カテゴリのマッピング
                    mapped_category = map_category_from_csv(category) if category else "Culture"
                    
                    # タグのパース
                    tags = parse_csv_hashtags(hashtags_str)
                    
                    # 価格の抽出
                    price = extract_price_from_range(price_range)
                    
                    # 日時のパース
                    created_at = parse_datetime(created_at_str)
                    updated_at = parse_datetime(updated_at_str)
                    
                    # IDの処理：既存と重複していなければCSVのIDを使用、重複していれば新しいUUIDを生成
                    spot_id = None
                    if csv_id:
                        # 既存のIDをチェック
                        existing_spot_by_id = db.query(Spot).filter(Spot.id == csv_id).first()
                        if existing_spot_by_id:
                            # IDが重複している場合、新しいUUIDを生成
                            spot_id = str(uuid.uuid4())
                        else:
                            # IDが重複していない場合、CSVのIDを使用（文字列に変換）
                            spot_id = str(csv_id)
                    else:
                        # CSVにIDがない場合、新しいUUIDを生成
                        spot_id = str(uuid.uuid4())
                    
                    # 重複チェック（名前とエリアで判定）
                    existing_spot = db.query(Spot).filter(
                        Spot.name == title,
                        Spot.area == area
                    ).first()
                    
                    if existing_spot:
                        # 重複が見つかった場合、スキップ（既存情報を保持）
                        skipped_count += 1
                        continue
                    
                    # Spotを作成
                    spot = Spot(
                        id=spot_id,
                        name=title,
                        description=description if description else None,
                        area=area,
                        category=mapped_category,
                        duration_minutes=60,  # デフォルト値
                        rating=4.0,  # デフォルト値
                        image=image_url if image_url else None,
                        price=price,
                        tags=tags,
                        latitude=latitude,
                        longitude=longitude
                    )
                    
                    # 日時を設定（手動で設定する場合）
                    if created_at:
                        spot.created_at = created_at
                    if updated_at:
                        spot.updated_at = updated_at
                    
                    db.add(spot)
                    db.commit()
                    db.refresh(spot)
                    imported_count += 1
                    
                except Exception as e:
                    db.rollback()
                    log_error("CSV_SPOT_IMPORT_ERROR", f"CSV行処理エラー (行{total_processed}): {e}", {"row": row})
                    error_count += 1
                    continue
                    
    except FileNotFoundError:
        log_error("CSV_FILE_NOT_FOUND", f"CSVファイルが見つかりません: {csv_file_path}")
        raise
    except Exception as e:
        log_error("CSV_IMPORT_ERROR", f"CSVインポートエラー: {e}", {"file_path": csv_file_path})
        raise
    
    return {
        "imported": imported_count,
        "errors": error_count,
        "skipped": skipped_count,
        "total_processed": total_processed
    }

