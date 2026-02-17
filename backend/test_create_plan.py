# test_create_plan.py
"""
SatoTrip APIを使用して鹿児島旅行の1泊2日プランを作成するテストスクリプト
APIキー認証とユーザー認証の両方をサポート
"""
import requests
import json
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

# API設定
API_BASE_URL = "http://localhost:8000"

# テスト用ユーザー情報（既存のユーザーを使用するか、新規登録）
TEST_USERNAME = "Admin_user001"#"test_user"
TEST_PASSWORD = "Teatpass#001"#"TestPassword123!"  # パスワード強度要件: 大文字、小文字、数字、記号を含む
TEST_EMAIL = "test@example.com"
TEST_NAME = "Admin_ds001"#"テストユーザー"

# APIキー認証を使用する場合は、ここにAPIキーを設定
# 管理者がAPIキーを作成した後、そのキーをここに設定してください
API_KEY = None  # 例: "st_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"


def register_or_login():
    """ユーザー登録またはログインしてトークンを取得"""
    # まずログインを試みる
    try:
        response = requests.post(
            f"{API_BASE_URL}/auth/login",
            json={
                "username": TEST_USERNAME,
                "password": TEST_PASSWORD
            },
            timeout=10
        )
        if response.status_code == 200:
            print("[OK] ログイン成功")
            return response.json()["access_token"]
    except requests.exceptions.RequestException as e:
        print(f"[INFO] ログイン失敗（ユーザーが存在しない可能性）: {e}")
    except Exception as e:
        print(f"[INFO] ログイン失敗: {e}")
    
    # ログインに失敗した場合は新規登録
    try:
        print("[INFO] 新規ユーザーを登録します...")
        response = requests.post(
            f"{API_BASE_URL}/auth/register",
            json={
                "username": TEST_USERNAME,
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD,
                "name": TEST_NAME
            },
            timeout=10
        )
        if response.status_code == 201:
            print("[OK] ユーザー登録成功")
            return response.json()["access_token"]
        else:
            print(f"[ERROR] ユーザー登録失敗: {response.status_code}")
            print(f"レスポンス: {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] ユーザー登録エラー: {e}")
        return None
    except Exception as e:
        print(f"[ERROR] ユーザー登録エラー: {e}")
        return None


def check_user_is_admin(token):
    """現在のユーザーが管理者かどうかを確認"""
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/users/me",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            user_data = response.json()
            role = user_data.get("role", "user")
            is_admin = role == "admin"
            
            if is_admin:
                print(f"[INFO] 管理者権限を確認しました（ユーザー: {user_data.get('username')}）")
            else:
                print(f"[INFO] 一般ユーザーです（ユーザー: {user_data.get('username')}, ロール: {role}）")
            
            return is_admin
        else:
            print(f"[WARN] ユーザー情報取得失敗: {response.status_code}")
            print(f"レスポンス: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] ユーザー情報取得エラー: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] 予期しないエラー: {e}")
        return False


def create_api_key(token, name="テスト用APIキー（自動生成）", user_id=None, 
                   rate_limit_per_minute=10, rate_limit_per_hour=100, 
                   rate_limit_per_day=1000, monthly_plan_limit=100, 
                   expires_at=None):
    """APIキーを作成（管理者のみ）"""
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
            print(f"  APIキーID: {api_key_data.get('id')}")
            print(f"  名前: {api_key_data.get('name')}")
            
            # 重要: APIキーは初回のみ表示されます
            api_key = api_key_data.get('key')
            if api_key:
                print(f"  [INFO] APIキーを取得しました（このキーは実行時のみ有効です）")
                return api_key
            else:
                print("\n[WARN] APIキーがレスポンスに含まれていません")
                return None
        else:
            print(f"\n[ERROR] APIキー作成失敗: {response.status_code}")
            print(f"レスポンス: {response.text}")
            try:
                error_detail = response.json()
                if response.status_code == 403:
                    print("[INFO] 管理者権限が必要です。一般ユーザーの場合は、ユーザー認証（トークン）を使用します。")
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


