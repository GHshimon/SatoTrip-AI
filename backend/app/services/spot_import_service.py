"""
スポットインポートサービス
収集データをSpotモデルに変換してDB保存
"""
import json
import re
import csv
import uuid
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.config import settings
from app.models.spot import Spot
from app.utils.error_handler import log_error
from app.utils.debug_logger import log_debug_step
from app.utils.tag_normalizer import normalize_tags, tags_to_dict_list, TagSource


# description の最大長（マージ時の暴走を防ぐ）
_DESCRIPTION_MAX_LEN = 600

# AI / Places の戻り値で「上書きする」と判定する最小文字数
_DESCRIPTION_GOOD_ENOUGH_LEN = 80


def _coerce_float(value: Any) -> Optional[float]:
    """安全に float 変換"""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _coords_in_prefecture(
    lat: Optional[float], lng: Optional[float], prefecture: Optional[str]
) -> Optional[bool]:
    """
    座標が都道府県境界（places_service._PREFECTURE_BOUNDS）内かを判定する。

    戻り: True=境界内 / False=境界外 / None=判定不能（県不明・座標なし・境界未登録）。
    None のときは呼び出し側で「判定できない」として扱う。
    """
    if not prefecture or lat is None or lng is None:
        return None
    try:
        from app.services.places_service import _PREFECTURE_BOUNDS
    except Exception:
        return None
    b = _PREFECTURE_BOUNDS.get(prefecture)
    if not b:
        return None
    return (b["lat_min"] <= lat <= b["lat_max"]) and (b["lng_min"] <= lng <= b["lng_max"])


def verify_spot_candidate(
    places_info: Optional[Dict[str, Any]], prefecture: Optional[str]
) -> Dict[str, Any]:
    """
    Places 照合結果から候補スポットを3値判定する（設計書 SPOT_DATA_QUALITY.md §5）。

    判定順:
      1. Places 未ヒット → rejected(no_places_hit)
      2. business_status == CLOSED_PERMANENTLY → rejected(closed)
      3. matched_score >= 自動合格閾値 かつ business_status in (None, OPERATIONAL)
         かつ 座標が県境界内（県が分かる場合のみ。不明ならこの条件はスキップ） → verified
      4. matched_score >= 要レビュー閾値 / CLOSED_TEMPORARILY / 座標が県境界外 → needs_review
      5. matched_score < 要レビュー閾値 → rejected(low_score)

    戻り: {"status", "score", "business_status", "reason"}
    """
    if not places_info:
        return {
            "status": "rejected",
            "score": None,
            "business_status": None,
            "reason": "no_places_hit",
        }

    business_status = places_info.get("business_status")
    score = _coerce_float(places_info.get("matched_score"))

    # 恒久閉業は自動棄却（掲載＝誤情報になる）
    if business_status == "CLOSED_PERMANENTLY":
        return {
            "status": "rejected",
            "score": score,
            "business_status": business_status,
            "reason": "closed",
        }

    lat = _coerce_float(places_info.get("latitude"))
    lng = _coerce_float(places_info.get("longitude"))
    # True=境界内 / False=境界外 / None=判定不能
    in_bounds = _coords_in_prefecture(lat, lng, prefecture)

    auto_pass = settings.SPOT_VERIFY_AUTO_PASS_SCORE
    review = settings.SPOT_VERIFY_REVIEW_SCORE

    # 自動合格: 高スコア AND 営業中(またはstatus不明) AND 県境界外でない
    if (
        score is not None
        and score >= auto_pass
        and business_status in (None, "OPERATIONAL")
        and in_bounds is not False
    ):
        return {
            "status": "verified",
            "score": score,
            "business_status": business_status,
            "reason": None,
        }

    # 要レビュー: 中スコア / 一時閉業 / 県境界外
    if (
        (score is not None and score >= review)
        or business_status == "CLOSED_TEMPORARILY"
        or in_bounds is False
    ):
        reason = None
        if in_bounds is False:
            reason = "out_of_bounds"
        elif business_status == "CLOSED_TEMPORARILY":
            reason = "temporarily_closed"
        return {
            "status": "needs_review",
            "score": score,
            "business_status": business_status,
            "reason": reason,
        }

    # 低スコアは自動棄却
    return {
        "status": "rejected",
        "score": score,
        "business_status": business_status,
        "reason": "low_score",
    }


