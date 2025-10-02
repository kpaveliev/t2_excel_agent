# Excel Agent Chat Interface

A conversational AI interface for processing Excel files using LangGraph's React Agent.

## Overview

This is a **separate** chat interface that uses LangGraph's `create_react_agent` with custom tools. It runs independently from the existing batch processing app (`app.py`) and can be merged later.

## Features

### 🤖 React Agent with Tools

The agent has access to 6 specialized tools:

1. **list_excel_files** - Lists all Excel files in the data directory
2. **get_excel_sheets** - Shows all sheets in a specific file
3. **get_sheet_columns** - Lists columns in a specific sheet
4. **preview_sheet_data** - Previews data from a sheet (configurable rows)
5. **find_columns_with_llm** - Uses AI to identify order number and cost columns
6. **extract_data** - Extracts data from specified columns and saves to CSV

### 💬 Chat Interface

- Natural language interaction with the agent
- Maintains conversation history
- Real-time tool execution feedback
- Quick action buttons in sidebar
- Example prompts for guidance

## Running the Chat Interface

### Start the Chat App

```bash
# Make sure you're in the project root
cd /Users/kpaveliev/PycharmProjects/t2/2025-09_excel_agent

# Activate virtual environment
source venv/bin/activate

# Run the chat interface
streamlit run chat_app.py
```

