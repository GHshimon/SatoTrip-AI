"""
タグ正規化ユーティリティ
"""
import json
import os
from pathlib import Path
from typing import List, Dict, Optional, Any
from app.schemas.tag import Tag, TagCategory, TagPriority, TagSource


# カテゴリ定義ファイルのパス
SCRIPT_DIR = Path(__file__).parent.parent.parent
CATEGORIES_FILE = SCRIPT_DIR / "data" / "tag_categories.json"

# カテゴリ定義をキャッシュ
_categories_cache: Optional[Dict[str, Any]] = None
_synonyms_cache: Optional[Dict[str, str]] = None


def load_tag_categories() -> Dict[str, Any]:
    """カテゴリ定義ファイルを読み込む"""
    global _categories_cache
    
    if _categories_cache is not None:
        return _categories_cache
    
    if not CATEGORIES_FILE.exists():
        # デフォルトのカテゴリ定義を返す
        return {
            "categories": {},
            "synonyms": {}
        }
    
    try:
        with open(CATEGORIES_FILE, "r", encoding="utf-8") as f:
            _categories_cache = json.load(f)
        return _categories_cache
    except Exception as e:
        print(f"警告: カテゴリ定義ファイルの読み込みに失敗しました: {e}")
        return {
            "categories": {},
            "synonyms": {}
        }


def get_synonyms_dict() -> Dict[str, str]:
    """同義語辞書を取得"""
    global _synonyms_cache
    
    if _synonyms_cache is not None:
        return _synonyms_cache
    
    categories_data = load_tag_categories()
    synonyms_data = categories_data.get("synonyms", {})
    
    # 双方向のマッピングを作成
    _synonyms_cache = {}
    for key, values in synonyms_data.items():
        _synonyms_cache[key] = key  # 自分自身
        for value in values:
            _synonyms_cache[value] = key  # 同義語から正規形へ
    
    return _synonyms_cache


def normalize_tag_value(tag_value: str) -> str:
    """
    タグの値を正規化（同義語を統合）
    
    Args:
        tag_value: タグの値
    
    Returns:
        正規化されたタグの値
    """
    if not tag_value or not isinstance(tag_value, str):
        return tag_value
    
    tag_value = tag_value.strip()
    if not tag_value:
        return tag_value
    
    synonyms = get_synonyms_dict()
    
    # 同義語辞書から正規形を取得
    normalized = synonyms.get(tag_value, tag_value)
    
    return normalized


def categorize_tag_value(tag_value: str) -> Optional[TagCategory]:
    """
    タグの値をカテゴリに分類
    
    Args:
        tag_value: タグの値
    
    Returns:
        カテゴリ（見つからない場合はNone）
    """
    if not tag_value or not isinstance(tag_value, str):
        return None
    
    tag_value = tag_value.strip()
    normalized = normalize_tag_value(tag_value)
    
    categories_data = load_tag_categories()
    categories = categories_data.get("categories", {})
    
    # 各カテゴリのタグリストをチェック
    for category_key, category_info in categories.items():
        category_tags = category_info.get("tags", [])
        # 正規化された値または元の値がカテゴリのタグリストに含まれているかチェック
        if normalized in category_tags or tag_value in category_tags:
            try:
                return TagCategory(category_key)
            except ValueError:
                continue
    
    return None


def create_structured_tag(
    value: str,
    source: TagSource = TagSource.MANUAL,
    category: Optional[TagCategory] = None,
    priority: TagPriority = TagPriority.MEDIUM
) -> Tag:
    """
    構造化タグを作成
    
    Args:
        value: タグの値
        source: 作成元
        category: カテゴリ（Noneの場合は自動判定）
        priority: 優先度
    
    Returns:
        構造化タグ
    """
    normalized = normalize_tag_value(value)
    
    if category is None:
        category = categorize_tag_value(value)
    
    return Tag(
        value=value,
        category=category,
        priority=priority,
        source=source,
        normalized=normalized
    )


