"""One-off script to apply supabase/migrations/*.sql and seed.sql against the live DB.
Reads DATABASE_URL from the single .env file at the repo root. Not part of the running app.
"""
import pathlib
import sys

import psycopg2

ROOT = pathlib.Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / ".env"


def load_database_url() -> str:
    for line in ENV_PATH.read_text().splitlines():
        if line.startswith("DATABASE_URL="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError(f"DATABASE_URL not found in {ENV_PATH}")


def main() -> None:
    database_url = load_database_url()
    migrations_dir = ROOT / "supabase" / "migrations"
    files = sorted(migrations_dir.glob("*.sql"))
    seed_file = ROOT / "supabase" / "seed.sql"

    print(f"Connecting to Supabase Postgres...")
    conn = psycopg2.connect(database_url)
    conn.autocommit = True
    cur = conn.cursor()

    for f in files:
        print(f"Applying {f.name} ...")
        sql = f.read_text(encoding="utf-8")
        try:
            cur.execute(sql)
            print(f"  OK")
        except Exception as e:
            print(f"  ERROR in {f.name}: {e}")
            if "--continue-on-error" not in sys.argv:
                sys.exit(1)

    if seed_file.exists():
        print("Applying seed.sql ...")
        try:
            cur.execute(seed_file.read_text(encoding="utf-8"))
            print("  OK")
        except Exception as e:
            print(f"  ERROR in seed.sql: {e}")

    cur.close()
    conn.close()
    print("Done.")


if __name__ == "__main__":
    main()
