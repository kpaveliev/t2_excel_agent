-- Common queries for file tracking database
-- Run these manually in DuckDB CLI or copy-paste into scripts

-- =============================================================================
-- BASIC QUERIES - FILE TRACKING
-- =============================================================================

-- View all processed files
SELECT * FROM processed_files ORDER BY processed_at DESC;

-- Count files by status
SELECT status, COUNT(*) as count 
FROM processed_files 
GROUP BY status;

-- Total rows extracted
SELECT SUM(rows_extracted) as total_rows FROM processed_files;

-- =============================================================================
-- BASIC QUERIES - EXTRACTED DATA
-- =============================================================================

-- View all extracted data
SELECT * FROM extracted_data ORDER BY extracted_at DESC LIMIT 100;

-- Count total records
SELECT COUNT(*) as total_records FROM extracted_data;

-- Total amount across all orders
SELECT 
    COUNT(*) as total_orders,
    SUM(total_cost) as total_amount,
    AVG(total_cost) as avg_amount
FROM extracted_data;

-- Data by file
SELECT 
    filename,
    COUNT(*) as orders,
    SUM(total_cost) as total_amount
FROM extracted_data
GROUP BY filename
ORDER BY total_amount DESC;

-- Recent extractions
SELECT * FROM latest_data LIMIT 50;

-- =============================================================================
-- FILTERING
-- =============================================================================

-- Files processed today
SELECT * FROM processed_files 
WHERE processed_at >= CURRENT_DATE;

-- Files with errors
SELECT filename, processed_at 
FROM processed_files 
WHERE status = 'error'
ORDER BY processed_at DESC;

-- Successfully processed files
SELECT filename, rows_extracted, processed_at
FROM processed_files 
WHERE status = 'success'
ORDER BY processed_at DESC;

-- =============================================================================
-- STATISTICS
-- =============================================================================

-- Files processed per day
SELECT 
    DATE(processed_at) as date,
    COUNT(*) as files_processed,
    SUM(rows_extracted) as rows_extracted
FROM processed_files
GROUP BY DATE(processed_at)
ORDER BY date DESC;

-- Average rows per file
SELECT 
    AVG(rows_extracted) as avg_rows,
    MIN(rows_extracted) as min_rows,
    MAX(rows_extracted) as max_rows
FROM processed_files
WHERE status = 'success';

-- File size statistics
SELECT 
    MIN(size) as min_size_bytes,
    AVG(size) as avg_size_bytes,
    MAX(size) as max_size_bytes,
    SUM(size) as total_size_bytes
FROM processed_files;

-- =============================================================================
-- FINDING ISSUES
-- =============================================================================

-- Files that might need reprocessing (errors)
SELECT filename, processed_at 
FROM processed_files 
WHERE status = 'error'
ORDER BY processed_at DESC;

-- Files with no rows extracted (suspicious)
SELECT filename, status, processed_at
FROM processed_files 
WHERE rows_extracted = 0 OR rows_extracted IS NULL;

-- Duplicate filenames (shouldn't happen with PRIMARY KEY)
SELECT filename, COUNT(*) as count
FROM processed_files
GROUP BY filename
HAVING COUNT(*) > 1;

-- =============================================================================
-- MAINTENANCE
-- =============================================================================

-- Delete specific file entry
DELETE FROM processed_files WHERE filename = 'specific_file.xlsx';

-- Reset error status for retry
UPDATE processed_files 
SET status = 'pending' 
WHERE filename = 'specific_file.xlsx';

-- Clear all error entries (to reprocess them)
DELETE FROM processed_files WHERE status = 'error';

-- Remove old entries (older than 1 year)
DELETE FROM processed_files 
WHERE processed_at < CURRENT_DATE - INTERVAL '1 year';

-- =============================================================================
-- ANALYSIS QUERIES
-- =============================================================================

-- Find largest orders
SELECT 
    order_number,
    total_cost,
    filename,
    extracted_at
FROM extracted_data
ORDER BY total_cost DESC
LIMIT 20;

-- Orders by month
SELECT 
    YEAR(extracted_at) as year,
    MONTH(extracted_at) as month,
    COUNT(*) as orders,
    SUM(total_cost) as total_amount
FROM extracted_data
GROUP BY YEAR(extracted_at), MONTH(extracted_at)
ORDER BY year DESC, month DESC;

-- Cost distribution
SELECT 
    CASE 
        WHEN total_cost < 10000 THEN '< 10k'
        WHEN total_cost < 50000 THEN '10k-50k'
        WHEN total_cost < 100000 THEN '50k-100k'
        WHEN total_cost < 500000 THEN '100k-500k'
        ELSE '> 500k'
    END as cost_range,
    COUNT(*) as count,
    SUM(total_cost) as total
FROM extracted_data
GROUP BY cost_range
ORDER BY MIN(total_cost);

-- Check for duplicates
SELECT * FROM potential_duplicates;

-- Find specific order
SELECT * FROM extracted_data 
WHERE order_number LIKE '%12345%';

-- =============================================================================
-- EXPORT
-- =============================================================================

-- Export all extracted data to CSV
COPY extracted_data TO 'extracted_data_export.csv' (HEADER, DELIMITER ',');

-- Export file tracking to CSV
COPY processed_files TO 'processed_files_export.csv' (HEADER, DELIMITER ',');

-- Export combined view
COPY (
    SELECT 
        e.filename,
        e.order_number,
        e.total_cost,
        e.extracted_at,
        e.source_sheet,
        p.processed_at,
        p.status
    FROM extracted_data e
    JOIN processed_files p ON e.filename = p.filename
    ORDER BY e.extracted_at DESC
) TO 'combined_export.csv' (HEADER, DELIMITER ',');

-- Export summary report
COPY data_summary_by_file TO 'summary_by_file.csv' (HEADER, DELIMITER ',');

-- Export daily summary
COPY daily_summary TO 'daily_summary.csv' (HEADER, DELIMITER ',');

