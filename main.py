import os
import requests
import psycopg2
import datetime 
import statistics

def get_api_intervals(date_range_tuple):
    if not date_range_tuple or len(date_range_tuple) != 2:
        return None, None

    start_date, end_date = date_range_tuple
    
    now = datetime.datetime.now() 

    if isinstance(start_date, datetime.date) and not isinstance(start_date, datetime.datetime):
        start_date = datetime.datetime.combine(start_date, datetime.time.min)
        
    if isinstance(end_date, datetime.date) and not isinstance(end_date, datetime.datetime):
        end_date = datetime.datetime.combine(end_date, datetime.time.max)

    start_seconds = int((now - start_date).total_seconds())
    stop_seconds = int((now - end_date).total_seconds())

    return max(0, start_seconds), max(0, stop_seconds)

def init_db_table(cursor):
    create_table_query = """
        CREATE TABLE IF NOT EXISTS daily_averages (
            id SERIAL PRIMARY KEY,
            sensor_id TEXT NOT NULL,
            measurement_date DATE NOT NULL,
            temperature REAL,
            humidity REAL,
            pressure REAL,
            pm25 REAL,
            data_date DATE DEFAULT CURRENT_DATE,
            fetched_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(sensor_id, measurement_date)
        );
    """
    cursor.execute(create_table_query)


def insert_average(cursor, sensor_id, avg_data, date_obj):
    insert_query = """
        INSERT INTO daily_averages (sensor_id, temperature, humidity, pressure, pm25, fetched_at)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    
    cursor.execute(insert_query, (
        sensor_id,
        date_obj,
        avg_data['temperature'],
        avg_data['humidity'],
        avg_data['pressure'],
        avg_data['pm25'],
        datetime.datetime.now()
    ))
    print(f" -> Inserted averages for {sensor_id}")


def calculate_averages(data):
    """
    Iterates through the list of sensor data points and calculates the mean
    for temperature, humidity, pressure, and pm25.
    """
    if not data or len(data) == 0:
        return None

    temps, hums, press, pm25s = [], [], [], []

    for item in data:
        try:
            if 'temperature' in item: temps.append(float(item['temperature']))
            if 'humidity' in item:    hums.append(float(item['humidity']))
            if 'pressure' in item:    press.append(float(item['pressure']))
            if 'pm25' in item:        pm25s.append(float(item['pm25']))
        except (ValueError, TypeError):
            continue 

    if not temps: 
        return None

    return {
        "temperature": statistics.mean(temps) if temps else 0,
        "humidity": statistics.mean(hums) if hums else 0,
        "pressure": statistics.mean(press) if press else 0,
        "pm25": statistics.mean(pm25s) if pm25s else 0
    }


def run_daily_job():
    print("Connecting to Supabase...")
    db_url = os.environ.get("DB_CONNECTION_STRING")
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)

    start_interval, end_interval = get_api_intervals((yesterday, yesterday))

    print(f"Current System Date: {today}")
    print(f"Fetching data for:   {yesterday}")
    print(f"Interval Range (Seconds Ago): {start_interval} (Start) to {end_interval} (End)")

    print("Fetching data...")

    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
            
        init_db_table(cur)
        conn.commit()

        api_headers = {
            "X-User-id":  os.environ.get("USER_ID"),
            "X-User-hash": os.environ.get("USER_HASH")               
        }

        sensors_ids = ["1600013B", "1600019F", "16000284", "16000224", "16000341", "16000342", "16000343", "16000344", "8200029B"]

        for sensor_id in sensors_ids:
            print(f"\nProcessing Sensor: {sensor_id}...")
                
            api_url = f"http://data.uradmonitor.com/api/v1/devices/{sensor_id}/all/{start_interval}/{end_interval}"
            try:
                    response = requests.get(api_url, headers=api_headers, timeout=10)
                    response.raise_for_status()
                    api_data = response.json()
            except Exception as e:
                    print(f" -> API Error for {sensor_id}: {e}")
                    continue
            data_points = []
            if isinstance(api_data, list):
                if len(api_data) > 0 and isinstance(api_data[0], list):
                    data_points = api_data[0]
                else:
                    data_points = api_data
            if not data_points:
                    print(f" -> No data found for sensor {sensor_id}")
                    continue

            averages = calculate_averages(data_points)
                
            if averages:
                    insert_average(cur, sensor_id, averages, yesterday)
                    conn.commit()
            else:
                    print(f" -> Could not calculate averages (empty or malformed data)")

    except Exception as e:
        print(f"Critical Database Error: {e}")
    finally:
        if 'cur' in locals(): cur.close()
        if 'conn' in locals(): conn.close()
        print("Database connection closed.")


if __name__ == "__main__":
    run_daily_job()