# description に書いてはいけない検証不能な事実断定（設計書 SPOT_FIELD_SPEC.md §4）。
# 受賞・格付け／最上級・序列／由来断定／数値的事実を対象にする簡易フィルタ用パターン。
_DESCRIPTION_NG_PATTERNS = [
    r"ミシュラン",
    r"三ツ星",
    r"三つ星",
    r"星付き",
    r"受賞",
    # 「◯◯賞」（鑑賞・観賞などの一般語は除外）
    r"(?<![鑑観])賞",
    # 最上級・序列
    r"日本一",
    r"世界一",
    r"県内一",
    r"[Nn][Oo]\.?\s*1",
    r"ナンバーワン",
    r"行列必至",
    # 由来・歴史断定
    r"元祖",
    r"発祥",
    r"創業",
    r"名物",
    # 数値的事実（年間◯万人・◯席 など）
    r"年間[0-9０-９〇一二三四五六七八九十百千万]+",
    r"[0-9０-９〇一二三四五六七八九十百千万]+\s*席",
]


def _contains_description_ng_word(text: str) -> bool:
    """文中に NG ワードが含まれるか"""
    for pattern in _DESCRIPTION_NG_PATTERNS:
        if re.search(pattern, text):
            return True
    return False


def filter_description_ng_words(description: Optional[str]) -> Optional[str]:
    """
    保存前の description から NG ワードを含む文を除去する簡易フィルタ（設計書 §4）。

    句点（。！!？?）区切りで文に分割し、NG ワードを含む文だけを落として再結合する。
    残る文が無ければ None を返す。
    """
    if not description:
        return description
    text = description.strip()
    if not text:
        return None
    # 区切り文字を保持したまま文分割
    sentences = re.split(r"(?<=[。！!？?])", text)
    kept: List[str] = []
    for sentence in sentences:
        if not sentence.strip():
            continue
        if _contains_description_ng_word(sentence):
            continue
        kept.append(sentence)
    result = "".join(kept).strip()
    return result or None


def _build_verification_columns(spot_data: Dict[str, Any], source: str) -> Dict[str, Any]:
    """
    enrich 済み spot_data から Spot 構築用の検証系カラム値をまとめる。

    verified のときのみ verified_at に現在時刻を入れる。
    """
    status = spot_data.get("verification_status") or "unverified"
    verified_at = datetime.now() if status == "verified" else None
    return {
        "source": source,
        "verification_status": status,
        "verification_score": spot_data.get("verification_score"),
        "verified_at": verified_at,
        "business_status": spot_data.get("business_status"),
        "rating_count": spot_data.get("rating_count"),
        "price_level": spot_data.get("price_level"),
        "price_range_min": spot_data.get("price_range_min"),
        "price_range_max": spot_data.get("price_range_max"),
        "opening_hours": spot_data.get("opening_hours"),
        "description_source": spot_data.get("description_source"),
        "rejected_reason": spot_data.get("rejected_reason"),
    }


