"""Script to apply enterprise MySQL Triggers to the health_claims_simulator database."""
import os
import pymysql
from dotenv import load_dotenv

# Load database credentials from .env
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "premsai444@123")
DB_NAME = os.getenv("DB_NAME", "health_claims_simulator")

SQL_FILE_PATH = os.path.join(BASE_DIR, "data", "database_triggers.sql")


def apply_triggers():
    print(f"Connecting to MySQL database '{DB_NAME}' on {DB_HOST}:{DB_PORT} as '{DB_USER}'...")
    try:
        conn = pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            charset="utf8mb4",
            autocommit=True,
            client_flag=pymysql.constants.CLIENT.MULTI_STATEMENTS
        )
    except Exception as e:
        print("\n[!] Connection Error: Unable to connect to MySQL.")
        print(f"    Details: {e}")
        print("\nEnsure MySQL service is running on your system (e.g. via MySQL Workbench or Services).")
        return

    print("Reading SQL trigger definitions from:", SQL_FILE_PATH)
    with open(SQL_FILE_PATH, "r", encoding="utf-8") as f:
        sql_content = f.read()

    # In pymysql with MULTI_STATEMENTS, DELIMITER directives are not supported by the protocol.
    # We strip out DELIMITER lines and split the statements.
    lines = []
    for line in sql_content.splitlines():
        trimmed = line.strip()
        if trimmed.startswith("DELIMITER") or trimmed.startswith("USE "):
            continue
        lines.append(line)

    raw_sql = "\n".join(lines)
    # Split by $$ delimiter used in script
    chunks = [c.strip() for c in raw_sql.split("$$") if c.strip()]

    with conn.cursor() as cursor:
        print(f"\nExecuting {len(chunks)} trigger and table definitions...")
        for i, chunk in enumerate(chunks, 1):
            # Clean up trailing semicolons if any
            clean_chunk = chunk.strip().rstrip(";")
            if not clean_chunk:
                continue
            try:
                cursor.execute(clean_chunk)
                first_line = clean_chunk.splitlines()[0][:60]
                print(f"  [{i}/{len(chunks)}] Executed: {first_line}...")
            except Exception as ex:
                print(f"  [x] Error in statement {i}: {ex}")

        # Verify active triggers
        print("\nVerifying installed triggers in database:")
        cursor.execute("SHOW TRIGGERS")
        triggers = cursor.fetchall()
        if triggers:
            print(f"\nTotal Triggers Active: {len(triggers)}")
            print("-" * 75)
            print(f"{'Trigger Name':<32} {'Event':<10} {'Timing':<10} {'Table':<15}")
            print("-" * 75)
            for t in triggers:
                # tuple format: (Trigger, Event, Table, Statement, Timing, Created, sql_mode, Definer, character_set_client, collation_connection, Database Collation)
                name = t[0]
                event = t[1]
                table = t[2]
                timing = t[4]
                print(f"{name:<32} {event:<10} {timing:<10} {table:<15}")
            print("-" * 75)
            print("\nAll database triggers applied successfully!")
        else:
            print("No triggers found.")

    conn.close()


if __name__ == "__main__":
    apply_triggers()
