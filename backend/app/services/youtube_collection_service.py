"""
YouTubeデータ収集サービス
既存のyoutube_summary_gemini.pyから移植
"""
import os
import json
import time
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime
from itertools import product
import google.generativeai as genai
from app.config import settings
from app.utils.error_handler import log_error


def load_keyword_config(keywords_config_path: str = "data/search_keywords.json") -> dict:
    """キーワード管理JSONを読み込み"""
    if not os.path.exists(keywords_config_path):
        # フォールバック: デフォルト設定
        return {
            "鹿児島県": {
                "カテゴリ": ["観光", "グルメ", "温泉", "イベント"],
                "エリア補助": []
            }
        }
    with open(keywords_config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def generate_search_keywords(config: dict) -> List[str]:
    """(県 × カテゴリ × エリア) の組み合わせで検索キーワードを自動生成"""
    keywords = []
    for prefecture, prefecture_settings in config.items():
        categories = prefecture_settings.get("カテゴリ", [])
        areas = prefecture_settings.get("エリア補助", [])
        
        # 県 + カテゴリ（基本）
        for cat in categories:
            keywords.append(f"{prefecture} {cat}")
        
        # 県 + カテゴリ + エリア（詳細）
        for cat, area in product(categories, areas):
            keywords.append(f"{prefecture} {cat} {area}")
    
    return list(set(keywords))  # 重複除去


def get_youtube_videos(keyword: str, max_results: int = 5) -> tuple[List[Dict[str, str]], Optional[str]]:
    """
    YouTube Data APIから動画リンクを取得
    
    Returns:
        (videos, error_type): 
        - videos: 動画リスト（成功時）または空リスト（エラー時）
        - error_type: None（成功）、"quota_exceeded"（クォータ制限）、"other"（その他のエラー）
    """
    if not settings.YOUTUBE_API_KEY:
        log_error("YOUTUBE_API_KEY_NOT_SET", "YOUTUBE_API_KEYが設定されていません")
        return [], "other"
    
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "q": keyword,
        "type": "video",
        "maxResults": max_results,
        "key": settings.YOUTUBE_API_KEY
    }
    
    try:
        res = requests.get(url, params=params, timeout=10)
        res.raise_for_status()
        data = res.json()
        videos = []
        for item in data.get("items", []):
            vid = item["id"]["videoId"]
            title = item["snippet"]["title"]
            link = f"https://www.youtube.com/watch?v={vid}"
            videos.append({"title": title, "url": link})
        return videos, None
    except requests.exceptions.HTTPError as e:
        # エラーレスポンスの詳細を取得
        error_detail = ""
        error_type = "other"
        
        try:
            error_data = e.response.json()
            error_message = error_data.get('error', {}).get('message', '')
            error_detail = f" - {error_message}"
            
            # 403エラーでクォータ制限のメッセージが含まれている場合
            if e.response.status_code == 403:
                if "quota" in error_message.lower() or "exceeded" in error_message.lower():
                    error_type = "quota_exceeded"
                    log_error(
                        "YOUTUBE_QUOTA_EXCEEDED",
                        f"YouTube APIクォータ制限に達しました ({keyword}): {error_message}",
                        {"keyword": keyword, "status_code": 403}
                    )
                else:
                    log_error(
                        "YOUTUBE_API_403_ERROR",
                        f"YouTube API 403エラー ({keyword}): {error_message}",
                        {"keyword": keyword, "status_code": 403}
                    )
            else:
                log_error(
                    "YOUTUBE_API_ERROR",
                    f"YouTube API呼び出しエラー ({keyword}): {e}{error_detail}",
                    {"keyword": keyword, "status_code": e.response.status_code}
                )
        except:
            error_detail = f" - {e.response.text[:200]}"
            if e.response.status_code == 403:
                error_type = "quota_exceeded"
            log_error("YOUTUBE_API_ERROR", f"YouTube API呼び出しエラー ({keyword}): {e}{error_detail}")
        
        return [], error_type
    except Exception as e:
        log_error("YOUTUBE_API_ERROR", f"YouTube API呼び出しエラー ({keyword}): {e}")
        return [], "other"


