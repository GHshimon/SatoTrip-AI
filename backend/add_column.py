import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), "data", "satotrip.db")
print(f"Connecting to database at {db_path}")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if column exists
    cursor.execute("PRAGMA table_info(plans)")
    columns = [info[1] for info in cursor.fetchall()]
    
    if "is_favorite" not in columns:
        print("Adding is_favorite column...")
        cursor.execute("ALTER TABLE plans ADD COLUMN is_favorite BOOLEAN DEFAULT 0")
        conn.commit()
        print("Column added successfully.")
    else:
        print("Column is_favorite already exists.")
        
    conn.close()
except Exception as e:
    print(f"Error: {e}")
