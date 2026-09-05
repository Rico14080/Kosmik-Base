#!/usr/bin/env python3
"""Create a timestamped backup of the Kosmik Circles SQLite database."""
from datetime import datetime, timezone
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
DB = HERE / "data" / "kosmik.db"
BACKUPS = HERE / "backups"
BACKUPS.mkdir(parents=True, exist_ok=True)
if not DB.exists():
    raise SystemExit("Database not found: start the server once first.")
name = datetime.now(timezone.utc).strftime("kosmik-%Y%m%d-%H%M%S.db")
dst = BACKUPS / name
shutil.copy2(DB, dst)
print(dst)
