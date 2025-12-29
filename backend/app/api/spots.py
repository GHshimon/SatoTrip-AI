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
    
    # duration_minutesが未指定の場合はAIで調査
    if not spot_dict.get("duration_minutes"):
        spot_name = spot_dict.get("name", "")
        if spot_name:
            try:
                research_result = research_spot_info(spot_name)
                if research_result and not research_result.get("error"):
                    # 調査結果からduration_minutesを取得
                    if "duration_minutes" in research_result:
                        spot_dict["duration_minutes"] = research_result["duration_minutes"]
                    # その他の情報も補完（未指定の場合のみ）
                    if not spot_dict.get("category") and "category" in research_result:
                        spot_dict["category"] = research_result["category"]
                    if not spot_dict.get("description") and "description" in research_result:
                        spot_dict["description"] = research_result["description"]
                    if not spot_dict.get("area") and "area" in research_result:
                        spot_dict["area"] = research_result["area"]
            except Exception as e:
                # AI調査失敗時はデフォルト値を使用（エラーはログに記録するが処理は続行）
                from app.utils.error_handler import log_error
                log_error("SPOT_DURATION_RESEARCH_ERROR", f"滞在時間調査エラー: {str(e)}", {"spot_name": spot_name})
                spot_dict["duration_minutes"] = spot_dict.get("duration_minutes", 60)  # デフォルト値
    
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
    from app.services.spot_service import get_spot
    
    spot_dict = spot_data.model_dump(exclude_unset=True)
    
    # 既存のスポット情報を取得
    existing_spot = get_spot(db, spot_id)
    if not existing_spot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="スポットが見つかりません"
        )
    
    # duration_minutesが未設定（既存も新規も）の場合はAIで調査
    if not spot_dict.get("duration_minutes") and not existing_spot.duration_minutes:
        spot_name = spot_dict.get("name") or existing_spot.name
        if spot_name:
            try:
                research_result = research_spot_info(spot_name)
                if research_result and not research_result.get("error"):
                    # 調査結果からduration_minutesを取得
                    if "duration_minutes" in research_result:
                        spot_dict["duration_minutes"] = research_result["duration_minutes"]
            except Exception as e:
                # AI調査失敗時はデフォルト値を使用（エラーはログに記録するが処理は続行）
                from app.utils.error_handler import log_error
                log_error("SPOT_DURATION_RESEARCH_ERROR", f"滞在時間調査エラー: {str(e)}", {"spot_id": spot_id, "spot_name": spot_name})
                spot_dict["duration_minutes"] = spot_dict.get("duration_minutes", 60)  # デフォルト値
    
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
                "category": request.category,
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
            add_location=request.add_location,
            category=request.category
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

