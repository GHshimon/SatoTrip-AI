"""
データ収集APIエンドポイント（管理者専用）
"""
import os
import tempfile
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from app.dependencies import get_db, get_current_admin_user
from app.models.user import User
from app.schemas.data_collection import (
    DataCollectionRequest,
    YouTubeCollectionResponse,
    LocationUpdateRequest,
    LocationUpdateResponse,
    SNSCollectionRequest,
    SNSCollectionResponse,
    SpotImportRequest,
    SNSImportRequest,
    SpotImportResponse,
    CSVImportResponse
)
from app.services.youtube_collection_service import collect_youtube_data
from app.services.geocoding_service import add_location_to_places
from app.services.sns_collection_service import collect_trending_topics, collect_sns_data_with_summary
from app.services.spot_import_service import (
    import_spots_from_youtube_data,
    import_spots_from_sns_data,
    add_location_to_existing_spots,
    import_spots_from_csv_file
)
from app.config import settings
from app.utils.error_handler import log_error

router = APIRouter(prefix="/api/admin/data-collection", tags=["データ収集（管理者）"])


@router.post("/youtube", response_model=YouTubeCollectionResponse)
async def collect_youtube_videos(
    request: DataCollectionRequest,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    YouTubeデータ収集を実行（管理者専用）
    
    YouTube Data APIから動画を取得し、Gemini APIで要約します。
    """
    if not settings.DATA_COLLECTION_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="データ収集機能が無効になっています。DATA_COLLECTION_ENABLEDをTrueに設定してください。"
        )
    
    if not settings.YOUTUBE_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="YOUTUBE_API_KEYが設定されていません。"
        )
    
    if not settings.GEMINI_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GEMINI_API_KEYが設定されていません。"
        )
    
    try:
        result = collect_youtube_data(
            prefecture=request.prefecture,
            keywords_config_path=request.keywords_config_path,
            max_results_per_keyword=request.max_results_per_keyword,
            stop_on_quota_exceeded=True
        )
        
        # メッセージの生成
        message_parts = []
        if result["total_videos"] > 0:
            message_parts.append(f"{result['total_videos']}件の動画データを収集しました。")
        
        if result["quota_exceeded"]:
            message_parts.append(
                f"⚠️ YouTube APIのクォータ制限に達しました。"
                f"処理済み: {result['successful_keywords']}/{result['total_keywords']}キーワード。"
                f"残り{result['quota_exceeded_keywords']}キーワードは処理できませんでした。"
            )
            message_parts.append(
                "💡 対処法: 1) max_results_per_keywordを減らす、2) キーワード数を減らす、"
                "3) クォータがリセットされるまで待つ（24時間ごと）、4) 複数のAPIキーを使用する"
            )
        
        if result["failed_keywords"] > 0:
            message_parts.append(f"⚠️ {result['failed_keywords']}キーワードでエラーが発生しました。")
        
        if result["total_videos"] > 0:
            message_parts.append(
                "📝 データベースに保存するには、収集したデータを"
                " POST /api/admin/data-collection/import-spots に送信してください。"
            )
        
        message = " ".join(message_parts) if message_parts else "データ収集が完了しました。"
        
        return YouTubeCollectionResponse(
            success=True,
            total_keywords=result["total_keywords"],
            total_videos=result["total_videos"],
            results=result["results"],
            message=message,
            quota_exceeded=result["quota_exceeded"],
            quota_exceeded_keywords=result["quota_exceeded_keywords"],
            successful_keywords=result["successful_keywords"],
            failed_keywords=result["failed_keywords"]
        )
    except Exception as e:
        log_error("YOUTUBE_COLLECTION_API_ERROR", str(e), {"prefecture": request.prefecture})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"YouTubeデータ収集エラー: {str(e)}"
        )


@router.post("/location", response_model=LocationUpdateResponse)
async def update_location_data(
    request: LocationUpdateRequest,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    既存のSpotに位置情報を付与（管理者専用）
    
    OpenCage Geocoding APIを使用して位置情報を取得し、Spotに付与します。
    """
    if not settings.DATA_COLLECTION_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="データ収集機能が無効になっています。DATA_COLLECTION_ENABLEDをTrueに設定してください。"
        )
    
    if not settings.OPENCAGE_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OPENCAGE_API_KEYが設定されていません。"
        )
    
    try:
        result = add_location_to_existing_spots(
            db=db,
            spot_ids=request.spot_ids,
            prefecture=request.prefecture
        )
        
        return LocationUpdateResponse(
            success=True,
            updated=result["updated"],
            errors=result["errors"],
            skipped=result["skipped"],
            total_processed=result["total_processed"],
            message=f"{result['updated']}件のSpotに位置情報を付与しました。"
        )
    except Exception as e:
        log_error("LOCATION_UPDATE_API_ERROR", str(e), {"prefecture": request.prefecture})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"位置情報付与エラー: {str(e)}"
        )