def check_time_schedule_consistency(plan):
    """
    タイムスケジュールの整合性をチェック
    空白の時間帯がないことを確認
    """
    spots = plan.get('spots', [])
    if not spots:
        return True, "スポットがありません"
    
    # 日ごとにグループ化
    spots_by_day = defaultdict(list)
    for spot in spots:
        day = spot.get('day', 1)
        spots_by_day[day].append(spot)
    
    issues = []
    
    for day in sorted(spots_by_day.keys()):
        day_spots = spots_by_day[day]
        
        # startTimeでソート
        day_spots_sorted = sorted(day_spots, key=lambda x: x.get('startTime', '00:00'))
        
        for i in range(len(day_spots_sorted) - 1):
            current_spot = day_spots_sorted[i]
            next_spot = day_spots_sorted[i + 1]
            
            # 現在のスポットの終了時刻を計算
            start_time_str = current_spot.get('startTime', '00:00')
            start_hour, start_minute = map(int, start_time_str.split(':'))
            start_minutes = start_hour * 60 + start_minute
            
            # 滞在時間を取得
            duration_minutes = 60
            spot_info = current_spot.get('spot', {})
            if isinstance(spot_info, dict):
                duration_minutes = spot_info.get('durationMinutes', 60)
            elif 'durationMinutes' in current_spot:
                duration_minutes = current_spot['durationMinutes']
            
            # 終了時刻を計算
            end_minutes = start_minutes + duration_minutes
            
            # 移動時間を取得
            transport_duration = current_spot.get('transportDuration', 20)
            
            # 次のスポットの開始時刻を計算（終了時刻 + 移動時間）
            next_start_minutes = end_minutes + transport_duration
            
            # 次のスポットの実際の開始時刻を取得
            next_start_time_str = next_spot.get('startTime', '00:00')
            next_start_hour, next_start_minute = map(int, next_start_time_str.split(':'))
            next_start_minutes_actual = next_start_hour * 60 + next_start_minute
            
            # 空白の時間帯をチェック
            if next_start_minutes_actual > next_start_minutes:
                gap_minutes = next_start_minutes_actual - next_start_minutes
                gap_hours = gap_minutes // 60
                gap_mins = gap_minutes % 60
                current_name = spot_info.get('name', '不明') if isinstance(spot_info, dict) else '不明'
                next_name = next_spot.get('spot', {}).get('name', '不明') if isinstance(next_spot.get('spot'), dict) else '不明'
                issues.append(
                    f"【{day}日目】{current_name} → {next_name}: "
                    f"{gap_hours}時間{gap_mins}分の空白があります "
                    f"(期待: {next_start_minutes // 60:02d}:{next_start_minutes % 60:02d}, "
                    f"実際: {next_start_time_str})"
                )
            elif next_start_minutes_actual < next_start_minutes:
                overlap_minutes = next_start_minutes - next_start_minutes_actual
                overlap_hours = overlap_minutes // 60
                overlap_mins = overlap_minutes % 60
                current_name = spot_info.get('name', '不明') if isinstance(spot_info, dict) else '不明'
                next_name = next_spot.get('spot', {}).get('name', '不明') if isinstance(next_spot.get('spot'), dict) else '不明'
                issues.append(
                    f"【{day}日目】{current_name} → {next_name}: "
                    f"{overlap_hours}時間{overlap_mins}分の重複があります "
                    f"(期待: {next_start_minutes // 60:02d}:{next_start_minutes % 60:02d}, "
                    f"実際: {next_start_time_str})"
                )
    
    if issues:
        return False, "\n".join(issues)
    else:
        return True, "タイムスケジュールに問題はありません"


