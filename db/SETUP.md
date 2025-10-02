# Database Setup Guide

## Step 1: Configure Environment

Add to your `.env` file in the project root:

```bash
# DuckDB Configuration
DUCKDB_PATH=db/excel_data.duckdb
```

If you don't have a `.env` file, create one:

```bash
# Copy from example
cp .env.example .env

# Edit the file
nano .env  # or use your preferred editor
```

## Step 2: Create the Database Table

Run the table creation script:

```bash
python3 -m db.create_base_table
```

Expected output:
```
📊 Creating base table in: db/excel_data.duckdb
  → Dropped existing table (if any)
  ✅ Table 'processed_requests' created successfully
  → Creating indexes...
    ✓ Index on filename
    ✓ Index on request_number
    ✓ Index on request_datetime

📋 Table structure:
  id                                 INTEGER        
  created_at                         TIMESTAMP      
  filename                           VARCHAR        
  branch_code                        VARCHAR        
  ...

📊 Current row count: 0

✅ Database ready at: /path/to/db/excel_data.duckdb
```

## Step 3: Verify the Table

You can verify the table was created:

```python
import duckdb

conn = duckdb.connect('db/excel_data.duckdb')
result = conn.execute("SELECT COUNT(*) FROM processed_requests").fetchone()
print(f"Rows: {result[0]}")
conn.close()
```

Or use DuckDB CLI:

```bash
duckdb db/excel_data.duckdb -c "DESCRIBE processed_requests"
```

## Troubleshooting

### Error: "No module named 'duckdb'"

Install DuckDB:
```bash
pip install duckdb
```

### Error: "Permission denied"

Ensure the `db/` directory is writable:
```bash
chmod +w db/
```

### Starting Fresh

To recreate the table from scratch:
```bash
# Delete the database file
rm db/excel_data.duckdb

# Recreate
python3 -m db.create_base_table
```

## Next Steps

See [README_TABLE.md](README_TABLE.md) for:
- Detailed table structure
- Usage examples
- Query examples

