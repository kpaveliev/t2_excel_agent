"""React Agent for Excel processing using LangGraph's create_react_agent."""

from typing import List, Dict, Any
from pathlib import Path
import pandas as pd
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from excel_agent.config import OPENAI_API_KEY, MODEL_NAME, TEMPERATURE, DATA_DIR, OUTPUT_DIR, logger
from excel_agent.excel_reader import read_excel_file, extract_all_columns, get_sheet_preview
from excel_agent.column_mapper import create_column_mapper, find_relevant_columns


@tool
def list_excel_files() -> str:
    """List all Excel files in the data directory.
    
    Returns:
        A formatted string listing all Excel files found.
    """
    try:
        excel_files = list(DATA_DIR.glob("*.xlsx")) + list(DATA_DIR.glob("*.xls"))
        if not excel_files:
            return f"No Excel files found in {DATA_DIR}"
        
        file_list = "\n".join([f"- {f.name}" for f in excel_files])
        return f"Found {len(excel_files)} Excel file(s):\n{file_list}"
    except Exception as e:
        logger.error(f"Error listing Excel files: {str(e)}")
        return f"Error listing files: {str(e)}"


@tool
def get_excel_sheets(filename: str) -> str:
    """Get all sheet names from an Excel file.
    
    Args:
        filename: Name of the Excel file (e.g., 'report.xlsx')
        
    Returns:
        A formatted string with sheet names and basic info.
    """
    try:
        file_path = DATA_DIR / filename
        if not file_path.exists():
            return f"File not found: {filename}"
        
        sheets_data = read_excel_file(file_path)
        
        result = [f"Excel file '{filename}' contains {len(sheets_data)} sheet(s):\n"]
        for sheet_name, df in sheets_data.items():
            result.append(f"- Sheet: '{sheet_name}' - {len(df)} rows, {len(df.columns)} columns")
        
        return "\n".join(result)
    except Exception as e:
        logger.error(f"Error reading Excel file: {str(e)}")
        return f"Error reading file: {str(e)}"


@tool
def get_sheet_columns(filename: str, sheet_name: str) -> str:
    """Get all columns from a specific sheet in an Excel file.
    
    Args:
        filename: Name of the Excel file
        sheet_name: Name of the sheet
        
    Returns:
        A formatted string with column names.
    """
    try:
        file_path = DATA_DIR / filename
        if not file_path.exists():
            return f"File not found: {filename}"
        
        sheets_data = read_excel_file(file_path)
        if sheet_name not in sheets_data:
            available = ", ".join(sheets_data.keys())
            return f"Sheet '{sheet_name}' not found. Available sheets: {available}"
        
        df = sheets_data[sheet_name]
        columns = [col for col in df.columns if not str(col).startswith('Unnamed')]
        
        return f"Sheet '{sheet_name}' in '{filename}' has {len(columns)} columns:\n" + "\n".join([f"- {col}" for col in columns])
    except Exception as e:
        logger.error(f"Error getting sheet columns: {str(e)}")
        return f"Error: {str(e)}"


@tool
def preview_sheet_data(filename: str, sheet_name: str, num_rows: int = 5) -> str:
    """Preview data from a specific sheet in an Excel file.
    
    Args:
        filename: Name of the Excel file
        sheet_name: Name of the sheet
        num_rows: Number of rows to preview (default: 5)
        
    Returns:
        A formatted string showing the preview data.
    """
    try:
        file_path = DATA_DIR / filename
        if not file_path.exists():
            return f"File not found: {filename}"
        
        sheets_data = read_excel_file(file_path)
        if sheet_name not in sheets_data:
            available = ", ".join(sheets_data.keys())
            return f"Sheet '{sheet_name}' not found. Available sheets: {available}"
        
        df = sheets_data[sheet_name]
        preview = get_sheet_preview(df, n_rows=num_rows)
        
        return f"Preview of sheet '{sheet_name}' (first {num_rows} rows):\n{preview}"
    except Exception as e:
        logger.error(f"Error previewing sheet data: {str(e)}")
        return f"Error: {str(e)}"


