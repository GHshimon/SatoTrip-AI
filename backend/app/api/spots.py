"""
スポット管理APIエンドポイント
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from app.utils.database import get_db
from app.dependencies import get_current_user, get_current_admin_user
from app.models.user import User
from app.schemas.spot import SpotCreate, SpotUpdate, SpotResponse, BulkAddRequest, BulkAddResponse
from app.services.spot_service import (
    create_spot,
    get_spots,
    get_spot,
    get_spots_by_area,
    update_spot,
    delete_spot
)
from app.services.gemini_service import research_spot_info
from app.services.spot_bulk_service import bulk_add_spots_by_prefecture
from app.services.bulk_job_service import create_job, get_job, run_bulk_add_job
from app.config import settings
from fastapi import Body

router = APIRouter(prefix="/api/spots", tags=["spots"])


@router.get("", response_model=List[SpotResponse])
async def list_spots(
    area: Optional[str] = Query(None, description="エリアでフィルタ"),
    category: Optional[str] = Query(None, description="カテゴリでフィルタ"),
    keyword: Optional[str] = Query(None, description="キーワード検索"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """スポット一覧取得（フィルタリング対応）"""
    spots = get_spots(db, area, category, keyword, skip, limit)
    return spots


@router.get("/{spot_id}", response_model=SpotResponse)
async def get_spot_detail(
    spot_id: str,
    db: Session = Depends(get_db)
):
    """スポット詳細取得"""
    spot = get_spot(db, spot_id)
    if not spot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="スポットが見つかりません"
        )
    return spot


@router.get("/area/{area}", response_model=List[SpotResponse])
async def get_spots_by_area_endpoint(
    area: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """エリア別スポット取得"""
    spots = get_spots_by_area(db, area, skip, limit)
    return spots


@router.post("", response_model=SpotResponse, status_code=status.HTTP_201_CREATED)
async def create_spot_endpoint(
    spot_data: SpotCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """スポット作成（管理者のみ）"""
    spot_dict = spot_data.model_dump()
    spot = create_spot(db, spot_dict)
    return spot


@router.put("/{spot_id}", response_model=SpotResponse)
async def update_spot_endpoint(
    spot_id: str,
    spot_data: SpotUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """スポット更新（管理者のみ）"""
    spot_dict = spot_data.model_dump(exclude_unset=True)
    spot = update_spot(db, spot_id, spot_dict)
    return spot


@router.delete("/{spot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_spot_endpoint(
    spot_id: str,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """スポット削除（管理者のみ）"""
    delete_spot(db, spot_id)
    return None


@router.post("/research", status_code=status.HTTP_200_OK)
async def research_spot_endpoint(
    spot_name: str = Body(..., embed=True),
    current_user: User = Depends(get_current_admin_user)
):
    """スポット情報のAIリサーチ（管理者のみ）"""
    result = research_spot_info(spot_name)
    
    # エラー情報が含まれている場合
    if result and result.get("error"):
        error_type = result.get("error_type", "UNKNOWN_ERROR")
        error_message = result.get("message", "AIリサーチに失敗しました")
        
        # エラータイプに応じて適切なHTTPステータスコードを設定
        if error_type == "QUOTA_ERROR":
            status_code = status.HTTP_429_TOO_MANY_REQUESTS
        elif error_type == "CONFIG_ERROR":
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        else:
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        
        raise HTTPException(
            status_code=status_code,
            detail=error_message
        )
    
    # 結果がNoneの場合
    if not result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AIリサーチに失敗しました"
        )
    
    return result


@router.post("/bulk-add-by-prefecture", response_model=BulkAddResponse, status_code=status.HTTP_200_OK)
async def bulk_add_spots_by_prefecture_endpoint(
    request: BulkAddRequest,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = None
):
    """都道府県名で複数キーワード検索してまとめてスポットを追加（管理者のみ）"""
    try:
        run_async = bool(request.run_async) if request.run_async is not None else settings.BULK_ADD_ENABLE_BACKGROUND_JOBS
        if settings.BULK_ADD_ENABLE_BACKGROUND_JOBS and run_async:
            job_id = create_job({
                "prefecture": request.prefecture,
                "max_results_per_keyword": request.max_results_per_keyword,
                "max_keywords": request.max_keywords,
                "max_total_videos": request.max_total_videos,
                "add_location": request.add_location,
            })
            if background_tasks is not None:
                background_tasks.add_task(run_bulk_add_job, job_id)
            return BulkAddResponse(
                success=True,
                imported=0,
                errors=0,
                skipped=0,
                total_keywords=0,
                quota_exceeded=False,
                processed_keywords=0,
                failed_keywords=0,
                total_videos=0,
                job_id=job_id,
                job_status="queued",
                error=None,
            )

        result = bulk_add_spots_by_prefecture(
            prefecture=request.prefecture,
            db=db,
            max_results_per_keyword=request.max_results_per_keyword,
            max_keywords=request.max_keywords,
            max_total_videos=request.max_total_videos,
            add_location=request.add_location
        )
        # #region agent log
        import json
        import time
        with open(r'c:\projects\SatoTrip\.cursor\debug.log', 'a', encoding='utf-8') as f:
            f.write(json.dumps({"location":"spots.py:153","message":"bulk_add_spots_by_prefecture result","data":{"result":result,"result_keys":list(result.keys()),"result_types":{k:type(v).__name__ for k,v in result.items()}},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"A"},ensure_ascii=False)+'\n')
        # #endregion
        try:
            response = BulkAddResponse(**result)
            # #region agent log
            with open(r'c:\projects\SatoTrip\.cursor\debug.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps({"location":"spots.py:160","message":"BulkAddResponse created successfully","data":{"response_dict":response.model_dump()},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"A"},ensure_ascii=False)+'\n')
            # #endregion
            return response
        except Exception as validation_error:
            # #region agent log
            with open(r'c:\projects\SatoTrip\.cursor\debug.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps({"location":"spots.py:167","message":"BulkAddResponse validation error","data":{"error":str(validation_error),"error_type":type(validation_error).__name__,"result":result},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"A"},ensure_ascii=False)+'\n')
            # #endregion
            raise
    except Exception as e:
        from app.utils.error_handler import log_error
        log_error("BULK_ADD_API_ERROR", f"一括追加APIエラー: {str(e)}", {"prefecture": request.prefecture})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"一括追加エラー: {str(e)}"
        )


@router.get("/bulk-add-jobs/{job_id}", response_model=BulkAddResponse, status_code=status.HTTP_200_OK)
async def get_bulk_add_job_status(
    job_id: str,
    current_user: User = Depends(get_current_admin_user),
):
    """一括追加ジョブの進捗/結果を取得（管理者のみ）"""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ジョブが見つかりません")

    job_status = job.get("job_status")
    result = job.get("result")
    error = job.get("error")

    if isinstance(result, dict) and result:
        # 完了結果を返す
        return BulkAddResponse(**{**result, "job_id": job_id, "job_status": job_status})

    if job_status == "failed":
        return BulkAddResponse(
            success=False,
            imported=0,
            errors=0,
            skipped=0,
            total_keywords=0,
            quota_exceeded=False,
            processed_keywords=0,
            failed_keywords=0,
            total_videos=0,
            job_id=job_id,
            job_status=job_status,
            error=error or "ジョブが失敗しました",
        )

    return BulkAddResponse(
        success=True,
        imported=0,
        errors=0,
        skipped=0,
        total_keywords=0,
        quota_exceeded=False,
        processed_keywords=0,
        failed_keywords=0,
        total_videos=0,
        job_id=job_id,
        job_status=job_status,
        error=None,
    )

