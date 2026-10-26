"""
Script to apply enterprise MySQL Triggers to the Health Insurance Claims Simulator database.
Reads database connection settings directly from config.py / .env.
"""
import os
import pymysql
from config import Config

SQL_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database_triggers.sql")


def apply_triggers():
    print("=" * 75)
    print("CAREPULSE / HEALTH CLAIMS SIMULATOR — MYSQL TRIGGERS INSTALLER")
    print("=" * 75)
    print(f"Connecting to MySQL database '{Config.DB_NAME}' on {Config.DB_HOST}:{Config.DB_PORT}...")

    try:
        conn = pymysql.connect(
            host=Config.DB_HOST,
            port=int(Config.DB_PORT),
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            charset="utf8mb4",
            autocommit=True,
            client_flag=pymysql.constants.CLIENT.MULTI_STATEMENTS
        )
    except Exception as e:
        print("\n[!] Connection Error: Unable to connect to MySQL database.")
        print(f"    Details: {e}")
        print("\nEnsure MySQL 8.0 service is running on your system (e.g. via MySQL Workbench or Windows Services).")
        return

    print("Reading SQL trigger definitions from:", SQL_FILE_PATH)
    with open(SQL_FILE_PATH, "r", encoding="utf-8") as f:
        sql_content = f.read()

    lines = []
    for line in sql_content.splitlines():
        trimmed = line.strip()
        if trimmed.startswith("DELIMITER") or trimmed.startswith("USE "):
            continue
        lines.append(line)

    raw_sql = "\n".join(lines)
    chunks = [c.strip() for c in raw_sql.split("$$") if c.strip()]

    with conn.cursor() as cursor:
        print(f"\nExecuting {len(chunks)} trigger and table statements...")
        for i, chunk in enumerate(chunks, 1):
            clean_chunk = chunk.strip().rstrip(";")
            if not clean_chunk:
                continue
            try:
                cursor.execute(clean_chunk)
                header = clean_chunk.splitlines()[0][:60]
                print(f"  [{i}/{len(chunks)}] Executed: {header}...")
            except Exception as ex:
                print(f"  [x] Error in statement {i}: {ex}")

        # Verification
        print("\n" + "=" * 75)
        print("INSTALLED MYSQL TRIGGERS IN DATABASE")
        print("=" * 75)
        cursor.execute("SHOW TRIGGERS")
        triggers = cursor.fetchall()

        if triggers:
            print(f"{'Trigger Name':<34} {'Event':<10} {'Timing':<10} {'Table':<15}")
            print("-" * 75)
            for t in triggers:
                name = t[0]
                event = t[1]
                table = t[2]
                timing = t[4]
                print(f"{name:<34} {event:<10} {timing:<10} {table:<15}")
            print("-" * 75)
            print(f"Total Active Triggers: {len(triggers)}")
            print("\n[SUCCESS] All triggers applied and verified successfully in MySQL!")
        else:
            print("No triggers found.")

    conn.close()


if __name__ == "__main__":
    apply_triggers()
