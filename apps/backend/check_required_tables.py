
import sqlite3

def check_schema():
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [t[0] for t in cursor.fetchall()]

    print("Tables in database:")
    for table in tables:
        print(f"  - {table}")

    # Check specific tables we need
    required_tables = [
        'agents',
        'marketplace_listings',
        'marketplace_agents',
        'digital_twin_profiles',
        'referrals',
        'announcements',
        'community_posts',
        'user_stats',
        'workspaces'
    ]

    print("\nRequired tables status:")
    for table in required_tables:
        status = "EXISTS" if table in tables else "MISSING"
        print(f"  - {table}: {status}")

    conn.close()

if __name__ == "__main__":
    check_schema()
