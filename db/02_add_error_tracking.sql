-- Migration: Add error tracking
-- Version: 2
-- Description: Add error_message column for better error diagnostics

-- Add error_message column if it doesn't exist
ALTER TABLE processed_files 
ADD COLUMN IF NOT EXISTS error_message TEXT;

-- Add column for retry count
ALTER TABLE processed_files 
ADD COLUMN IF NOT EXISTS retry_count INTEGER DEFAULT 0;

-- Add column for last error time
ALTER TABLE processed_files 
ADD COLUMN IF NOT EXISTS last_error_at TIMESTAMP;

-- Update schema version
UPDATE schema_metadata 
SET value = '2', updated_at = CURRENT_TIMESTAMP 
WHERE key = 'schema_version';

-- Create view for error analysis
CREATE OR REPLACE VIEW error_summary AS
SELECT 
    filename,
    error_message,
    retry_count,
    last_error_at,
    processed_at
FROM processed_files
WHERE status = 'error'
ORDER BY last_error_at DESC;

