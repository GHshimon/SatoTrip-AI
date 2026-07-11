"""
FastAPIメインアプリケーション
"""
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.utils.database import init_db
from app.utils.storage import ensure_upload_dir
from app.api import auth, plans, spots, users, data_collection, admin, hotels, folders, ai_agent, api_keys, favorites, payments
import logging

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# FastAPIアプリケーション作成
# 本番では API ドキュメント（/docs, /redoc, /openapi.json）を無効化する
_is_production = getattr(settings, "ENVIRONMENT", "development") == "production"
app = FastAPI(
    title="SatoTrip API",
    description="SatoTrip旅行プラン生成API",
    version="1.0.0",
    docs_url=None if _is_production else "/docs",
    redoc_url=None if _is_production else "/redoc",
    openapi_url=None if _is_production else "/openapi.json",
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# データベース初期化
@app.on_event("startup")
async def startup_event():
    """アプリケーション起動時の処理"""
    logger.info("データベースを初期化しています...")
    init_db()
    logger.info("データベース初期化完了")


# ルーター登録
app.include_router(auth.router)
app.include_router(plans.router)
app.include_router(spots.router)
app.include_router(users.router)
app.include_router(data_collection.router)
app.include_router(admin.router)
app.include_router(hotels.router)
app.include_router(folders.router)
app.include_router(ai_agent.router)
app.include_router(api_keys.router)
app.include_router(favorites.router)
app.include_router(payments.router)

# アップロードされたファイル（アバター等）を /uploads で配信
app.mount("/uploads", StaticFiles(directory=ensure_upload_dir()), name="uploads")


# エラーハンドリング
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """グローバル例外ハンドラー"""
    logger.error(f"未処理のエラー: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "内部サーバーエラーが発生しました"}
    )


# ヘルスチェック
@app.get("/health")
async def health_check():
    """ヘルスチェックエンドポイント"""
    return {"status": "ok"}


# ルート
@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {
        "message": "SatoTrip API",
        "version": "1.0.0",
        "docs": "/docs"
    }

