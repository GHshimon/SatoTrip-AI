"""
SNS/Web検索データ収集サービス
既存のcollect_sns_data.pyから移植
RSSフィード対応、AI要約機能追加
"""
import feedparser
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
from urllib.parse import quote
import google.generativeai as genai
from app.config import settings
from app.utils.error_handler import log_error


def collect_trending_topics(keyword: str = "鹿児島 観光") -> List[Dict[str, Any]]:
    """
    SNSやWebからキーワードに関連するトレンド情報を収集（RSSフィード使用）
    
    Args:
        keyword: 検索キーワード
    
    Returns:
        トレンド情報のリスト（タイトル、リンク、公開日時）
    """
    # キーワードをURLエンコード（スペースを%20に変換）
    encoded_keyword = quote(keyword, safe='')
    url = f"https://news.google.com/rss/search?q={encoded_keyword}&hl=ja&gl=JP&ceid=JP:ja"
    
    try:
        feed = feedparser.parse(url)
        results = []
        
        for entry in feed.entries:
            results.append({
                "keyword": keyword,
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
                "source": "GoogleNews",
                "timestamp": datetime.now().isoformat()
            })
        
        return results
    except Exception as e:
        log_error("SNS_COLLECTION_ERROR", f"SNS/Web検索エラー ({keyword}): {e}")
        return []


def summarize_sns_article_with_gemini(article_title: str, article_link: str) -> Optional[str]:
    """
    Geminiで記事タイトルから観光スポット情報を構造化抽出
    
    Args:
        article_title: 記事タイトル
        article_link: 記事リンク
    
    Returns:
        構造化JSON形式の要約テキスト
    """
    if not settings.GEMINI_API_KEY:
        log_error("GEMINI_API_KEY_NOT_SET", "GEMINI_API_KEYが設定されていません")
        return None
    
    prompt = f"""
以下のニュース記事から、観光地・グルメ情報として構造的に要約してください。

- タイトル: {article_title}
- リンク: {article_link}

以下の形式で、**必ず日本語で出力**してください：
---
■ テーマ（例: グルメ / 観光 / 体験 / イベント）
■ 主なエリア（都道府県、市町村、地区名まで可能なら記載）
■ 店舗・施設名（複数あればすべて列挙）
■ 登場する商品・料理名・名物（記事内で紹介されたもの）
■ おすすめポイント（100文字以内、旅行者目線）
■ 雰囲気（例: 癒やし / 活気 / 美味しそう / 歴史的）
■ 推定緯度経度（分からなければ "不明" と記載）
■ JSON出力例:
{{
  "theme": "観光",
  "area": "鹿児島市",
  "places": ["桜島", "城山公園"],
  "items": ["観光スポット", "展望台"],
  "recommend": "鹿児島のシンボル桜島と市内を一望できる展望台。",
  "mood": "絶景",
  "geo": "不明"
}}
---

出力は文章ではなく、このJSON形式に従ってください。
"""
    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)
        
        # レスポンスのテキストを安全に取得
        if not hasattr(response, 'text') or not response.text:
            error_msg = "Gemini APIからのレスポンスが空です"
            if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                error_msg += f": {response.prompt_feedback}"
            log_error("GEMINI_EMPTY_RESPONSE", error_msg)
            return None
        
        return response.text.strip()
    except Exception as e:
        log_error("GEMINI_SNS_SUMMARY_ERROR", f"Gemini要約失敗: {e}")
        return None


def collect_sns_data_with_summary(
    keyword: str = "鹿児島 観光",
    max_results: int = 10
) -> Dict[str, Any]:
    """
    SNS/Web検索データ収集とAI要約を実行
    
    Args:
        keyword: 検索キーワード
        max_results: 最大取得件数
    
    Returns:
        収集結果の辞書（summaryフィールドを含む）
    """
    # RSSフィードから記事を取得
    articles = collect_trending_topics(keyword)
    
    # 最大件数で制限
    articles = articles[:max_results]
    
    results = []
    for article in articles:
        # AI要約を実行
        summary = summarize_sns_article_with_gemini(
            article.get("title", ""),
            article.get("link", "")
        )
        
        if summary:
            entry = {
                "keyword": keyword,
                "title": article.get("title", ""),
                "link": article.get("link", ""),
                "published": article.get("published", ""),
                "source": "GoogleNews",
                "summary": summary,
                "timestamp": datetime.now().isoformat()
            }
            results.append(entry)
        
        time.sleep(1)  # アクセス制限回避
    
    return {
        "results": results,
        "total_articles": len(articles),
        "total_summarized": len(results)
    }

