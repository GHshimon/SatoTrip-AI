import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), "data", "satotrip.db")
print(f"Connecting to database at {db_path}")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if columns exist
    cursor.execute("PRAGMA table_info(plans)")
    columns = [info[1] for info in cursor.fetchall()]
    
    if "check_in_date" not in columns:
        print("Adding check_in_date column...")
        cursor.execute("ALTER TABLE plans ADD COLUMN check_in_date TEXT")
        conn.commit()
        print("Column check_in_date added successfully.")
    else:
        print("Column check_in_date already exists.")
    
    if "check_out_date" not in columns:
        print("Adding check_out_date column...")
        cursor.execute("ALTER TABLE plans ADD COLUMN check_out_date TEXT")
        conn.commit()
        print("Column check_out_date added successfully.")
    else:
        print("Column check_out_date already exists.")
        
    conn.close()
    print("Migration completed successfully.")
except Exception as e:
    print(f"Error: {e}")

