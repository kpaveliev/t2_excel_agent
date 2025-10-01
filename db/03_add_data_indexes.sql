-- Migration: Add additional indexes for better query performance
-- Version: 3
-- Description: Add composite indexes and full-text search support

-- Composite index for filtering by filename and date
CREATE INDEX IF NOT EXISTS idx_extracted_filename_date 
ON extracted_data(filename, extracted_at DESC);

-- Composite index for cost range queries
CREATE INDEX IF NOT EXISTS idx_extracted_cost_date 
ON extracted_data(total_cost, extracted_at DESC);

-- Index for order number searches (if you need to find specific orders)
CREATE INDEX IF NOT EXISTS idx_order_number_search
ON extracted_data(order_number);

-- Update schema version
UPDATE schema_metadata 
SET value = '3', updated_at = CURRENT_TIMESTAMP 
WHERE key = 'schema_version';

-- Create view for duplicate detection
CREATE OR REPLACE VIEW potential_duplicates AS
SELECT 
    order_number,
    COUNT(*) as occurrence_count,
    COUNT(DISTINCT filename) as file_count,
    SUM(total_cost) as total_cost_sum,
    STRING_AGG(DISTINCT filename, ', ') as files
FROM extracted_data
GROUP BY order_number
HAVING COUNT(*) > 1
ORDER BY occurrence_count DESC;

