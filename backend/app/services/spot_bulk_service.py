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


def bulk_add_spots_by_prefecture(
    prefecture: str,
    db: Session,
    keywords_config_path: Optional[str] = None,
    max_results_per_keyword: int = 5,
    max_keywords: Optional[int] = None,
    max_total_videos: Optional[int] = None,
    add_location: bool = True
) -> Dict[str, Any]:
    """
    都道府県名を元に複数キーワードで検索し、まとめてスポットを追加
    
    Args:
        prefecture: 都道府県名（例: "鹿児島県"）
        db: データベースセッション
        keywords_config_path: キーワード設定JSONファイルのパス（デフォルト: backend/data/search_keywords.json）
        max_results_per_keyword: キーワードあたりの最大取得件数
        add_location: 位置情報を付与するか（デフォルト: True）
    
    Returns:
        処理結果の辞書（imported, errors, skipped, total_keywords, quota_exceeded等）
    """
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
        with open(r'c:\projects\SatoTrip\.cursor\debug.log', 'a', encoding='utf-8') as f:
            f.write(json.dumps({"location":"spot_bulk_service.py:52","message":"prefecture not found - returning error dict","data":{"prefecture":prefecture,"return_keys":["success","error","imported","errors","skipped","total_keywords","quota_exceeded"]},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"A"},ensure_ascii=False)+'\n')
        # #endregion
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
    search_keywords = generate_search_keywords(filtered_config)
    
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

        youtube_data = collect_youtube_data(
            prefecture=prefecture,
            keywords_config_path=keywords_config_path,
            max_results_per_keyword=effective_max_results_per_keyword,
            max_keywords=effective_max_keywords,
            max_total_videos=effective_max_total_videos,
            stop_on_quota_exceeded=True
        )
    except Exception as e:
        error_msg = f"YouTubeデータ収集エラー: {str(e)}"
        log_error("YOUTUBE_COLLECTION_ERROR", error_msg, {"prefecture": prefecture})
        # #region agent log
        import json
        import time
        with open(r'c:\projects\SatoTrip\.cursor\debug.log', 'a', encoding='utf-8') as f:
            f.write(json.dumps({"location":"spot_bulk_service.py:83","message":"youtube collection error - returning error dict","data":{"prefecture":prefecture,"error":str(e),"return_keys":["success","error","imported","errors","skipped","total_keywords","quota_exceeded"]},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"B"},ensure_ascii=False)+'\n')
        # #endregion
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
            with open(r'c:\projects\SatoTrip\.cursor\debug.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps({"location":"spot_bulk_service.py:106","message":"quota exceeded with no videos - returning error dict","data":{"prefecture":prefecture,"youtube_data_keys":list(youtube_data.keys())},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"C"},ensure_ascii=False)+'\n')
            # #endregion
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
    try:
        import_result = import_spots_from_youtube_data(
            db=db,
            youtube_data=youtube_data,
            prefecture=prefecture
        )
    except Exception as e:
        error_msg = f"スポットインポートエラー: {str(e)}"
        log_error("SPOT_IMPORT_ERROR", error_msg, {"prefecture": prefecture})
        # #region agent log
        import json
        import time
        with open(r'c:\projects\SatoTrip\.cursor\debug.log', 'a', encoding='utf-8') as f:
            f.write(json.dumps({"location":"spot_bulk_service.py:127","message":"spot import error - returning error dict","data":{"prefecture":prefecture,"error":str(e),"youtube_data_keys":list(youtube_data.keys()) if youtube_data else None},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"D"},ensure_ascii=False)+'\n')
        # #endregion
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
        except Exception as e:
            log_error("LOCATION_UPDATE_ERROR", f"位置情報付与エラー: {str(e)}", {"prefecture": prefecture})
            # 位置情報のエラーは致命的ではないので続行
    
    # 結果をまとめる
    result = {
        "success": True,
        "imported": import_result.get("imported", 0),
        "errors": import_result.get("errors", 0),
        "skipped": import_result.get("skipped", 0),
        "total_keywords": len(search_keywords),
        "quota_exceeded": youtube_data.get("quota_exceeded", False),
        "processed_keywords": youtube_data.get("successful_keywords", 0),
        "failed_keywords": youtube_data.get("failed_keywords", 0),
        "total_videos": youtube_data.get("total_videos", 0)
    }
    
    # 位置情報の結果を追加
    if location_result:
        result["location_updated"] = location_result.get("updated", 0)
        result["location_errors"] = location_result.get("errors", 0)
    
    log_error(
        "BULK_ADD_COMPLETE",
        f"都道府県 '{prefecture}' の一括追加が完了しました。追加件数: {result['imported']}",
        result
    )
    
    return result