def normalize_tags(tags: List[Any], source: TagSource = TagSource.MANUAL) -> List[Tag]:
    """
    タグリストを正規化して構造化タグに変換
    
    Args:
        tags: タグリスト（文字列または構造化タグ）
        source: 作成元
    
    Returns:
        構造化タグのリスト
    """
    result = []
    
    for tag in tags:
        if isinstance(tag, str):
            # 文字列タグを構造化タグに変換
            structured_tag = create_structured_tag(tag, source=source)
            result.append(structured_tag)
        elif isinstance(tag, dict):
            # 既存の構造化タグ（辞書形式）をTagオブジェクトに変換
            tag_value = tag.get("value", "")
            if not tag_value:
                continue
            
            # カテゴリを取得または自動判定
            category_str = tag.get("category")
            category = None
            if category_str:
                try:
                    category = TagCategory(category_str)
                except ValueError:
                    category = categorize_tag_value(tag_value)
            else:
                category = categorize_tag_value(tag_value)
            
            # 優先度を取得
            priority = TagPriority(tag.get("priority", TagPriority.MEDIUM))
            
            # 作成元を取得
            source_str = tag.get("source", source.value)
            try:
                tag_source = TagSource(source_str)
            except ValueError:
                tag_source = source
            
            structured_tag = Tag(
                value=tag_value,
                category=category,
                priority=priority,
                source=tag_source,
                normalized=normalize_tag_value(tag_value)
            )
            result.append(structured_tag)
        elif isinstance(tag, Tag):
            # 既にTagオブジェクトの場合はそのまま
            result.append(tag)
    
    return result


def get_recommended_tags(category: Optional[TagCategory] = None) -> List[str]:
    """
    推奨タグリストを取得
    
    Args:
        category: カテゴリ（Noneの場合は全カテゴリ）
    
    Returns:
        推奨タグのリスト
    """
    categories_data = load_tag_categories()
    categories = categories_data.get("categories", {})
    
    if category:
        category_info = categories.get(category.value, {})
        return category_info.get("tags", [])
    
    # 全カテゴリのタグを統合
    all_tags = []
    for category_info in categories.values():
        all_tags.extend(category_info.get("tags", []))
    
    return list(set(all_tags))  # 重複を除去


def validate_tag(tag: Tag) -> bool:
    """
    タグのバリデーション
    
    Args:
        tag: タグオブジェクト
    
    Returns:
        有効な場合はTrue
    """
    if not tag.value or not isinstance(tag.value, str):
        return False
    
    if not tag.value.strip():
        return False
    
    return True


def filter_valid_tags(tags: List[Tag]) -> List[Tag]:
    """
    有効なタグのみをフィルター
    
    Args:
        tags: タグリスト
    
    Returns:
        有効なタグのリスト
    """
    return [tag for tag in tags if validate_tag(tag)]


def extract_tag_values(tags: List[Any]) -> List[str]:
    """
    タグリストから値のみを抽出（後方互換性）
    
    Args:
        tags: タグリスト（文字列、辞書、Tagオブジェクト）
    
    Returns:
        タグの値のリスト
    """
    result = []
    for tag in tags:
        if isinstance(tag, str):
            result.append(tag)
        elif isinstance(tag, dict):
            value = tag.get("value", "")
            if value:
                result.append(value)
        elif isinstance(tag, Tag):
            result.append(tag.value)
    
    return result


def tags_to_dict_list(tags: List[Tag]) -> List[Dict[str, Any]]:
    """
    タグリストを辞書リストに変換（データベース保存用）
    
    Args:
        tags: タグリスト
    
    Returns:
        辞書リスト
    """
    return [tag.model_dump(exclude_none=True) for tag in tags]


def dict_list_to_tags(tag_dicts: List[Dict[str, Any]]) -> List[Tag]:
    """
    辞書リストをタグリストに変換（データベース読み込み用）
    
    Args:
        tag_dicts: 辞書リスト
    
    Returns:
        タグリスト
    """
    return normalize_tags(tag_dicts)

