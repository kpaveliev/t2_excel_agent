"""Module for reading Excel files with various structures."""

import pandas as pd
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import openpyxl


def read_excel_file(file_path: Path) -> Dict[str, pd.DataFrame]:
    """
    Read all sheets from an Excel file.
    
    Args:
        file_path: Path to the Excel file
        
    Returns:
        Dictionary mapping sheet names to DataFrames
    """
    try:
        # Try reading with openpyxl (for .xlsx files)
        excel_file = pd.ExcelFile(file_path, engine='openpyxl')
    except Exception:
        # Fallback to xlrd for older .xls files
        excel_file = pd.ExcelFile(file_path, engine='xlrd')
    
    sheets_data = {}
    for sheet_name in excel_file.sheet_names:
        # Read each sheet, trying different starting rows
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        sheets_data[sheet_name] = df
    
    return sheets_data


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

