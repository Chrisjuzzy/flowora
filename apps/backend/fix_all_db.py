
import sqlite3
from datetime import datetime

def migrate_database():
    db_path = "app.db"

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        print("Checking database schema...")

        # Get current columns
        cursor.execute("PRAGMA table_info(agents)")
        existing_columns = [column[1] for column in cursor.fetchall()]

        print("Current columns in agents table:")
        for col in existing_columns:
            print(f"  - {col}")

        # Define required columns
        required_columns = {
            "created_at": "DATETIME DEFAULT CURRENT_TIMESTAMP",
            "updated_at": "DATETIME DEFAULT CURRENT_TIMESTAMP",
            "role": "VARCHAR",
            "skills": "JSON"
        }

        # Add missing columns
        for column_name, column_type in required_columns.items():
            if column_name not in existing_columns:
                print(f"Adding column: {column_name}")
                try:
                    cursor.execute(f"ALTER TABLE agents ADD COLUMN {column_name} {column_type}")
                    print(f"  Column {column_name} added successfully")
                except Exception as e:
                    print(f"  Error adding {column_name}: {e}")
            else:
                print(f"Column {column_name} already exists")

        # Verify the changes
        print("
Verifying updated schema...")
        cursor.execute("PRAGMA table_info(agents)")
        columns = [column[1] for column in cursor.fetchall()]

        print("Updated columns in agents table:")
        for col in columns:
            print(f"  - {col}")

        # Check if all required columns exist
        missing = [col for col in required_columns.keys() if col not in columns]
        if missing:
            print(f"
Missing columns: {missing}")
        else:
            print("
All required columns are present!")

        conn.commit()
        print("
Migration completed successfully!")

    except Exception as e:
        print(f"
Migration failed: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    migrate_database()
