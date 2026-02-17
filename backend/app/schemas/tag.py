"""
タグ関連のPydanticスキーマ
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from enum import Enum


class TagCategory(str, Enum):
    """タグカテゴリ"""
    FOOD = "food"
    NATURE = "nature"
    CULTURE = "culture"
    ACTIVITY = "activity"
    ART = "art"
    RELAX = "relax"
    SHOPPING = "shopping"
    SNS = "sns"
    HIDDEN = "hidden"
    OTHER = "other"


class TagPriority(int, Enum):
    """タグ優先度"""
    HIGH = 1  # 高優先度
    MEDIUM = 2  # 中優先度
    LOW = 3  # 低優先度


class TagSource(str, Enum):
    """タグの作成元"""
    AI = "ai"
    MANUAL = "manual"
    IMPORT = "import"
    THEME = "theme"
    MIGRATION = "migration"


class Tag(BaseModel):
    """構造化タグスキーマ"""
    value: str = Field(..., description="タグの値（文字列）")
    category: Optional[TagCategory] = Field(None, description="カテゴリ")
    priority: TagPriority = Field(TagPriority.MEDIUM, description="優先度（1=高、2=中、3=低）")
    source: TagSource = Field(TagSource.MANUAL, description="作成元")
    normalized: str = Field(..., description="正規化された値（同義語統合用）")
    
    class Config:
        use_enum_values = True


class TagList(BaseModel):
    """タグリスト（後方互換性のため文字列配列も許可）"""
    tags: List[Tag]
    
    @classmethod
    def from_string_list(cls, tags: List[str], source: TagSource = TagSource.MANUAL) -> "TagList":
        """文字列配列からTagListを作成（後方互換性）"""
        from app.utils.tag_normalizer import normalize_tags
        
        tag_objects = normalize_tags(tags, source=source)
        return cls(tags=tag_objects)
    
    def to_string_list(self) -> List[str]:
        """文字列配列に変換（後方互換性）"""
        return [tag.value for tag in self.tags]


class TagStats(BaseModel):
    """タグ統計情報"""
    value: str
    count: int
    category: Optional[str] = None
    normalized: str


class TagResponse(BaseModel):
    """タグレスポンス（API用）"""
    tags: List[TagStats]
    total: int
    categories: dict


class TagNormalizeRequest(BaseModel):
    """タグ正規化リクエスト"""
    tags: List[str]


class TagNormalizeResponse(BaseModel):
    """タグ正規化レスポンス"""
    normalized_tags: List[Tag]
    original_tags: List[str]

