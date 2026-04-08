
"""
Database migration script to fix workspaces table
"""
import sqlite3

def migrate_workspaces():
    db_path = "app.db"

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(workspaces)")
        columns = [column[1] for column in cursor.fetchall()]

        print("Current columns in workspaces table:")
        for col in columns:
            print(f"  - {col}")

        if "type" not in columns:
            print("Adding column: type")
            cursor.execute("ALTER TABLE workspaces ADD COLUMN type VARCHAR")
            print("Column type added successfully")
        else:
            print("Column type already exists, skipping")

        conn.commit()

        print("Updated columns in workspaces table:")
        cursor.execute("PRAGMA table_info(workspaces)")
        columns = [column[1] for column in cursor.fetchall()]
        for col in columns:
            print(f"  - {col}")

        print("Migration completed successfully!")

    except Exception as e:
        print(f"Migration failed: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    migrate_workspaces()
