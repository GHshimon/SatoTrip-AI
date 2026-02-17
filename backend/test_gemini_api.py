# test_gemini_api.py
import os
import time
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai

# スクリプトのディレクトリ（backend）を取得
script_dir = Path(__file__).parent
env_path = script_dir / ".env"

# .envファイルの存在確認
if not env_path.exists():
    print(f"[ERROR] .envファイルが見つかりません: {env_path}")
    print("   backendディレクトリに.envファイルを作成し、GEMINI_API_KEYを設定してください")
    print("   例: GEMINI_API_KEY=your-api-key-here")
    exit(1)

# .envファイルを読み込み（OSの環境変数は上書きしない）
load_dotenv(dotenv_path=env_path, override=False)

# APIキーを取得（.envファイルから読み込まれた値）
api_key_raw = os.getenv("GEMINI_API_KEY")

if not api_key_raw:
    print(f"[ERROR] GEMINI_API_KEYが設定されていません")
    print(f"   .envファイル ({env_path}) にGEMINI_API_KEYを設定してください")
    print("   例: GEMINI_API_KEY=your-api-key-here")
    exit(1)

# 前後の空白や改行を削除
api_key = api_key_raw.strip()

# デバッグ情報を出力
print(f"[DEBUG] APIキーの生データ（先頭10文字）: {repr(api_key_raw[:10])}")
print(f"[DEBUG] APIキーの生データ（末尾10文字）: {repr(api_key_raw[-10:])}")
print(f"[DEBUG] APIキーの生データの長さ: {len(api_key_raw)}文字")
print(f"[DEBUG] トリム後の長さ: {len(api_key)}文字")
print(f"[DEBUG] 先頭文字: {repr(api_key[:1])}")
print(f"[DEBUG] 末尾文字: {repr(api_key[-1:])}")

# APIキーの形式チェック
if not api_key.startswith("AIza"):
    print(f"[WARN] APIキーの形式が正しくない可能性があります")
    print(f"   通常、Gemini APIキーは 'AIza' で始まります")
    print(f"   現在の先頭: {repr(api_key[:4])}")

print(f"[OK] APIキーが設定されています（先頭: {api_key[:10]}...）")
print(f"   キーの長さ: {len(api_key)}文字\n")

# Gemini APIを設定
try:
    genai.configure(api_key=api_key)
    print("[OK] genai.configure() 成功\n")
except Exception as e:
    print(f"[ERROR] genai.configure() 失敗: {e}")
    exit(1)

# エクスポネンシャルバックオフによるリトライ処理
def retry_with_backoff(api_call, max_retries=3, model_name=""):
    """
    エクスポネンシャルバックオフを使用してAPI呼び出しをリトライする
    
    Args:
        api_call: 実行するAPI呼び出し関数（引数なし）
        max_retries: 最大リトライ回数（デフォルト: 3）
        model_name: モデル名（ログ出力用）
    
    Returns:
        API呼び出しの結果、またはNone（全リトライ失敗時）
    """
    for i in range(max_retries):
        try:
            return api_call()
        except Exception as e:
            error_msg = str(e)
            is_rate_limit = "429" in error_msg or "quota" in error_msg.lower() or "rate limit" in error_msg.lower()
            
            # 429エラーで、まだリトライ可能な場合
            if is_rate_limit and i < max_retries - 1:
                wait_time = (2 ** i)  # 1秒、2秒、4秒...
                print(f"  [RETRY] {model_name} レート制限エラー検出（{i+1}回目）")
                print(f"      {wait_time}秒待機してからリトライします...")
                time.sleep(wait_time)
                continue
            else:
                # 429エラー以外、または最後のリトライでも失敗した場合
                raise e
    
    return None

# モデル一覧を取得して確認
print("[INFO] 利用可能なモデルを確認中...")
try:
    def get_models():
        return genai.list_models()
    
    models = retry_with_backoff(get_models, max_retries=3, model_name="モデル一覧取得")
    available_models = []
    for model in models:
        if 'generateContent' in model.supported_generation_methods:
            available_models.append(model.name)
    
    print(f"[OK] {len(available_models)}個のモデルが見つかりました\n")
    
    # gemini-2.0-flashが利用可能か確認
    gemini_2_0_flash_available = any('gemini-2.0-flash' in m for m in available_models)
    gemini_1_5_pro_available = any('gemini-1.5-pro' in m for m in available_models)
    gemini_pro_available = any('gemini-pro' in m for m in available_models)
    
    print("利用可能なモデル:")
    if gemini_2_0_flash_available:
        print("  [OK] gemini-2.0-flash")
    else:
        print("  [NG] gemini-2.0-flash (利用不可)")
    
    if gemini_1_5_pro_available:
        print("  [OK] gemini-1.5-pro")
    else:
        print("  [NG] gemini-1.5-pro (利用不可)")
    
    if gemini_pro_available:
        print("  [OK] gemini-pro")
    else:
        print("  [NG] gemini-pro (利用不可)")
    
    print()
    
