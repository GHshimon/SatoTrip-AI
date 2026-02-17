"""
スポット関連のPydanticスキーマ
"""
from pydantic import BaseModel, field_validator
from typing import Optional, List, Dict, Union, Any
from datetime import datetime
from app.schemas.tag import Tag, TagList
from app.utils.tag_normalizer import normalize_tags, extract_tag_values, tags_to_dict_list, dict_list_to_tags


class SpotBase(BaseModel):
    """スポットベーススキーマ"""
    name: str
    description: Optional[str] = None
    area: Optional[str] = None
    category: Optional[str] = None
    duration_minutes: Optional[int] = None
    rating: Optional[float] = None
    image: Optional[str] = None
    price: Optional[float] = None
    tags: Optional[Union[List[str], List[Dict[str, Any]], List[Tag]]] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    
    @field_validator('tags', mode='before')
    @classmethod
    def validate_tags(cls, v: Any) -> Optional[List[Dict[str, Any]]]:
        """タグを構造化タグ（辞書リスト）に変換"""
        if v is None:
            return None
        
        if isinstance(v, list) and len(v) == 0:
            return None
        
        # 文字列リストまたは構造化タグリストを正規化
        normalized = normalize_tags(v)
        return tags_to_dict_list(normalized)


class SpotCreate(SpotBase):
    """スポット作成スキーマ"""
    pass


class SpotUpdate(BaseModel):
    """スポット更新スキーマ"""
    name: Optional[str] = None
    description: Optional[str] = None
    area: Optional[str] = None
    category: Optional[str] = None
    duration_minutes: Optional[int] = None
    rating: Optional[float] = None
    image: Optional[str] = None
    price: Optional[float] = None
    tags: Optional[Union[List[str], List[Dict[str, Any]], List[Tag]]] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    
    @field_validator('tags', mode='before')
    @classmethod
    def validate_tags(cls, v: Any) -> Optional[List[Dict[str, Any]]]:
        """タグを構造化タグ（辞書リスト）に変換"""
        if v is None:
            return None
        
        if isinstance(v, list) and len(v) == 0:
            return None
        
        # 文字列リストまたは構造化タグリストを正規化
        normalized = normalize_tags(v)
        return tags_to_dict_list(normalized)


class SpotResponse(SpotBase):
    """スポットレスポンススキーマ"""
    id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    @field_validator('tags', mode='after')
    @classmethod
    def convert_tags_for_response(cls, v: Any) -> Optional[List[Dict[str, Any]]]:
        """レスポンス用にタグを変換（データベースから読み込んだ形式をそのまま返す）"""
        if v is None:
            return None
        
        # データベースから読み込まれた形式（辞書リストまたは文字列リスト）をそのまま返す
        if isinstance(v, list):
            # 辞書リストの場合はそのまま
            if v and isinstance(v[0], dict):
                return v
            # 文字列リストの場合は構造化タグに変換
            elif v and isinstance(v[0], str):
                normalized = normalize_tags(v)
                return tags_to_dict_list(normalized)
        
        return v
    
    class Config:
        from_attributes = True


class BulkAddRequest(BaseModel):
    """都道府県一括追加リクエストスキーマ"""
    prefecture: str
    max_results_per_keyword: Optional[int] = 5
    max_keywords: Optional[int] = None
    max_total_videos: Optional[int] = None
    add_location: Optional[bool] = True
    run_async: Optional[bool] = None
    category: Optional[str] = None


class BulkAddResponse(BaseModel):
    """都道府県一括追加レスポンススキーマ"""
    success: bool
    imported: int
    created: Optional[int] = None  # 新規作成数
    merged: Optional[int] = None   # マージ数
    errors: int
    skipped: int
    total_keywords: int
    quota_exceeded: bool
    processed_keywords: int
    failed_keywords: int
    total_videos: int
    location_updated: Optional[int] = None
    location_errors: Optional[int] = None
    error: Optional[str] = None
    job_id: Optional[str] = None
    job_status: Optional[str] = None