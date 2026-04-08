import sqlite3

def check_schema():
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()

    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type="table"")
    tables = [t[0] for t in cursor.fetchall()]

    print("Tables in database:")
    for table in tables:
        print(f"  - {table}")

    # Check agents table schema
    print("
Agents table schema:")
    cursor.execute("PRAGMA table_info(agents)")
    columns = cursor.fetchall()
    for col in columns:
        print(f"  - {col[1]} ({col[2]})")

    conn.close()

if __name__ == "__main__":
    check_schema()
