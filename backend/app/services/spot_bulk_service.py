"""
スポット一括追加サービス
都道府県名を入力して複数キーワードで検索し、まとめてデータベースに追加
"""
import os
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.config import settings
from app.services.youtube_collection_service import (
    load_keyword_config,
    generate_search_keywords,
    collect_youtube_data
)
from app.services.spot_import_service import (
    import_spots_from_youtube_data,
    add_location_to_existing_spots
)
from app.utils.error_handler import log_error
from app.utils.debug_logger import init_debug_log, log_debug_step, finalize_debug_log


def bulk_add_spots_by_prefecture(
    prefecture: str,
    db: Session,
    keywords_config_path: Optional[str] = None,
    max_results_per_keyword: int = 5,
    max_keywords: Optional[int] = None,
    max_total_videos: Optional[int] = None,
    add_location: bool = True,
    category: Optional[str] = None
) -> Dict[str, Any]:
    """
    都道府県名を元に複数キーワードで検索し、まとめてスポットを追加
    
    Args:
        prefecture: 都道府県名（例: "鹿児島県"）
        db: データベースセッション
        keywords_config_path: キーワード設定JSONファイルのパス（デフォルト: backend/data/search_keywords.json）
        max_results_per_keyword: キーワードあたりの最大取得件数
        add_location: 位置情報を付与するか（デフォルト: True）
        category: 特定のカテゴリに絞る場合（例: "Food"）
    
    Returns:
        処理結果の辞書（imported, errors, skipped, total_keywords, quota_exceeded等）
    """
    # デバッグログセッションを開始
    # #region agent log
    import json as json_module
    import time
    with open(r'c:\projects\SatoTrip-AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
        f.write(json_module.dumps({"location":"spot_bulk_service.py:45","message":"init_debug_log called","data":{"prefecture":prefecture,"max_results_per_keyword":max_results_per_keyword,"max_keywords":max_keywords,"max_total_videos":max_total_videos,"add_location":add_location,"category":category},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"A"},ensure_ascii=False)+'\n')
    # #endregion
    session_id = init_debug_log(
        prefecture=prefecture,
        max_results_per_keyword=max_results_per_keyword,
        max_keywords=max_keywords,
        max_total_videos=max_total_videos,
        add_location=add_location,
        category=category
    )
    # #region agent log
    with open(r'c:\projects\SatoTrip-AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
        f.write(json_module.dumps({"location":"spot_bulk_service.py:52","message":"init_debug_log completed","data":{"session_id":session_id},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"A"},ensure_ascii=False)+'\n')
    # #endregion
    
    # #region agent log
    import json
    import time
    with open(r'c:\projects\SatoTrip-AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
        f.write(json.dumps({"location":"spot_bulk_service.py:66","message":"category parameter received","data":{"category":category,"category_type":type(category).__name__ if category else None,"category_repr":repr(category) if category else None},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"A"},ensure_ascii=False)+'\n')
    # #endregion
    
    target_keywords = None
    if category:
        # カテゴリに応じた検索キーワードを生成
        # 日本語カテゴリ名と英語カテゴリ名の両方に対応
        category_map = {
            # 英語カテゴリ名
            "Food": ["グルメ", "ランチ", "ディナー", "カフェ", "名物"],
            "Nature": ["自然", "絶景", "公園", "海", "山", "川", "景色"],
            "History": ["歴史", "神社", "寺", "史跡", "城", "文化財"],
            "Art": ["美術館", "博物館", "アート", "ギャラリー", "芸術"],
            "Shopping": ["買い物", "ショッピング", "お土産", "雑貨"],
            "Relax": ["温泉", "サウナ", "スパ", "リラックス", "癒やし"],
            "Culture": ["観光", "体験", "イベント", "祭り", "伝統"],
            "Tourism": ["観光", "名所", "見どころ", "スポット"],
            "Experience": ["体験", "アクティビティ", "ワークショップ"],
            "Event": ["イベント", "祭り", "フェス", "お祭り"],
            "HotSpring": ["温泉", "湯", "入浴", "温泉地"],
            "ScenicView": ["絶景", "景色", "展望", "ビュー"],
            "Cafe": ["カフェ", "コーヒー", "喫茶店"],
            "Hotel": ["宿泊", "ホテル", "旅館", "民宿", "泊まる"],
            "Drink": ["お酒", "酒", "居酒屋", "バー", "飲み物"],
            "Fashion": ["ファッション", "服", "アパレル", "ショップ"],
            "Date": ["デート", "カップル", "恋人"],
            "Drive": ["ドライブ", "車", "道の駅"],
            # 日本語カテゴリ名（search_keywords.jsonで使用される形式）
            "グルメ": ["グルメ", "ランチ", "ディナー", "カフェ", "名物"],
            "自然": ["自然", "絶景", "公園", "海", "山", "川", "景色"],
            "歴史": ["歴史", "神社", "寺", "史跡", "城", "文化財"],
            "観光": ["観光", "名所", "見どころ", "スポット"],
            "体験": ["体験", "アクティビティ", "ワークショップ"],
            "イベント": ["イベント", "祭り", "フェス", "お祭り"],
            "温泉": ["温泉", "湯", "入浴", "温泉地"],
            "絶景": ["絶景", "景色", "展望", "ビュー"],
            "カフェ": ["カフェ", "コーヒー", "喫茶店"],
            "宿泊": ["宿泊", "ホテル", "旅館", "民宿", "泊まる"],
            "お酒": ["お酒", "酒", "居酒屋", "バー", "飲み物"],
            "ショッピング": ["買い物", "ショッピング", "お土産", "雑貨"],
            "ファッション": ["ファッション", "服", "アパレル", "ショップ"],
            "デート": ["デート", "カップル", "恋人"],
            "ドライブ": ["ドライブ", "車", "道の駅"],
        }
        # #region agent log
        with open(r'c:\projects\SatoTrip-AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
            f.write(json.dumps({"location":"spot_bulk_service.py:107","message":"checking category_map","data":{"category":category,"category_in_map":category in category_map,"map_keys_sample":list(category_map.keys())[:15]},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"B"},ensure_ascii=False)+'\n')
        # #endregion
        terms = category_map.get(category, [])
        # #region agent log
        with open(r'c:\projects\SatoTrip-AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
            f.write(json.dumps({"location":"spot_bulk_service.py:108","message":"category_map.get result","data":{"category":category,"terms":terms,"terms_count":len(terms) if terms else 0},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"B"},ensure_ascii=False)+'\n')
        # #endregion
        if terms:
            target_keywords = [f"{prefecture} {term}" for term in terms]
            # #region agent log
            with open(r'c:\projects\SatoTrip-AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps({"location":"spot_bulk_service.py:111","message":"target_keywords generated","data":{"category":category,"target_keywords":target_keywords,"keywords_count":len(target_keywords)},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"B"},ensure_ascii=False)+'\n')
            # #endregion
            log_error(
                "CATEGORY_KEYWORDS_GENERATED",
                f"カテゴリ '{category}' のキーワードを生成しました: {len(target_keywords)}個",
                {"category": category, "keywords": target_keywords[:5]}  # 最初の5個のみ
            )
        else:
            # マップにない場合は、指定された文字をそのままキーワードとして使用（例: "グルメ" -> "鹿児島県 グルメ"）
            target_keywords = [f"{prefecture} {category}"]
            # #region agent log
            with open(r'c:\projects\SatoTrip-AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps({"location":"spot_bulk_service.py:120","message":"category not in map, using default","data":{"category":category,"target_keywords":target_keywords},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"B"},ensure_ascii=False)+'\n')
            # #endregion
            log_error(
                "CATEGORY_NOT_IN_MAP",
                f"カテゴリ '{category}' がマッピングに存在しません。デフォルトキーワードを使用します: {target_keywords[0]}",
                {"category": category, "available_categories": list(category_map.keys())[:10]}
            )
    
    # キーワード設定ファイルのパスを決定
    if keywords_config_path is None:
        # backend/data/search_keywords.jsonを相対パスで指定
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        keywords_config_path = os.path.join(base_dir, "data", "search_keywords.json")
    
    # キーワード設定を読み込み
    keyword_config = load_keyword_config(keywords_config_path)
    
    # 指定都道府県が設定に存在するか確認
    if prefecture not in keyword_config:
        error_msg = f"都道府県 '{prefecture}' がsearch_keywords.jsonに存在しません。"
        log_error("PREJECTURE_NOT_FOUND", error_msg, {"prefecture": prefecture})
        # #region agent log
        import json
        import time
        with open(r'c:\projects\SatoTrip-AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
            f.write(json.dumps({"location":"spot_bulk_service.py:52","message":"prefecture not found - returning error dict","data":{"prefecture":prefecture,"return_keys":["success","error","imported","errors","skipped","total_keywords","quota_exceeded"]},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"A"},ensure_ascii=False)+'\n')
        # #endregion
        finalize_debug_log(summary={"error": error_msg})
        return {
            "success": False,
            "error": error_msg,
            "imported": 0,
            "errors": 0,
            "skipped": 0,
            "total_keywords": 0,
            "quota_exceeded": False,
            "processed_keywords": 0,
            "failed_keywords": 0,
            "total_videos": 0
        }
    
    # 指定都道府県のキーワードのみを生成
    filtered_config = {prefecture: keyword_config[prefecture]}
    # #region agent log
    import json
    import time
    with open(r'c:\projects\SatoTrip-AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
        f.write(json.dumps({"location":"spot_bulk_service.py:87","message":"Generating keywords","data":{"prefecture":prefecture,"config_categories":filtered_config[prefecture].get("カテゴリ",[]),"config_areas":filtered_config[prefecture].get("エリア補助",[])},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"F"},ensure_ascii=False)+'\n')
    # #endregion
    search_keywords = generate_search_keywords(filtered_config)
    # #region agent log
    with open(r'c:\projects\SatoTrip-AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
        f.write(json.dumps({"location":"spot_bulk_service.py:88","message":"Keywords generated","data":{"keywords_count":len(search_keywords),"keywords_sample":search_keywords[:5]},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"F"},ensure_ascii=False)+'\n')
    # #endregion
    
    log_debug_step(
        step="keyword_generation",
        status="completed",
        data={
            "keywords_count": len(search_keywords),
            "keywords_sample": search_keywords[:10] if len(search_keywords) > 10 else search_keywords
        }
    )
    
    log_error(
        "BULK_ADD_START",
        f"都道府県 '{prefecture}' の一括追加を開始します。生成キーワード数: {len(search_keywords)}",
        {"prefecture": prefecture, "keyword_count": len(search_keywords)}
    )
    
    # YouTubeデータ収集
    try:
        # サーバ側強制上限（安全装置）
        def _clamp_int(value: Optional[int], default: int, hard_max: int) -> int:
            try:
                v = int(value) if value is not None else int(default)
            except Exception:
                v = int(default)
            if v < 1:
                v = 1
            if v > int(hard_max):
                v = int(hard_max)
            return v

        effective_max_results_per_keyword = _clamp_int(
            max_results_per_keyword,
            settings.BULK_ADD_DEFAULT_MAX_RESULTS_PER_KEYWORD,
            settings.BULK_ADD_HARD_MAX_RESULTS_PER_KEYWORD
        )
        effective_max_keywords = None
        if max_keywords is not None:
            effective_max_keywords = _clamp_int(
                max_keywords,
                settings.BULK_ADD_DEFAULT_MAX_KEYWORDS,
                settings.BULK_ADD_HARD_MAX_KEYWORDS
            )
        effective_max_total_videos = None
        if max_total_videos is not None:
            effective_max_total_videos = _clamp_int(
                max_total_videos,
                settings.BULK_ADD_DEFAULT_MAX_VIDEOS,
                settings.BULK_ADD_HARD_MAX_VIDEOS
            )

        log_debug_step(
            step="youtube_collection",
            status="started",
            data={
                "max_results_per_keyword": effective_max_results_per_keyword,
                "max_keywords": effective_max_keywords,
                "max_total_videos": effective_max_total_videos
            }
        )
        
        # #region agent log
        with open(r'c:\projects\SatoTrip-AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
            f.write(json.dumps({"location":"spot_bulk_service.py:230","message":"calling collect_youtube_data","data":{"target_keywords":target_keywords,"target_keywords_type":type(target_keywords).__name__ if target_keywords else None,"target_keywords_len":len(target_keywords) if target_keywords else 0},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"C"},ensure_ascii=False)+'\n')
        # #endregion
        youtube_data = collect_youtube_data(
            prefecture=prefecture,
            keywords_config_path=keywords_config_path,
            max_results_per_keyword=effective_max_results_per_keyword,
            max_keywords=effective_max_keywords,
            max_total_videos=effective_max_total_videos,
            stop_on_quota_exceeded=True,
            target_keywords=target_keywords
        )
        # #region agent log
        with open(r'c:\projects\SatoTrip-AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
            f.write(json.dumps({"location":"spot_bulk_service.py:239","message":"collect_youtube_data returned","data":{"total_videos":youtube_data.get("total_videos",0),"total_keywords":youtube_data.get("total_keywords",0),"processed_keywords":youtube_data.get("successful_keywords",0),"quota_exceeded":youtube_data.get("quota_exceeded",False)},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"D"},ensure_ascii=False)+'\n')
        # #endregion
        
        log_debug_step(
            step="youtube_collection",
            status="completed",
            data={
                "total_keywords": youtube_data.get("total_keywords", 0),
                "total_videos": youtube_data.get("total_videos", 0),
                "processed_keywords": youtube_data.get("successful_keywords", 0),
                "failed_keywords": youtube_data.get("failed_keywords", 0),
                "quota_exceeded": youtube_data.get("quota_exceeded", False)
            }
        )
    except Exception as e:
        error_msg = f"YouTubeデータ収集エラー: {str(e)}"
        log_debug_step(
            step="youtube_collection",
            status="error",
            error=str(e)
        )
        log_error("YOUTUBE_COLLECTION_ERROR", error_msg, {"prefecture": prefecture})
        # #region agent log
        import json
        import time
        with open(r'c:\projects\SatoTrip-AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
            f.write(json.dumps({"location":"spot_bulk_service.py:83","message":"youtube collection error - returning error dict","data":{"prefecture":prefecture,"error":str(e),"return_keys":["success","error","imported","errors","skipped","total_keywords","quota_exceeded"]},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"B"},ensure_ascii=False)+'\n')
        # #endregion
        finalize_debug_log(summary={"error": error_msg, "total_keywords": len(search_keywords)})
        return {
            "success": False,
            "error": error_msg,
            "imported": 0,
            "errors": 0,
            "skipped": 0,
            "total_keywords": len(search_keywords),
            "quota_exceeded": False,
            "processed_keywords": 0,
            "failed_keywords": 0,
            "total_videos": 0
        }
    
    # クォータエラーの場合
    if youtube_data.get("quota_exceeded", False):
        log_error(
            "YOUTUBE_QUOTA_EXCEEDED",
            f"YouTube APIクォータ制限に達しました。処理済み: {youtube_data.get('successful_keywords', 0)}/{len(search_keywords)}キーワード",
            {
                "prefecture": prefecture,
                "processed": youtube_data.get("successful_keywords", 0),
                "total": len(search_keywords)
            }
        )
        # クォータエラーでも収集できたデータがあればインポートを試みる
        if youtube_data.get("total_videos", 0) == 0:
            # #region agent log
            import json
            import time
            with open(r'c:\projects\SatoTrip-AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps({"location":"spot_bulk_service.py:106","message":"quota exceeded with no videos - returning error dict","data":{"prefecture":prefecture,"youtube_data_keys":list(youtube_data.keys())},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"C"},ensure_ascii=False)+'\n')
            # #endregion
            finalize_debug_log(summary={
                "error": "YouTube APIクォータ制限に達しました",
                "total_keywords": len(search_keywords),
                "quota_exceeded": True
            })
            return {
                "success": False,
                "error": "YouTube APIクォータ制限に達しました。データが収集できませんでした。",
                "imported": 0,
                "errors": 0,
                "skipped": 0,
                "total_keywords": len(search_keywords),
                "quota_exceeded": True,
                "processed_keywords": youtube_data.get("successful_keywords", 0),
                "failed_keywords": youtube_data.get("failed_keywords", 0),
                "total_videos": 0
            }
    
    # スポットにインポート
    log_debug_step(
        step="spot_import",
        status="started"
    )
    try:
        # #region agent log
        with open(r'c:\projects\SatoTrip-AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
            f.write(json.dumps({"location":"spot_bulk_service.py:283","message":"calling import_spots_from_youtube_data","data":{"youtube_results_count":len(youtube_data.get("results",[]))},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"E"},ensure_ascii=False)+'\n')
        # #endregion
        import_result = import_spots_from_youtube_data(
            db=db,
            youtube_data=youtube_data,
            prefecture=prefecture,
            target_category=category
        )
        # #region agent log
        with open(r'c:\projects\SatoTrip-AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
            f.write(json.dumps({"location":"spot_bulk_service.py:290","message":"import_spots_from_youtube_data returned","data":{"imported":import_result.get("imported",0),"created":import_result.get("created",0),"merged":import_result.get("merged",0),"errors":import_result.get("errors",0),"skipped":import_result.get("skipped",0)},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"E"},ensure_ascii=False)+'\n')
        # #endregion
        log_debug_step(
            step="spot_import",
            status="completed",
            data={
                "imported_count": import_result.get("imported", 0),
                "errors_count": import_result.get("errors", 0),
                "skipped_count": import_result.get("skipped", 0),
                "spot_ids": import_result.get("spot_ids", [])[:10]  # 最初の10件のみ
            }
        )
    except Exception as e:
        error_msg = f"スポットインポートエラー: {str(e)}"
        log_debug_step(
            step="spot_import",
            status="error",
            error=str(e)
        )
        log_error("SPOT_IMPORT_ERROR", error_msg, {"prefecture": prefecture})
        # #region agent log
        import json
        import time
        with open(r'c:\projects\SatoTrip-AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
            f.write(json.dumps({"location":"spot_bulk_service.py:127","message":"spot import error - returning error dict","data":{"prefecture":prefecture,"error":str(e),"youtube_data_keys":list(youtube_data.keys()) if youtube_data else None},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"D"},ensure_ascii=False)+'\n')
        # #endregion
        finalize_debug_log(summary={
            "error": error_msg,
            "total_keywords": len(search_keywords),
            "quota_exceeded": youtube_data.get("quota_exceeded", False) if youtube_data else False
        })
        return {
            "success": False,
            "error": error_msg,
            "imported": 0,
            "errors": 0,
            "skipped": 0,
            "total_keywords": len(search_keywords),
            "quota_exceeded": youtube_data.get("quota_exceeded", False) if youtube_data else False,
            "processed_keywords": youtube_data.get("successful_keywords", 0) if youtube_data else 0,
            "failed_keywords": youtube_data.get("failed_keywords", 0) if youtube_data else 0,
            "total_videos": youtube_data.get("total_videos", 0) if youtube_data else 0
        }
    
    # 位置情報を付与（オプション）
    location_result = None
    if add_location:
        log_debug_step(
            step="location_assignment",
            status="started"
        )
        try:
            spot_ids = import_result.get("spot_ids") or []
            if not isinstance(spot_ids, list):
                spot_ids = []
            # 今回追加/更新されたスポットのみ位置情報を付与
            if not spot_ids:
                location_result = {"updated": 0, "errors": 0, "skipped": 0, "total_processed": 0}
            else:
                location_result = add_location_to_existing_spots(
                    db=db,
                    spot_ids=spot_ids,
                    prefecture=prefecture
                )
            log_debug_step(
                step="location_assignment",
                status="completed",
                data={
                    "updated_count": location_result.get("updated", 0),
                    "errors_count": location_result.get("errors", 0),
                    "skipped_count": location_result.get("skipped", 0),
                    "total_processed": location_result.get("total_processed", 0)
                }
            )
        except Exception as e:
            log_debug_step(
                step="location_assignment",
                status="error",
                error=str(e)
            )
            log_error("LOCATION_UPDATE_ERROR", f"位置情報付与エラー: {str(e)}", {"prefecture": prefecture})
            # 位置情報のエラーは致命的ではないので続行
    
    # 結果をまとめる
    result = {
        "success": True if import_result.get("imported", 0) > 0 or youtube_data.get("total_videos", 0) > 0 else False,
        "imported": import_result.get("imported", 0),
        "created": import_result.get("created", 0),
        "merged": import_result.get("merged", 0),
        "errors": import_result.get("errors", 0),
        "skipped": import_result.get("skipped", 0),
        "total_keywords": len(search_keywords),
        "quota_exceeded": youtube_data.get("quota_exceeded", False),
        "processed_keywords": youtube_data.get("successful_keywords", 0),
        "failed_keywords": youtube_data.get("failed_keywords", 0),
        "total_videos": youtube_data.get("total_videos", 0)
    }
    
    # Gemini要約が全て失敗した場合の警告
    if result["total_videos"] == 0 and result["processed_keywords"] > 0:
        result["error"] = "YouTube検索は成功しましたが、Gemini要約が全て失敗しました。APIクォータを確認してください。"
    
    # 位置情報の結果を追加
    if location_result:
        result["location_updated"] = location_result.get("updated", 0)
        result["location_errors"] = location_result.get("errors", 0)
    
    log_error(
        "BULK_ADD_COMPLETE",
        f"都道府県 '{prefecture}' の一括追加が完了しました。追加件数: {result['imported']}",
        result
    )
    
    # デバッグログを保存
    # #region agent log
    import json as json_module
    import time
    with open(r'c:\projects\SatoTrip-AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
        f.write(json_module.dumps({"location":"spot_bulk_service.py:365","message":"finalize_debug_log called","data":{"summary":result},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"F"},ensure_ascii=False)+'\n')
    # #endregion
    log_file = finalize_debug_log(summary={
        "total_keywords": result.get("total_keywords", 0),
        "processed_keywords": result.get("processed_keywords", 0),
        "total_videos": result.get("total_videos", 0),
        "imported_spots": result.get("imported", 0),
        "location_updated": result.get("location_updated", 0),
        "errors": result.get("errors", 0)
    })
    # #region agent log
    with open(r'c:\projects\SatoTrip-AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
        f.write(json_module.dumps({"location":"spot_bulk_service.py:375","message":"finalize_debug_log completed","data":{"log_file":log_file},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"F"},ensure_ascii=False)+'\n')
    # #endregion
    if log_file:
        log_error("DEBUG_LOG_SAVED", f"デバッグログを保存しました: {log_file}")
    
    return result

