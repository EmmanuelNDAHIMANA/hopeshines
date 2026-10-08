"""
Run this once to create all RH Database tables in your MySQL server.

    streamlit run Home.py   (must be run via streamlit so st.secrets loads)

Actually simplest: this script reads secrets.toml directly with tomllib,
so it can be run as a plain script too:

    python init_db.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # Python < 3.11 fallback

import pymysql

from utils.schemas import SCHEMAS, CREATION_ORDER
from utils.db import _table_ddl  # reuse the exact same DDL generator the app uses


def load_secrets():
    secrets_path = os.path.join(os.path.dirname(__file__), ".streamlit", "secrets.toml")
    if not os.path.exists(secrets_path):
        print(f"ERROR: {secrets_path} not found.")
        print("Copy config/secrets.toml.example to .streamlit/secrets.toml and fill in your MySQL details first.")
        sys.exit(1)
    with open(secrets_path, "rb") as f:
        return tomllib.load(f)


def main():
    secrets = load_secrets()
    cfg = secrets["mysql"]

    print(f"Connecting to {cfg['host']}:{cfg['port']} / db={cfg['db']} ...")
    conn = pymysql.connect(
        charset="utf8mb4",
        connect_timeout=10,
        cursorclass=pymysql.cursors.DictCursor,
        db=cfg["db"],
        host=cfg["host"],
        password=cfg["password"],
        port=int(cfg["port"]),
        user=cfg["user"],
        autocommit=True,
    )
    print("Connected OK.")

    with conn.cursor() as cur:
        for dataset_name in CREATION_ORDER:
            table = SCHEMAS[dataset_name]["table"]
            print(f"Creating table `{table}` for '{dataset_name}' ...")
            cur.execute(_table_ddl(dataset_name))
        # CREATE TABLE IF NOT EXISTS does not change existing columns. Apply
        # this migration so existing installations can store an unknown DOB.
        student_table = SCHEMAS["Student Database"]["table"]
        cur.execute(f"ALTER TABLE `{student_table}` MODIFY COLUMN `Student_DoB` DATE NULL")
        cur.execute(f"ALTER TABLE `{student_table}` MODIFY COLUMN `Student_Parent` VARCHAR(255) NULL")
        print(f"Ensured `{student_table}`.`Student_DoB` and `Student_Parent` accept NULL.")
        performance_table = SCHEMAS["Students Performance"]["table"]
        cur.execute(f"SHOW COLUMNS FROM `{performance_table}` LIKE 'Name'")
        if cur.fetchone():
            cur.execute(f"ALTER TABLE `{performance_table}` DROP COLUMN `Name`")
            print(f"Removed obsolete `Name` column from `{performance_table}`.")
        items_table = SCHEMAS["Students Item"]["table"]
        cur.execute(f"SHOW COLUMNS FROM `{items_table}` LIKE 'Date'")
        has_legacy_date = cur.fetchone() is not None
        cur.execute(f"SHOW COLUMNS FROM `{items_table}` LIKE 'School_Year'")
        has_school_year = cur.fetchone() is not None
        if has_legacy_date:
            if not has_school_year:
                cur.execute(f"ALTER TABLE `{items_table}` ADD COLUMN `School_Year` VARCHAR(9) NULL")
            cur.execute(
                f"UPDATE `{items_table}` SET `School_Year` = "
                "CONCAT(YEAR(`Date`), '-', YEAR(`Date`) + 1) "
                "WHERE `Date` IS NOT NULL AND (`School_Year` IS NULL OR `School_Year` = '')"
            )
            cur.execute(f"ALTER TABLE `{items_table}` DROP COLUMN `Date`")
            cur.execute(f"SELECT COUNT(*) AS missing FROM `{items_table}` WHERE `School_Year` IS NULL")
            missing_school_years = cur.fetchone()["missing"]
            if missing_school_years == 0:
                cur.execute(f"ALTER TABLE `{items_table}` MODIFY COLUMN `School_Year` VARCHAR(9) NOT NULL")
            print(
                f"Migrated `{items_table}` dates to school years using each date's calendar year."
            )
            if missing_school_years:
                print(f"Warning: {missing_school_years} item row(s) still have no School_Year.")
        food_table = SCHEMAS["Food Database"]["table"]
        cur.execute(
            f"UPDATE `{food_table}` "
            "SET `Total_Cost` = CASE "
            "WHEN `Purchased_Quantity` IS NOT NULL AND `Purchase_Unity_Cost` IS NOT NULL "
            "THEN ROUND(`Purchased_Quantity` * `Purchase_Unity_Cost`, 2) "
            "ELSE NULL END, "
            "`Meals_Served` = CASE "
            "WHEN LOWER(TRIM(`Food_Item`)) = 'rice' AND `Quantity_Used` IS NOT NULL "
            "THEN `Quantity_Used` * 5 "
            "WHEN LOWER(TRIM(`Food_Item`)) = 'mixed porridge flour' AND `Quantity_Used` IS NOT NULL "
            "THEN `Quantity_Used` * 13 "
            "ELSE NULL END"
        )
        print(f"Recalculated computed columns in `{food_table}`.")
    conn.close()
    print("\nAll tables created (or already existed). You're ready to run: streamlit run Home.py")


if __name__ == "__main__":
    main()
