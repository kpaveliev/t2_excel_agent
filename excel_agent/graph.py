"""LangGraph workflow for processing Excel files."""

from typing import TypedDict, List, Dict, Optional
from pathlib import Path
import pandas as pd
from langgraph.graph import StateGraph, END
from excel_agent.excel_reader import (
    read_excel_file,
    extract_all_columns,
    get_sheet_preview
)
from excel_agent.column_mapper import create_column_mapper, find_relevant_columns
from excel_agent.config import MODEL_NAME, TEMPERATURE


class ExcelProcessingState(TypedDict):
    """State for the Excel processing workflow."""
    file_path: Path
    filename: str
    sheets_data: Dict[str, pd.DataFrame]
    all_columns: List[str]
    column_mapping: Optional[Dict]
    extracted_data: Optional[pd.DataFrame]
    error: Optional[str]


def read_file_node(state: ExcelProcessingState) -> ExcelProcessingState:
    """Node to read the Excel file and extract sheets."""
    try:
        file_path = state["file_path"]
        sheets_data = read_excel_file(file_path)
        all_columns = extract_all_columns(sheets_data)
        
        return {
            **state,
            "sheets_data": sheets_data,
            "all_columns": all_columns,
            "error": None
        }
    except Exception as e:
        return {
            **state,
            "error": f"Error reading file: {str(e)}"
        }


def find_columns_node(state: ExcelProcessingState) -> ExcelProcessingState:
    """Node to identify relevant columns using LLM."""
    try:
        sheets_data = state["sheets_data"]
        filename = state["filename"]
        
        # Create LLM chain
        llm_chain = create_column_mapper(MODEL_NAME, TEMPERATURE)
        
        # Try each sheet to find the best match
        best_mapping = None
        best_confidence = None
        
        for sheet_name, df in sheets_data.items():
            columns = [col for col in df.columns if not str(col).startswith('Unnamed')]
            if not columns:
                continue
                
            preview = get_sheet_preview(df, n_rows=10)
            
            mapping = find_relevant_columns(
                filename=filename,
                sheets=list(sheets_data.keys()),
                current_sheet=sheet_name,
                columns=columns,
                preview=preview,
                llm_chain=llm_chain
            )
            
            # Keep the mapping with highest confidence
            if mapping.order_number_column and mapping.total_cost_column:
                if best_confidence is None or mapping.confidence == "high":
                    best_mapping = {
                        "sheet_name": sheet_name,
                        "order_column": mapping.order_number_column,
                        "cost_column": mapping.total_cost_column,
                        "confidence": mapping.confidence
                    }
                    if mapping.confidence == "high":
                        break
        
        return {
            **state,
            "column_mapping": best_mapping,
            "error": None if best_mapping else "Could not find relevant columns"
        }
    except Exception as e:
        return {
            **state,
            "error": f"Error finding columns: {str(e)}"
        }


def extract_data_node(state: ExcelProcessingState) -> ExcelProcessingState:
    """Node to extract data from the identified columns."""
    try:
        if state.get("error"):
            return state
            
        mapping = state["column_mapping"]
        if not mapping:
            return {
                **state,
                "error": "No column mapping available"
            }
        
        sheet_name = mapping["sheet_name"]
        order_col = mapping["order_column"]
        cost_col = mapping["cost_column"]
        
        df = state["sheets_data"][sheet_name]
        
        # Extract relevant columns
        extracted_df = pd.DataFrame({
            "Filename": state["filename"],
            "Номер заявки": df[order_col],
            "Итоговая Стоимость Заявки": df[cost_col]
        })
        
        # Remove rows with null values
        extracted_df = extracted_df.dropna()
        
        return {
            **state,
            "extracted_data": extracted_df,
            "error": None
        }
    except Exception as e:
        return {
            **state,
            "error": f"Error extracting data: {str(e)}"
        }


def create_excel_processing_graph():
    """Create the LangGraph workflow for processing Excel files."""
    workflow = StateGraph(ExcelProcessingState)
    
    # Add nodes
    workflow.add_node("read_file", read_file_node)
    workflow.add_node("find_columns", find_columns_node)
    workflow.add_node("extract_data", extract_data_node)
    
    # Add edges
    workflow.set_entry_point("read_file")
    workflow.add_edge("read_file", "find_columns")
    workflow.add_edge("find_columns", "extract_data")
    workflow.add_edge("extract_data", END)
    
    return workflow.compile()


def process_excel_file(file_path: Path) -> Dict:
    """
    Process a single Excel file through the workflow.
    
    Args:
        file_path: Path to the Excel file
        
    Returns:
        Dictionary with processing results
    """
    graph = create_excel_processing_graph()
    
    initial_state = {
        "file_path": file_path,
        "filename": file_path.name,
        "sheets_data": {},
        "all_columns": [],
        "column_mapping": None,
        "extracted_data": None,
        "error": None
    }
    
    result = graph.invoke(initial_state)
    return result

