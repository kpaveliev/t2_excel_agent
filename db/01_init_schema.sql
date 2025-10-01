-- Initial schema for file tracking database
-- Version: 1
-- Created: 2025-10-01

-- =============================================================================
-- FILE TRACKING TABLE
-- =============================================================================
-- Tracks which files have been processed and their status
CREATE TABLE IF NOT EXISTS processed_files (
    filename TEXT PRIMARY KEY,
    file_path TEXT,
    size BIGINT,
    mtime DOUBLE,
    data_hash TEXT,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    rows_extracted INTEGER,
    status TEXT CHECK (status IN ('success', 'error', 'pending')),
    schema_version INTEGER DEFAULT 1
);

-- Create index on status for faster filtering
CREATE INDEX IF NOT EXISTS idx_status ON processed_files(status);

-- Create index on processed_at for time-based queries
CREATE INDEX IF NOT EXISTS idx_processed_at ON processed_files(processed_at);

-- =============================================================================
-- EXTRACTED DATA TABLE
-- =============================================================================
-- Stores the actual extracted data from Excel files
CREATE TABLE IF NOT EXISTS extracted_data (
    id INTEGER PRIMARY KEY,
    filename TEXT NOT NULL,
    order_number TEXT NOT NULL,
    total_cost DECIMAL(15, 2),
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source_sheet TEXT,
    source_row INTEGER,
    -- Foreign key to track which file this came from
    FOREIGN KEY (filename) REFERENCES processed_files(filename) ON DELETE CASCADE
);

-- Create sequence for auto-incrementing ID
CREATE SEQUENCE IF NOT EXISTS seq_extracted_data_id START 1;

-- Create indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_extracted_filename ON extracted_data(filename);
CREATE INDEX IF NOT EXISTS idx_extracted_order ON extracted_data(order_number);
CREATE INDEX IF NOT EXISTS idx_extracted_date ON extracted_data(extracted_at);

-- =============================================================================
-- VIEWS FOR FILE TRACKING
-- =============================================================================

-- Summary of file processing status
CREATE OR REPLACE VIEW file_status_summary AS
SELECT 
    status,
    COUNT(*) as count,
    SUM(rows_extracted) as total_rows,
    MIN(processed_at) as first_processed,
    MAX(processed_at) as last_processed
FROM processed_files
GROUP BY status;

-- Recent file processing activity
CREATE OR REPLACE VIEW recent_activity AS
SELECT 
    filename,
    status,
    rows_extracted,
    processed_at,
    CASE 
        WHEN processed_at > CURRENT_TIMESTAMP - INTERVAL '1 day' THEN 'Today'
        WHEN processed_at > CURRENT_TIMESTAMP - INTERVAL '7 days' THEN 'This Week'
        WHEN processed_at > CURRENT_TIMESTAMP - INTERVAL '30 days' THEN 'This Month'
        ELSE 'Older'
    END as period
FROM processed_files
ORDER BY processed_at DESC
LIMIT 100;

-- =============================================================================
-- VIEWS FOR EXTRACTED DATA
-- =============================================================================

-- Latest extracted data with file info
CREATE OR REPLACE VIEW latest_data AS
SELECT 
    e.id,
    e.filename,
    e.order_number,
    e.total_cost,
    e.extracted_at,
    e.source_sheet,
    p.processed_at,
    p.status
FROM extracted_data e
JOIN processed_files p ON e.filename = p.filename
ORDER BY e.extracted_at DESC;

-- Summary by file
CREATE OR REPLACE VIEW data_summary_by_file AS
SELECT 
    filename,
    COUNT(*) as row_count,
    SUM(total_cost) as total_amount,
    AVG(total_cost) as avg_amount,
    MIN(total_cost) as min_amount,
    MAX(total_cost) as max_amount,
    MIN(extracted_at) as first_extracted,
    MAX(extracted_at) as last_extracted
FROM extracted_data
GROUP BY filename
ORDER BY last_extracted DESC;

-- Daily summary
CREATE OR REPLACE VIEW daily_summary AS
SELECT 
    DATE(extracted_at) as date,
    COUNT(DISTINCT filename) as files_processed,
    COUNT(*) as rows_extracted,
    SUM(total_cost) as total_amount
FROM extracted_data
GROUP BY DATE(extracted_at)
ORDER BY date DESC;

-- Insert initial metadata
CREATE TABLE IF NOT EXISTS schema_metadata (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT OR REPLACE INTO schema_metadata (key, value) 
VALUES ('schema_version', '1');

INSERT OR REPLACE INTO schema_metadata (key, value) 
VALUES ('created_at', CURRENT_TIMESTAMP::TEXT);

