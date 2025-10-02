"""React Agent for Excel processing using LangGraph's create_react_agent."""

from typing import List, Dict, Any, Optional
from pathlib import Path
import pandas as pd
import time
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from excel_agent.config import OPENAI_API_KEY, MODEL_NAME, TEMPERATURE, DATA_DIR, OUTPUT_DIR, logger
from excel_agent.excel_reader import read_excel_file, extract_all_columns, get_sheet_preview
from excel_agent.column_mapper import create_column_mapper, find_relevant_columns
from excel_agent.graph import process_excel_file as run_stategraph_pipeline

# Global storage for human interaction (will be managed by Streamlit session state)
_human_question_queue = []
_human_answer_queue = []


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
def run_pipeline(filename: str, require_high_confidence: bool = False) -> str:
    """Run the full Excel processing pipeline on a file.
    
    This tool executes the complete StateGraph workflow (read → find columns → extract data).
    
    Args:
        filename: Name of the Excel file to process
        require_high_confidence: If True, only processes files with high confidence.
                                 If False, processes all files automatically.
    
    Returns:
        Processing results or a request for human review.
    """
    try:
        file_path = DATA_DIR / filename
        if not file_path.exists():
            return f"❌ File not found: {filename}"
        
        logger.info(f"🚀 Running pipeline for: {filename}")
        
        # Run the existing StateGraph workflow
        result = run_stategraph_pipeline(file_path)
        
        if result.get("error"):
            return f"❌ Error processing {filename}: {result['error']}"
        
        mapping = result.get("column_mapping", {})
        confidence = mapping.get("confidence", "low")
        extracted_data = result.get("extracted_data")
        
        # Build result message
        result_msg = f"📊 Processing Results for '{filename}':\n\n"
        result_msg += f"Sheet: {mapping.get('sheet_name', 'N/A')}\n"
        result_msg += f"Order Column: {mapping.get('order_column', 'N/A')}\n"
        result_msg += f"Cost Column: {mapping.get('cost_column', 'N/A')}\n"
        result_msg += f"Confidence: {confidence}\n"
        
        if extracted_data is not None:
            rows_count = len(extracted_data)
            result_msg += f"\n✅ Extracted {rows_count} rows successfully"
            
            # Save to CSV
            from pathlib import Path
            output_filename = f"extracted_{Path(filename).stem}.csv"
            output_path = OUTPUT_DIR / output_filename
            extracted_data.to_csv(output_path, index=False, encoding='utf-8-sig')
            result_msg += f"\n💾 Saved to: {output_path}"
            
            # Check if confidence is acceptable
            if require_high_confidence and confidence != "high":
                result_msg += f"\n\n⚠️ Warning: Confidence is '{confidence}' (not 'high'). "
                result_msg += "You may want to review the column selection using ask_human tool."
        else:
            result_msg += "\n⚠️ No data extracted"
        
        return result_msg
        
    except Exception as e:
        logger.error(f"Error in run_pipeline: {str(e)}")
        return f"❌ Pipeline error: {str(e)}"


@tool
def run_batch_pipeline(auto_mode: bool = True, require_high_confidence: bool = False) -> str:
    """Run the pipeline on ALL Excel files in the data directory.
    
    Args:
        auto_mode: If True, processes all files automatically.
                   If False, stops for review when confidence is not high.
        require_high_confidence: If True, reports files with non-high confidence.
    
    Returns:
        Summary of processing results for all files.
    """
    try:
        excel_files = list(DATA_DIR.glob("*.xlsx")) + list(DATA_DIR.glob("*.xls"))
        
        if not excel_files:
            return "❌ No Excel files found in data directory"
        
        logger.info(f"🚀 Starting batch processing of {len(excel_files)} files")
        
        results = []
        successful = 0
        needs_review = []
        errors = []
        all_extracted_data = []  # To combine all results
        
        for file_path in excel_files:
            filename = file_path.name
            logger.info(f"Processing: {filename}")
            
            result = run_stategraph_pipeline(file_path)
            
            if result.get("error"):
                errors.append(filename)
                results.append(f"❌ {filename}: {result['error']}")
            else:
                mapping = result.get("column_mapping", {})
                confidence = mapping.get("confidence", "low")
                extracted_data = result.get("extracted_data")
                
                if extracted_data is not None:
                    rows = len(extracted_data)
                    all_extracted_data.append(extracted_data)  # Collect for combined CSV
                    
                    if confidence == "high":
                        successful += 1
                        results.append(f"✅ {filename}: {rows} rows (confidence: {confidence})")
                    else:
                        if require_high_confidence or not auto_mode:
                            needs_review.append(filename)
                            results.append(f"⚠️ {filename}: {rows} rows (confidence: {confidence}) - may need review")
                        else:
                            successful += 1
                            results.append(f"✅ {filename}: {rows} rows (confidence: {confidence})")
                else:
                    errors.append(filename)
                    results.append(f"❌ {filename}: No data extracted")
        
        # Save combined results to CSV
        if all_extracted_data:
            combined_df = pd.concat(all_extracted_data, ignore_index=True)
            output_path = OUTPUT_DIR / "combined_results.csv"
            combined_df.to_csv(output_path, index=False, encoding='utf-8-sig')
            total_rows = len(combined_df)
        else:
            output_path = None
            total_rows = 0
        
        # Build summary
        summary = f"📊 Batch Processing Complete!\n\n"
        summary += f"Total files: {len(excel_files)}\n"
        summary += f"✅ Successful: {successful}\n"
        summary += f"⚠️ Need review: {len(needs_review)}\n"
        summary += f"❌ Errors: {len(errors)}\n"
        
        if output_path:
            summary += f"\n💾 Combined results saved to: {output_path}\n"
            summary += f"📊 Total rows extracted: {total_rows}\n"
        
        summary += "\nDetails:\n" + "\n".join(results)
        
        if needs_review:
            summary += f"\n\n💡 Files that may need review:\n"
            summary += "\n".join([f"  - {f}" for f in needs_review])
            summary += "\n\nUse 'ask_human' tool to get confirmation for these files."
        
        return summary
        
    except Exception as e:
        logger.error(f"Error in batch pipeline: {str(e)}")
        return f"❌ Batch processing error: {str(e)}"


