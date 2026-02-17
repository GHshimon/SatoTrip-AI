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
from app.utils.tag_normalizer import normalize_tags, tags_to_dict_list, TagSource


# Gemini API設定
if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)


def format_places_for_prompt(places: List[Dict[str, Any]], include_details: bool = True) -> str:
    """
    スポット情報をプロンプト用にフォーマット（品質向上版）
    
    Args:
        places: スポットリスト
        include_details: 詳細情報を含めるか（デフォルト: True）
    
    Returns:
        フォーマットされたスポット情報の文字列
    """
    if not places:
        return "なし"
    
    formatted = []
    for p in places:
        name = p.get("name", "")
        area = p.get("area", "")
        
        # 基本情報（SatoTrip形式に合わせる）
        line_parts = [f"- {name}"]
        if area:
            line_parts.append(f"({area})")
        
        # items/tags の情報（構造化された特徴）
        items = p.get("items", []) or p.get("tags", [])
        if items:
            # itemsが辞書のリストの場合、文字列に変換
            items_str_list = []
            for item in items[:5]:  # 最大5件
                if isinstance(item, str):
                    items_str_list.append(item)
                elif isinstance(item, dict):
                    # 辞書の場合はnameキーを取得、なければ文字列化
                    items_str_list.append(item.get("name", str(item)))
                else:
                    items_str_list.append(str(item))
            items_str = ", ".join(items_str_list)
            line_parts.append(f": {items_str}")
        
        formatted.append(" ".join(line_parts))
        
        # 詳細情報（include_details=True の場合のみ）
        if include_details:
            details = []
            
            # recommend または description（SatoTrip形式に合わせる）
            recommend = p.get("recommend", "")
            description = p.get("description", "")
            if recommend:
                details.append(f"  {recommend[:100]}")
            elif description:
                details.append(f"  {description[:100]}")
            
            # 構造化情報（カテゴリ、評価、滞在時間）
            category = p.get("category", "")
            rating = p.get("rating")
            duration = p.get("durationMinutes") or p.get("duration_minutes")
            
            if category:
                details.append(f"  カテゴリ: {category}")
            if rating:
                details.append(f"  評価: {rating:.1f}/5.0")
            if duration:
                details.append(f"  滞在時間: 約{duration}分")
            
            if details:
                formatted.extend(details)
    
    return "\n".join(formatted)


