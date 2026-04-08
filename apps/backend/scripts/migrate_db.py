import sqlite3

def migrate():
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    
    # 1. Add role column to users if not exists
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN role VARCHAR DEFAULT 'user'")
        print("✅ Added 'role' column to users table")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("ℹ️ 'role' column already exists in users table")
        else:
            print(f"⚠️ Error adding 'role' column: {e}")

    # 1.1 Add is_active column to users if not exists
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT 1")
        print("✅ Added 'is_active' column to users table")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("ℹ️ 'is_active' column already exists in users table")
        else:
            print(f"⚠️ Error adding 'is_active' column: {e}")

    # 2. Add refresh_tokens table if not exists (handled by create_tables.py but good to double check)
    # 3. Add audit_logs table if not exists (handled by create_tables.py)
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    migrate()
