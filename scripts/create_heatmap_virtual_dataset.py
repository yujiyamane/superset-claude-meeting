"""
Fallback: Create a virtual (SQL-based) dataset for the heatmap that pre-orders
rows by day_of_week_number, hour_of_day so that when sort options are disabled
the chart receives data in chronological order.

The primary fix in create_meeting_charts.py uses a custom query_context that
adds day_of_week_number / hour_of_day to GROUP BY + ORDER BY on the physical
table, which is more reliable. This script provides the virtual dataset as an
alternative datasource should that approach need adjustment.
"""
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scripts.superset_client import api_get, api_post, api_put, api_delete

VIRTUAL_DS_NAME = "meeting_bookings_sorted"
HEALTHCARE_DB_URI = "postgresql+psycopg2://superset:superset@postgres:5432/healthcare_db"

VIRTUAL_DS_SQL = """\
SELECT
    booking_id,
    organizer_name,
    room_name,
    floor_level,
    floor_level_name,
    subject,
    start_datetime,
    end_datetime,
    start_date,
    day_of_week,
    day_of_week_number,
    hour_ampm,
    hour_of_day,
    duration_minutes,
    is_cancelled,
    total_available_minutes,
    total_minutes_booked,
    utilisation_rate
FROM meeting_bookings
ORDER BY day_of_week_number, hour_of_day"""


def get_or_create_database():
    existing = api_get("/api/v1/database/")
    for db in existing.get("result", []):
        if "healthcare" in db.get("database_name", "").lower():
            return db["id"]
    result = api_post("/api/v1/database/", {
        "database_name": "healthcare_db",
        "sqlalchemy_uri": HEALTHCARE_DB_URI,
        "expose_in_sqllab": True,
        "allow_run_async": True,
        "allow_dml": False,
        "allow_file_upload": False,
    })
    return result["id"]


def get_or_create_virtual_dataset(db_id):
    existing = api_get("/api/v1/dataset/")
    for ds in existing.get("result", []):
        if ds.get("table_name") == VIRTUAL_DS_NAME:
            print(f"  Virtual dataset already exists: {VIRTUAL_DS_NAME} id={ds['id']}")
            return ds["id"]

    result = api_post("/api/v1/dataset/", {
        "database": db_id,
        "sql": VIRTUAL_DS_SQL,
        "table_name": VIRTUAL_DS_NAME,
        "schema": None,
    })
    ds_id = result["id"]
    print(f"  Virtual dataset created: {VIRTUAL_DS_NAME} id={ds_id}")
    return ds_id


def main():
    print("Setting up healthcare_db connection...")
    db_id = get_or_create_database()
    print(f"  db_id={db_id}")

    print(f"\nCreating virtual dataset '{VIRTUAL_DS_NAME}'...")
    vds_id = get_or_create_virtual_dataset(db_id)
    print(f"  vds_id={vds_id}")
    print(f"\nSQL:\n{VIRTUAL_DS_SQL}\n")
    print("Done. Use this dataset id in the heatmap chart if needed.")
    return vds_id


if __name__ == "__main__":
    main()
