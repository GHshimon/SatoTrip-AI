"""
SQLiteデータベースの内容を確認するスクリプト
"""
import sqlite3
import sys
from pathlib import Path

db_path = Path("data/satotrip.db")

if not db_path.exists():
    print(f"❌ データベースファイルが見つかりません: {db_path}")
    sys.exit(1)

try:
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # テーブル一覧を取得
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    print("=" * 60)
    print("データベース: satotrip.db")
    print("=" * 60)
    print(f"\n📊 テーブル一覧 ({len(tables)}個):")
    for table in tables:
        print(f"  - {table[0]}")
    
    # 各テーブルの内容を表示
    for table_name, in tables:
        print(f"\n{'=' * 60}")
        print(f"テーブル: {table_name}")
        print(f"{'=' * 60}")
        
        # カラム情報を取得
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        print(f"カラム: {', '.join(column_names)}")
        
        # データを取得
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"レコード数: {count}")
        
        if count > 0:
            print(f"\nデータ（最大10件）:")
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 10")
            rows = cursor.fetchall()
            
            # ヘッダーを表示
            print(" | ".join(column_names))
            print("-" * 60)
            
            # データを表示
            for row in rows:
                # 長い文字列は切り詰め
                display_row = []
                for i, val in enumerate(row):
                    if val is None:
                        display_val = "NULL"
                    elif isinstance(val, str) and len(val) > 30:
                        display_val = val[:27] + "..."
                    else:
                        display_val = str(val)
                    display_row.append(display_val)
                print(" | ".join(display_row))
            
            if count > 10:
                print(f"\n... 他 {count - 10} 件")
    
    conn.close()
    print(f"\n{'=' * 60}")
    print("✅ 確認完了")
    
except sqlite3.Error as e:
    print(f"❌ データベースエラー: {e}")
    sys.exit(1)

