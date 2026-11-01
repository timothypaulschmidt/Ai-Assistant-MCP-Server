"""List the demo answer key: which records hold an injection payload, and which canary
values are planted. Reads the database file directly (the MCP server itself cannot,
because it blocks the _lab_ tables).

Usage:  python examples/show_poisoned.py [data-dir]      (default: data)
Run it from the repo folder, or pass the folder the server was started with.
"""
import sqlite3
import sys
from pathlib import Path

data_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data")
db = data_dir / "company.db"
if not db.exists():
    sys.exit(f"{db} not found. Start the server once (it creates the data), or pass the data folder.")

con = sqlite3.connect(db)

print("Poisoned records (injection payloads hidden in the data)")
print("-" * 60)
for table, row_id, column, kind in con.execute(
    "SELECT table_name, row_id, column_name, payload_kind FROM _lab_poisoned "
    "ORDER BY table_name, row_id"
):
    print(f"{table:22} id={row_id:<5} {column:12} {kind}")

print("\nCanary values (search model replies and logs for these)")
print("-" * 60)
for kind, value, location in con.execute("SELECT kind, value, location FROM _lab_canaries"):
    print(f"{kind:10} {value:34} {location}")