The chat interface will be available at `http://localhost:8501` (different from the main app if it's running).

### Running Both Apps Simultaneously

You can run both the original app and the chat interface at the same time on different ports:

```bash
# Terminal 1: Original batch processing app
streamlit run app.py --server.port 8501

# Terminal 2: Chat interface
streamlit run chat_app.py --server.port 8502
```

## Example Conversations

### Basic File Exploration

```
User: List all Excel files

Agent: Let me check the data directory for you...
[Uses list_excel_files tool]
Found 3 Excel files:
- Отчет 49_Орех_март_TU.xlsx
- Отчет АВР Opex март общ  2025г. к Дог. № АВР_ПАО БИС_2023-04.xlsx
- Отчет о выполнении работ  05. 2025 Oрex.xlsx
```

### Exploring a Specific File

```
User: Show me the sheets in Отчет 49_Орех_март_TU.xlsx

Agent: [Uses get_excel_sheets tool]
Excel file 'Отчет 49_Орех_март_TU.xlsx' contains 2 sheets:
- Sheet: 'Общий отчет' - 45 rows, 12 columns
- Sheet: 'Детализация' - 120 rows, 8 columns
```

### AI-Powered Column Identification

```
User: Find the order numbers and costs in the first sheet

Agent: [Uses find_columns_with_llm tool]
LLM Analysis Results:
- Order Number Column: Номер заявки
- Total Cost Column: Итоговая стоимость
- Confidence: high
- Reasoning: The column "Номер заявки" contains sequential numbers typical of order IDs...
```

### Data Extraction

```
User: Extract the data from those columns

Agent: [Uses extract_data tool]
Successfully extracted 45 rows from 'Отчет 49_Орех_март_TU.xlsx' - Sheet 'Общий отчет'

Data saved to: /path/to/output/extracted_Отчет_49_Орех_март_TU_Общий_отчет.csv
```

## Architecture

### React Agent Pattern

The agent uses LangGraph's `create_react_agent` which implements the ReAct (Reasoning + Acting) pattern:

1. **Thought** - Agent reasons about what to do
2. **Action** - Agent calls a tool
3. **Observation** - Agent observes tool output
4. **Repeat** - Continue until task is complete

### File Structure

```
excel_agent/
├── react_agent.py      # React agent with tools (NEW)
├── graph.py            # Original StateGraph workflow (UNCHANGED)
├── excel_reader.py     # Excel utilities (SHARED)
├── column_mapper.py    # LLM column mapping (SHARED)
└── config.py          # Configuration (SHARED)

chat_app.py            # Chat interface (NEW)
app.py                 # Original batch processing app (UNCHANGED)
```

## Key Differences from Original App

| Feature | Original App (`app.py`) | Chat Interface (`chat_app.py`) |
|---------|------------------------|--------------------------------|
| **Interaction** | Batch processing with buttons | Conversational chat |
| **Agent Type** | StateGraph workflow | React Agent with tools |
| **Processing** | All files at once | Interactive, file-by-file |
| **Flexibility** | Fixed workflow | Dynamic tool selection |
| **User Control** | Limited | High (can guide process) |
| **Output** | Combined CSV | Individual CSVs per request |

## Tools Details

### 1. list_excel_files

```python
@tool
def list_excel_files() -> str:
    """List all Excel files in the data directory."""
```

**Returns**: Formatted list of all `.xlsx` and `.xls` files

### 2. get_excel_sheets

```python
@tool
def get_excel_sheets(filename: str) -> str:
    """Get all sheet names from an Excel file."""
```

**Parameters**:
- `filename`: Name of the Excel file

**Returns**: Sheet names with row/column counts

### 3. get_sheet_columns

```python
@tool
def get_sheet_columns(filename: str, sheet_name: str) -> str:
    """Get all columns from a specific sheet."""
```

**Parameters**:
- `filename`: Name of the Excel file
- `sheet_name`: Name of the sheet

**Returns**: List of column names (excluding unnamed columns)

### 4. preview_sheet_data

```python
@tool
def preview_sheet_data(filename: str, sheet_name: str, num_rows: int = 5) -> str:
    """Preview data from a specific sheet."""
```

**Parameters**:
- `filename`: Name of the Excel file
- `sheet_name`: Name of the sheet
- `num_rows`: Number of rows to preview (default: 5)

**Returns**: Formatted data preview

### 5. find_columns_with_llm

```python
@tool
def find_columns_with_llm(filename: str, sheet_name: str) -> str:
    """Use LLM to identify relevant columns."""
```

**Parameters**:
- `filename`: Name of the Excel file
- `sheet_name`: Name of the sheet

**Returns**: Identified columns with confidence and reasoning

### 6. extract_data

```python
@tool
def extract_data(filename: str, sheet_name: str, order_column: str, cost_column: str) -> str:
    """Extract data from specific columns."""
```

**Parameters**:
- `filename`: Name of the Excel file
- `sheet_name`: Name of the sheet
- `order_column`: Name of the order number column
- `cost_column`: Name of the cost column

**Returns**: Extraction summary and CSV file path

## Configuration

The chat interface uses the same configuration as the main app:

```python
# .env file
OPENAI_API_KEY=your_api_key_here
MODEL_NAME=gpt-4o-mini  # or gpt-4
TEMPERATURE=0
```

## Next Steps (Merging)

When ready to merge with the existing app:

1. **Add tab to main app** - Add a "Chat" tab to `app.py`
2. **Unified interface** - Let users choose between batch processing and chat
3. **Shared state** - Share processing results between both interfaces
4. **Enhanced tools** - Add more tools for advanced analysis
5. **Memory** - Add conversation memory for better context

## Troubleshooting

### Agent not responding

- Check OpenAI API key is set correctly
- Verify network connection
- Check logs for errors

### Tool execution errors

- Ensure Excel files are in the `data/` directory
- Check file names match exactly (case-sensitive)
- Verify sheet names are correct

### Memory issues with large files

- Preview fewer rows using `num_rows` parameter
- Process sheets one at a time
- Use the batch processing app for large-scale operations

## Development

To add new tools:

1. Define a new function with `@tool` decorator in `react_agent.py`
2. Add it to the `tools` list in `create_excel_react_agent()`
3. Update documentation

Example:

```python
@tool
def calculate_statistics(filename: str, sheet_name: str, column: str) -> str:
    """Calculate statistics for a numeric column."""
    # Implementation here
    pass
```

## License

Same as the main project.

