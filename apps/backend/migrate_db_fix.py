import sqlite3

def migrate_database():
    db_path = "app.db"

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(agents)")
        columns = [column[1] for column in cursor.fetchall()]

        print("Current columns in agents table:")
        for col in columns:
            print(f"  - {col}")

        new_columns = {
            "created_at": "DATETIME DEFAULT CURRENT_TIMESTAMP",
            "updated_at": "DATETIME DEFAULT CURRENT_TIMESTAMP",
            "role": "VARCHAR",
            "skills": "JSON"
        }

        for column_name, column_type in new_columns.items():
            if column_name not in columns:
                print(f"
Adding column: {column_name}")
                cursor.execute(f"ALTER TABLE agents ADD COLUMN {column_name} {column_type}")
                print(f"Column {column_name} added successfully")
            else:
                print(f"
Column {column_name} already exists, skipping")

        conn.commit()

        print("

Updated columns in agents table:")
        cursor.execute("PRAGMA table_info(agents)")
        columns = [column[1] for column in cursor.fetchall()]
        for col in columns:
            print(f"  - {col}")

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
