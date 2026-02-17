"""
宿泊施設カテゴリ管理
ホテル・旅館などのカテゴリ分類と検索キーワード生成
"""
from typing import Dict, List, Optional

# 宿泊施設カテゴリ定義
HOTEL_CATEGORIES = {
    "ビジネスホテル": {
        "keywords": ["ビジネスホテル", "シティホテル", "都市型ホテル"],
        "description": "都市部に多く、ビジネス利用に適したホテル",
        "icon": "🏢"
    },
    "リゾートホテル": {
        "keywords": ["リゾートホテル", "リゾート", "リゾート施設"],
        "description": "観光地や温泉地にあるリゾート向けホテル",
        "icon": "🏖️"
    },
    "旅館": {
        "keywords": ["旅館", "和風旅館", "日本旅館"],
        "description": "和室中心の伝統的な日本式宿泊施設",
        "icon": "🏮"
    },
    "民宿・ペンション": {
        "keywords": ["民宿", "ペンション", "ゲストハウス"],
        "description": "小規模でアットホームな宿泊施設",
        "icon": "🏡"
    },
    "温泉旅館": {
        "keywords": ["温泉", "温泉旅館", "温泉ホテル"],
        "description": "温泉が楽しめる宿泊施設",
        "icon": "♨️"
    },
    "高級ホテル": {
        "keywords": ["高級ホテル", "ラグジュアリーホテル", "5つ星"],
        "description": "高級感のある上質なホテル",
        "icon": "⭐"
    },
    "カプセルホテル": {
        "keywords": ["カプセルホテル", "カプセル"],
        "description": "コンパクトで低価格な宿泊施設",
        "icon": "📦"
    },
    "その他": {
        "keywords": [],
        "description": "その他の宿泊施設",
        "icon": "🏨"
    }
}


def get_hotel_category_keywords(category: str) -> List[str]:
    """カテゴリに対応するキーワードを取得"""
    return HOTEL_CATEGORIES.get(category, HOTEL_CATEGORIES["その他"])["keywords"]


def generate_hotel_search_query(area: str, category: Optional[str] = None, hotel_name: Optional[str] = None) -> str:
    """
    ホテル検索クエリを生成
    Args:
        area: エリア名
        category: カテゴリ名（オプション）
        hotel_name: ホテル名（オプション）
    Returns:
        検索クエリ文字列
    """
    query_parts = []
    
    if hotel_name:
        query_parts.append(hotel_name)
    else:
        if category and category != "その他":
            keywords = get_hotel_category_keywords(category)
            if keywords:
                query_parts.append(keywords[0])
        query_parts.append(area)
        query_parts.append("宿泊")
    
    return " ".join(query_parts)


def get_category_description(category: str) -> str:
    """カテゴリの説明を取得"""
    return HOTEL_CATEGORIES.get(category, HOTEL_CATEGORIES["その他"])["description"]


def get_category_icon(category: str) -> str:
    """カテゴリのアイコンを取得"""
    return HOTEL_CATEGORIES.get(category, HOTEL_CATEGORIES["その他"])["icon"]


def get_all_categories() -> List[str]:
    """すべてのカテゴリ名を取得"""
    return list(HOTEL_CATEGORIES.keys())

