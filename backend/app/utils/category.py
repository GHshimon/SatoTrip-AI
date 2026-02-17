"""カテゴリ分類機能"""
from typing import List, Dict, Any
from collections import defaultdict


def categorize_item(item: str) -> str:
    """アイテムをカテゴリに分類"""
    if not item:
        return "その他"
    item_lower = item.lower()
    if any(kw in item for kw in ["パン", "料理", "ラーメン", "とんかつ", "しゃぶしゃぶ", "黒豚", "白熊", "かき氷", "さつま揚げ", "揚げ", "メロン", "ソフトクリーム", "食事", "レストラン", "カフェ"]):
        return "グルメ"
    if any(kw in item for kw in ["庭園", "展望台", "灯台", "博物館", "館", "御殿", "銅像", "観光"]):
        return "観光・施設"
    if any(kw in item for kw in ["歴史", "西郷", "島津", "維新", "武者", "武家屋敷", "神社", "神宮", "特攻"]):
        return "歴史・文化"
    if any(kw in item for kw in ["滝", "自然", "山", "海", "砂浜", "夕日", "屋久杉", "苔", "亜熱帯植物", "砂むし"]):
        return "自然・絶景"
    if any(kw in item for kw in ["体験", "温泉", "トレッキング", "散策", "ドライブ"]):
        return "体験・アクティビティ"
    if any(kw in item for kw in ["雑貨", "お土産", "ショップ", "ハンズメイド"]):
        return "ショッピング"
    return "その他"


def build_hierarchical_facets(places: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    """階層構造のファセットを構築"""
    theme_hierarchy = defaultdict(set)
    for p in places:
        items = p.get("items", [])
        if isinstance(items, list):
            for item in items:
                if item and isinstance(item, str):
                    category = categorize_item(item)
                    theme_hierarchy[category].add(item)
    return {k: sorted(list(v)) for k, v in sorted(theme_hierarchy.items())}

