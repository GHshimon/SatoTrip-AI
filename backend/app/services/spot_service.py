"""
スポットサービス
"""
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.spot import Spot
from typing import List, Optional
from fastapi import HTTPException, status
from app.utils.tag_normalizer import (
    normalize_tags,
    extract_tag_values,
    tags_to_dict_list,
    dict_list_to_tags,
    create_structured_tag,
    TagSource
)
from app.schemas.tag import TagCategory
import uuid


def create_spot(db: Session, spot_data: dict) -> Spot:
    """スポットを作成"""
    spot = Spot(
        id=str(uuid.uuid4()),
        name=spot_data["name"],
        description=spot_data.get("description"),
        area=spot_data.get("area"),
        category=spot_data.get("category"),
        duration_minutes=spot_data.get("duration_minutes"),
        rating=spot_data.get("rating"),
        image=spot_data.get("image"),
        price=spot_data.get("price"),
        tags=spot_data.get("tags"),
        latitude=spot_data.get("latitude"),
        longitude=spot_data.get("longitude")
    )
    db.add(spot)
    db.commit()
    db.refresh(spot)
    return spot


def get_spots(
    db: Session,
    area: Optional[str] = None,
    category: Optional[str] = None,
    keyword: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> List[Spot]:
    """スポット一覧を取得（フィルタリング対応）"""
    query = db.query(Spot)
    
    if area:
        query = query.filter(Spot.area.contains(area))
    if category:
        query = query.filter(Spot.category == category)
    if keyword:
        query = query.filter(
            or_(
                Spot.name.contains(keyword),
                Spot.description.contains(keyword)
            )
        )
    
    return query.offset(skip).limit(limit).all()


def get_spot(db: Session, spot_id: str) -> Optional[Spot]:
    """スポットを取得"""
    return db.query(Spot).filter(Spot.id == spot_id).first()


def get_spots_by_area(db: Session, area: str, skip: int = 0, limit: int = 100) -> List[Spot]:
    """エリア別スポット取得"""
    return db.query(Spot).filter(
        Spot.area.contains(area)
    ).offset(skip).limit(limit).all()


def update_spot(db: Session, spot_id: str, spot_data: dict) -> Spot:
    """スポットを更新"""
    spot = get_spot(db, spot_id)
    if not spot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="スポットが見つかりません"
        )
    
    # 更新
    for key, value in spot_data.items():
        if value is not None:
            setattr(spot, key, value)
    
    db.commit()
    db.refresh(spot)
    return spot


def delete_spot(db: Session, spot_id: str) -> bool:
    """スポットを削除"""
    spot = get_spot(db, spot_id)
    if not spot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="スポットが見つかりません"
        )
    
    db.delete(spot)
    db.commit()
    return True


