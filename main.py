import os
import requests
import psycopg2
from datetime import datetime

def get_api_intervals(date_range_tuple):
    if not date_range_tuple or len(date_range_tuple) != 2:
        return None, None

    start_date, end_date = date_range_tuple
    now = datetime.now()

    if isinstance(start_date, datetime.date) and not isinstance(start_date, datetime):
        start_date = datetime.combine(start_date, datetime.time.min)
    if isinstance(end_date, datetime.date) and not isinstance(end_date, datetime):
        end_date = datetime.combine(end_date, datetime.time.max)

    start_seconds = int((now - start_date).total_seconds())
    stop_seconds = int((now - end_date).total_seconds())

    return max(0, start_seconds), max(0, stop_seconds)

def run_daily_job():
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)

    # 3. Pass "yesterday" as both start and end
    # Your function handles 'dt.date' inputs by automatically setting:
    # Start -> 00:00:00
    # End   -> 23:59:59.999999
    start_interval, end_interval = get_api_intervals((yesterday, yesterday))

    print(f"Current System Date: {today}")
    print(f"Fetching data for:   {yesterday}")
    print(f"Interval Range (Seconds Ago): {start_interval} (Start) to {end_interval} (End)")

    print("Fetching data...")

    api_headers = {
        "X-User-id":  os.environ.get("USER_ID"),
        "X-User-hash": os.environ.get("USER_HASH")               
    }

    # api_url = f"{API_URL}/1600013B/all/920914/834514"
    # https://data.uradmonitor.com/api/v1/devices/1600013B/all/920914/834514
    # response = requests.get(api_url, headers=api_headers, timeout=3)

    api_url = f"http://data.uradmonitor.com/api/v1/devices/1600013B/all/{start_interval}/{end_interval}"
    # Example API call
    # api_key = os.environ.get("MY_API_KEY")
    # response = requests.get(f"https://api.example.com/data?key={api_key}")
    # data = response.json()

    response = requests.get(api_url, headers=api_headers, timeout=3)
    api_data = response.json() 

    if isinstance(api_data, list) and len(api_data) > 0 and isinstance(api_data[0], list):
        data_to_insert = api_data[0]
    else:
        data_to_insert = api_data

    print("Connecting to Supabase...")
    db_url = os.environ.get("DB_CONNECTION_STRING")
    
    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()

        # --- 3. Create Table ---
        # FIX 2: Changed latitude/longitude to REAL to preserve decimals
        # FIX 3: Renamed columns to match API keys strictly (optional, but cleaner)
        create_table_query = """
        CREATE TABLE IF NOT EXISTS daily_stats_data (
            id SERIAL PRIMARY KEY,
            time INTEGER,
            latitude REAL,
            longitude REAL,
            altitude INTEGER,
            timelocal INTEGER,
            temperature REAL,
            humidity REAL,
            pressure REAL,
            pm1 REAL,
            pm25 REAL,
            pm10 REAL,
            fetched_at TIMESTAMP DEFAULT NOW()
        );
        """
        cur.execute(create_table_query)
        conn.commit()

        print("Inserting data...")
        
        insert_query = """
        INSERT INTO daily_stats_data (time, latitude, longitude, altitude, timelocal, temperature, humidity, pressure, pm1, pm25, pm10, fetched_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        current_time = datetime.now()

        for item in data_to_insert:
            cur.execute(insert_query, (
                item["time"],
                item["latitude"],
                item["longitude"],
                item["altitude"],
                item["timelocal"],   
                item["temperature"],
                item["humidity"],
                item["pressure"],
                item["pm1"],
                item["pm25"],       
                item["pm10"],
                current_time
            ))

        conn.commit()
        print(f"Success! Inserted {len(data_to_insert)} rows.")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"Error: {e}")
        raise e

if __name__ == "__main__":
    run_daily_job()