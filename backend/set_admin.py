import sqlite3
import sys

# データベースファイルのパス
db_path = "data/satotrip.db"

# ユーザー名を指定
username = "Admin_user001"

try:
    # データベースに接続
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 現在のユーザー情報を確認
    cursor.execute("SELECT id, username, email, role FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    
    if not user:
        print(f"❌ エラー: ユーザー '{username}' が見つかりません。")
        conn.close()
        sys.exit(1)
    
    print(f"現在のユーザー情報:")
    print(f"  ID: {user[0]}")
    print(f"  ユーザー名: {user[1]}")
    print(f"  メール: {user[2]}")
    print(f"  現在の権限: {user[3]}")
    
    # 既に管理者の場合はスキップ
    if user[3] == "admin":
        print(f"\n✅ ユーザー '{username}' は既に管理者権限を持っています。")
        conn.close()
        sys.exit(0)
    
    # 管理者権限を付与
    cursor.execute("UPDATE users SET role = 'admin' WHERE username = ?", (username,))
    conn.commit()
    
    # 更新後の情報を確認
    cursor.execute("SELECT id, username, email, role FROM users WHERE username = ?", (username,))
    updated_user = cursor.fetchone()
    
    print(f"\n更新後のユーザー情報:")
    print(f"  ID: {updated_user[0]}")
    print(f"  ユーザー名: {updated_user[1]}")
    print(f"  メール: {updated_user[2]}")
    print(f"  新しい権限: {updated_user[3]}")
    print(f"\n✅ ユーザー '{username}' に管理者権限を付与しました。")
    print(f"\n⚠️ 注意: 新しいトークンを取得するには、再度ログインしてください。")
    
    conn.close()
    
except sqlite3.Error as e:
    print(f"❌ データベースエラー: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ エラー: {e}")
    sys.exit(1)