def map_themes_to_tags(themes: List[str]) -> List[str]:
    """テーマをタグにマッピング（後方互換性のため文字列リストを返す）"""
    # #region agent log
    import json
    import time
    with open(r'c:\projects\SatoTrip-AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
        f.write(json.dumps({"location":"spot_service.py:103","message":"map_themes_to_tags called","data":{"themes":themes},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"B"},ensure_ascii=False)+'\n')
    # #endregion
    theme_tag_map = {
        "食べ歩き": ["グルメ", "美食", "レストラン", "カフェ"],
        "歴史・文化": ["歴史", "文化", "史跡", "伝統"],
        "自然・絶景": ["自然", "絶景", "景色", "山", "海"],
        "SNS映え": ["SNS", "インスタ", "写真", "映え"],
        "アート": ["アート", "美術", "芸術", "ギャラリー"],
        "温泉・癒し": ["温泉", "癒し", "リラックス", "スパ"],
        "穴場スポット": ["穴場", "隠れ", "ローカル"],
        "体験・アクティビティ": ["体験", "アクティビティ", "アクション"]
    }
    tags = []
    for theme in themes:
        tags.extend(theme_tag_map.get(theme, [theme]))
    result = list(set(tags))  # 重複を除去
    # #region agent log
    with open(r'c:\projects\SatoTrip-AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
        f.write(json.dumps({"location":"spot_service.py:118","message":"map_themes_to_tags result","data":{"tags":result},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"B"},ensure_ascii=False)+'\n')
    # #endregion
    return result


def map_themes_to_structured_tags(themes: List[str]) -> List[dict]:
    """テーマを構造化タグにマッピング"""
    tag_strings = map_themes_to_tags(themes)
    structured_tags = normalize_tags(tag_strings, source=TagSource.THEME)
    return tags_to_dict_list(structured_tags)


def get_spots_for_plan(
    db: Session,
    area: str,
    themes: List[str],
    limit: int = 100
) -> List[Spot]:
    """プラン生成用にスポットを取得（エリアとテーマでフィルタリング）"""
    # #region agent log
    import json
    import time
    with open(r'c:\projects\SatoTrip-AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
        f.write(json.dumps({"location":"spot_service.py:121","message":"get_spots_for_plan called","data":{"area":area,"themes":themes,"limit":limit},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"A"},ensure_ascii=False)+'\n')
    # #endregion
    # テーマをタグにマッピング
    tags = map_themes_to_tags(themes)
    
    # エリアでフィルタリング
    query = db.query(Spot).filter(Spot.area.contains(area))
    # #region agent log
    area_count = query.count()
    with open(r'c:\projects\SatoTrip-AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
        f.write(json.dumps({"location":"spot_service.py:133","message":"After area filter","data":{"areaCount":area_count},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"A"},ensure_ascii=False)+'\n')
    # #endregion
    
    # タグでフィルタリング（JSON配列内の検索）
    if tags:
        # データベースのタグ形式を確認するため、サンプルスポットを取得
        sample_spots = query.limit(3).all()
        # #region agent log
        sample_tags = [s.tags for s in sample_spots if s.tags]
        with open(r'c:\projects\SatoTrip-AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
            f.write(json.dumps({"location":"spot_service.py:135","message":"Sample tags from DB","data":{"sampleTags":sample_tags,"sampleTagsType":[type(s.tags).__name__ for s in sample_spots if s.tags]},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"A"},ensure_ascii=False)+'\n')
        # #endregion
        
        # JSON配列内の要素を検索（PostgreSQL/SQLite対応）
        # SQLAlchemyのJSON型では、配列内の要素検索は複雑なため、
        # まずはタグフィルタリングを緩和して、エリアのみでフィルタリング
        # または、Python側でフィルタリングする方法に変更
        tag_filters = []
        for tag in tags:
            # JSON配列内の文字列要素を検索
            # PostgreSQLの場合: tags @> '["tag"]'::jsonb
            # SQLiteの場合: JSON_EXTRACT(tags, '$') LIKE '%tag%'
            # より確実な方法として、Python側でフィルタリング
            pass
        
        # タグフィルタリングを一旦スキップ（後でPython側でフィルタリング）
        # query = query.filter(or_(*tag_filters))
        # #region agent log
        tag_count = query.count()
        with open(r'c:\projects\SatoTrip-AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
            f.write(json.dumps({"location":"spot_service.py:150","message":"After tag filter (skipped)","data":{"tagCount":tag_count,"tags":tags},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"A"},ensure_ascii=False)+'\n')
        # #endregion
    
    result = query.limit(limit * 2).all()  # タグフィルタリング前なので多めに取得
    
    # Python側でタグフィルタリング（構造化タグ対応）
    if tags and result:
        filtered_result = []
        for spot in result:
            spot_tags = spot.tags or []
            if not spot_tags:
                continue
            
            # タグを構造化タグに変換
            if isinstance(spot_tags, list) and spot_tags:
                if isinstance(spot_tags[0], dict):
                    # 既に構造化タグ形式（辞書リスト）
                    spot_tag_objects = dict_list_to_tags(spot_tags)
                elif isinstance(spot_tags[0], str):
                    # 文字列リスト形式
                    spot_tag_objects = normalize_tags(spot_tags, source=TagSource.THEME)
                else:
                    continue
            else:
                continue
            
            spot_tag_values = [tag.value for tag in spot_tag_objects]
            spot_tag_normalized = [tag.normalized for tag in spot_tag_objects]
            
            # 検索タグとマッチするかチェック（値または正規化された値でマッチ）
            matched = False
            for search_tag in tags:
                # 検索タグも正規化
                from app.utils.tag_normalizer import normalize_tag_value
                normalized_search_tag = normalize_tag_value(search_tag)
                
                if (search_tag in spot_tag_values or 
                    normalized_search_tag in spot_tag_normalized or
                    any(search_tag in value or value in search_tag for value in spot_tag_values)):
                    matched = True
                    break
            
            if matched:
                filtered_result.append(spot)
        
        result = filtered_result[:limit]  # 制限を適用
        # #region agent log
        with open(r'c:\projects\SatoTrip-AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
            f.write(json.dumps({"location":"spot_service.py:165","message":"After Python tag filter","data":{"filteredCount":len(result)},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"A"},ensure_ascii=False)+'\n')
        # #endregion
    else:
        result = result[:limit]  # 制限を適用
    
    # #region agent log
    with open(r'c:\projects\SatoTrip-AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
        f.write(json.dumps({"location":"spot_service.py:171","message":"get_spots_for_plan result","data":{"spotsCount":len(result),"spotNames":[s.name for s in result[:5]]},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"A"},ensure_ascii=False)+'\n')
    # #endregion
    return result

