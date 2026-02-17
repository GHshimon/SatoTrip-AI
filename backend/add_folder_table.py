import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), "data", "satotrip.db")
print(f"Connecting to database at {db_path}")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON")

    # Create plan_folders table
    print("Creating plan_folders table...")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS plan_folders (
        id VARCHAR PRIMARY KEY,
        user_id VARCHAR NOT NULL,
        name VARCHAR NOT NULL,
        parent_id VARCHAR,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (parent_id) REFERENCES plan_folders(id)
    )
    """)
    
    # Create index on user_id
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_plan_folders_user_id ON plan_folders (user_id)")
    
    print("Table plan_folders created/verified.")

    # Check if folder_id column exists in plans
    cursor.execute("PRAGMA table_info(plans)")
    columns = [info[1] for info in cursor.fetchall()]
    
    if "folder_id" not in columns:
        print("Adding folder_id column to plans...")
        cursor.execute("ALTER TABLE plans ADD COLUMN folder_id VARCHAR REFERENCES plan_folders(id)")
        print("Column folder_id added successfully.")
    else:
        print("Column folder_id already exists in plans.")
        
    conn.commit()
    conn.close()
    print("Migration completed successfully.")
except Exception as e:
    print(f"Error: {e}")
