"""Module for reading Excel files with various structures."""

import pandas as pd
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import openpyxl


def read_excel_file(file_path: Path) -> Dict[str, pd.DataFrame]:
    """
    Read all sheets from an Excel file.
    Handles cases where column headers are not in the first row.
    
    Args:
        file_path: Path to the Excel file
        
    Returns:
        Dictionary mapping sheet names to DataFrames
    """
    from excel_agent.config import logger
    
    try:
        # Try reading with openpyxl (for .xlsx files)
        excel_file = pd.ExcelFile(file_path, engine='openpyxl')
    except Exception:
        # Fallback to xlrd for older .xls files
        excel_file = pd.ExcelFile(file_path, engine='xlrd')
    
    sheets_data = {}
    for sheet_name in excel_file.sheet_names:
        # First, read without headers to analyze structure
        df_raw = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
        
        # Find where the actual headers are
        header_row = find_header_row(df_raw)
        
        logger.info(f"  → Sheet '{sheet_name}': Header found at row {header_row}")
        
        # Now read again with correct header row
        df = pd.read_excel(file_path, sheet_name=sheet_name, header=header_row)
        
        # Clean column names (strip whitespace)
        df.columns = [str(col).strip() if not str(col).startswith('Unnamed') else col 
                      for col in df.columns]
        
        sheets_data[sheet_name] = df
    
    return sheets_data


def find_header_row(df: pd.DataFrame, max_rows_to_check: int = 20) -> int:
    """
    Find the row that contains column headers.
    
    Strategy:
    1. Look for rows with mostly string values (headers are usually text)
    2. Look for rows where subsequent rows have similar data types (data rows)
    3. Avoid rows with all same values (merged title cells)
    4. Prefer rows with more non-null values
    
    Args:
        df: DataFrame read with header=None
        max_rows_to_check: Maximum number of rows to check
        
    Returns:
        Index of the header row (0-based)
    """
    from excel_agent.config import logger
    
    best_candidate = 0
    best_score = 0
    
    for i in range(min(max_rows_to_check, len(df))):
        row = df.iloc[i]
        
        # Skip completely empty rows
        if row.isna().all():
            continue
        
        # Count non-null values
        non_null_count = row.notna().sum()
        
        # Headers typically have multiple non-empty cells
        if non_null_count < 2:
            continue
        
        # Get non-null values
        non_null_values = row.dropna()
        
        # Check if all values are the same (merged cell - likely a title)
        unique_values = non_null_values.unique()
        if len(unique_values) == 1:
            continue
        
        # Calculate score based on multiple factors
        score = 0
        
        # Factor 1: String ratio (headers are usually text)
        string_count = sum(isinstance(val, str) for val in non_null_values)
        string_ratio = string_count / len(non_null_values) if len(non_null_values) > 0 else 0
        score += string_ratio * 40  # Weight: 40 points max
        
        # Factor 2: Number of non-null columns
        score += min(non_null_count, 10) * 3  # Weight: 30 points max for 10+ columns
        
        # Factor 3: Check if next row has data (not header-like)
        if i + 1 < len(df):
            next_row = df.iloc[i + 1]
            next_non_null = next_row.notna().sum()
            if next_non_null >= 2:
                next_non_null_values = next_row.dropna()
                next_string_count = sum(isinstance(val, str) for val in next_non_null_values)
                next_string_ratio = next_string_count / len(next_non_null_values) if len(next_non_null_values) > 0 else 0
                
                # If next row has fewer strings, it's likely data (good sign this is header)
                if next_string_ratio < string_ratio:
                    score += 20
        
        # Factor 4: Penalize very early rows (row 0 often has titles)
        if i > 0:
            score += 10
        
        logger.debug(f"Row {i}: score={score:.1f}, non_null={non_null_count}, string_ratio={string_ratio:.2f}")
        
        if score > best_score:
            best_score = score
            best_candidate = i
    
    logger.debug(f"Selected row {best_candidate} as header (score: {best_score:.1f})")
    return best_candidate


def find_data_start_row(df: pd.DataFrame, max_rows_to_check: int = 20) -> int:
    """
    Find the row where actual data starts (after merged cells or headers).
    
    Args:
        df: DataFrame to analyze
        max_rows_to_check: Maximum number of rows to check
        
    Returns:
        Index of the first data row
    """
    for i in range(min(max_rows_to_check, len(df))):
        row = df.iloc[i]
        # Check if row has reasonable amount of non-null values
        non_null_count = row.notna().sum()
        if non_null_count >= 2:  # At least 2 columns with data
            return i
    return 0


def extract_all_columns(sheets_data: Dict[str, pd.DataFrame]) -> List[str]:
    """
    Extract all unique column names from all sheets.
    
    Args:
        sheets_data: Dictionary of sheet names to DataFrames
        
    Returns:
        List of all unique column names
    """
    all_columns = set()
    for df in sheets_data.values():
        all_columns.update(df.columns.tolist())
    
    # Filter out unnamed columns
    return [col for col in all_columns if not str(col).startswith('Unnamed')]


def get_sheet_preview(df: pd.DataFrame, n_rows: int = 10) -> str:
    """
    Get a preview of the sheet for LLM analysis.
    
    Args:
        df: DataFrame to preview
        n_rows: Number of rows to include
        
    Returns:
        String representation of the preview
    """
    preview = df.head(n_rows).to_string()
    return preview