@tool
def find_columns_with_llm(filename: str, sheet_name: str) -> str:
    """Use LLM to automatically identify relevant columns (order number and cost) in a sheet.
    
    Args:
        filename: Name of the Excel file
        sheet_name: Name of the sheet to analyze
        
    Returns:
        A formatted string with the identified columns and confidence level.
    """
    try:
        file_path = DATA_DIR / filename
        if not file_path.exists():
            return f"File not found: {filename}"
        
        sheets_data = read_excel_file(file_path)
        if sheet_name not in sheets_data:
            available = ", ".join(sheets_data.keys())
            return f"Sheet '{sheet_name}' not found. Available sheets: {available}"
        
        df = sheets_data[sheet_name]
        columns = [col for col in df.columns if not str(col).startswith('Unnamed')]
        
        if not columns:
            return f"No named columns found in sheet '{sheet_name}'"
        
        # Create LLM chain
        llm_chain = create_column_mapper(MODEL_NAME, TEMPERATURE)
        
        # Get preview
        preview = get_sheet_preview(df, n_rows=10)
        
        # Find columns
        mapping = find_relevant_columns(
            filename=filename,
            sheets=list(sheets_data.keys()),
            current_sheet=sheet_name,
            columns=columns,
            preview=preview,
            llm_chain=llm_chain
        )
        
        result = f"LLM Analysis Results for '{filename}' - Sheet '{sheet_name}':\n"
        result += f"- Order Number Column: {mapping.order_number_column or 'Not found'}\n"
        result += f"- Total Cost Column: {mapping.total_cost_column or 'Not found'}\n"
        result += f"- Confidence: {mapping.confidence}\n"
        
        if mapping.reasoning:
            result += f"- Reasoning: {mapping.reasoning}"
        
        return result
    except Exception as e:
        logger.error(f"Error finding columns with LLM: {str(e)}")
        return f"Error: {str(e)}"


@tool
def extract_data(filename: str, sheet_name: str, order_column: str, cost_column: str) -> str:
    """Extract data from specific columns in a sheet.
    
    Args:
        filename: Name of the Excel file
        sheet_name: Name of the sheet
        order_column: Name of the order number column
        cost_column: Name of the cost column
        
    Returns:
        A summary of extracted data and path to saved CSV.
    """
    try:
        file_path = DATA_DIR / filename
        if not file_path.exists():
            return f"File not found: {filename}"
        
        sheets_data = read_excel_file(file_path)
        if sheet_name not in sheets_data:
            available = ", ".join(sheets_data.keys())
            return f"Sheet '{sheet_name}' not found. Available sheets: {available}"
        
        df = sheets_data[sheet_name]
        
        # Check if columns exist
        if order_column not in df.columns:
            available = ", ".join(df.columns)
            return f"Column '{order_column}' not found. Available columns: {available}"
        
        if cost_column not in df.columns:
            available = ", ".join(df.columns)
            return f"Column '{cost_column}' not found. Available columns: {available}"
        
        # Extract relevant columns
        extracted_df = pd.DataFrame({
            "Filename": filename,
            "Номер заявки": df[order_column],
            "Итоговая Стоимость Заявки": df[cost_column]
        })
        
        # Remove rows with null values
        before_count = len(extracted_df)
        extracted_df = extracted_df.dropna()
        after_count = len(extracted_df)
        
        # Save to CSV
        output_filename = f"extracted_{Path(filename).stem}_{sheet_name}.csv"
        output_path = OUTPUT_DIR / output_filename
        extracted_df.to_csv(output_path, index=False, encoding='utf-8-sig')
        
        result = f"Successfully extracted {after_count} rows from '{filename}' - Sheet '{sheet_name}'\n"
        if before_count > after_count:
            result += f"(Removed {before_count - after_count} rows with null values)\n"
        result += f"\nData saved to: {output_path}\n"
        result += f"\nFirst few rows:\n{extracted_df.head(3).to_string()}"
        
        return result
    except Exception as e:
        logger.error(f"Error extracting data: {str(e)}")
        return f"Error: {str(e)}"


def create_excel_react_agent():
    """Create a React agent with Excel processing tools and memory.
    
    Returns:
        A compiled LangGraph React agent with memory persistence.
    """
    # Initialize LLM
    llm = ChatOpenAI(
        model=MODEL_NAME,
        temperature=TEMPERATURE,
        api_key=OPENAI_API_KEY
    )
    
    # Define tools
    tools = [
        list_excel_files,
        get_excel_sheets,
        get_sheet_columns,
        preview_sheet_data,
        find_columns_with_llm,
        extract_data
    ]
    
    # Create system message
    system_message = """You are an Excel processing assistant. You can help users:
1. List Excel files in the data directory
2. Explore sheet names and structure
3. View column names and preview data
4. Use AI to identify relevant columns (order numbers and costs)
5. Extract data from specific columns

When helping users, be proactive and use the available tools to provide detailed information.
If a user asks to process a file, guide them through the steps or automatically process it using the tools.

Always provide clear, formatted responses and explain what you're doing.
You have access to the full conversation history, so you can refer back to previous interactions."""
    
    # Create memory saver for conversation persistence
    memory = MemorySaver()
    
    # Create the agent with checkpointing
    agent = create_react_agent(llm, tools, state_modifier=system_message, checkpointer=memory)
    
    logger.info("✓ React Agent created successfully with memory")
    return agent


# Singleton instance
_agent_instance = None


def get_react_agent():
    """Get or create the React agent instance."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = create_excel_react_agent()
    return _agent_instance

