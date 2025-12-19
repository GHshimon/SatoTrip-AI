"""
Gemini API統合サービス
既存のSatoTripプロジェクトの実装を参考
"""
import google.generativeai as genai
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.config import settings
from app.utils.error_handler import (
    retry_on_error,
    safe_json_parse,
    generate_template_plan,
    log_error
)


# Gemini API設定
if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)


def format_places_for_prompt(places: List[Dict[str, Any]]) -> str:
    """スポットリストをプロンプト用のテキストに変換"""
    if not places:
        return "なし"
    
    lines = []
    for i, place in enumerate(places, 1):
        name = place.get("name", "")
        description = place.get("description", "") or place.get("recommend", "")
        area = place.get("area", "")
        category = place.get("category", "")
        
        line = f"{i}. {name}"
        if area:
            line += f" ({area})"
        if category:
            line += f" [{category}]"
        if description:
            line += f" - {description[:100]}"
        lines.append(line)
    
    return "\n".join(lines)


def generate_plan(
    destination: str,
    days: int,
    budget: str,
    themes: List[str],
    pending_spots: List[Dict[str, Any]],
    database_spots: List[Dict[str, Any]] = None,
    use_fallback: bool = True,
) -> Optional[Dict[str, Any]]:
    """
    旅行プランを生成
    
    Args:
        destination: 目的地
        days: 日数
        budget: 予算感
        themes: テーマリスト
        pending_spots: 必須スポットリスト
        database_spots: データベースから取得したスポットリスト
        use_fallback: フォールバックを使用するか
    
    Returns:
        生成されたプラン辞書
    """
    if not settings.GEMINI_API_KEY:
        log_error("GEMINI_API_KEY_NOT_SET", "GEMINI_API_KEYが設定されていません")
        if use_fallback:
            return generate_template_plan(pending_spots, days, destination)
        return None
    
    database_spots = database_spots or []
    # #region agent log
    import json
    import time
    with open(r'c:\projects\SatoTrip-AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
        f.write(json.dumps({"location":"gemini_service.py:132","message":"generate_plan called","data":{"databaseSpotsCount":len(database_spots),"pendingSpotsCount":len(pending_spots)},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"C"},ensure_ascii=False)+'\n')
    # #endregion
    
    # データベーススポットをプロンプト用にフォーマット
    db_spots_text = format_places_for_prompt(database_spots)
    places_text = format_places_for_prompt(pending_spots)
    # #region agent log
    with open(r'c:\projects\SatoTrip-AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
        f.write(json.dumps({"location":"gemini_service.py:136","message":"After format_places_for_prompt","data":{"dbSpotsTextLength":len(db_spots_text),"dbSpotsTextPreview":db_spots_text[:200] if db_spots_text != "なし" else "なし"},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"C"},ensure_ascii=False)+'\n')
    # #endregion
    
    prompt = f"""あなたは旅行代理店AIエージェント「SatoTrip」です。
SatoTripが保有する**観光スポットデータベース（SNSやYouTubeのトレンド情報を事前に収集・分析済み）**に基づいて、ユーザーに最適な旅行プランを作成してください。

# 旅行条件
- 目的地: {destination}
- 日数: {days}日間
- 予算感: {budget}
- テーマ: {', '.join(themes) if themes else '人気'}
- 必須スポット: {places_text}

# データベース内の利用可能なスポット
以下のスポットは、SatoTripのデータベースに実際に登録されている情報です。
これらのスポットから選定してプランを作成してください：

{db_spots_text if db_spots_text != "なし" else "データベースに該当するスポットが見つかりませんでした。一般的な知識に基づいてプランを作成してください。"}

# 指示
- **必ず上記のデータベース内のスポットから選定してください。**
- 特に「{'・'.join(themes) if themes else '人気'}」に関連するスポットを優先的に選定してください。
- ユーザーの満足度が高くなるよう、効率的なルートと滞在時間を計算してください。
- 必須スポットは必ずプランに組み込んでください。
- 各スポットの説明には、データベースに記録されている情報を活用してください。
- データベースにないスポットは作成しないでください。

# 出力形式
必ず以下のJSONフォーマットのみを含むコードブロック(```json ... ```)を出力してください。

```json
{{
  "title": "プランのタイトル (例: 【SatoTrip厳選】{destination}の最旬トレンド旅)",
  "area": "エリア名",
  "budget": 予算総額(数値),
  "spots": [
    {{
      "day": 1,
      "name": "スポット名（データベースから選定）",
      "description": "説明文（データベースの情報を活用）",
      "category": "History" | "Nature" | "Food" | "Culture" | "Shopping" | "Art" | "Relax",
      "tags": ["#絶景", "#行列グルメ", "#穴場"],
      "durationMinutes": 60,
      "transportMode": "walk" | "train" | "car" | "bus",
      "transportDuration": 20,
      "startTime": "10:00"
    }}
  ]
}}
```
"""
    
    try:
        @retry_on_error(max_retries=3, delay=1.0, backoff=2.0)
        def _generate():
            try:
                model = genai.GenerativeModel("gemini-2.0-flash")
                response = model.generate_content(prompt)
            except Exception as api_error:
                # API呼び出しエラー（クォータエラーなど）を処理
                error_str = str(api_error)
                if "429" in error_str or "quota" in error_str.lower():
                    log_error("GEMINI_QUOTA_ERROR", f"Gemini APIクォータエラー: {error_str}")
                    # クォータエラーの場合は即座にフォールバックに移行
                    raise ValueError("Gemini APIクォータエラーが発生しました")
                else:
                    log_error("GEMINI_API_ERROR", f"Gemini API呼び出しエラー: {error_str}")
                    raise ValueError(f"Gemini API呼び出しエラー: {error_str}")
            
            # レスポンスのテキストを安全に取得
            if not hasattr(response, 'text') or not response.text:
                error_msg = "Gemini APIからのレスポンスが空です"
                if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                    error_msg += f": {response.prompt_feedback}"
                log_error("GEMINI_EMPTY_RESPONSE", error_msg)
                raise ValueError(error_msg)
            
            response_text = response.text
            log_error("DEBUG_RAW_RESPONSE", response_text[:1000] if len(response_text) > 1000 else response_text)
            parsed = safe_json_parse(response_text)
            log_error("DEBUG_PARSED_JSON", str(parsed)[:1000] if parsed else "None")
            return parsed
        
        plan = _generate()
        
        if plan:
            plan["selected_places_count"] = len(pending_spots)
            plan["generated_at"] = datetime.now().isoformat()
            return plan
        else:
            if use_fallback:
                log_error(
                    "PLAN_GENERATION_FALLBACK",
                    "プラン生成失敗、テンプレートを使用します",
                    {"days": days, "places_count": len(pending_spots), "database_spots_count": len(database_spots)}
                )
                return generate_template_plan(pending_spots, days, destination, database_spots)
            return None
    except ValueError as ve:
        # クォータエラーやAPIエラーの場合
        log_error(
            "PLAN_GENERATION_ERROR",
            f"プラン生成失敗: {str(ve)}",
            {"days": days, "places_count": len(pending_spots), "database_spots_count": len(database_spots)}
        )
        if use_fallback:
            return generate_template_plan(pending_spots, days, destination, database_spots)
        return None
    except Exception as e:
        # その他の予期しないエラー
        log_error(
            "PLAN_GENERATION_ERROR",
            f"プラン生成最終失敗: {str(e)}",
            {"days": days, "places_count": len(pending_spots), "database_spots_count": len(database_spots)}
        )
        if use_fallback:
            return generate_template_plan(pending_spots, days, destination, database_spots)
        return None


def research_spot_info(spot_name: str) -> Optional[Dict[str, Any]]:
    """
    スポット名を元に詳細情報を生成する
    
    Args:
        spot_name: スポット名
        
    Returns:
        JSON形式のスポット詳細情報 (name, area, category, description, price, etc.)
        エラー時は {"error": True, "error_type": "...", "message": "..."} 形式の辞書を返す
    """
    if not settings.GEMINI_API_KEY:
        log_error("GEMINI_API_KEY_NOT_SET", "GEMINI_API_KEYが設定されていません")
        return {
            "error": True,
            "error_type": "CONFIG_ERROR",
            "message": "GEMINI_API_KEYが設定されていません"
        }
        
    prompt = f"""
あなたは日本の観光スポットに詳しいAIアシスタントです。
以下の観光スポットについて、データベースに登録するための詳細情報を生成してください。
正確な情報が不明な場合は、一般的な傾向や推定値（妥当な範囲）を用いて補完してください。

対象スポット: {spot_name}

出力形式は必ず以下のJSONフォーマットのみを含むコードブロック(```json ... ```)としてください。

```json
{{
  "name": "{spot_name}",
  "area": "都道府県または主要都市（例: 京都、東京、浅草、金沢）",
  "category": "History" | "Nature" | "Food" | "Shopping" | "Art" | "Relax" | "Culture" の中から最も適切なものを1つ,
  "description": "スポットの魅力や特徴を100〜200文字程度で魅力的に記述してください。",
  "price": 参考価格（大人の入場料や平均予算、円単位、数値のみ、不明な場合は0）,
  "image": "https://placehold.co/600x400?text={spot_name}" (このまま出力),
  "duration_minutes": 標準滞在時間（分単位、数値）
}}
```
"""

    try:
        @retry_on_error(max_retries=3, delay=1.0, backoff=2.0)
        def _research():
            try:
                model = genai.GenerativeModel("gemini-2.0-flash")
                response = model.generate_content(prompt)
            except Exception as api_error:
                # API呼び出しエラー（クォータエラーなど）を処理
                error_str = str(api_error)
                if "429" in error_str or "quota" in error_str.lower():
                    log_error("GEMINI_QUOTA_ERROR", f"Gemini APIクォータエラー: {error_str}")
                    # リトライ待機時間を抽出（可能な場合）
                    retry_after = None
                    if "retry_delay" in error_str or "retry in" in error_str.lower():
                        # エラーメッセージから秒数を抽出を試みる
                        import re
                        match = re.search(r'retry in (\d+\.?\d*)s', error_str.lower())
                        if match:
                            retry_after = int(float(match.group(1)))
                    
                    raise ValueError(f"Gemini APIクォータエラーが発生しました{('。再試行まで約' + str(retry_after) + '秒待機してください。' if retry_after else '。しばらく待ってから再度お試しください。')}")
                else:
                    log_error("GEMINI_API_ERROR", f"Gemini API呼び出しエラー: {error_str}")
                    raise ValueError(f"Gemini API呼び出しエラー: {error_str}")
            
            # レスポンスのテキストを安全に取得
            if not hasattr(response, 'text') or not response.text:
                error_msg = "Gemini APIからのレスポンスが空です"
                if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                    error_msg += f": {response.prompt_feedback}"
                log_error("GEMINI_EMPTY_RESPONSE", error_msg)
                raise ValueError(error_msg)
            
            response_text = response.text
            parsed = safe_json_parse(response_text)
            return parsed
        
        result = _research()
        
        # 成功時は通常の辞書を返す
        if result and not result.get("error"):
            return result
        else:
            # パースエラーの場合
            return {
                "error": True,
                "error_type": "PARSE_ERROR",
                "message": "AIからのレスポンスの解析に失敗しました"
            }
        
    except ValueError as ve:
        # クォータエラーやAPIエラーの場合
        error_message = str(ve)
        error_type = "QUOTA_ERROR" if "クォータ" in error_message else "API_ERROR"
        log_error(
            "RESEARCH_SPOT_ERROR",
            f"スポットリサーチ失敗: {error_message}",
            {"spot_name": spot_name}
        )
        return {
            "error": True,
            "error_type": error_type,
            "message": error_message
        }
    except Exception as e:
        # その他の予期しないエラー
        log_error(
            "RESEARCH_SPOT_ERROR",
            f"スポットリサーチ最終失敗: {str(e)}",
            {"spot_name": spot_name}
        )
        return {
            "error": True,
            "error_type": "UNKNOWN_ERROR",
            "message": f"予期しないエラーが発生しました: {str(e)}"
        }