def build_plan_generation_prompt(
    destination: str,
    days: int,
    budget: str,
    themes: List[str],
    pending_spots: List[Dict[str, Any]],
    database_spots: List[Dict[str, Any]] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    transportation: Optional[str] = None,
    preferences: Optional[str] = None,
    spot_distances: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """
    プラン生成用プロンプトを構築（品質向上版）
    
    Args:
        destination: 目的地
        days: 日数
        budget: 予算感
        themes: テーマリスト
        pending_spots: 必須スポットリスト
        database_spots: データベースから取得したスポットリスト
        start_time: 開始時間（オプション）
        end_time: 終了時間（オプション）
        transportation: 交通手段（オプション）
        preferences: 希望・要望（オプション）
    
    Returns:
        構築されたプロンプト文字列
    """
    # 1. 基本情報セクション
    basic_info = f"""以下の観光スポットを{days}日間で効率的に回る旅行プランを作成してください。

【選択されたスポット（必須・データベース登録済みのみ）】
以下のスポットは、管理者画面（データベース）に登録されているスポットのみです。
データベースに登録されていないスポットは使用できません。

{format_places_for_prompt(pending_spots, include_details=True) if pending_spots else "（選択されたスポットはありません）"}
"""
    
    # 2. データベース情報セクション（SatoTrip-AI の強み）
    db_info = ""
    if database_spots:
        db_info = f"""
【データベース内の利用可能なスポット】
以下のスポットは、SatoTripのデータベースに実際に登録されている情報です。
**重要**: プラン作成時は、このデータベースに登録されているスポットのみを使用してください。
データベースに登録されていないスポットは使用できません。

{format_places_for_prompt(database_spots, include_details=False)}  # 詳細は簡略化
"""
    
    # 2.5. スポット間の距離・時間情報（利用可能な場合）
    distance_info = ""
    if spot_distances:
        distance_info = "\n【スポット間の距離・移動時間情報】\n"
        distance_info += "以下の情報を参考に、移動時間を正確に計算してください：\n"
        for dist_info in spot_distances[:10]:  # 最大10件まで
            from_name = dist_info.get("from", "")
            to_name = dist_info.get("to", "")
            distance_km = dist_info.get("distance_km", 0)
            duration_min = dist_info.get("duration_minutes", 0)
            if from_name and to_name:
                distance_info += f"- {from_name} → {to_name}: 距離 {distance_km:.1f}km, 移動時間 約{duration_min:.0f}分\n"
        distance_info += "\n"
    
    # 3. プラン要件セクション（条件付き）
    # themesが文字列のリストであることを確認
    themes_list = []
    if themes:
        for theme in themes:
            if isinstance(theme, str):
                themes_list.append(theme)
            elif isinstance(theme, dict):
                # 辞書の場合はnameキーを取得、なければ文字列化
                themes_list.append(theme.get("name", str(theme)))
            else:
                themes_list.append(str(theme))
    
    requirements = [
        f"- 目的地: {destination}",
        f"- 日数: {days}日間",
        f"- 予算感: {budget}",
        f"- テーマ: {', '.join(themes_list) if themes_list else '人気'}",
    ]
    
    if start_time:
        requirements.append(f"- 開始時間: {start_time}")
    if end_time:
        requirements.append(f"- 終了時間: {end_time}")
    if transportation:
        requirements.append(f"- 交通手段: {transportation}")
    if preferences:
        requirements.append(f"- 希望・要望: {preferences}")
    
    requirements_text = "\n".join(requirements)
    
    # 4. 指示セクション（明確で実行可能）
    time_constraint = f"開始時間 {start_time} から終了時間 {end_time} の間でスケジュールを組んでください" if start_time and end_time else "1日の活動時間を適切に配分してください"
    
    # 交通手段ごとの移動時間の目安
    transport_guidelines = {
        "車": "車での移動: 市街地で平均40km/h、高速道路で80-100km/hを想定。駐車時間（5-10分）も考慮してください。",
        "電車": "電車での移動: 駅間移動時間 + 乗り換え時間（5-15分） + 駅から目的地までの徒歩時間（5-10分）を考慮してください。",
        "バス": "バスでの移動: バス停間移動時間 + 待ち時間（5-10分） + バス停から目的地までの徒歩時間（3-5分）を考慮してください。",
        "徒歩": "徒歩での移動: 平均時速4km（分速67m）で計算してください。距離1km = 約15分。",
        "その他": "適切な交通手段を選択し、移動時間を計算してください。"
    }
    transport_instruction = transport_guidelines.get(transportation, transport_guidelines["その他"]) if transportation else "適切な交通手段を選択し、移動時間を計算してください。"
    transportation_consistency_note = f"。交通手段は「{transportation}」で統一してください。" if transportation else "。"

    instructions = f"""
【プラン要件】
{requirements_text}

【作成指示】
1. **データベース限定**: データベースに登録されているスポットのみを使用してください。データベースにないスポットは使用できません。
2. **必須スポット組み込み**: 選択されたスポット（データベース登録済み）は必ずプランに組み込んでください
3. **テーマ重視**: 「{'・'.join(themes_list) if themes_list else '人気'}」に関連するスポットを優先的に選定してください
4. **情報活用**: 各スポットの説明には、データベースに記録されている情報を活用してください
5. **時間制約**: {time_constraint}
6. **交通手段**: {transport_instruction}
7. **禁止事項**: データベースに登録されていないスポットを生成したり、提案したりしないでください{transportation_consistency_note}

【滞在時間の設定】
- データベースに「滞在時間: 約XX分」と記載されている場合は、その値を優先的に使用してください
- 記載がない場合は、スポットの種類に応じて適切な滞在時間を設定してください：
  * グルメ・レストラン: 60-90分
  * 観光スポット・博物館: 60-120分
  * ショッピング: 30-60分
  * 自然・公園: 90-180分
  * カフェ・軽食: 30-45分

【時刻計算のロジック】
以下のルールに従って、各スポットの開始時刻を正確に計算してください：
1. **最初のスポット**: 開始時刻は指定された開始時間（{start_time or '09:00'}）から開始
2. **次のスポットの開始時刻**: 前のスポットの終了時刻 + 移動時間
   - 前のスポットの終了時刻 = 前のスポットの開始時刻 + 滞在時間（分）
   - 例: 09:00開始、滞在60分 → 終了時刻 10:00 → 移動20分 → 次のスポット開始時刻 10:20
3. **移動時間の計算**: 
   - スポット間の距離が不明な場合: 交通手段に応じた目安時間を使用
   - 距離が分かる場合: 距離 ÷ 速度（km/h） × 60 = 移動時間（分）
4. **終了時間の制約**: 各日の最後のスポットの終了時刻が、指定された終了時間（{end_time or '18:00'}）を超えないようにしてください
5. **時間の余裕**: 移動時間には、待ち時間や乗り換え時間も含めてください

【出力時の注意】
- startTimeは「HH:MM」形式で正確に計算してください
- durationMinutesは分単位の数値で指定してください（データベースの値を使用）
- transportDurationは分単位の数値で指定してください（実際の移動時間を計算）
- 時刻の計算が不整合にならないよう、必ず前のスポットの終了時刻から次のスポットの開始時刻を計算してください
"""
    
    # 5. 出力形式セクション（デュアル形式）
    output_format = f"""
【出力形式】
必ず以下のJSONフォーマットのみを含むコードブロック(```json ... ```)を出力してください。
両方の形式（days配列とspots配列）を含めてください。

```json
{{
  "title": "プランのタイトル (例: 【SatoTrip厳選】{destination}の最旬トレンド旅)",
  "summary": "プランの概要（100文字程度）",
  "area": "エリア名",
  "budget": 予算総額(数値),
  "days": [
    {{
      "day": 1,
      "theme": "テーマ（例: グルメ、観光、歴史）",
      "schedule": [
        {{
          "time": "09:00",
          "activity": "活動内容",
          "place": "スポット名",
          "duration": "滞在時間（例: 1-2時間）",
          "description": "説明"
        }}
      ]
    }}
  ],
  "spots": [
    {{
      "day": 1,
      "name": "スポット名（データベースから選定）",
      "description": "説明文（データベースの情報を活用）",
      "category": "History" | "Nature" | "Food" | "Culture" | "Shopping" | "Art" | "Relax" | "Tourism" | "Experience" | "Event" | "HotSpring" | "ScenicView" | "Cafe" | "Hotel" | "Drink" | "Fashion" | "Date" | "Drive",
      "tags": ["#絶景", "#行列グルメ", "#穴場"],
      "durationMinutes": 60,
      "transportMode": "walk" | "train" | "car" | "bus",
      "transportDuration": 20,
      "startTime": "10:00"
    }}
  ],
  "tips": ["ヒント1", "ヒント2"]
}}
```
"""
    
    return basic_info + db_info + distance_info + instructions + output_format


def parse_duration_to_minutes(duration_str: str) -> int:
    """
    滞在時間の文字列を分単位に変換
    
    Args:
        duration_str: 滞在時間（例: "1-2時間", "60分", "2時間"）
    
    Returns:
        分単位の数値
    """
    import re
    
    # "1-2時間" 形式
    match = re.search(r'(\d+)-(\d+)時間', duration_str)
    if match:
        return (int(match.group(1)) + int(match.group(2))) // 2 * 60
    
    # "2時間" 形式
    match = re.search(r'(\d+)時間', duration_str)
    if match:
        return int(match.group(1)) * 60
    
    # "60分" 形式
    match = re.search(r'(\d+)分', duration_str)
    if match:
        return int(match.group(1))
    
    # デフォルト
    return 60


def convert_days_to_spots(days_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    days配列形式からspots配列形式に変換
    
    Args:
        days_data: days配列形式のプランデータ
    
    Returns:
        spots配列形式のプランデータ
    """
    spots = []
    for day_info in days_data:
        day = day_info.get("day", 1)
        theme = day_info.get("theme", "観光")
        
        for schedule_item in day_info.get("schedule", []):
            spot = {
                "day": day,
                "name": schedule_item.get("place", ""),
                "description": schedule_item.get("description", schedule_item.get("activity", "")),
                "category": theme if theme in ["History", "Nature", "Food", "Culture", "Shopping", "Art", "Relax", "Tourism", "Experience", "Event", "HotSpring", "ScenicView", "Cafe", "Hotel", "Drink", "Fashion", "Date", "Drive"] else "Culture",
                "tags": [],
                "durationMinutes": parse_duration_to_minutes(schedule_item.get("duration", "60分")),
                "transportMode": "walk",  # デフォルト
                "transportDuration": 0,
                "startTime": schedule_item.get("time", "09:00")
            }
            spots.append(spot)
    return spots


def convert_spots_to_days(spots_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    spots配列形式からdays配列形式に変換
    
    Args:
        spots_data: spots配列形式のプランデータ
    
    Returns:
        days配列形式のプランデータ
    """
    days_dict = {}
    for spot in spots_data:
        day = spot.get("day", 1)
        if day not in days_dict:
            days_dict[day] = {
                "day": day,
                "theme": spot.get("category", "観光"),
                "schedule": []
            }
        
        duration_minutes = spot.get("durationMinutes", 60)
        duration_str = f"{duration_minutes}分" if duration_minutes < 60 else f"{duration_minutes // 60}時間"
        
        schedule_item = {
            "time": spot.get("startTime", "09:00"),
            "activity": spot.get("description", "")[:50] if spot.get("description") else "観光",
            "place": spot.get("name", ""),
            "duration": duration_str,
            "description": spot.get("description", "")
        }
        days_dict[day]["schedule"].append(schedule_item)
    
    # 時間順にソート
    for day_data in days_dict.values():
        day_data["schedule"].sort(key=lambda x: x.get("time", "00:00"))
    
    return sorted(days_dict.values(), key=lambda x: x["day"])


def generate_plan(
    destination: str,
    days: int,
    budget: str,
    themes: List[str],
    pending_spots: List[Dict[str, Any]],
    database_spots: List[Dict[str, Any]] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    transportation: Optional[str] = None,
    preferences: Optional[str] = None,
    spot_distances: Optional[List[Dict[str, Any]]] = None,
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
    
    # プロンプトを構築（品質向上版）
    prompt = build_plan_generation_prompt(
        destination=destination,
        days=days,
        budget=budget,
        themes=themes,
        pending_spots=pending_spots,
        database_spots=database_spots,
        start_time=start_time,
        end_time=end_time,
        transportation=transportation,
        preferences=preferences,
        spot_distances=spot_distances
    )
    
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
            
            # デュアル出力形式の確保（days と spots の両方があることを確認）
            if "days" in plan and "spots" not in plan:
                # days配列のみの場合、spots配列を生成
                plan["spots"] = convert_days_to_spots(plan["days"])
            elif "spots" in plan and "days" not in plan:
                # spots配列のみの場合、days配列を生成
                plan["days"] = convert_spots_to_days(plan["spots"])
            elif "days" in plan and "spots" in plan:
                # 両方ある場合は、整合性を確認（spotsを優先）
                if not plan["spots"]:
                    plan["spots"] = convert_days_to_spots(plan["days"])
                if not plan["days"]:
                    plan["days"] = convert_spots_to_days(plan["spots"])
            
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

【滞在時間の算出方法】
以下のルールに従って、適切な滞在時間（分単位）を算出してください：

1. **カテゴリ別の標準滞在時間**:
   - History（歴史・史跡）: 60-120分（博物館・資料館は90-120分、史跡・記念碑は30-60分）
   - Nature（自然・公園）: 90-180分（公園・散策路は90-120分、展望台・絶景スポットは30-60分）
   - Food（グルメ・レストラン）: 60-90分（レストランは60-90分、カフェ・軽食は30-45分、立ち食い・屋台は15-30分）
   - Shopping（ショッピング）: 30-60分（大型ショッピングモールは60-120分、専門店・市場は30-60分）
   - Art（アート・美術館）: 90-180分（大型美術館は120-180分、小さなギャラリーは30-60分）
   - Relax（温泉・癒し）: 120-240分（温泉施設は120-180分、スパ・リラクゼーションは60-120分）
   - Culture（文化・伝統）: 60-120分（伝統工芸体験は90-120分、文化施設は60-90分）

2. **スポットの規模を考慮**:
   - 大型施設（複数の展示エリア、広大な敷地）: 上記の上限値を使用
   - 中型施設（標準的な規模）: 上記の中間値を使用
   - 小型施設（コンパクトな規模）: 上記の下限値を使用

3. **実際の訪問時間を考慮**:
   - 観光客の平均滞在時間を考慮
   - 混雑状況や待ち時間は考慮しない（標準的な滞在時間）
   - スポットの特徴（見学コースの長さ、展示物の量など）を考慮

出力形式は必ず以下のJSONフォーマットのみを含むコードブロック(```json ... ```)としてください。

```json
{{
  "name": "{spot_name}",
  "area": "都道府県または主要都市（例: 京都、東京、浅草、金沢）",
  "category": "History" | "Nature" | "Food" | "Shopping" | "Art" | "Relax" | "Culture" の中から最も適切なものを1つ,
  "description": "スポットの魅力や特徴を100〜200文字程度で魅力的に記述してください。",
  "price": 参考価格（大人の入場料や平均予算、円単位、数値のみ、不明な場合は0）,
  "image": "https://placehold.co/600x400?text={spot_name}" (このまま出力),
  "duration_minutes": 標準滞在時間（分単位、数値。上記のルールに従って算出してください。最小15分、最大480分）,
  "tags": ["タグ1", "タグ2", "タグ3"]
}}
```

【タグ生成のルール】
- スポットの特徴を表す3〜5個のタグを生成してください
- カテゴリに応じた適切なタグを選択してください（例: Foodカテゴリなら「グルメ」「美食」「レストラン」など）
- タグは日本語で、簡潔に（2〜4文字程度）記述してください
- ハッシュタグ記号（#）は不要です
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
        
        # 成功時は通常の辞書を返す（タグを構造化タグに変換）
        if result and not result.get("error"):
            # タグを構造化タグに変換
            if "tags" in result and isinstance(result["tags"], list):
                try:
                    tag_strings = result["tags"]
                    structured_tags = normalize_tags(tag_strings, source=TagSource.AI)
                    result["tags"] = tags_to_dict_list(structured_tags)
                except Exception:
                    # エラーが発生した場合は元のタグを保持
                    pass
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