def enrich_spot_data(
    spot_data: Dict[str, Any],
    *,
    prefecture: Optional[str] = None,
    source_video: Optional[Dict[str, Any]] = None,
    metrics: Optional[Dict[str, int]] = None,
) -> Dict[str, Any]:
    """
    動画由来の粗い spot_data を Places（一次ソース）+ Gemini（非事実系）で補強する。

    設計方針（SPOT_DATA_QUALITY.md §3 / SPOT_FIELD_SPEC.md §1）:
      - 事実フィールド（place_id/住所/緯度経度/電話/サイト/rating/営業情報/価格）は Places のみ。
      - Gemini から採用してよいのは description/category/duration_minutes/tags/area(分類補助) のみ。
        AI 由来の住所・価格・座標は保存しない。
      - Places を先行させ、未ヒット候補（後段で棄却）には AI エンリッチを行わずコストを抑える。
      - 最後に verify_spot_candidate で3値判定し、検証情報を enriched に載せる。

    引数の ``spot_data`` は破壊的に書き換えず、コピーを返す。
    """
    enriched = dict(spot_data)

    name = (enriched.get("name") or "").strip()
    if not name:
        return enriched

    pref = prefecture or ""

    places_info: Optional[Dict[str, Any]] = None
    places_enabled = bool(settings.SPOT_ENRICH_WITH_PLACES and settings.GOOGLE_MAPS_API_KEY)

    # 1) Google Places を先行（事実フィールドの一次ソース）
    if places_enabled:
        try:
            from app.services.places_service import enrich_spot_with_places

            places_info = enrich_spot_with_places(
                name=name,
                area=enriched.get("area"),
                prefecture=pref or None,
                category=enriched.get("category"),
            )
            if metrics is not None:
                metrics["places_search_count"] = metrics.get("places_search_count", 0) + int(places_info.get("search_attempts", 0) if places_info else 1)
                metrics["details_call_count"] = metrics.get("details_call_count", 0) + int(places_info.get("details_called", 0) if places_info else 0)
            if places_info:
                if metrics is not None:
                    metrics["places_hit_count"] = metrics.get("places_hit_count", 0) + 1
                if places_info.get("place_id"):
                    enriched["place_id"] = places_info["place_id"]
                if places_info.get("address"):
                    enriched["address"] = places_info["address"]
                lat = _coerce_float(places_info.get("latitude"))
                lng = _coerce_float(places_info.get("longitude"))
                if lat is not None:
                    enriched["latitude"] = lat
                if lng is not None:
                    enriched["longitude"] = lng
                if metrics is not None and lat is not None and lng is not None:
                    metrics["geo_filled_count"] = metrics.get("geo_filled_count", 0) + 1
                if places_info.get("phone"):
                    enriched["phone"] = places_info["phone"]
                if places_info.get("website"):
                    enriched["website"] = places_info["website"]
                # rating は Places 由来のみ（件数とセット）。無ければ None（一律デフォルト値は付けない）
                enriched["rating"] = _coerce_float(places_info.get("rating"))
                if places_info.get("rating_count") is not None:
                    enriched["rating_count"] = int(places_info["rating_count"])
                # 価格は序数 price_level と実額 price_range のみ保存（旧 price=金額への書込はしない）
                if places_info.get("price_level") is not None:
                    enriched["price_level"] = places_info["price_level"]
                if places_info.get("price_range_min") is not None:
                    enriched["price_range_min"] = places_info["price_range_min"]
                if places_info.get("price_range_max") is not None:
                    enriched["price_range_max"] = places_info["price_range_max"]
                if places_info.get("business_status"):
                    enriched["business_status"] = places_info["business_status"]
                if places_info.get("opening_hours") is not None:
                    enriched["opening_hours"] = places_info["opening_hours"]
                if places_info.get("image") and not enriched.get("image"):
                    enriched["image"] = places_info["image"]
                # Places の正規名称が大きく違う場合は採用しない（誤同定防止）
                # 名前は呼び出し元で控えた値を尊重
            else:
                if metrics is not None:
                    metrics["places_miss_count"] = metrics.get("places_miss_count", 0) + 1
        except Exception as e:
            log_error("SPOT_ENRICH_PLACES_EXCEPTION", f"Places エンリッチ例外 ({name}): {e}")
        if settings.SPOT_ENRICH_DELAY_SEC:
            time.sleep(settings.SPOT_ENRICH_DELAY_SEC)

    # 2) Gemini で非事実系（description/category/duration/tags/area分類補助）を補強
    #    Places 有効時は未ヒット候補（後段で棄却）に AI 呼び出しを行わずコストを抑える。
    run_ai = bool(settings.SPOT_ENRICH_WITH_GEMINI and settings.GEMINI_API_KEY)
    if places_enabled and not places_info:
        run_ai = False
    if run_ai:
        if metrics is not None:
            metrics["gemini_enrich_call_count"] = metrics.get("gemini_enrich_call_count", 0) + 1
        try:
            from app.services.gemini_service import research_spot_info

            research = research_spot_info(name, area=enriched.get("area") or "", prefecture=pref)
            if research and not research.get("error"):
                research_desc = (research.get("description") or "").strip()
                if research_desc:
                    # NG ワードを含む文を除去してから採用し、AI 生成であることを記録
                    filtered_desc = filter_description_ng_words(research_desc[:_DESCRIPTION_MAX_LEN])
                    if filtered_desc:
                        enriched["description"] = filtered_desc
                        enriched["description_source"] = "ai"

                research_category = research.get("category")
                if research_category and not enriched.get("category"):
                    enriched["category"] = research_category

                research_duration = research.get("duration_minutes")
                if isinstance(research_duration, (int, float)) and research_duration > 0:
                    enriched["duration_minutes"] = int(research_duration)

                research_tags = research.get("tags")
                if research_tags:
                    enriched["tags"] = research_tags

                research_area = (research.get("area") or "").strip()
                if research_area and not enriched.get("area"):
                    enriched["area"] = research_area

                # 住所・価格は AI から採用しない（一次ソース限定。SPOT_FIELD_SPEC.md §4）
            elif research and research.get("error"):
                log_error(
                    "SPOT_ENRICH_GEMINI_ERROR",
                    f"research_spot_info エラー ({name}): {research.get('message')}",
                    {"name": name, "error_type": research.get("error_type")},
                )
        except Exception as e:
            log_error("SPOT_ENRICH_GEMINI_EXCEPTION", f"Gemini エンリッチ例外 ({name}): {e}")
        if settings.SPOT_ENRICH_DELAY_SEC:
            time.sleep(settings.SPOT_ENRICH_DELAY_SEC)

    # 3) 3値判定（設計書 §5）。呼び出し側が Spot 構築時に保存できるよう enriched に載せる。
    verification = verify_spot_candidate(places_info, pref or None)
    enriched["verification_status"] = verification["status"]
    enriched["verification_score"] = verification["score"]
    if verification.get("business_status") is not None:
        enriched["business_status"] = verification["business_status"]
    enriched["rejected_reason"] = (
        verification["reason"] if verification["status"] == "rejected" else None
    )
    # verify に渡した Places 情報も保持（呼び出し側の参照用）
    enriched["_places_info"] = places_info

    # 4) ソース動画情報を保持
    if source_video:
        existing_videos = enriched.get("source_videos") or []
        if not isinstance(existing_videos, list):
            existing_videos = []
        # 同一 URL は重複追加しない
        urls = {v.get("url") for v in existing_videos if isinstance(v, dict)}
        if source_video.get("url") not in urls:
            existing_videos.append(source_video)
        enriched["source_videos"] = existing_videos

    return enriched


