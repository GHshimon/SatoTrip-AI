"""
スポットマッチングユーティリティ
パフォーマンス最適化されたスポットマッチング機能を提供
"""
from typing import List, Optional, Tuple, Dict
from app.models.spot import Spot
from difflib import SequenceMatcher


def create_spot_index(spots: List[Spot]) -> Dict[str, Spot]:
    """
    スポットリストを名前でインデックス化
    
    Args:
        spots: スポットリスト
    
    Returns:
        {spot_name: spot} の辞書
    """
    index = {}
    for spot in spots:
        # 基本の名前でインデックス化
        if spot.name:
            index[spot.name] = spot
            # 別名や部分一致も考慮
            if spot.area:
                key = f"{spot.name} ({spot.area})"
                if key not in index:
                    index[key] = spot
    return index


def match_spot(
    spot_name: str,
    spot_index: Dict[str, Spot],
    threshold: float = 0.8
) -> Optional[Tuple[Spot, float]]:
    """
    スポット名をマッチング
    
    Args:
        spot_name: マッチング対象のスポット名
        spot_index: インデックス化されたスポット辞書
        threshold: あいまいマッチングの閾値（0.0-1.0）
    
    Returns:
        (マッチしたSpot, スコア) または None
    """
    if not spot_name:
        return None
    
    # 1. 完全一致
    if spot_name in spot_index:
        return (spot_index[spot_name], 1.0)
    
    # 2. 部分一致（spot_name in db_name または db_name in spot_name）
    for db_name, spot in spot_index.items():
        if spot_name in db_name or db_name in spot_name:
            return (spot, 0.9)
    
    # 3. あいまいマッチング
    best_match = None
    best_score = 0.0
    
    spot_name_lower = spot_name.lower()
    for db_name, spot in spot_index.items():
        # 名前のみで比較（エリア情報を除く）
        db_name_clean = db_name.split(" (")[0]  # エリア情報を除去
        score = SequenceMatcher(None, spot_name_lower, db_name_clean.lower()).ratio()
        if score > best_score and score >= threshold:
            best_score = score
            best_match = spot
    
    if best_match:
        return (best_match, best_score)
    
    return None

