#!/usr/bin/env python3
"""
Reset the database by dropping all tables and recreating the schema.
USE WITH CAUTION: This will delete all data!
"""

import duckdb
from pathlib import Path
import sys

DB_PATH = Path(__file__).parent.parent / "file_tracker.duckdb"
SCHEMA_FILE = Path(__file__).parent / "01_init_schema.sql"


def reset_database():
    """Drop all tables and recreate schema."""
    print(f"⚠️  WARNING: This will delete all data in {DB_PATH}")
    response = input("Are you sure? Type 'yes' to continue: ")
    
    if response.lower() != 'yes':
        print("❌ Aborted")
        return
    
    print(f"🗑️  Dropping existing database...")
    if DB_PATH.exists():
        DB_PATH.unlink()
    
    print(f"📝 Creating new database...")
    conn = duckdb.connect(str(DB_PATH))
    
    print(f"📋 Running schema: {SCHEMA_FILE}")
    schema_sql = SCHEMA_FILE.read_text()
    conn.execute(schema_sql)
    
    print(f"✅ Database reset complete!")
    
    # Show tables
    tables = conn.execute("SHOW TABLES").fetchall()
    print(f"\n📊 Created tables:")
    for table in tables:
        print(f"  - {table[0]}")
    
    conn.close()


if __name__ == "__main__":
    reset_database()

