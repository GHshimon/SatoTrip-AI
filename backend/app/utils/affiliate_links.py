"""宿泊サイト検索リンク生成"""
import urllib.parse
from datetime import datetime, date
from typing import Dict, Optional, Any, Tuple
from app.config import settings


# アフィリエイトID（環境変数から読み込み、オプション）
AFFILIATE_IDS = {
    "rakuten_travel": getattr(settings, "AFFILIATE_RAKUTEN_TRAVEL", ""),
    "yahoo_travel": getattr(settings, "AFFILIATE_YAHOO_TRAVEL", ""),
    "yahoo_sid": getattr(settings, "AFFILIATE_YAHOO_SID", ""),
    "yahoo_pid": getattr(settings, "AFFILIATE_YAHOO_PID", ""),
    "booking": getattr(settings, "AFFILIATE_BOOKING", ""),
    "jalan": getattr(settings, "AFFILIATE_JALAN", ""),
}


def validate_date_range(check_in: str, check_out: str) -> Tuple[bool, Optional[str]]:
    """日付範囲の妥当性を検証"""
    if not check_in or not check_out:
        return True, None
    try:
        check_in_date = datetime.strptime(check_in, "%Y-%m-%d").date()
        check_out_date = datetime.strptime(check_out, "%Y-%m-%d").date()
        today = date.today()
        if check_in_date < today or check_out_date < today:
            return False, "チェックイン日は今日以降の日付を指定してください"
        if check_out_date <= check_in_date:
            return False, "チェックアウト日はチェックイン日より後の日付を指定してください"
        if (check_out_date - check_in_date).days > 365:
            return False, "滞在日数は365日以内にしてください"
        return True, None
    except ValueError as e:
        return False, f"日付形式が正しくありません（YYYY-MM-DD形式で指定してください）: {e}"


def validate_guests(num_guests: int) -> Tuple[bool, Optional[str]]:
    """予約人数の妥当性を検証"""
    if num_guests < 1:
        return False, "予約人数は1人以上を指定してください"
    if num_guests > 20:
        return False, "予約人数は20人以下にしてください"
    return True, None


def _build_error_response(hotel_name: str, area: str, affiliate_type: str, error_msg: str) -> Dict[str, Any]:
    """エラーレスポンスを生成"""
    return {
        "name": hotel_name or "ホテル検索",
        "area": area,
        "link": "",
        "type": "hotel",
        "affiliate": affiliate_type,
        "description": "エラー",
        "error": error_msg
    }


def generate_hotel_link(
    hotel_name: str,
    area: str,
    check_in: str = "",
    check_out: str = "",
    num_guests: int = 2,
    affiliate_type: str = "rakuten"
) -> Dict[str, Any]:
    """
    ホテル検索リンク生成（アフェリエイトリンクは保留）
    
    Args:
        hotel_name: ホテル名（検索クエリとして使用）
        area: エリア名
        check_in: チェックイン日（YYYY-MM-DD形式）
        check_out: チェックアウト日（YYYY-MM-DD形式）
        num_guests: 予約人数（1-20）
        affiliate_type: 予約サイトタイプ（rakuten, yahoo, jalan）
    
    Returns:
        予約サイトリンク情報を含む辞書
    """
    if check_in and check_out:
        is_valid, error_msg = validate_date_range(check_in, check_out)
        if not is_valid:
            return _build_error_response(hotel_name, area, affiliate_type, error_msg)
    
    is_valid, error_msg = validate_guests(num_guests)
    if not is_valid:
        return _build_error_response(hotel_name, area, affiliate_type, error_msg)
    
    if affiliate_type == "rakuten":
        params = {}
        try:
            if hotel_name:
                params["f_keyword"] = hotel_name
            if area:
                params["f_landmark"] = area
            if check_in and check_out:
                params["f_checkin"] = check_in.replace("-", "")
                params["f_checkout"] = check_out.replace("-", "")
            if num_guests:
                params["f_adult_num"] = str(num_guests)
            base_url = "https://travel.rakuten.co.jp/"
            link = f"{base_url}?{urllib.parse.urlencode(params, encoding='utf-8')}" if params else base_url
        except Exception as e:
            return _build_error_response(hotel_name, area, "楽天トラベル", f"URL生成エラー: {str(e)}")
        return {
            "name": hotel_name or "ホテル検索",
            "area": area,
            "link": link,
            "type": "hotel",
            "affiliate": "楽天トラベル",
            "description": "楽天トラベルでホテルを検索・予約"
        }
    
    elif affiliate_type == "yahoo":
        params = {}
        try:
            if hotel_name:
                params["keyword"] = hotel_name
            if area:
                params["area"] = area
            if check_in and check_out:
                params["checkin"] = check_in.replace("-", "")
                params["checkout"] = check_out.replace("-", "")
            if num_guests:
                params["adult"] = str(num_guests)
            base_url = "https://travel.yahoo.co.jp/"
            link = f"{base_url}?{urllib.parse.urlencode(params, encoding='utf-8')}" if params else base_url
        except Exception as e:
            return _build_error_response(hotel_name, area, "Yahoo!トラベル", f"URL生成エラー: {str(e)}")
        return {
            "name": hotel_name or "ホテル検索",
            "area": area,
            "link": link,
            "type": "hotel",
            "affiliate": "Yahoo!トラベル",
            "description": "Yahoo!トラベルでホテルを検索・予約"
        }
    
    elif affiliate_type == "jalan":
        params = {}
        try:
            if hotel_name:
                params["keyword"] = hotel_name
            if area:
                # じゃらんはエリア名をそのまま使用
                params["area"] = area
            if check_in and check_out:
                params["stayYear"] = check_in[:4]
                params["stayMonth"] = check_in[5:7]
                params["stayDay"] = check_in[8:10]
                check_in_date = datetime.strptime(check_in, "%Y-%m-%d")
                check_out_date = datetime.strptime(check_out, "%Y-%m-%d")
                stay_count = (check_out_date - check_in_date).days
                if stay_count > 0:
                    params["stayCount"] = str(stay_count)
            if num_guests:
                params["adultNum"] = str(num_guests)
            base_url = "https://www.jalan.net/"
            link = f"{base_url}?{urllib.parse.urlencode(params, encoding='utf-8')}" if params else base_url
        except (ValueError, IndexError) as e:
            return _build_error_response(hotel_name, area, "じゃらん", f"日付形式エラー: {str(e)}")
        except Exception as e:
            return _build_error_response(hotel_name, area, "じゃらん", f"URL生成エラー: {str(e)}")
        return {
            "name": hotel_name or "ホテル検索",
            "area": area,
            "link": link,
            "type": "hotel",
            "affiliate": "じゃらん",
            "description": "じゃらんでホテルを検索・予約"
        }
    
    # デフォルト: Google検索
    return {
        "name": hotel_name or "ホテル検索",
        "area": area,
        "link": f"https://www.google.com/search?q={urllib.parse.quote(f'{area} ホテル')}",
        "type": "hotel",
        "affiliate": "検索",
        "description": "ホテルを検索"
    }

