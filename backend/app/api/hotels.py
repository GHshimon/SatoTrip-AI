"""
宿泊施設検索APIエンドポイント
"""
from fastapi import APIRouter, HTTPException, status, Query
from typing import Optional, List, Dict, Any
from app.utils.hotel_categories import (
    get_all_categories,
    get_category_description,
    get_category_icon,
    generate_hotel_search_query
)
from app.utils.affiliate_links import generate_hotel_link

router = APIRouter(prefix="/api/hotels", tags=["hotels"])


@router.get("/categories")
async def get_hotel_categories():
    """宿泊施設カテゴリ一覧を取得"""
    categories = get_all_categories()
    result = []
    for category in categories:
        result.append({
            "name": category,
            "description": get_category_description(category),
            "icon": get_category_icon(category)
        })
    return {"categories": result}


@router.get("/search")
async def search_hotels(
    area: str = Query(..., description="エリア名"),
    category: Optional[str] = Query(None, description="宿泊施設カテゴリ"),
    hotel_name: Optional[str] = Query(None, description="ホテル名"),
    check_in: Optional[str] = Query(None, description="チェックイン日（YYYY-MM-DD形式）"),
    check_out: Optional[str] = Query(None, description="チェックアウト日（YYYY-MM-DD形式）"),
    num_guests: int = Query(2, ge=1, le=20, description="予約人数（1-20）")
) -> Dict[str, Any]:
    """
    宿泊施設検索
    
    予約サイトへの検索リンクを生成します。
    """
    # 検索クエリを生成
    search_query = generate_hotel_search_query(
        area=area,
        category=category,
        hotel_name=hotel_name
    )
    
    # 各予約サイトへのリンクを生成
    links = {}
    
    # 楽天トラベル
    rakuten_link = generate_hotel_link(
        hotel_name=search_query,
        area=area,
        check_in=check_in or "",
        check_out=check_out or "",
        num_guests=num_guests,
        affiliate_type="rakuten"
    )
    links["rakuten"] = rakuten_link
    
    # Yahoo!トラベル
    yahoo_link = generate_hotel_link(
        hotel_name=search_query,
        area=area,
        check_in=check_in or "",
        check_out=check_out or "",
        num_guests=num_guests,
        affiliate_type="yahoo"
    )
    links["yahoo"] = yahoo_link
    
    # じゃらん
    jalan_link = generate_hotel_link(
        hotel_name=search_query,
        area=area,
        check_in=check_in or "",
        check_out=check_out or "",
        num_guests=num_guests,
        affiliate_type="jalan"
    )
    links["jalan"] = jalan_link
    
    # エラーがある場合は警告として含める
    errors = []
    for site, link_info in links.items():
        if link_info.get("error"):
            errors.append({
                "site": site,
                "affiliate": link_info.get("affiliate", ""),
                "error": link_info.get("error", "")
            })
    
    return {
        "area": area,
        "category": category,
        "hotel_name": hotel_name,
        "check_in": check_in,
        "check_out": check_out,
        "num_guests": num_guests,
        "search_query": search_query,
        "links": links,
        "errors": errors if errors else None
    }