@router.post("/sns", response_model=SNSCollectionResponse)
async def collect_sns_data(
    request: SNSCollectionRequest,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    SNS/Web検索データ収集を実行（管理者専用）
    
    GoogleニュースRSSフィードから記事を取得し、Gemini APIで要約します。
    """
    if not settings.DATA_COLLECTION_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="データ収集機能が無効になっています。DATA_COLLECTION_ENABLEDをTrueに設定してください。"
        )
    
    if not settings.GEMINI_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GEMINI_API_KEYが設定されていません。"
        )
    
    try:
        result = collect_sns_data_with_summary(
            keyword=request.keyword,
            max_results=20  # デフォルト最大20件
        )
        
        return SNSCollectionResponse(
            success=True,
            count=len(result["results"]),
            results=result["results"],
            message=f"{len(result['results'])}件のトレンド情報を収集・要約しました。"
        )
    except Exception as e:
        log_error("SNS_COLLECTION_API_ERROR", str(e), {"keyword": request.keyword})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"SNS/Web検索データ収集エラー: {str(e)}"
        )


@router.post("/import-spots", response_model=SpotImportResponse)
async def import_spots(
    request: SpotImportRequest,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    YouTube収集データからSpotをインポート（管理者専用）
    
    YouTube収集データをパースしてSpotモデルに変換し、データベースに保存します。
    """
    if not settings.DATA_COLLECTION_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="データ収集機能が無効になっています。DATA_COLLECTION_ENABLEDをTrueに設定してください。"
        )
    
    try:
        result = import_spots_from_youtube_data(
            db=db,
            youtube_data=request.youtube_data,
            prefecture=request.prefecture
        )
        
        return SpotImportResponse(
            success=True,
            imported=result["imported"],
            errors=result["errors"],
            skipped=result["skipped"],
            total_processed=result["total_processed"],
            message=f"{result['imported']}件のSpotをインポートしました。"
        )
    except Exception as e:
        log_error("SPOT_IMPORT_API_ERROR", str(e), {"prefecture": request.prefecture})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Spotインポートエラー: {str(e)}"
        )


@router.post("/import-spots-from-sns", response_model=SpotImportResponse)
async def import_spots_from_sns(
    request: SNSImportRequest,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    SNS収集データからSpotをインポート（管理者専用）
    
    SNS収集データをパースしてSpotモデルに変換し、データベースに保存します。
    重複するSpotが見つかった場合、情報をマージ（統合）します。
    """
    if not settings.DATA_COLLECTION_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="データ収集機能が無効になっています。DATA_COLLECTION_ENABLEDをTrueに設定してください。"
        )
    
    try:
        result = import_spots_from_sns_data(
            db=db,
            sns_data=request.sns_data,
            prefecture=request.prefecture
        )
        
        return SpotImportResponse(
            success=True,
            imported=result["imported"],
            errors=result["errors"],
            skipped=result["skipped"],
            total_processed=result["total_processed"],
            message=f"{result['imported']}件のSpotをインポート/マージしました。"
        )
    except Exception as e:
        log_error("SNS_SPOT_IMPORT_API_ERROR", str(e), {"prefecture": request.prefecture})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"SNS Spotインポートエラー: {str(e)}"
        )


@router.post("/import-spots-from-csv", response_model=CSVImportResponse)
async def import_spots_from_csv(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    CSVファイルからSpotをインポート（管理者専用）
    
    CSVファイルをアップロードして、Spotモデルに変換し、データベースに保存します。
    重複するSpotが見つかった場合、スキップします（既存情報を保持）。
    """
    if not settings.DATA_COLLECTION_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="データ収集機能が無効になっています。DATA_COLLECTION_ENABLEDをTrueに設定してください。"
        )
    
    # ファイル拡張子の検証
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSVファイルのみアップロード可能です。"
        )
    
    # 一時ファイルに保存
    temp_file_path = None
    try:
        # 一時ファイルを作成
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.csv') as temp_file:
            temp_file_path = temp_file.name
            # アップロードされたファイルの内容を書き込む
            content = await file.read()
            temp_file.write(content)
        
        # CSVインポートを実行
        result = import_spots_from_csv_file(
            db=db,
            csv_file_path=temp_file_path
        )
        
        return CSVImportResponse(
            success=True,
            imported=result["imported"],
            errors=result["errors"],
            skipped=result["skipped"],
            total_processed=result["total_processed"],
            message=f"{result['imported']}件のSpotをインポートしました。"
        )
    except FileNotFoundError as e:
        log_error("CSV_FILE_NOT_FOUND", str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"CSVファイルが見つかりません: {str(e)}"
        )
    except Exception as e:
        log_error("CSV_SPOT_IMPORT_API_ERROR", str(e), {"filename": file.filename})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"CSV Spotインポートエラー: {str(e)}"
        )
    finally:
        # 一時ファイルを削除
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except Exception:
                pass  # 削除に失敗しても続行

