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
from app.utils.debug_logger import log_debug_step
from app.utils.tag_normalizer import normalize_tags, tags_to_dict_list, TagSource


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
        # #region agent log
        import json as json_module
        import time
        with open(r'c:\projects\SatoTrip-AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
            f.write(json_module.dumps({"location":"spot_import_service.py:39","message":"JSON parse succeeded","data":{"summary_type":type(summary_data).__name__,"is_dict":isinstance(summary_data, dict),"is_list":isinstance(summary_data, list),"data_preview":str(summary_data)[:200]},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"C"},ensure_ascii=False)+'\n')
        # #endregion
        # 単一のdictの場合はリストに変換
        if isinstance(summary_data, dict):
            return [summary_data]
        elif isinstance(summary_data, list):
            return summary_data
        else:
            # #region agent log
            with open(r'c:\projects\SatoTrip-AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
                f.write(json_module.dumps({"location":"spot_import_service.py:46","message":"Invalid summary format","data":{"summary_type":type(summary_data).__name__,"summary_data":str(summary_data)[:200]},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"C"},ensure_ascii=False)+'\n')
            # #endregion
            log_error("INVALID_SUMMARY_FORMAT", f"不正な要約形式: {type(summary_data)}")
            return []
    except json.JSONDecodeError as e:
        # #region agent log
        import json as json_module
        import time
        with open(r'c:\projects\SatoTrip-AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
            f.write(json_module.dumps({"location":"spot_import_service.py:48","message":"JSON parse error","data":{"error":str(e),"error_type":type(e).__name__,"raw_summary_preview":summary_text[:500],"clean_json_preview":clean_json_str[:500]},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"C"},ensure_ascii=False)+'\n')
        # #endregion
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
        Spotモデルのカテゴリ（History, Nature, Food, Culture, Shopping, Art, Relax, Tourism, Experience, Event, HotSpring, ScenicView, Cafe, Hotel, Drink, Fashion, Date, Drive）
    """
    theme_lower = theme.lower()
    if "グルメ" in theme or "食べ" in theme or "料理" in theme or "レストラン" in theme:
        return "Food"
    elif "観光" in theme or "名所" in theme or "見学" in theme:
        return "Tourism"
    elif "体験" in theme:
        return "Experience"
    elif "イベント" in theme or "祭り" in theme or "フェス" in theme:
        return "Event"
    elif "温泉" in theme:
        return "HotSpring"
    elif "絶景" in theme or "景色" in theme or "ビュー" in theme:
        return "ScenicView"
    elif "歴史" in theme or "史跡" in theme or "遺跡" in theme:
        return "History"
    elif "カフェ" in theme or "喫茶" in theme:
        return "Cafe"
    elif "自然" in theme or "公園" in theme or "山" in theme or "海" in theme:
        return "Nature"
    elif "宿泊" in theme or "ホテル" in theme or "旅館" in theme or "民宿" in theme:
        return "Hotel"
    elif "お酒" in theme or "酒" in theme or "飲み" in theme or "バー" in theme:
        return "Drink"
    elif "ショッピング" in theme or "買い物" in theme:
        return "Shopping"
    elif "ファッション" in theme or "服" in theme or "衣類" in theme:
        return "Fashion"
    elif "デート" in theme or "恋人" in theme:
        return "Date"
    elif "ドライブ" in theme or "車" in theme or "ドライブコース" in theme:
        return "Drive"
    elif "アート" in theme or "美術" in theme or "芸術" in theme:
        return "Art"
    elif "癒やし" in theme or "リラックス" in theme:
        return "Relax"
    else:
        return "Culture"  # デフォルト


def merge_spot_data(existing_spot: Spot, new_spot_data: Dict[str, Any], target_category: Optional[str] = None) -> None:
    """
    既存Spotと新しいデータをマージ（統合）
    
    Args:
        existing_spot: 既存のSpotオブジェクト（更新される）
        new_spot_data: 新しいSpotデータ
        target_category: ターゲットカテゴリ（指定されている場合、既存カテゴリを保護）
    """
    # description: 既存 + " | " + 新しい（重複除去）
    existing_desc = existing_spot.description or ""
    new_desc = new_spot_data.get("description", "")
    if new_desc and new_desc not in existing_desc:
        if existing_desc:
            existing_spot.description = f"{existing_desc} | {new_desc}"
        else:
            existing_spot.description = new_desc
    
    # tags: 既存タグと新しいタグを統合（構造化タグ対応、重複除去）
    existing_tags = existing_spot.tags or []
    new_tags = new_spot_data.get("tags") or []
    
    # 既存タグと新規タグを構造化タグに変換
    existing_structured = normalize_tags(existing_tags, source=TagSource.IMPORT) if existing_tags else []
    new_structured = normalize_tags(new_tags, source=TagSource.IMPORT) if new_tags else []
    
    # 正規化された値で重複をチェックして統合
    existing_normalized = {tag.normalized: tag for tag in existing_structured}
    for new_tag in new_structured:
        if new_tag.normalized not in existing_normalized:
            existing_structured.append(new_tag)
    
    # 辞書リストに変換して保存
    merged_tags = tags_to_dict_list(existing_structured) if existing_structured else None
    existing_spot.tags = merged_tags
    
    # image: 既存がない場合のみ新しい画像を設定
    if not existing_spot.image and new_spot_data.get("image"):
        existing_spot.image = new_spot_data["image"]
    
    # latitude/longitude: 既存がない場合のみ新しい位置情報を設定
    if not existing_spot.latitude and new_spot_data.get("latitude"):
        existing_spot.latitude = new_spot_data["latitude"]
    if not existing_spot.longitude and new_spot_data.get("longitude"):
        existing_spot.longitude = new_spot_data["longitude"]
    
    # category: target_categoryが指定されている場合、既存カテゴリを保護（変更しない）
    # target_categoryが指定されていない場合も、既存カテゴリを優先
    # （既存カテゴリがない場合のみ新しいカテゴリを設定）
    # #region agent log
    import json
    import time
    with open(r'c:\projects\SatoTrip-AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
        f.write(json.dumps({"location":"spot_import_service.py:176","message":"merge_spot_data category check","data":{"existing_spot_category":existing_spot.category,"new_spot_data_category":new_spot_data.get("category"),"target_category":target_category,"target_category_type":type(target_category).__name__ if target_category else None,"target_category_bool":bool(target_category)},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"G"},ensure_ascii=False)+'\n')
    # #endregion
    if target_category:
        # target_categoryが指定されている場合、既存カテゴリを絶対に変更しない
        # #region agent log
        import json
        import time
        with open(r'c:\projects\SatoTrip-AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
            f.write(json.dumps({"location":"spot_import_service.py:185","message":"merge_spot_data preserving existing category","data":{"existing_spot_category":existing_spot.category,"target_category":target_category},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"G"},ensure_ascii=False)+'\n')
        # #endregion
        pass  # 既存カテゴリを維持
    elif not existing_spot.category and new_spot_data.get("category"):
        # target_categoryが指定されていない場合のみ、既存カテゴリがない場合に新しいカテゴリを設定
        # #region agent log
        import json
        import time
        with open(r'c:\projects\SatoTrip-AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
            f.write(json.dumps({"location":"spot_import_service.py:193","message":"merge_spot_data setting new category","data":{"existing_spot_category":existing_spot.category,"new_spot_data_category":new_spot_data.get("category")},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"G"},ensure_ascii=False)+'\n')
        # #endregion
        existing_spot.category = new_spot_data["category"]
    # #region agent log
    import json
    import time
    with open(r'c:\projects\SatoTrip-AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
        f.write(json.dumps({"location":"spot_import_service.py:200","message":"merge_spot_data category after check","data":{"existing_spot_category":existing_spot.category},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"G"},ensure_ascii=False)+'\n')
    # #endregion
    
    # rating, area等は既存を優先（変更しない）


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
    
    # タグを生成（items + mood）して構造化タグに変換
    tag_strings = []
    if isinstance(items, list):
        tag_strings.extend(items)
    if mood:
        tag_strings.append(mood)
    
    # 構造化タグに変換
    structured_tags = normalize_tags(tag_strings, source=TagSource.IMPORT) if tag_strings else []
    tags = tags_to_dict_list(structured_tags) if structured_tags else None
    
    spot_data = {
        "name": name,
        "description": description,
        "area": area,
        "category": category,
        "duration_minutes": 60,  # デフォルト値
        "rating": 4.0,  # デフォルト値
        "image": "",  # 後で設定可能
        "price": None,
        "tags": tags,
        "latitude": latitude,
        "longitude": longitude
    }
    
    return spot_data


def import_spots_from_youtube_data(
    db: Session,
    youtube_data: Dict[str, Any],
    prefecture: str = "鹿児島県",
    target_category: Optional[str] = None
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
    created_count = 0  # 新規作成数
    merged_count = 0   # マージ数
    error_count = 0
    skipped_count = 0
    spot_ids: List[str] = []
    
    # #region agent log
    import json as json_module
    import time
    with open(r'c:\projects\SatoTrip-AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
        f.write(json_module.dumps({"location":"spot_import_service.py:217","message":"import_spots_from_youtube_data started","data":{"results_count":len(results),"prefecture":prefecture},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"D"},ensure_ascii=False)+'\n')
    # #endregion
    
    for entry in results:
        summary_text = entry.get("summary", "")
        source_url = entry.get("url", "")
        video_title = entry.get("title", "")
        
        if not summary_text:
            log_debug_step(
                step="spot_import",
                status="skipped",
                data={
                    "reason": "empty_summary",
                    "video_title": video_title,
                    "url": source_url
                }
            )
            skipped_count += 1
            continue
        
        # Gemini要約をパース
        place_data_list = parse_gemini_summary(summary_text)
        
        if not place_data_list:
            log_debug_step(
                step="spot_import",
                status="skipped",
                data={
                    "reason": "parse_failed",
                    "video_title": video_title,
                    "url": source_url,
                    "summary_preview": summary_text[:200] if summary_text else ""
                }
            )
            skipped_count += 1  # error_countからskipped_countに変更
            continue
        
        log_debug_step(
            step="spot_import",
            status="parsed",
            data={
                "video_title": video_title,
                "places_count": sum(len(pd.get("places", [])) for pd in place_data_list),
                "place_data_sample": place_data_list[0] if place_data_list else None
            }
        )
        
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
                
                # カテゴリマッピング: 日本語カテゴリ名を英語カテゴリ名に変換
                category_map = {
                    "宿泊": "Hotel",
                    "グルメ": "Food",
                    "観光": "Tourism",
                    "自然": "Nature",
                    "歴史": "History",
                    "文化": "Culture",
                    "ショッピング": "Shopping",
                    "アート": "Art",
                    "温泉": "HotSpring",
                    "絶景": "ScenicView",
                    "カフェ": "Cafe",
                    "お酒": "Drink",
                    "ファッション": "Fashion",
                    "デート": "Date",
                    "ドライブ": "Drive"
                }
                
                # target_categoryが指定されている場合は、spot_dataのカテゴリを上書き
                original_category = spot_data.get("category")
                target_category_en = None
                # #region agent log
                import json
                import time
                with open(r'c:\projects\SatoTrip-AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
                    f.write(json.dumps({"location":"spot_import_service.py:368","message":"before category overwrite check","data":{"place_name":place_name,"original_category":original_category,"target_category":target_category,"target_category_type":type(target_category).__name__,"target_category_bool":bool(target_category)},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"F"},ensure_ascii=False)+'\n')
                # #endregion
                if target_category:
                    target_category_en = category_map.get(target_category, target_category)
                    spot_data["category"] = target_category_en
                    # #region agent log
                    import json
                    import time
                    with open(r'c:\projects\SatoTrip-AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
                        f.write(json.dumps({"location":"spot_import_service.py:340","message":"category overwritten by target_category","data":{"place_name":place_name,"original_category":original_category,"target_category":target_category,"target_category_en":target_category_en,"final_category":spot_data.get("category")},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"F"},ensure_ascii=False)+'\n')
                    # #endregion
                else:
                    # #region agent log
                    import json
                    import time
                    with open(r'c:\projects\SatoTrip-AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
                        f.write(json.dumps({"location":"spot_import_service.py:380","message":"target_category not provided, skipping overwrite","data":{"place_name":place_name,"original_category":original_category,"target_category":target_category},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"F"},ensure_ascii=False)+'\n')
                    # #endregion
                
                # #region agent log
                import json
                import time
                with open(r'c:\projects\SatoTrip-AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
                    f.write(json.dumps({"location":"spot_import_service.py:333","message":"checking duplicate before query","data":{"place_name":place_name,"spot_name":spot_data["name"],"spot_area":spot_data.get("area"),"spot_category":spot_data.get("category"),"target_category":target_category,"target_category_en":target_category_en,"theme":place_data.get("theme","")},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"E"},ensure_ascii=False)+'\n')
                # #endregion
                
                # 重複チェック（名前、エリア、カテゴリで判定）
                # target_categoryが指定されている場合は、カテゴリも一致する場合のみ重複と判定
                if target_category_en:
                    existing_spot = db.query(Spot).filter(
                        Spot.name == spot_data["name"],
                        Spot.area == spot_data["area"],
                        Spot.category == target_category_en
                    ).first()
                    # エリア名が一致しない場合、名前とカテゴリのみで検索（エリア名の不一致を確認）
                    if not existing_spot:
                        existing_spot_by_name_category = db.query(Spot).filter(
                            Spot.name == spot_data["name"],
                            Spot.category == target_category_en
                        ).first()
                        # #region agent log
                        if existing_spot_by_name_category:
                            with open(r'c:\projects\SatoTrip-AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
                                f.write(json.dumps({"location":"spot_import_service.py:432","message":"duplicate found by name and category but area mismatch","data":{"spot_name":spot_data["name"],"spot_area":spot_data.get("area"),"existing_spot_area":existing_spot_by_name_category.area,"category":spot_data.get("category"),"target_category":target_category},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"H"},ensure_ascii=False)+'\n')
                        # #endregion
                else:
                    existing_spot = db.query(Spot).filter(
                        Spot.name == spot_data["name"],
                        Spot.area == spot_data["area"]
                    ).first()
                
                # #region agent log
                with open(r'c:\projects\SatoTrip-AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
                    f.write(json.dumps({"location":"spot_import_service.py:345","message":"duplicate check result","data":{"spot_name":spot_data["name"],"spot_area":spot_data.get("area"),"category":spot_data.get("category"),"target_category":target_category,"existing_spot_found":existing_spot is not None,"existing_spot_id":existing_spot.id if existing_spot else None,"existing_spot_category":existing_spot.category if existing_spot else None},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"E"},ensure_ascii=False)+'\n')
                # #endregion
                
                if existing_spot:
                    # 重複が見つかった場合、マージする
                    # （既に重複チェックでカテゴリも考慮しているため、カテゴリが一致する場合のみここに到達する）
                    try:
                        merge_spot_data(existing_spot, spot_data, target_category=target_category)
                        db.commit()
                        db.refresh(existing_spot)
                        imported_count += 1  # マージもインポートとしてカウント
                        merged_count += 1  # マージ数をカウント
                        # #region agent log
                        with open(r'c:\projects\SatoTrip-AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
                            f.write(json.dumps({"location":"spot_import_service.py:350","message":"spot merged with existing","data":{"spot_name":spot_data["name"],"existing_spot_id":existing_spot.id,"existing_spot_category":existing_spot.category,"new_category":spot_data.get("category")},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"E"},ensure_ascii=False)+'\n')
                        # #endregion
                        if existing_spot.id:
                            spot_ids.append(existing_spot.id)
                        log_debug_step(
                            step="spot_import",
                            status="merged",
                            data={
                                "spot_name": place_name,
                                "spot_id": existing_spot.id,
                                "area": spot_data.get("area", "")
                            }
                        )
                    except Exception as e:
                        db.rollback()
                        log_debug_step(
                            step="spot_import",
                            status="error",
                            data={
                                "spot_name": place_name,
                                "action": "merge",
                                "error": str(e)
                            }
                        )
                        log_error("SPOT_MERGE_ERROR", f"Spotマージエラー ({place_name}): {e}")
                        error_count += 1
                    continue
                
                # Spotを作成（重複が見つからなかった場合、またはカテゴリが異なる場合）
                try:
                    # #region agent log
                    import json as json_module
                    import time
                    with open(r'c:\projects\SatoTrip-AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
                        f.write(json_module.dumps({"location":"spot_import_service.py:425","message":"Creating new spot","data":{"spot_name":place_name,"spot_category":spot_data.get("category"),"target_category":target_category,"spot_data":{k:v for k,v in spot_data.items() if k not in ["latitude","longitude"]}},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"D"},ensure_ascii=False)+'\n')
                    # #endregion
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
                    # #region agent log
                    with open(r'c:\projects\SatoTrip-AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
                        f.write(json_module.dumps({"location":"spot_import_service.py:515","message":"Before db.commit","data":{"spot_name":place_name,"spot_id_before_commit":spot.id if hasattr(spot, 'id') else None},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"I"},ensure_ascii=False)+'\n')
                    # #endregion
                    db.commit()
                    db.refresh(spot)
                    # #region agent log
                    with open(r'c:\projects\SatoTrip-AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
                        f.write(json_module.dumps({"location":"spot_import_service.py:520","message":"After db.commit and refresh","data":{"spot_name":place_name,"spot_id_after_commit":spot.id,"spot_id_is_none":spot.id is None},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"I"},ensure_ascii=False)+'\n')
                    # #endregion
                    # コミット後、実際にデータベースに追加されているかを確認
                    if spot.id:
                        verified_spot = db.query(Spot).filter(Spot.id == spot.id).first()
                    imported_count += 1
                    created_count += 1  # 新規作成数をカウント
                    if spot.id:
                        spot_ids.append(spot.id)
                    # #region agent log
                    with open(r'c:\projects\SatoTrip-AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
                        f.write(json_module.dumps({"location":"spot_import_service.py:288","message":"Spot created successfully","data":{"spot_id":spot.id,"spot_name":place_name,"created_count":created_count},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"D"},ensure_ascii=False)+'\n')
                    # #endregion
                    log_debug_step(
                        step="spot_import",
                        status="created",
                        data={
                            "spot_name": place_name,
                            "spot_id": spot.id,
                            "area": spot_data.get("area", ""),
                            "category": spot_data.get("category", "")
                        }
                    )
                except Exception as e:
                    db.rollback()
                    # #region agent log
                    import json as json_module
                    import time
                    import traceback
                    with open(r'c:\projects\SatoTrip-AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
                        f.write(json_module.dumps({"location":"spot_import_service.py:348","message":"Spot creation error","data":{"spot_name":place_name,"error":str(e),"error_type":type(e).__name__,"traceback":traceback.format_exc()},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"D"},ensure_ascii=False)+'\n')
                    # #endregion
                    log_debug_step(
                        step="spot_import",
                        status="error",
                        data={
                            "spot_name": place_name,
                            "action": "create",
                            "error": str(e)
                        }
                    )
                    log_error("SPOT_CREATE_ERROR", f"Spot作成エラー ({place_name}): {e}")
                    error_count += 1
    
    result = {
        "imported": imported_count,
        "created": created_count,  # 新規作成数
        "merged": merged_count,    # マージ数
        "errors": error_count,
        "skipped": skipped_count,
        "total_processed": len(results),
        "spot_ids": list(set(spot_ids))
    }
    
    log_debug_step(
        step="spot_import",
        status="completed",
        data={
            "imported_count": imported_count,
            "errors_count": error_count,
            "skipped_count": skipped_count,
            "total_processed": len(results),
            "spot_ids_count": len(result["spot_ids"])
        }
    )
    
    # #region agent log
    with open(r'c:\projects\SatoTrip-AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
        f.write(json_module.dumps({"location":"spot_import_service.py:420","message":"import_spots_from_youtube_data completed","data":{"imported":imported_count,"errors":error_count,"skipped":skipped_count,"spot_ids_count":len(result["spot_ids"])},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"D"},ensure_ascii=False)+'\n')
    # #endregion
    
    return result


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
    
    log_debug_step(
        step="location_assignment",
        status="processing",
        data={
            "total_spots": len(spots),
            "spot_ids_count": len(spot_ids) if spot_ids else 0
        }
    )
    
    for spot in spots:
        # 既に位置情報がある場合はスキップ
        if spot.latitude and spot.longitude:
            skipped_count += 1
            continue
        
        if not spot.name or not spot.area:
            skipped_count += 1
            continue
        
        # 位置情報を取得
        # #region agent log
        import json as json_module
        import time
        with open(r'c:\projects\SatoTrip-AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
            f.write(json_module.dumps({"location":"spot_import_service.py:424","message":"Getting location","data":{"spot_name":spot.name,"spot_id":spot.id,"area":spot.area,"prefecture":prefecture},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"E"},ensure_ascii=False)+'\n')
        # #endregion
        lat, lng = get_geo(spot.name, spot.area, prefecture)
        # #region agent log
        with open(r'c:\projects\SatoTrip-AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
            f.write(json_module.dumps({"location":"spot_import_service.py:425","message":"Location result","data":{"spot_name":spot.name,"spot_id":spot.id,"latitude":lat,"longitude":lng,"success":bool(lat and lng)},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"E"},ensure_ascii=False)+'\n')
        # #endregion
        if lat and lng:
            try:
                spot.latitude = lat
                spot.longitude = lng
                db.commit()
                db.refresh(spot)
                updated_count += 1
                log_debug_step(
                    step="location_assignment",
                    status="updated",
                    data={
                        "spot_name": spot.name,
                        "spot_id": spot.id,
                        "latitude": lat,
                        "longitude": lng
                    }
                )
            except Exception as e:
                db.rollback()
                log_debug_step(
                    step="location_assignment",
                    status="error",
                    data={
                        "spot_name": spot.name,
                        "spot_id": spot.id,
                        "error": str(e)
                    }
                )
                log_error("SPOT_UPDATE_ERROR", f"Spot更新エラー ({spot.name}): {e}")
                error_count += 1
        else:
            log_debug_step(
                step="location_assignment",
                status="error",
                data={
                    "spot_name": spot.name,
                    "spot_id": spot.id,
                    "error": "Geocoding returned None"
                }
            )
            error_count += 1
    
    result = {
        "updated": updated_count,
        "errors": error_count,
        "skipped": skipped_count,
        "total_processed": len(spots)
    }
    
    # #region agent log
    import json as json_module
    import time
    with open(r'c:\projects\SatoTrip-AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
        f.write(json_module.dumps({"location":"spot_import_service.py:531","message":"add_location_to_existing_spots completed","data":{"updated":updated_count,"errors":error_count,"skipped":skipped_count,"total_processed":len(spots)},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"E"},ensure_ascii=False)+'\n')
    # #endregion
    
    return result


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
                
                # #region agent log
                import json
                import time
                with open(r'c:\projects\SatoTrip-AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
                    f.write(json.dumps({"location":"spot_import_service.py:647","message":"checking duplicate before query","data":{"place_name":place_name,"spot_name":spot_data["name"],"spot_area":spot_data.get("area"),"spot_category":spot_data.get("category"),"theme":place_data.get("theme","")},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"E"},ensure_ascii=False)+'\n')
                # #endregion
                
                # 重複チェック（名前とエリアで判定）
                existing_spot = db.query(Spot).filter(
                    Spot.name == spot_data["name"],
                    Spot.area == spot_data["area"]
                ).first()
                
                # #region agent log
                with open(r'c:\projects\SatoTrip-AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
                    f.write(json.dumps({"location":"spot_import_service.py:655","message":"duplicate check result","data":{"spot_name":spot_data["name"],"spot_area":spot_data.get("area"),"category":spot_data.get("category"),"existing_spot_found":existing_spot is not None,"existing_spot_id":existing_spot.id if existing_spot else None,"existing_spot_category":existing_spot.category if existing_spot else None},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"E"},ensure_ascii=False)+'\n')
                # #endregion
                
                if existing_spot:
                    # CSVインポートでは常にマージする（target_categoryは使用しない）
                    # 重複が見つかった場合、マージする
                    try:
                        merge_spot_data(existing_spot, spot_data, target_category=None)
                        db.commit()
                        db.refresh(existing_spot)
                        imported_count += 1  # マージもインポートとしてカウント
                        # #region agent log
                        with open(r'c:\projects\SatoTrip-AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
                            f.write(json.dumps({"location":"spot_import_service.py:662","message":"spot merged with existing","data":{"spot_name":spot_data["name"],"existing_spot_id":existing_spot.id,"existing_spot_category":existing_spot.category,"new_category":spot_data.get("category")},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"E"},ensure_ascii=False)+'\n')
                        # #endregion
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
        Spotモデルのカテゴリ（History, Nature, Food, Culture, Shopping, Art, Relax, Tourism, Experience, Event, HotSpring, ScenicView, Cafe, Hotel, Drink, Fashion, Date, Drive）
    """
    if not category:
        return "Culture"  # デフォルト
    
    category_lower = category.lower()
    
    # 既存のmap_category_from_themeを参考にマッピング
    if "グルメ" in category or "食べ" in category or "料理" in category or "レストラン" in category or "食材" in category:
        return "Food"
    elif "観光" in category or "名所" in category or "見学" in category or "スポット" in category:
        return "Tourism"
    elif "体験" in category:
        return "Experience"
    elif "イベント" in category or "祭り" in category or "フェス" in category:
        return "Event"
    elif "温泉" in category:
        return "HotSpring"
    elif "絶景" in category or "景色" in category or "ビュー" in category:
        return "ScenicView"
    elif "歴史" in category or "史跡" in category or "遺跡" in category or "文化" in category:
        return "History"
    elif "カフェ" in category or "喫茶" in category:
        return "Cafe"
    elif "自然" in category or "公園" in category or "山" in category or "海" in category:
        return "Nature"
    elif "宿泊" in category or "ホテル" in category or "旅館" in category or "民宿" in category:
        return "Hotel"
    elif "お酒" in category or "酒" in category or "飲み" in category or "バー" in category:
        return "Drink"
    elif "ショッピング" in category or "買い物" in category:
        return "Shopping"
    elif "ファッション" in category or "服" in category or "衣類" in category:
        return "Fashion"
    elif "デート" in category or "恋人" in category:
        return "Date"
    elif "ドライブ" in category or "車" in category or "ドライブコース" in category:
        return "Drive"
    elif "アート" in category or "美術" in category or "芸術" in category:
        return "Art"
    elif "癒やし" in category or "リラックス" in category or "リラクゼーション" in category:
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

