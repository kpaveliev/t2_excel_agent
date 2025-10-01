#!/usr/bin/env python3
"""
Backup the database to a timestamped file.
"""

import duckdb
from pathlib import Path
from datetime import datetime
import shutil

DB_PATH = Path(__file__).parent.parent / "file_tracker.duckdb"
BACKUP_DIR = Path(__file__).parent.parent / "backups"


def backup_database():
    """Create a backup of the database."""
    if not DB_PATH.exists():
        print(f"❌ Database not found: {DB_PATH}")
        return
    
    # Create backup directory
    BACKUP_DIR.mkdir(exist_ok=True)
    
    # Generate backup filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = BACKUP_DIR / f"file_tracker_backup_{timestamp}.duckdb"
    
    print(f"💾 Backing up database...")
    print(f"   From: {DB_PATH}")
    print(f"   To:   {backup_file}")
    
    # Copy the database file
    shutil.copy2(DB_PATH, backup_file)
    
    # Also export to CSV for extra safety
    csv_file = BACKUP_DIR / f"processed_files_{timestamp}.csv"
    conn = duckdb.connect(str(DB_PATH), read_only=True)
    conn.execute(f"COPY processed_files TO '{csv_file}' (HEADER, DELIMITER ',');")
    conn.close()
    
    print(f"✅ Backup complete!")
    print(f"   Database: {backup_file}")
    print(f"   CSV:      {csv_file}")
    
    # Show backup size
    db_size = backup_file.stat().st_size
    csv_size = csv_file.stat().st_size
    print(f"   DB Size:  {db_size:,} bytes")
    print(f"   CSV Size: {csv_size:,} bytes")
    
    # Clean old backups (keep last 10)
    backups = sorted(BACKUP_DIR.glob("file_tracker_backup_*.duckdb"))
    if len(backups) > 10:
        print(f"\n🗑️  Cleaning old backups (keeping last 10)...")
        for old_backup in backups[:-10]:
            old_backup.unlink()
            # Also delete corresponding CSV
            csv_to_delete = old_backup.parent / old_backup.name.replace("file_tracker_backup_", "processed_files_").replace(".duckdb", ".csv")
            if csv_to_delete.exists():
                csv_to_delete.unlink()
            print(f"   Deleted: {old_backup.name}")


if __name__ == "__main__":
    backup_database()

