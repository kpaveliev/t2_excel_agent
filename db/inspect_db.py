#!/usr/bin/env python3
"""
Inspect the file tracking database.
Shows statistics, recent files, errors, etc.
"""

import duckdb
from pathlib import Path
import sys
from datetime import datetime

DB_PATH = Path(__file__).parent.parent / "file_tracker.duckdb"


def inspect_database():
    """Display database contents and statistics."""
    if not DB_PATH.exists():
        print(f"❌ Database not found: {DB_PATH}")
        print("💡 Run: python db/reset_db.py to create it")
        return
    
    conn = duckdb.connect(str(DB_PATH), read_only=True)
    
    print("=" * 80)
    print("📊 FILE TRACKER DATABASE INSPECTION")
    print("=" * 80)
    print()
    
    # Schema version
    try:
        version = conn.execute(
            "SELECT value FROM schema_metadata WHERE key = 'schema_version'"
        ).fetchone()
        if version:
            print(f"Schema Version: v{version[0]}")
    except:
        print("Schema Version: Unknown")
    print()
    
    # Overall statistics
    print("📈 OVERALL STATISTICS")
    print("-" * 80)
    stats = conn.execute("""
        SELECT 
            COUNT(*) as total_files,
            SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful,
            SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as errors,
            SUM(rows_extracted) as total_rows,
            MIN(processed_at) as first_processed,
            MAX(processed_at) as last_processed
        FROM processed_files
    """).fetchone()
    
    if stats and stats[0] > 0:
        print(f"Total Files:     {stats[0]}")
        print(f"Successful:      {stats[1]}")
        print(f"Errors:          {stats[2]}")
        print(f"Total Rows:      {stats[3] or 0}")
        print(f"First Processed: {stats[4]}")
        print(f"Last Processed:  {stats[5]}")
    else:
        print("No files processed yet")
    print()
    
    # Status breakdown
    print("📊 STATUS BREAKDOWN")
    print("-" * 80)
    status_data = conn.execute("""
        SELECT status, COUNT(*) as count, SUM(rows_extracted) as rows
        FROM processed_files
        GROUP BY status
        ORDER BY count DESC
    """).fetchall()
    
    if status_data:
        for row in status_data:
            print(f"{row[0]:12} {row[1]:>6} files  {row[2] or 0:>8} rows")
    else:
        print("No data")
    print()
    
    # Recent files
    print("📁 RECENT FILES (Last 10)")
    print("-" * 80)
    recent = conn.execute("""
        SELECT 
            filename,
            status,
            rows_extracted,
            processed_at
        FROM processed_files
        ORDER BY processed_at DESC
        LIMIT 10
    """).fetchall()
    
    if recent:
        for row in recent:
            status_icon = "✅" if row[1] == "success" else "❌"
            print(f"{status_icon} {row[0]:45} {row[2] or 0:>4} rows  {row[3]}")
    else:
        print("No files")
    print()
    
    # Errors
    print("❌ RECENT ERRORS (Last 5)")
    print("-" * 80)
    errors = conn.execute("""
        SELECT 
            filename,
            processed_at
        FROM processed_files
        WHERE status = 'error'
        ORDER BY processed_at DESC
        LIMIT 5
    """).fetchall()
    
    if errors:
        for row in errors:
            print(f"• {row[0]:50} {row[1]}")
    else:
        print("No errors 🎉")
    print()
    
    # File sizes
    print("💾 FILE SIZE STATISTICS")
    print("-" * 80)
    size_stats = conn.execute("""
        SELECT 
            MIN(size) as min_size,
            AVG(size) as avg_size,
            MAX(size) as max_size
        FROM processed_files
    """).fetchone()
    
    if size_stats and size_stats[0]:
        print(f"Min Size: {size_stats[0]:>12,} bytes")
        print(f"Avg Size: {int(size_stats[1]):>12,} bytes")
        print(f"Max Size: {size_stats[2]:>12,} bytes")
    else:
        print("No data")
    print()
    
    conn.close()
    print("=" * 80)


if __name__ == "__main__":
    inspect_database()