def summarize_with_gemini(video_title: str, video_url: str) -> Optional[str]:
    """Geminiで動画を構造化要約（マップ化対応）"""
    if not settings.GEMINI_API_KEY:
        log_error("GEMINI_API_KEY_NOT_SET", "GEMINI_API_KEYが設定されていません")
        return None
    
    prompt = f"""
以下のYouTube動画の内容を、観光地・グルメ情報として構造的に要約してください。

- タイトル: {video_title}
- URL: {video_url}

以下の形式で、**必ず日本語で出力**してください：
---
■ テーマ（例: グルメ / 観光 / 体験 / イベント）
■ 主なエリア（都道府県、市町村、地区名まで可能なら記載）
■ 店舗・施設名（複数あればすべて列挙）
■ 登場する商品・料理名・名物（動画内で紹介されたもの）
■ おすすめポイント（100文字以内、旅行者目線）
■ 雰囲気（例: 癒やし / 活気 / 美味しそう / 歴史的）
■ 推定緯度経度（分からなければ "不明" と記載）
■ JSON出力例:
{{
  "theme": "グルメ",
  "area": "鹿児島市 天文館",
  "places": ["黒かつ亭", "ラーメン小金太"],
  "items": ["黒豚とんかつ", "鹿児島ラーメン"],
  "recommend": "地元食材を使った名店が並び、観光と食を両立できる。",
  "mood": "美味しそう",
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
        log_error("GEMINI_SUMMARY_ERROR", f"Gemini要約失敗: {e}")
        return None


def collect_youtube_data(
    prefecture: str = "鹿児島県",
    keywords_config_path: str = "data/search_keywords.json",
    max_results_per_keyword: int = 5,
    max_keywords: Optional[int] = None,
    max_total_videos: Optional[int] = None,
    stop_on_quota_exceeded: bool = True
) -> Dict[str, Any]:
    """
    YouTubeデータ収集のメイン処理
    
    Args:
        prefecture: 都道府県名
        keywords_config_path: キーワード設定JSONファイルのパス
        max_results_per_keyword: キーワードあたりの最大取得件数
        stop_on_quota_exceeded: クォータ制限に達した場合、処理を停止するか（デフォルト: True）
    
    Returns:
        収集結果の辞書（quota_exceeded、quota_exceeded_keywords、successful_keywordsを含む）
    """
    results = []
    keyword_results = {}  # キーワードごとの結果
    quota_exceeded = False
    quota_exceeded_keywords = 0
    successful_keywords = 0
    failed_keywords = 0
    
    # キーワード設定を読み込み
    keyword_config = load_keyword_config(keywords_config_path)
    
    # 指定都道府県のキーワードのみを生成
    if prefecture in keyword_config:
        filtered_config = {prefecture: keyword_config[prefecture]}
        search_keywords = generate_search_keywords(filtered_config)
    else:
        # 指定都道府県が設定にない場合は全件
        search_keywords = generate_search_keywords(keyword_config)
    
    # キーワード上限（切り詰め）
    if max_keywords is not None and isinstance(max_keywords, int) and max_keywords > 0:
        search_keywords = search_keywords[:max_keywords]

    for keyword in search_keywords:
        # 動画数上限（打ち切り）
        if max_total_videos is not None and isinstance(max_total_videos, int) and max_total_videos > 0:
            if len(results) >= max_total_videos:
                break

        videos, error_type = get_youtube_videos(keyword, max_results_per_keyword)
        
        # クォータ制限エラーの場合
        if error_type == "quota_exceeded":
            quota_exceeded = True
            quota_exceeded_keywords += 1
            
            if stop_on_quota_exceeded:
                log_error(
                    "YOUTUBE_QUOTA_EXCEEDED_STOP",
                    f"YouTube APIクォータ制限に達したため、処理を停止します。処理済み: {successful_keywords}/{len(search_keywords)}キーワード",
                    {"processed": successful_keywords, "total": len(search_keywords)}
                )
                break
        
        # その他のエラーの場合
        elif error_type == "other":
            failed_keywords += 1
            keyword_results[keyword] = []
            continue
        
        # 成功した場合
        if videos:
            successful_keywords += 1
            keyword_videos = []
            for v in videos:
                # 動画数上限（打ち切り）
                if max_total_videos is not None and isinstance(max_total_videos, int) and max_total_videos > 0:
                    if len(results) >= max_total_videos:
                        break
                summary = summarize_with_gemini(v["title"], v["url"])
                if summary:
                    entry = {
                        "keyword": keyword,
                        "title": v["title"],
                        "url": v["url"],
                        "summary": summary,
                        "timestamp": datetime.now().isoformat()
                    }
                    results.append(entry)
                    keyword_videos.append(entry)
                time.sleep(1)  # アクセス制限回避
            
            keyword_results[keyword] = keyword_videos
        else:
            keyword_results[keyword] = []
    
    return {
        "results": results,
        "keyword_results": keyword_results,
        "total_keywords": len(search_keywords),
        "total_videos": len(results),
        "quota_exceeded": quota_exceeded,
        "quota_exceeded_keywords": quota_exceeded_keywords,
        "successful_keywords": successful_keywords,
        "failed_keywords": failed_keywords
    }


# 直接実行方法:
# cd backend
# python -m app.services.youtube_collection_service --prefecture "鹿児島県" --keywords "data/search_keywords.json" --max-results 5
#
# または:
# cd backend
# python app/services/youtube_collection_service.py --prefecture "鹿児島県"
#
# 注意: API経由での実行は既存の方法（POST /api/admin/data-collection/youtube）をそのまま使用できます
if __name__ == "__main__":
    import sys
    import argparse
    from pathlib import Path
    
    # 直接実行時のみ、backendディレクトリをsys.pathに追加
    backend_dir = Path(__file__).parent.parent.parent
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
    
    # .envファイルの読み込み
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=backend_dir / ".env")
    
    # コマンドライン引数の解析
    parser = argparse.ArgumentParser(
        description="YouTubeデータ収集サービス（直接実行）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
実行例:
  python -m app.services.youtube_collection_service --prefecture "鹿児島県"
  python -m app.services.youtube_collection_service --prefecture "鹿児島県" --keywords "data/search_keywords.json" --max-results 3
        """
    )
    parser.add_argument(
        "--prefecture",
        type=str,
        default="鹿児島県",
        help="都道府県名（デフォルト: 鹿児島県）"
    )
    parser.add_argument(
        "--keywords",
        type=str,
        default="data/search_keywords.json",
        help="キーワード設定JSONファイルのパス（デフォルト: data/search_keywords.json）"
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=5,
        help="キーワードあたりの最大取得件数（デフォルト: 5）"
    )
    parser.add_argument(
        "--output",
        type=str,
        choices=["json", "pretty"],
        default="pretty",
        help="出力形式: json（JSON形式）またはpretty（読みやすい形式、デフォルト）"
    )
    
    args = parser.parse_args()
    
    # 設定の確認
    print("=" * 60)
    print("YouTubeデータ収集サービス（直接実行）")
    print("=" * 60)
    print(f"都道府県: {args.prefecture}")
    print(f"キーワード設定: {args.keywords}")
    print(f"最大取得件数/キーワード: {args.max_results}")
    print(f"出力形式: {args.output}")
    print("=" * 60)
    print()
    
    # 環境変数の確認
    from app.config import settings
    
    if not settings.YOUTUBE_API_KEY:
        print("❌ エラー: YOUTUBE_API_KEYが設定されていません")
        print("   .envファイルにYOUTUBE_API_KEYを設定してください")
        sys.exit(1)
    
    if not settings.GEMINI_API_KEY:
        print("❌ エラー: GEMINI_API_KEYが設定されていません")
        print("   .envファイルにGEMINI_API_KEYを設定してください")
        sys.exit(1)
    
    print("✅ 環境変数の確認完了")
    print()
    
    # データ収集の実行
    try:
        print("📡 データ収集を開始します...")
        print()
        
        result = collect_youtube_data(
            prefecture=args.prefecture,
            keywords_config_path=args.keywords,
            max_results_per_keyword=args.max_results,
            stop_on_quota_exceeded=True
        )
        
        # 結果の表示
        print("=" * 60)
        print("📊 収集結果")
        print("=" * 60)
        print(f"処理キーワード数: {result['total_keywords']}")
        print(f"取得動画数: {result['total_videos']}")
        print(f"成功キーワード数: {result.get('successful_keywords', 0)}")
        print(f"失敗キーワード数: {result.get('failed_keywords', 0)}")
        
        if result.get('quota_exceeded', False):
            print()
            print("⚠️ YouTube APIのクォータ制限に達しました")
            print(f"   クォータ制限により処理できなかったキーワード数: {result.get('quota_exceeded_keywords', 0)}")
            print()
            print("💡 対処法:")
            print("   1. max_results_per_keywordを減らす（例: --max-results 1）")
            print("   2. キーワード数を減らす（search_keywords.jsonを編集）")
            print("   3. クォータがリセットされるまで待つ（24時間ごと）")
            print("   4. 複数のAPIキーを使用する")
        
        print()
        
        if args.output == "json":
            # JSON形式で出力
            import json
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            # 読みやすい形式で出力
            if result['results']:
                print("取得した動画:")
                print()
                for i, entry in enumerate(result['results'], 1):
                    print(f"{i}. {entry['title']}")
                    print(f"   キーワード: {entry['keyword']}")
                    print(f"   URL: {entry['url']}")
                    print(f"   要約: {entry['summary'][:100]}..." if len(entry['summary']) > 100 else f"   要約: {entry['summary']}")
                    print()
            else:
                print("⚠️ 取得した動画がありません")
                if result.get('quota_exceeded', False):
                    print("   原因: YouTube APIのクォータ制限に達しました")
        
        print("=" * 60)
        if result.get('quota_exceeded', False):
            print("⚠️ データ収集が完了しました（クォータ制限により一部未処理）")
        else:
            print("✅ データ収集が完了しました")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n⚠️ ユーザーによって中断されました")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

