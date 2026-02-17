"""
プラン関連のPydanticスキーマ
"""
from pydantic import BaseModel, Field, field_validator, ValidationInfo
from typing import List, Optional, Dict, Any, Union
from datetime import datetime


class PlanSpotBase(BaseModel):
    """プランスポットベーススキーマ"""
    spot_id: str
    day: int
    start_time: Optional[str] = None
    note: Optional[str] = None
    transport_mode: Optional[str] = None
    transport_duration: Optional[int] = None
    is_must_visit: Optional[bool] = False


class PlanBase(BaseModel):
    """プランベーススキーマ"""
    title: str
    area: str
    days: int
    people: Optional[int] = None
    budget: Optional[float] = None
    thumbnail: Optional[str] = None
    spots: List[Dict[str, Any]]  # PlanSpot objects as JSON
    grounding_urls: Optional[List[str]] = None
    is_favorite: bool = False
    check_in_date: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    check_out_date: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")


class PlanCreate(PlanBase):
    """プラン作成スキーマ"""
    pass


class PlanSpotUpdate(BaseModel):
    """プランスポット更新スキーマ"""
    id: str  # PlanSpotのID
    startTime: Optional[str] = Field(None, pattern=r"^([0-1][0-9]|2[0-3]):[0-5][0-9]$")
    durationMinutes: Optional[int] = Field(None, ge=5, le=480)  # 最小5分、最大480分（8時間）
    transportDuration: Optional[int] = Field(None, ge=0, le=300)  # 最小0分、最大300分（5時間）
    transportMode: Optional[str] = None
    order: Optional[int] = Field(None, ge=0)  # 順序情報（オプション）


class PlanUpdate(BaseModel):
    """プラン更新スキーマ"""
    title: Optional[str] = None
    area: Optional[str] = None
    days: Optional[int] = None
    people: Optional[int] = None
    budget: Optional[float] = None
    thumbnail: Optional[str] = None
    spots: Optional[List[Dict[str, Any]]] = None  # PlanSpotの更新情報または完全なPlanSpotオブジェクト
    grounding_urls: Optional[List[str]] = None
    is_favorite: Optional[bool] = None
    folder_id: Optional[str] = None
    check_in_date: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    check_out_date: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")


class PlanResponse(PlanBase):
    """プランレスポンススキーマ"""
    id: str
    user_id: str
    folder_id: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    excluded_spots: Optional[List[Dict[str, Any]]] = None  # 除外されたスポット情報（プラン生成時のみ）
    
    class Config:
        from_attributes = True


class PlanGenerateRequest(BaseModel):
    """プラン生成リクエスト（改善版）"""
    destination: str
    days: int
    budget: str
    themes: List[str]
    pending_spots: List[Dict[str, Any]]  # Spot objects
    
    # 新規追加パラメータ（デフォルト値付き）
    preferences: Optional[str] = None
    start_time: Optional[str] = Field(default="09:00", pattern=r"^([0-1][0-9]|2[0-3]):[0-5][0-9]$")
    end_time: Optional[str] = Field(default="18:00", pattern=r"^([0-1][0-9]|2[0-3]):[0-5][0-9]$")
    transportation: Optional[str] = Field(default="train", pattern="^(車|電車|バス|徒歩|その他)$")
    
    # 宿泊先情報（オプション）
    check_in_date: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    check_out_date: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    num_guests: Optional[int] = Field(default=None, ge=1, le=20)
    
    @field_validator('days')
    @classmethod
    def validate_days(cls, v):
        if v < 1 or v > 7:
            raise ValueError('日数は1日から7日の間で指定してください')
        return v
    
    @field_validator('end_time')
    @classmethod
    def validate_time_range(cls, v: Optional[str], info: ValidationInfo) -> Optional[str]:
        if info.data and 'start_time' in info.data and v and info.data.get('start_time'):
            from datetime import datetime as dt
            try:
                start = dt.strptime(info.data['start_time'], "%H:%M")
                end = dt.strptime(v, "%H:%M")
                if end <= start:
                    raise ValueError('終了時間は開始時間より後である必要があります')
            except ValueError as e:
                if '終了時間' in str(e):
                    raise
                # 時間形式のエラーは無視（patternで検証済み）
                pass
        return v
    
    @field_validator('check_out_date')
    @classmethod
    def validate_date_range(cls, v: Optional[str], info: ValidationInfo) -> Optional[str]:
        """チェックアウト日がチェックイン日より後であることを確認"""
        if v and info.data and 'check_in_date' in info.data and info.data.get('check_in_date'):
            from datetime import datetime as dt, date
            try:
                check_in = datetime.strptime(info.data['check_in_date'], "%Y-%m-%d").date()
                check_out = datetime.strptime(v, "%Y-%m-%d").date()
                today = date.today()
                
                if check_in < today:
                    raise ValueError('チェックイン日は今日以降の日付を指定してください')
                if check_out <= check_in:
                    raise ValueError('チェックアウト日はチェックイン日より後の日付を指定してください')
                if (check_out - check_in).days > 365:
                    raise ValueError('滞在日数は365日以内にしてください')
            except ValueError as e:
                if any(keyword in str(e) for keyword in ['チェックイン', 'チェックアウト', '滞在日数']):
                    raise
                # 日付形式のエラーは無視（patternで検証済み）
                pass
        return v