def find_existing_spot(db: Session, spot_data: Dict[str, Any]) -> Optional[Spot]:
    """
    place_id 優先で既存スポットを検索。なければ name+area で互換検索。
    """
    place_id = spot_data.get("place_id")
    if place_id:
        existing = db.query(Spot).filter(Spot.place_id == place_id).first()
        if existing:
            return existing

    name = spot_data.get("name")
    area = spot_data.get("area")
    if name and area:
        return (
            db.query(Spot)
            .filter(Spot.name == name, Spot.area == area)
            .first()
        )
    if name:
        return db.query(Spot).filter(Spot.name == name).first()
    return None


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
    # description: 既存が十分な長さなら追記しない。短い場合のみ最大長まで連結。
    existing_desc = (existing_spot.description or "").strip()
    new_desc = (new_spot_data.get("description") or "").strip()
    if new_desc and new_desc not in existing_desc:
        if not existing_desc:
            existing_spot.description = new_desc[:_DESCRIPTION_MAX_LEN]
        elif len(existing_desc) < _DESCRIPTION_GOOD_ENOUGH_LEN:
            combined = f"{existing_desc} | {new_desc}".strip(" |")
            existing_spot.description = combined[:_DESCRIPTION_MAX_LEN]
        # 既存が十分長い場合は新規 description を捨てる（無限肥大防止）

    # 住所/place_id/電話/サイト: 既存が空なら新規で埋める
    if not getattr(existing_spot, "address", None) and new_spot_data.get("address"):
        existing_spot.address = new_spot_data["address"]
    if not getattr(existing_spot, "place_id", None) and new_spot_data.get("place_id"):
        existing_spot.place_id = new_spot_data["place_id"]
    if not getattr(existing_spot, "phone", None) and new_spot_data.get("phone"):
        existing_spot.phone = new_spot_data["phone"]
    if not getattr(existing_spot, "website", None) and new_spot_data.get("website"):
        existing_spot.website = new_spot_data["website"]

    # source_videos は配列追記
    new_videos = new_spot_data.get("source_videos") or []
    if new_videos:
        existing_videos = list(getattr(existing_spot, "source_videos", None) or [])
        urls = {v.get("url") for v in existing_videos if isinstance(v, dict)}
        for v in new_videos:
            if isinstance(v, dict) and v.get("url") not in urls:
                existing_videos.append(v)
                urls.add(v.get("url"))
        existing_spot.source_videos = existing_videos
    
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
    
    # image: 既存が空 or placehold ダミーなら新しい画像で上書き
    new_image = new_spot_data.get("image")
    existing_image = existing_spot.image or ""
    if new_image and (not existing_image or "placehold.co" in existing_image):
        existing_spot.image = new_image

    # latitude/longitude: 既存がない場合のみ新しい位置情報を設定
    if not existing_spot.latitude and new_spot_data.get("latitude") is not None:
        existing_spot.latitude = new_spot_data["latitude"]
    if not existing_spot.longitude and new_spot_data.get("longitude") is not None:
        existing_spot.longitude = new_spot_data["longitude"]
    
    # category: target_categoryが指定されている場合、既存カテゴリを保護（変更しない）
    # target_categoryが指定されていない場合も、既存カテゴリを優先
    # （既存カテゴリがない場合のみ新しいカテゴリを設定）
    if target_category:
        # target_categoryが指定されている場合、既存カテゴリを絶対に変更しない
        pass  # 既存カテゴリを維持
    elif not existing_spot.category and new_spot_data.get("category"):
        # target_categoryが指定されていない場合のみ、既存カテゴリがない場合に新しいカテゴリを設定
        existing_spot.category = new_spot_data["category"]

    # Places 由来の事実カラムは既存が空なら補完する（マージでも Phase 1 の情報を取りこぼさない）。
    # これがないと、複数キーワードで再ヒットしてマージされたスポットや既存スポットに
    # 営業時間・営業状態・評価件数・価格帯が永久に入らない（SPOT_FIELD_SPEC.md §1）。
    for col in (
        "business_status", "rating_count", "price_level",
        "price_range_min", "price_range_max", "opening_hours",
    ):
        if getattr(existing_spot, col, None) is None and new_spot_data.get(col) is not None:
            setattr(existing_spot, col, new_spot_data[col])
    # rating は一次ソース（Places）由来のみ。既存が無いときだけ補完（捏造はしない）
    if getattr(existing_spot, "rating", None) is None and new_spot_data.get("rating") is not None:
        existing_spot.rating = new_spot_data["rating"]
    # source が未設定なら記録
    if not getattr(existing_spot, "source", None) and new_spot_data.get("source"):
        existing_spot.source = new_spot_data["source"]

    # 検証ステータスは「上げる方向のみ」更新する（下げない。設計書 §3.6）。
    # verified へ昇格したときは照合日時・スコアも記録する。
    _status_rank = {"rejected": 0, "unverified": 1, "needs_review": 2, "verified": 3}
    new_status = new_spot_data.get("verification_status")
    cur_status = getattr(existing_spot, "verification_status", None) or "unverified"
    if new_status and _status_rank.get(new_status, 0) > _status_rank.get(cur_status, 0):
        existing_spot.verification_status = new_status
        if new_spot_data.get("verification_score") is not None:
            existing_spot.verification_score = new_spot_data["verification_score"]
        if new_status == "verified":
            existing_spot.verified_at = datetime.now()

    # area は既存を優先（変更しない）


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
        "duration_minutes": 60,  # 所要時間の目安（カテゴリ別の実値は enrich で上書き）
        "rating": None,  # rating は Places 由来のみ。一律デフォルト値は付けない（景表法対応）
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
    rejected_count = 0  # Places 照合で棄却した数（保存しない）
    review_count = 0    # 要レビューで保存した数
    verified_count = 0  # 自動合格で保存した数
    spot_ids: List[str] = []
    kpi_metrics: Dict[str, int] = {
        "places_search_count": 0,
        "places_hit_count": 0,
        "places_miss_count": 0,
        "details_call_count": 0,
        "gemini_enrich_call_count": 0,
        "geo_filled_count": 0,
    }
    
    
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
                
                # Spotデータを作成（動画由来の粗い初期値）
                spot_data = create_spot_from_data(spot_place_data, source_url)

                # 動画情報をソースとして保持
                source_video = {
                    "url": source_url,
                    "title": video_title,
                    "keyword": entry.get("keyword"),
                    "imported_at": datetime.now().isoformat(),
                }

                # Places 先行 + Gemini で店舗単位に補強し、3値判定を付与
                spot_data = enrich_spot_data(
                    spot_data,
                    prefecture=prefecture,
                    source_video=source_video,
                    metrics=kpi_metrics,
                )

                # rejected（Places未ヒット/低スコア/恒久閉業）は保存しない（設計書 §5）。
                # 公開されないことを保証するため DB へ入れずスキップ。
                if spot_data.get("verification_status") == "rejected":
                    rejected_count += 1
                    log_debug_step(
                        step="spot_import",
                        status="rejected",
                        data={
                            "spot_name": place_name,
                            "reason": spot_data.get("rejected_reason"),
                            "area": spot_data.get("area", ""),
                        },
                    )
                    continue

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
                if target_category:
                    target_category_en = category_map.get(target_category, target_category)
                    spot_data["category"] = target_category_en

                # 重複チェック: place_id 優先、なければ name+area
                existing_spot = find_existing_spot(db, spot_data)

                # target_category 指定時、見つかった既存スポットのカテゴリが target と異なる場合は別スポット扱い
                if existing_spot and target_category_en and existing_spot.category != target_category_en and not spot_data.get("place_id"):
                    existing_spot = None
                
                if existing_spot:
                    # 重複が見つかった場合、マージする
                    # （既に重複チェックでカテゴリも考慮しているため、カテゴリが一致する場合のみここに到達する）
                    try:
                        merge_spot_data(existing_spot, spot_data, target_category=target_category)
                        db.commit()
                        db.refresh(existing_spot)
                        imported_count += 1  # マージもインポートとしてカウント
                        merged_count += 1  # マージ数をカウント
                        # 内訳カウントは候補の判定単位で数える（rejected と粒度を揃える）
                        if spot_data.get("verification_status") == "verified":
                            verified_count += 1
                        elif spot_data.get("verification_status") == "needs_review":
                            review_count += 1
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
                    spot = Spot(
                        name=spot_data["name"],
                        description=spot_data.get("description"),
                        area=spot_data.get("area"),
                        address=spot_data.get("address"),
                        category=spot_data.get("category"),
                        duration_minutes=spot_data.get("duration_minutes"),
                        rating=spot_data.get("rating"),
                        image=spot_data.get("image"),
                        price=spot_data.get("price"),
                        tags=spot_data.get("tags"),
                        latitude=spot_data.get("latitude"),
                        longitude=spot_data.get("longitude"),
                        place_id=spot_data.get("place_id"),
                        phone=spot_data.get("phone"),
                        website=spot_data.get("website"),
                        source_videos=spot_data.get("source_videos"),
                        **_build_verification_columns(spot_data, "youtube"),
                    )
                    db.add(spot)
                    db.commit()
                    db.refresh(spot)
                    # コミット後、実際にデータベースに追加されているかを確認
                    if spot.id:
                        verified_spot = db.query(Spot).filter(Spot.id == spot.id).first()
                    imported_count += 1
                    created_count += 1  # 新規作成数をカウント
                    if spot_data.get("verification_status") == "verified":
                        verified_count += 1
                    elif spot_data.get("verification_status") == "needs_review":
                        review_count += 1
                    if spot.id:
                        spot_ids.append(spot.id)
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
        "rejected": rejected_count,      # Places 照合で棄却（DB保存せず）
        "verified": verified_count,      # 自動合格で保存
        "needs_review": review_count,    # 要レビューで保存（非公開）
        "total_processed": len(results),
        "spot_ids": list(set(spot_ids)),
        **kpi_metrics,
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

    # Places API で事前補完したうえでここに来るケースが多いため、
    # OpenCage キー未設定時はエラー連発を避けて安全にスキップする。
    if not settings.OPENCAGE_API_KEY:
        total = 0
        try:
            if spot_ids:
                total = db.query(Spot).filter(Spot.id.in_(spot_ids)).count()
            else:
                total = db.query(Spot).count()
        except Exception:
            total = len(spot_ids) if spot_ids else 0
        log_error(
            "LOCATION_ASSIGNMENT_SKIPPED_NO_OPENCAGE_KEY",
            "OPENCAGE_API_KEY 未設定のため OpenCage 補完をスキップしました",
            {"prefecture": prefecture, "target_count": total},
        )
        return {
            "updated": 0,
            "errors": 0,
            "skipped": total,
            "total_processed": total,
        }
    
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
        lat, lng = get_geo(spot.name, spot.area, prefecture)
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
    rejected_count = 0  # Places 照合で棄却した数（保存しない）
    review_count = 0    # 要レビューで保存した数
    verified_count = 0  # 自動合格で保存した数
    kpi_metrics: Dict[str, int] = {
        "places_search_count": 0,
        "places_hit_count": 0,
        "places_miss_count": 0,
        "details_call_count": 0,
        "gemini_enrich_call_count": 0,
        "geo_filled_count": 0,
    }

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

                # 記事情報をソースとして保持
                source_article = {
                    "url": source_url,
                    "title": entry.get("title", ""),
                    "keyword": entry.get("keyword"),
                    "imported_at": datetime.now().isoformat(),
                }

                # YouTube 経路と同様に Places 先行 + Gemini で補強し、3値判定を通す
                # （従来この経路は enrich を通らず素通しだった）
                spot_data = enrich_spot_data(
                    spot_data,
                    prefecture=prefecture,
                    source_video=source_article,
                    metrics=kpi_metrics,
                )

                # rejected は保存しない（設計書 §5。公開されないことを保証）
                if spot_data.get("verification_status") == "rejected":
                    rejected_count += 1
                    continue

                # 重複チェック: place_id 優先、なければ name+area（find_existing_spot に統一）
                existing_spot = find_existing_spot(db, spot_data)

                if existing_spot:
                    # 重複が見つかった場合、マージする（target_category は使用しない）
                    try:
                        merge_spot_data(existing_spot, spot_data, target_category=None)
                        db.commit()
                        db.refresh(existing_spot)
                        imported_count += 1  # マージもインポートとしてカウント
                        # 内訳カウントは候補の判定単位で数える（rejected と粒度を揃える）
                        if spot_data.get("verification_status") == "verified":
                            verified_count += 1
                        elif spot_data.get("verification_status") == "needs_review":
                            review_count += 1
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
                        address=spot_data.get("address"),
                        category=spot_data.get("category"),
                        duration_minutes=spot_data.get("duration_minutes"),
                        rating=spot_data.get("rating"),
                        image=spot_data.get("image"),
                        price=spot_data.get("price"),
                        tags=spot_data.get("tags"),
                        latitude=spot_data.get("latitude"),
                        longitude=spot_data.get("longitude"),
                        place_id=spot_data.get("place_id"),
                        phone=spot_data.get("phone"),
                        website=spot_data.get("website"),
                        source_videos=spot_data.get("source_videos"),
                        **_build_verification_columns(spot_data, "sns"),
                    )
                    db.add(spot)
                    db.commit()
                    db.refresh(spot)
                    imported_count += 1
                    if spot_data.get("verification_status") == "verified":
                        verified_count += 1
                    elif spot_data.get("verification_status") == "needs_review":
                        review_count += 1
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
        "rejected": rejected_count,      # Places 照合で棄却（DB保存せず）
        "verified": verified_count,      # 自動合格で保存
        "needs_review": review_count,    # 要レビューで保存（非公開）
        "total_processed": len(results),
        **kpi_metrics,
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
                        duration_minutes=60,  # 所要時間の目安（デフォルト）
                        rating=None,  # rating は Places 由来のみ。一律デフォルト値は付けない（景表法対応）
                        image=image_url if image_url else None,
                        price=price,
                        tags=tags,
                        latitude=latitude,
                        longitude=longitude,
                        # CSV は Places 照合を通さないため未検証扱い（verification_status は既定の unverified）
                        source="csv",
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

