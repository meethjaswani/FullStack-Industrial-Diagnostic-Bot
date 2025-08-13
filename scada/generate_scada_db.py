import sqlite3
import random
import os
from datetime import datetime

def generate_database():
    # Base directory = SentientFinal/
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, "data")
    os.makedirs(data_dir, exist_ok=True)

    # Create DB path inside data/
    db_path = os.path.join(data_dir, "scada_data.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Reset table
    cursor.execute("DROP TABLE IF EXISTS scada_logs")
    cursor.execute("""
        CREATE TABLE scada_logs (
            id INTEGER PRIMARY KEY,
            machine_name TEXT,
            timestamp TEXT,
            metric_name TEXT,
            value REAL,
            error_code TEXT
        )
    """)

    machines = ["Filler_01", "Capper_01", "Labeler_01", "Packer_04"]

    metrics = {
        "pressure_psi": (40, 60),
        "temperature_celsius": (20, 35),
        "vibration_hz": (5, 15),
        "load_kw": (100, 500),
        "rpm": (500, 2000)
    }

    error_map = {
        "pressure_psi": ["ERR_PRESSURE_LOW_503"],
        "temperature_celsius": ["ERR_TEMP_HIGH_504"],
        "vibration_hz": ["ERR_VIBRATION_505"],
        "load_kw": ["ERR_LOAD_OVER_506", "ERR_LOAD_UNDER_507"],
        "rpm": ["ERR_OVERSPEED_508", "ERR_UNDERSPEED_509"]
    }

    for metric, (low, high) in metrics.items():
        for month in range(1, 13):
            for _ in range(25):
                machine = random.choice(machines)
                day = random.randint(1, 28)
                hour = random.randint(0, 23)
                minute = random.randint(0, 59)

                timestamp = datetime.strptime(
                    f"2024-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:00",
                    "%Y-%m-%d %H:%M:%S"
                )

                value = round(random.uniform(low, high), 2)
                error_code = None

                if random.random() < 0.2:
                    error_code = random.choice(error_map.get(metric, [None]))

                cursor.execute("""
                    INSERT INTO scada_logs (machine_name, timestamp, metric_name, value, error_code)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    machine,
                    timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    metric,
                    value,
                    error_code
                ))

    conn.commit()
    conn.close()

if __name__ == "__main__":
    generate_database()
