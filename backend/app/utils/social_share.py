"""SNSシェア機能"""
import urllib.parse
from typing import Dict, Any, Optional


def generate_twitter_share_url(text: str, url: Optional[str] = None) -> str:
    """TwitterシェアURL生成"""
    params = {"text": text[:280]}
    if url:
        params["url"] = url
    return f"https://twitter.com/intent/tweet?{urllib.parse.urlencode(params)}"


def generate_facebook_share_url(url: str) -> str:
    """FacebookシェアURL生成"""
    return f"https://www.facebook.com/sharer/sharer.php?u={urllib.parse.quote(url)}"


def generate_line_share_url(text: str, url: Optional[str] = None) -> str:
    """LINEシェアURL生成"""
    if url:
        return f"https://social-plugins.line.me/lineit/share?url={urllib.parse.quote(url)}"
    return f"https://social-plugins.line.me/lineit/share?text={urllib.parse.quote(text)}"


def generate_plan_share_text(plan: Dict[str, Any]) -> str:
    """プランのシェア用テキスト生成"""
    title = plan.get("title", "旅行プラン")
    summary = plan.get("summary", "")
    days = len(plan.get("days", []))
    text = f"{title}\n"
    if summary:
        text += f"{summary[:100]}\n"
    text += f"{days}日間の旅行プラン"
    return text


def generate_plan_share_urls(plan: Dict[str, Any], base_url: str = "") -> Dict[str, str]:
    """プランのシェアURL生成"""
    share_text = generate_plan_share_text(plan)
    plan_json = urllib.parse.quote(str(plan))
    share_url = f"{base_url}?plan={plan_json}" if base_url else ""
    
    return {
        "twitter": generate_twitter_share_url(share_text, share_url),
        "facebook": generate_facebook_share_url(share_url) if share_url else "",
        "line": generate_line_share_url(share_text, share_url),
    }

