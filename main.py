import os
import requests
import psycopg2
from datetime import datetime

def run_daily_job():
    # --- 1. Fetch Data from API ---
    print("Fetching data...")
    # Example API call
    # api_key = os.environ.get("MY_API_KEY")
    # response = requests.get(f"https://api.example.com/data?key={api_key}")
    # data = response.json()
    
    # Mock data for demonstration
    data = [
        {"name": "Item A", "value": 100},
        {"name": "Item B", "value": 200}
    ]

    # --- 2. Connect to Supabase (PostgreSQL) ---
    print("Connecting to Supabase...")
    db_url = os.environ.get("DB_CONNECTION_STRING")
    
    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()

        # --- 3. Create Table (Only runs once) ---
        # We create a table 'daily_stats' if it doesn't exist yet.
        create_table_query = """
        CREATE TABLE IF NOT EXISTS daily_stats (
            id SERIAL PRIMARY KEY,
            item_name TEXT,
            item_value INTEGER,
            fetched_at TIMESTAMP DEFAULT NOW()
        );
        """
        cur.execute(create_table_query)
        conn.commit()

        # --- 4. Insert Data ---
        print("Inserting data...")
        insert_query = """
        INSERT INTO daily_stats (item_name, item_value, fetched_at)
        VALUES (%s, %s, %s)
        """
        
        current_time = datetime.now()
        
        for item in data:
            cur.execute(insert_query, (item["name"], item["value"], current_time))
        
        conn.commit()
        print(f"Success! Inserted {len(data)} rows.")

        # Close connection
        cur.close()
        conn.close()

    except Exception as e:
        print(f"Error: {e}")
        # Make sure GitHub Actions marks this as a failure so you get an email
        exit(1)

if __name__ == "__main__":
    run_daily_job()