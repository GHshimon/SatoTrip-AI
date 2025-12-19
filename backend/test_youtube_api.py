"""
YouTube Data API動作確認テストスクリプト
"""
import os
import sys
import requests
from dotenv import load_dotenv

# .envファイルを読み込み
load_dotenv()

# APIキーを取得
api_key = os.getenv("YOUTUBE_API_KEY", "")

print("=" * 60)
print("YouTube Data API動作確認テスト")
print("=" * 60)
print()

# APIキーの確認
if not api_key:
    print("❌ エラー: YOUTUBE_API_KEYが設定されていません")
    print("   .envファイルにYOUTUBE_API_KEYを設定してください")
    sys.exit(1)

print(f"✅ APIキーが設定されています")
print(f"   キーの長さ: {len(api_key)}文字")
print(f"   キーの先頭: {api_key[:5]}...")
print()

# APIキーの形式チェック
if api_key.startswith("y"):
    print("⚠️  警告: APIキーの先頭に'y'が付いています")
    print("   正しい形式: AIzaSy...")
    print("   現在の形式: yAIzaSy...")
    print()

# テストキーワード
test_keyword = "鹿児島 観光"

print(f"🔍 テストキーワード: {test_keyword}")
print()

# YouTube Data APIを呼び出し
url = "https://www.googleapis.com/youtube/v3/search"
params = {
    "part": "snippet",
    "q": test_keyword,
    "type": "video",
    "maxResults": 3,
    "key": api_key
}

print(f"📡 APIリクエスト送信...")
print(f"   URL: {url}")
print(f"   パラメータ: part=snippet, q={test_keyword}, type=video, maxResults=3")
print()

try:
    response = requests.get(url, params=params, timeout=10)
    
    print(f"📥 レスポンス受信")
    print(f"   ステータスコード: {response.status_code}")
    print()
    
    if response.status_code == 200:
        data = response.json()
        items = data.get("items", [])
        
        print(f"✅ 成功: {len(items)}件の動画を取得しました")
        print()
        
        for i, item in enumerate(items, 1):
            video_id = item["id"]["videoId"]
            title = item["snippet"]["title"]
            channel = item["snippet"]["channelTitle"]
            link = f"https://www.youtube.com/watch?v={video_id}"
            
            print(f"   {i}. {title}")
            print(f"      チャンネル: {channel}")
            print(f"      URL: {link}")
            print()
        
        print("=" * 60)
        print("✅ YouTube APIは正常に動作しています")
        print("=" * 60)
        
    else:
        print(f"❌ エラー: ステータスコード {response.status_code}")
        print()
        
        # エラーレスポンスの詳細を表示
        try:
            error_data = response.json()
            error_info = error_data.get("error", {})
            
            print("エラー詳細:")
            print(f"   メッセージ: {error_info.get('message', 'N/A')}")
            
            errors = error_info.get("errors", [])
            if errors:
                print("   エラー詳細:")
                for err in errors:
                    print(f"     - ドメイン: {err.get('domain', 'N/A')}")
                    print(f"     - 理由: {err.get('reason', 'N/A')}")
                    print(f"     - メッセージ: {err.get('message', 'N/A')}")
                    print()
            
        except:
            print(f"   レスポンス本文: {response.text[:500]}")
            print()
        
        print("=" * 60)
        print("❌ YouTube APIの呼び出しに失敗しました")
        print("=" * 60)
        sys.exit(1)
        
except requests.exceptions.RequestException as e:
    print(f"❌ リクエストエラー: {e}")
    print()
    print("=" * 60)
    print("❌ YouTube APIの呼び出しに失敗しました")
    print("=" * 60)
    sys.exit(1)
except Exception as e:
    print(f"❌ 予期しないエラー: {e}")
    print()
    print("=" * 60)
    print("❌ テスト実行中にエラーが発生しました")
    print("=" * 60)
    sys.exit(1)

