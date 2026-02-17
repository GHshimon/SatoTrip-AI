# test_create_api_key.py
"""
SatoTrip APIを使用してAPIキーを発行するテストスクリプト
管理者権限が必要です
"""
import requests
import json
from datetime import datetime, timedelta

# API設定
API_BASE_URL = "http://localhost:8000"

# 管理者ユーザー情報（管理者権限を持つユーザーでログインする必要があります）
ADMIN_USERNAME = "Admin_user001"  # 管理者ユーザー名に変更してください
ADMIN_PASSWORD = "Teatpass#001"  # 管理者パスワードに変更してください


def login_as_admin():
    """管理者としてログインしてトークンを取得"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/auth/login",
            json={
                "username": ADMIN_USERNAME,
                "password": ADMIN_PASSWORD
            },
            timeout=10
        )
        if response.status_code == 200:
            print("[OK] 管理者ログイン成功")
            return response.json()["access_token"]
        else:
            print(f"[ERROR] ログイン失敗: {response.status_code}")
            print(f"レスポンス: {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] ログインエラー: {e}")
        return None
    except Exception as e:
        print(f"[ERROR] 予期しないエラー: {e}")
        return None


def create_api_key(token, name="テスト用APIキー", user_id=None, 
                   rate_limit_per_minute=10, rate_limit_per_hour=100, 
                   rate_limit_per_day=1000, monthly_plan_limit=100, 
                   expires_at=None):
    """APIキーを作成"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    request_data = {
        "name": name,
        "rate_limit_per_minute": rate_limit_per_minute,
        "rate_limit_per_hour": rate_limit_per_hour,
        "rate_limit_per_day": rate_limit_per_day,
        "monthly_plan_limit": monthly_plan_limit
    }
    
    # user_idが指定されている場合は追加
    if user_id:
        request_data["user_id"] = user_id
    
    # 有効期限が指定されている場合は追加
    if expires_at:
        request_data["expires_at"] = expires_at
    
    print("\n[INFO] APIキー作成リクエストを送信しています...")
    print(f"  名前: {name}")
    print(f"  レート制限: {rate_limit_per_minute}/分, {rate_limit_per_hour}/時, {rate_limit_per_day}/日")
    print(f"  月間プラン生成上限: {monthly_plan_limit}")
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/admin/api-keys",
            headers=headers,
            json=request_data,
            timeout=10
        )
        
        if response.status_code == 201:
            api_key_data = response.json()
            print("\n[OK] APIキー作成成功！")
            print(f"\nAPIキーID: {api_key_data.get('id')}")
            print(f"名前: {api_key_data.get('name')}")
            print(f"所有者ユーザーID: {api_key_data.get('user_id')}")
            print(f"有効: {api_key_data.get('is_active')}")
            print(f"レート制限: {api_key_data.get('rate_limit_per_minute')}/分, "
                  f"{api_key_data.get('rate_limit_per_hour')}/時, "
                  f"{api_key_data.get('rate_limit_per_day')}/日")
            print(f"月間プラン生成上限: {api_key_data.get('monthly_plan_limit')}")
            
            # 重要: APIキーは初回のみ表示されます
            api_key = api_key_data.get('key')
            if api_key:
                print(f"\n{'='*60}")
                print("【重要】APIキー（このキーは初回のみ表示されます）")
                print(f"{'='*60}")
                print(f"{api_key}")
                print(f"{'='*60}")
                print("\nこのキーを test_create_plan.py の API_KEY 変数に設定してください:")
                print(f"API_KEY = \"{api_key}\"")
                print(f"{'='*60}\n")
            else:
                print("\n[WARN] APIキーがレスポンスに含まれていません")
            
            # APIキー情報をJSONファイルに保存
            from pathlib import Path
            script_dir = Path(__file__).parent
            output_file = script_dir / f"api_key_{api_key_data.get('id')}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(api_key_data, f, ensure_ascii=False, indent=2, default=str)
            print(f"[INFO] APIキー情報を {output_file} に保存しました")
            
            return api_key_data
        else:
            print(f"\n[ERROR] APIキー作成失敗: {response.status_code}")
            print(f"レスポンス: {response.text}")
            try:
                error_detail = response.json()
                print(f"エラー詳細: {json.dumps(error_detail, ensure_ascii=False, indent=2)}")
            except:
                pass
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"\n[ERROR] APIキー作成エラー: {e}")
        return None
    except Exception as e:
        print(f"\n[ERROR] 予期しないエラー: {e}")
        return None


def list_api_keys(token):
    """既存のAPIキー一覧を取得"""
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/admin/api-keys",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            keys = data.get('keys', [])
            total = data.get('total', 0)
            print(f"\n[INFO] 既存のAPIキー: {total}件")
            for key in keys:
                print(f"  - {key.get('name')} (ID: {key.get('id')}, 有効: {key.get('is_active')})")
            return keys
        else:
            print(f"[ERROR] APIキー一覧取得失敗: {response.status_code}")
            return []
    except Exception as e:
        print(f"[ERROR] APIキー一覧取得エラー: {e}")
        return []


def main():
    """メイン処理"""
    print("=" * 60)
    print("SatoTrip API テスト: APIキー発行")
    print("=" * 60)
    
    # サーバーのヘルスチェック
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("[OK] サーバーに接続できました")
        else:
            print(f"[WARN] サーバーのヘルスチェックが失敗しました: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] サーバーに接続できません: {e}")
        print(f"  確認事項:")
        print(f"  1. バックエンドサーバーが起動しているか確認してください")
        print(f"  2. API_BASE_URL ({API_BASE_URL}) が正しいか確認してください")
        print(f"  3. サーバーを起動するには: cd backend && python -m uvicorn app.main:app --reload")
        return
    except Exception as e:
        print(f"[ERROR] サーバー接続エラー: {e}")
        return
    
    # 管理者としてログイン
    print("\n[INFO] 管理者としてログインしています...")
    token = login_as_admin()
    if not token:
        print("[ERROR] 管理者ログインに失敗しました")
        print("[INFO] 管理者権限を持つユーザーでログインする必要があります")
        print("[INFO] スクリプト内の ADMIN_USERNAME と ADMIN_PASSWORD を確認してください")
        return
    
    # 既存のAPIキー一覧を表示
    print("\n[INFO] 既存のAPIキーを確認しています...")
    existing_keys = list_api_keys(token)
    
    # 新しいAPIキーを作成
    print("\n[INFO] 新しいAPIキーを作成します...")
    api_key_data = create_api_key(
        token=token,
        name="テスト用APIキー",
        # user_id=None,  # 指定しない場合は現在のユーザー（管理者）が所有者になります
        rate_limit_per_minute=10,
        rate_limit_per_hour=100,
        rate_limit_per_day=1000,
        monthly_plan_limit=100,  # -1で無制限
        # expires_at=None  # 有効期限を設定する場合: (datetime.now() + timedelta(days=30)).isoformat()
    )
    
    if api_key_data:
        print("\n" + "=" * 60)
        print("APIキー発行が完了しました！")
        print("=" * 60)
        print("\n次のステップ:")
        print("1. 上記に表示されたAPIキーをコピーしてください")
        print("2. test_create_plan.py の API_KEY 変数に設定してください")
        print("3. test_create_plan.py を実行してAPIキー認証をテストしてください")
    else:
        print("\n" + "=" * 60)
        print("APIキー発行に失敗しました")
        print("=" * 60)


if __name__ == "__main__":
    main()

