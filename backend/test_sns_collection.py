"""
SNSデータ収集のテストスクリプト
問題の原因を特定するため
"""
import requests
from bs4 import BeautifulSoup
from datetime import datetime

def test_google_news_scraping(keyword="鹿児島 観光"):
    """Googleニュースのスクレイピングをテスト"""
    url = f"https://news.google.com/search?q={keyword}&hl=ja&gl=JP&ceid=JP:ja"
    
    print(f"🔍 テスト開始: {keyword}")
    print(f"📡 URL: {url}\n")
    
    try:
        # ユーザーエージェントを設定（Googleニュースがブロックする可能性があるため）
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        print("📥 リクエスト送信中...")
        response = requests.get(url, headers=headers, timeout=10)
        print(f"✅ ステータスコード: {response.status_code}")
        print(f"📄 レスポンスサイズ: {len(response.text)} bytes\n")
        
        # HTMLの一部を表示（デバッグ用）
        print("📋 HTMLの先頭500文字:")
        print(response.text[:500])
        print("\n" + "="*80 + "\n")
        
        # BeautifulSoupでパース
        print("🔍 HTMLをパース中...")
        soup = BeautifulSoup(response.text, "html.parser")
        
        # 様々なセレクタを試す
        print("\n📊 セレクタテスト結果:")
        
        # 1. articleタグ
        articles = soup.select("article")
        print(f"  - 'article' セレクタ: {len(articles)}件")
        if articles:
            print(f"    最初の記事のテキスト: {articles[0].text.strip()[:100]}")
        
        # 2. h3タグ（Googleニュースのタイトルはh3に含まれることが多い）
        h3_tags = soup.select("h3")
        print(f"  - 'h3' セレクタ: {len(h3_tags)}件")
        if h3_tags:
            print(f"    最初のh3のテキスト: {h3_tags[0].text.strip()[:100]}")
        
        # 3. aタグ（記事リンク）
        article_links = soup.select("a[href*='/articles/']")
        print(f"  - 'a[href*=\"/articles/\"]' セレクタ: {len(article_links)}件")
        if article_links:
            print(f"    最初のリンクのテキスト: {article_links[0].text.strip()[:100]}")
        
        # 4. クラス名で検索（Googleニュースの構造に依存）
        # Googleニュースは動的にコンテンツを読み込むため、初期HTMLには記事が含まれない可能性がある
        js_articles = soup.find_all(attrs={"jslog": True})
        print(f"  - 'jslog'属性を持つ要素: {len(js_articles)}件")
        
        # 5. データ属性で検索
        data_articles = soup.select("[data-n-tid]")
        print(f"  - '[data-n-tid]' セレクタ: {len(data_articles)}件")
        
        # 6. 実際に取得できる記事を探す
        print("\n📰 取得可能な記事タイトル:")
        results = []
        
        # 複数のセレクタを試す
        selectors = [
            "article h3",
            "article a",
            "h3 a",
            "[role='article'] h3",
            "[role='article'] a"
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            for elem in elements[:5]:  # 最初の5件のみ
                text = elem.text.strip()
                if text and text not in results:
                    results.append(text)
                    print(f"  - {text[:80]}")
        
        print(f"\n✅ 合計 {len(results)}件の記事タイトルを取得")
        
        return results
        
    except requests.exceptions.RequestException as e:
        print(f"❌ リクエストエラー: {e}")
        return []
    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == "__main__":
    test_google_news_scraping("鹿児島 観光")

