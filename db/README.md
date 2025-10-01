# Database Scripts

This folder contains DuckDB database management scripts that are run manually, separate from the main application pipeline.

## Files

- `01_init_schema.sql` - Initial database schema creation
- `02_add_error_tracking.sql` - Example migration: add error tracking
- `reset_db.py` - Python script to reset the database
- `inspect_db.py` - Python script to inspect database contents
- `backup_db.py` - Python script to backup the database

## Usage

### Initial Setup

```bash
# Run the initial schema
duckdb file_tracker.duckdb < db/01_init_schema.sql
```

Or use Python:

```bash
python db/reset_db.py
```

### Applying Migrations

```bash
# Apply a specific migration
duckdb file_tracker.duckdb < db/02_add_error_tracking.sql
```

### Inspecting Database

```bash
# View all processed files
python db/inspect_db.py

# Or use DuckDB CLI
duckdb file_tracker.duckdb
D SELECT * FROM processed_files;
D .quit
```

### Backup

```bash
python db/backup_db.py
```

## Manual DuckDB Commands

```bash
# Open database
duckdb file_tracker.duckdb

# List tables
D .tables

# Show schema
D DESCRIBE processed_files;

# Query data
D SELECT filename, status, rows_extracted FROM processed_files;

# Count files by status
D SELECT status, COUNT(*) FROM processed_files GROUP BY status;

# Export to CSV
D COPY (SELECT * FROM processed_files) TO 'processed_files_backup.csv';

# Quit
D .quit
```

## Database Schema

### Tables

**processed_files** - Tracks which Excel files have been processed
- `filename` (PRIMARY KEY)
- `file_path`, `size`, `mtime`
- `data_hash` - hash of extracted data
- `processed_at`, `rows_extracted`, `status`

**extracted_data** - Stores the actual data from Excel files
- `id` (PRIMARY KEY, auto-increment)
- `filename` (FOREIGN KEY → processed_files)
- `order_number` - Номер заявки
- `total_cost` - Итоговая Стоимость Заявки
- `extracted_at`, `source_sheet`, `source_row`

### Views

- `file_status_summary` - Processing status overview
- `latest_data` - Recent extracted data with file info
- `data_summary_by_file` - Aggregated stats per file
- `daily_summary` - Daily processing statistics
- `potential_duplicates` - Find duplicate orders

## Schema Version History

- **v1** - Initial schema with file tracking + extracted data tables
- **v2** - Added error_message field for better error tracking
- **v3** - Added composite indexes for better query performance

