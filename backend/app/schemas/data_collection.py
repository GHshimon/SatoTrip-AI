"""
データ収集関連のPydanticスキーマ
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class KeywordConfig(BaseModel):
    """キーワード設定（都道府県ごと）"""
    カテゴリ: List[str] = Field(default_factory=list, description="カテゴリリスト")
    エリア補助: List[str] = Field(default_factory=list, description="エリア補助リスト")


class DataCollectionRequest(BaseModel):
    """データ収集リクエスト"""
    prefecture: str = Field(..., description="都道府県名", example="鹿児島県")
    keywords_config_path: Optional[str] = Field(
        default="data/search_keywords.json",
        description="キーワード設定JSONファイルのパス"
    )
    max_results_per_keyword: Optional[int] = Field(
        default=5,
        ge=1,
        le=50,
        description="キーワードあたりの最大取得件数"
    )


class YouTubeCollectionResponse(BaseModel):
    """YouTubeデータ収集レスポンス"""
    success: bool
    total_keywords: int
    total_videos: int
    results: List[Dict[str, Any]] = Field(default_factory=list)
    message: Optional[str] = None
    quota_exceeded: Optional[bool] = Field(default=False, description="クォータ制限に達したかどうか")
    quota_exceeded_keywords: Optional[int] = Field(default=0, description="クォータ制限により処理できなかったキーワード数")
    successful_keywords: Optional[int] = Field(default=0, description="正常に処理できたキーワード数")
    failed_keywords: Optional[int] = Field(default=0, description="その他のエラーで処理できなかったキーワード数")


class LocationUpdateRequest(BaseModel):
    """位置情報付与リクエスト"""
    prefecture: str = Field(..., description="都道府県名", example="鹿児島県")
    spot_ids: Optional[List[str]] = Field(
        default=None,
        description="処理対象のSpot IDリスト（Noneの場合は全件）"
    )


class LocationUpdateResponse(BaseModel):
    """位置情報付与レスポンス"""
    success: bool
    updated: int
    errors: int
    skipped: int
    total_processed: int
    message: Optional[str] = None


class SNSCollectionRequest(BaseModel):
    """SNS/Web検索データ収集リクエスト"""
    keyword: str = Field(..., description="検索キーワード", example="鹿児島 観光")


class SNSCollectionResponse(BaseModel):
    """SNS/Web検索データ収集レスポンス"""
    success: bool
    count: int
    results: List[Dict[str, Any]] = Field(default_factory=list)
    message: Optional[str] = None


class SpotImportRequest(BaseModel):
    """スポットインポートリクエスト（YouTubeデータ用）"""
    youtube_data: Dict[str, Any] = Field(..., description="YouTube収集データ")
    prefecture: str = Field(..., description="都道府県名", example="鹿児島県")


class SNSImportRequest(BaseModel):
    """SNSデータインポートリクエスト"""
    sns_data: Dict[str, Any] = Field(..., description="SNS収集データ（collect_sns_data_with_summaryの戻り値）")
    prefecture: str = Field(..., description="都道府県名", example="鹿児島県")


class SpotImportResponse(BaseModel):
    """スポットインポートレスポンス"""
    success: bool
    imported: int  # 新規作成 + マージ件数
    errors: int
    skipped: int
    total_processed: int
    message: Optional[str] = None


class CSVImportResponse(BaseModel):
    """CSVスポットインポートレスポンス"""
    success: bool
    imported: int  # 新規インポート件数
    errors: int
    skipped: int  # 重複によりスキップされた件数
    total_processed: int
    message: Optional[str] = None