@tool
def ask_human(question: str, options: Optional[List[str]] = None, context: Optional[str] = None) -> str:
    """Ask a question to the human user and wait for their response.
    
    This tool pauses agent execution and presents a question to the user in the chat interface.
    The agent will wait for the user's response before continuing.
    
    Args:
        question: The question to ask the human
        options: Optional list of suggested response options (e.g., ["Option 1", "Option 2"])
        context: Optional additional context or information to help the human decide
    
    Returns:
        The human's response as a string
    
    Example:
        ask_human(
            question="Which column should I use for order numbers?",
            options=["Номер заявки", "№ заявки", "Order Number"],
            context="File: report.xlsx, Sheet: Main"
        )
    """
    global _human_question_queue, _human_answer_queue
    
    # Format the question
    formatted_question = {
        "question": question,
        "options": options or [],
        "context": context,
        "timestamp": time.time()
    }
    
    # Add to question queue
    _human_question_queue.append(formatted_question)
    
    logger.info(f"❓ Asking human: {question}")
    
    # Create a marker message that Streamlit will detect
    marker = "🤔 **[WAITING FOR HUMAN RESPONSE]**"
    
    if context:
        marker += f"\n\n**Context:** {context}"
    
    marker += f"\n\n**Question:** {question}"
    
    if options:
        marker += f"\n\n**Options:**\n"
        for i, opt in enumerate(options, 1):
            marker += f"{i}. {opt}\n"
    
    marker += "\n\n*Please provide your answer below...*"
    
    # Return marker - Streamlit will handle the actual waiting
    return marker


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
    
    # Define tools - only high-level orchestration tools
    tools = [
        list_excel_files,      # To see what files are available
        run_pipeline,          # To process a single file
        run_batch_pipeline,    # To process all files at once
        ask_human             # To ask for human input when uncertain
    ]
    
    # Create system message
    system_message = """You are an Excel processing assistant with autonomous capabilities.

**Your Tools:**
1. **list_excel_files** - List all Excel files in the data directory
2. **run_pipeline** - Process a SINGLE file through the full workflow (read → analyze → extract)
3. **run_batch_pipeline** - Process ALL files at once
4. **ask_human** - Ask for human input or confirmation when uncertain

**The Pipeline:**
Each pipeline run automatically:
- Reads the Excel file and all sheets
- Uses AI to identify order number and cost columns
- Extracts the data
- Saves results to CSV

You don't need to do these steps manually - just call run_pipeline or run_batch_pipeline.

**When to use ask_human:**
- When the pipeline reports low/medium confidence in column detection
- When there are errors or unclear situations
- When the user explicitly asks you to confirm before proceeding
- When you need to make a decision between multiple options

**Processing modes:**
- **Fully Automatic**: Use run_batch_pipeline(auto_mode=True, require_high_confidence=False)
  → Processes everything without stopping
  
- **Ask When Unsure**: Use run_batch_pipeline(auto_mode=False, require_high_confidence=True)
  → Stops and uses ask_human for files with low/medium confidence
  
- **Manual Review**: Process files one by one with run_pipeline, then ask_human for each result

**Best practices:**
- When user says "process files" or clicks "Start Processing", use run_batch_pipeline
- When user mentions a specific file, use run_pipeline for that file
- Always explain what you're doing and show clear results
- Use ask_human proactively when confidence is not high
- Remember the conversation history and context"""
    
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