except Exception as e:
    error_msg = str(e)
    print(f"[WARN] モデル一覧の取得に失敗")
    
    if "400" in error_msg and ("api key" in error_msg.lower() or "api_key" in error_msg.lower() or "invalid" in error_msg.lower()):
        print(f"   原因: APIキーが無効です")
        print(f"   考えられる原因:")
        print(f"   1. APIキーが間違っている、または削除された")
        print(f"   2. APIキーに余分な空白や改行が含まれている")
        print(f"   3. Gemini APIが有効化されていない")
        print(f"   4. APIキーにIP制限やHTTPリファラー制限が設定されている")
        print(f"   確認: https://aistudio.google.com/app/apikey")
    elif "429" in error_msg or "quota" in error_msg.lower() or "rate limit" in error_msg.lower():
        print(f"   原因: レート制限/クォータエラー（連続的な使用による制限）")
        print(f"   しばらく待ってから再試行してください")
    elif "403" in error_msg or "permission" in error_msg.lower():
        print(f"   原因: 権限エラー")
        print(f"   Google Cloud ConsoleでGemini APIが有効化されているか確認してください")
    else:
        print(f"   エラー詳細: {error_msg[:200]}")
    
    print("   直接API呼び出しを試行します...\n")

# 実際にAPIを呼び出してテスト
test_models = [
    "gemini-2.0-flash",
    "gemini-1.5-pro",
    "gemini-pro"
]

# リクエスト間の基本遅延時間（秒）
REQUEST_DELAY = 1.0

for idx, model_name in enumerate(test_models):
    # 最初のリクエスト以外は遅延を追加（連続リクエストを避ける）
    if idx > 0:
        print(f"[INFO] 連続リクエストを避けるため、{REQUEST_DELAY}秒待機します...")
        time.sleep(REQUEST_DELAY)
    
    print(f"[TEST] {model_name} をテスト中...")
    try:
        # エクスポネンシャルバックオフでリトライ処理を実装
        def test_model():
            model = genai.GenerativeModel(model_name)
            return model.generate_content("こんにちは。1+1は？")
        
        response = retry_with_backoff(test_model, max_retries=3, model_name=model_name)
        
        if response and response.text:
            print(f"  [OK] {model_name} 成功")
            print(f"     レスポンス: {response.text[:50]}...")
        else:
            print(f"  [WARN] {model_name} レスポンスが空です")
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "quota" in error_msg.lower() or "rate limit" in error_msg.lower():
            print(f"  [WARN] {model_name} レート制限/クォータエラー")
            print(f"      APIキーは有効ですが、連続的な使用により制限に達しています")
            print(f"      しばらく待ってから再試行してください")
        elif "403" in error_msg or "permission" in error_msg.lower() or "forbidden" in error_msg.lower():
            print(f"  [ERROR] {model_name} 権限エラー")
            print(f"      APIキーに必要な権限がありません")
            print(f"      Google Cloud ConsoleでGemini APIが有効化されているか確認してください")
        elif "400" in error_msg and ("api key" in error_msg.lower() or "api_key" in error_msg.lower() or "invalid" in error_msg.lower()):
            print(f"  [ERROR] {model_name} APIキーが無効です")
            print(f"      考えられる原因:")
            print(f"      1. APIキーが間違っている、または削除された")
            print(f"      2. APIキーに余分な空白や改行が含まれている")
            print(f"      3. Gemini APIが有効化されていない")
            print(f"      4. APIキーにIP制限やHTTPリファラー制限が設定されている")
            print(f"      確認: https://aistudio.google.com/app/apikey")
        elif "404" in error_msg or "not found" in error_msg.lower():
            print(f"  [ERROR] {model_name} モデルが見つかりません（このAPIキーでは利用できません）")
        else:
            print(f"  [ERROR] {model_name} エラー: {error_msg[:200]}")
    print()

print("[OK] テスト完了")