def create_kagoshima_plan(token=None, api_key=None):
    """鹿児島旅行の1泊2日プランを作成"""
    headers = {
        "Content-Type": "application/json"
    }
    
    # 認証ヘッダーを設定
    if api_key:
        headers["X-API-Key"] = api_key
        endpoint = f"{API_BASE_URL}/api/v1/ai/generate-plan"
    elif token:
        headers["Authorization"] = f"Bearer {token}"
        endpoint = f"{API_BASE_URL}/api/plans/generate-plan"
    else:
        print("[ERROR] 認証情報が提供されていません（tokenまたはapi_keyが必要）")
        return None
    
    # 明日をチェックイン日、明後日をチェックアウト日として設定
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    day_after_tomorrow = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
    
    request_data = {
        "destination": "鹿児島県",
        "days": 2,
        "budget": "50000",
        "themes": ["観光", "グルメ", "温泉"],
        "pending_spots": [],  # 特定のスポットを指定しない場合は空配列
        "preferences": "桜島の眺めが良い場所や、鹿児島の名物を楽しみたい",
        "start_time": "09:00",
        "end_time": "20:00",
        "transportation": "車",
        "check_in_date": tomorrow,
        "check_out_date": day_after_tomorrow,
        "num_guests": 2
    }
    
    print("\n[INFO] プラン生成リクエストを送信しています...")
    print(f"  目的地: {request_data['destination']}")
    print(f"  日数: {request_data['days']}泊{request_data['days']+1}日")
    print(f"  予算: {request_data['budget']}円")
    print(f"  テーマ: {', '.join(request_data['themes'])}")
    print(f"  チェックイン: {request_data['check_in_date']}")
    print(f"  チェックアウト: {request_data['check_out_date']}")
    
    try:
        response = requests.post(
            endpoint,
            headers=headers,
            json=request_data,
            timeout=120  # プラン生成には時間がかかる可能性があるため120秒
        )
        
        if response.status_code == 201:
            plan = response.json()
            print("\n[OK] プラン生成成功！")
            print(f"\nプランID: {plan.get('id')}")
            print(f"タイトル: {plan.get('title')}")
            print(f"エリア: {plan.get('area')}")
            print(f"日数: {plan.get('days')}日")
            print(f"予算: {plan.get('budget')}円")
            
            # スポット情報を表示
            spots = plan.get('spots', [])
            print(f"\nスポット数: {len(spots)}件")
            
            # 日ごとにスポットをグループ化
            spots_by_day = defaultdict(list)
            for spot in spots:
                day = spot.get('day', 1)
                spots_by_day[day].append(spot)
            
            for day in sorted(spots_by_day.keys()):
                day_spots = spots_by_day[day]
                print(f"\n【{day}日目】")
                for i, spot in enumerate(day_spots, 1):
                    spot_info = spot.get('spot', {})
                    name = spot_info.get('name', '不明')
                    start_time = spot.get('startTime', '未設定')
                    category = spot_info.get('category', '不明')
                    note = spot.get('note', '')
                    
                    print(f"  {i}. {start_time} - {name} ({category})")
                    if note:
                        print(f"     備考: {note}")
            
            # 除外されたスポットがある場合
            excluded_spots = plan.get('excluded_spots')
            if excluded_spots:
                print(f"\n[INFO] 除外されたスポット: {len(excluded_spots)}件")
                for excluded in excluded_spots:
                    print(f"  - {excluded.get('name', '不明')}: {excluded.get('reason', '')}")
            
            # タイムスケジュールの整合性をチェック
            print("\n[INFO] タイムスケジュールの整合性をチェックしています...")
            is_consistent, message = check_time_schedule_consistency(plan)
            if is_consistent:
                print(f"[OK] {message}")
            else:
                print(f"[ERROR] タイムスケジュールに問題があります:")
                print(message)
            
            # プランデータをJSONファイルに保存
            script_dir = Path(__file__).parent
            output_file = script_dir / f"kagoshima_plan_{plan.get('id')}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(plan, f, ensure_ascii=False, indent=2, default=str)
            print(f"\n[INFO] プランデータを {output_file} に保存しました")
            
            return plan
        else:
            print(f"\n[ERROR] プラン生成失敗: {response.status_code}")
            print(f"レスポンス: {response.text}")
            try:
                error_detail = response.json()
                print(f"エラー詳細: {json.dumps(error_detail, ensure_ascii=False, indent=2)}")
            except:
                pass
            return None
            
    except requests.exceptions.Timeout:
        print("\n[ERROR] リクエストがタイムアウトしました（120秒）")
        print("  プラン生成には時間がかかることがあります。しばらく待ってから再試行してください。")
        return None
    except requests.exceptions.RequestException as e:
        print(f"\n[ERROR] プラン生成エラー: {e}")
        return None
    except Exception as e:
        print(f"\n[ERROR] 予期しないエラー: {e}")
        return None


def main():
    """メイン処理"""
    print("=" * 60)
    print("SatoTrip API テスト: 鹿児島旅行プラン作成")
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
    
    # 認証
    token = None
    api_key = API_KEY
    
    if api_key:
        print("\n[INFO] APIキー認証を使用します")
    else:
        print("\n[INFO] APIキーが未設定のため、認証方式を決定します...")
        token = register_or_login()
        if not token:
            print("[ERROR] 認証に失敗しました")
            print("[INFO] APIキー認証を使用する場合は、スクリプト内のAPI_KEY変数を設定してください")
            return
        
        # 管理者権限を確認
        is_admin = check_user_is_admin(token)
        
        if is_admin:
            # 管理者の場合: APIキーを自動作成
            print("\n[INFO] 管理者権限を確認しました。APIキーを自動作成します...")
            created_api_key = create_api_key(token)
            
            if created_api_key:
                api_key = created_api_key
                print("[INFO] 作成したAPIキーを使用してプラン生成を行います")
            else:
                # APIキー作成に失敗した場合は、トークン認証にフォールバック
                print("[WARN] APIキー作成に失敗しました。ユーザー認証（トークン）を使用します...")
                # tokenは既に設定されているので、そのまま使用
        else:
            # 一般ユーザーの場合: トークン認証を使用
            print("\n[INFO] 一般ユーザーのため、ユーザー認証（トークン）を使用します...")
            # tokenは既に設定されているので、そのまま使用
    
    # プラン作成
    plan = create_kagoshima_plan(token=token, api_key=api_key)
    
    if plan:
        print("\n" + "=" * 60)
        print("プラン作成が完了しました！")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("プラン作成に失敗しました")
        print("=" * 60)


if __name__ == "__main__":
    main()

