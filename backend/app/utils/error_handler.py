"""
エラーハンドリング改善
リトライ機能、フォールバック機能、エラーログ記録
既存のSatoTripプロジェクトの実装を参考
"""
import time
import json
import logging
import os
from datetime import datetime
from typing import Optional, Callable, Any, List, Dict
from functools import wraps

# ログ記録の設定
LOGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# ファイルハンドラーの設定
log_file = os.path.join(LOGS_DIR, f"error_log_{datetime.now().strftime('%Y%m%d')}.log")
file_handler = logging.FileHandler(log_file, encoding="utf-8")
file_handler.setLevel(logging.DEBUG)

# フォーマッターの設定
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


def retry_on_error(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    リトライデコレータ
    
    Args:
        max_retries: 最大リトライ回数
        delay: 初回待機時間（秒）
        backoff: 指数バックオフ係数
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        wait_time = delay * (backoff ** attempt)
                        logger.warning(
                            f"{func.__name__} 失敗 (試行 {attempt + 1}/{max_retries}): {str(e)}. "
                            f"{wait_time:.1f}秒後に再試行します。"
                        )
                        time.sleep(wait_time)
                    else:
                        logger.error(
                            f"{func.__name__} 最終失敗 (総試行 {max_retries}回): {str(e)}"
                        )
                        break
            
            # 全てのリトライが失敗した場合
            raise last_exception
        
        return wrapper
    return decorator


def generate_template_plan(
    selected_places: list, 
    duration: int, 
    destination: str = "",
    database_spots: Optional[List[Dict[str, Any]]] = None
) -> dict:
    """
    フォールバック用のテンプレートプラン
    Gemini APIと同じ形式（spotsフィールドを含む）を返す
    
    Args:
        selected_places: 選択された観光スポットのリスト
        duration: 旅行日数
        destination: 目的地（エリア名の取得に使用）
        database_spots: データベースから取得したスポットリスト（優先的に使用）
    
    Returns:
        テンプレートプランの辞書（Gemini API形式）
    """
    database_spots = database_spots or []
    logger.info(f"テンプレートプランを生成しています ({duration}日間, データベーススポット: {len(database_spots)}件, 選択スポット: {len(selected_places)}件)")
    
    # Gemini APIと同じ形式で返す
    spots = []
    
    # データベーススポットを優先的に使用
    if database_spots:
        # データベーススポットを日数に応じて分散
        spots_per_day = max(1, len(database_spots) // duration)
        start_time = 9
        
        for day in range(1, duration + 1):
            day_start_idx = (day - 1) * spots_per_day
            day_end_idx = day_start_idx + spots_per_day if day < duration else len(database_spots)
            day_spots = database_spots[day_start_idx:day_end_idx]
            
            current_time = start_time
            for spot in day_spots:
                spot_name = spot.get("name", "")
                spot_desc = spot.get("description", "") or f"{spot_name}での観光"
                spot_category = spot.get("category", "Culture")
                spot_tags = spot.get("tags", [])
                spot_duration = spot.get("durationMinutes", 60)
                
                spots.append({
                    "day": day,
                    "name": spot_name,
                    "description": spot_desc,
                    "category": spot_category,
                    "tags": spot_tags if isinstance(spot_tags, list) else [],
                    "durationMinutes": spot_duration,
                    "transportMode": "walk" if day == 1 and len(spots) == 0 else "train",
                    "transportDuration": 0 if day == 1 and len(spots) == 0 else 20,
                    "startTime": f"{current_time:02d}:00"
                })
                current_time += (spot_duration // 60) + 1  # 滞在時間 + 移動時間を考慮
    # データベーススポットがない場合、選択されたスポットを使用
    elif selected_places:
        places_per_day = max(1, len(selected_places) // duration)
        start_time = 9
        
        for day in range(1, duration + 1):
            day_places = selected_places[(day-1)*places_per_day:day*places_per_day]
            current_time = start_time
            
            for place in day_places:
                place_name = place.get("name", "") if isinstance(place, dict) else str(place)
                place_desc = place.get("description", "") or place.get("recommend", "") if isinstance(place, dict) else ""
                place_area = place.get("area", destination) if isinstance(place, dict) else destination
                place_category = place.get("category", "Culture") if isinstance(place, dict) else "Culture"
                
                spots.append({
                    "day": day,
                    "name": place_name,
                    "description": place_desc or f"{place_name}での観光",
                    "category": place_category,
                    "tags": place.get("tags", []) if isinstance(place, dict) else [],
                    "durationMinutes": place.get("durationMinutes", 60) if isinstance(place, dict) else 60,
                    "transportMode": "walk" if day == 1 and len(spots) == 0 else "train",
                    "transportDuration": 0 if day == 1 and len(spots) == 0 else 20,
                    "startTime": f"{current_time:02d}:00"
                })
                current_time += 2
    else:
        # スポットがない場合はデフォルトスポットを生成
        for day in range(1, duration + 1):
            spots.append({
                "day": day,
                "name": f"{destination}の観光スポット",
                "description": f"{destination}の観光スポットを訪れます",
                "category": "Culture",
                "tags": ["観光"],
                "durationMinutes": 60,
                "transportMode": "walk" if day == 1 else "train",
                "transportDuration": 0 if day == 1 else 20,
                "startTime": "10:00"
            })
    
    template = {
        "title": f"{destination}の{duration}日間旅行プラン" if destination else f"{duration}日間の旅行プラン",
        "area": destination,
        "budget": 50000 * duration,  # デフォルト予算
        "spots": spots,
        "grounding_urls": []
    }
    
    logger.info(f"テンプレートプラン生成完了 ({len(spots)}件のスポット)")
    return template


def safe_json_parse(text: str, fallback: Optional[dict] = None) -> dict:
    """
    安全なJSON解析
    
    Args:
        text: JSON文字列
        fallback: 解析失敗時のフォールバック辞書
    
    Returns:
        解析されたJSON辞書
    """
    try:
        # コードブロック除去
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        
        return json.loads(text)
    except json.JSONDecodeError as e:
        # JSON解析失敗時のフォールバック
        logger.error(f"JSON解析失敗: {str(e)}. テキスト: {text[:100]}...")
        if fallback:
            logger.info("フォールバック辞書を使用します")
            return fallback
        raise ValueError("JSON解析に失敗しました")


def log_error(error_type: str, error_message: str, context: Optional[dict] = None):
    """
    エラーを詳細情報付けて記録
    
    Args:
        error_type: エラータイプ (e.g., "API_ERROR", "PARSE_ERROR")
        error_message: エラーメッセージ
        context: 追加情報 (e.g., {"user_id": "123", "plan_id": "456"})
    """
    context_str = json.dumps(context, ensure_ascii=False) if context else ""
    logger.error(f"[{error_type}] {error_message} | Context: {context_str}")

