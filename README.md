# 📊 Excel Agent

An intelligent tool for extracting data from multiple Excel files with varying structures using AI.

## Version history

- v0.1 - работающий простой пайплайн
- v0.2 - описание БД
- v0.3 - агент с инструментами и чатом

## 🎯 Purpose

Process multiple Excel files that have similar information but different structures:
- Files and sheets may be named differently
- Columns with relevant information may have slightly different names
- Tables could start from different lines
- Some cells could be merged

The tool extracts the following columns from each file:
- **Номер заявки** (Order/Application Number)
- **Итоговая Стоимость Заявки** (Total Cost)
- **Filename** (automatically added)

## 🏗️ Architecture

The application uses:
- **Streamlit** for the web interface
- **LangGraph** for workflow orchestration (StateGraph + React Agent)
- **LangChain + OpenAI** for intelligent column detection
- **Pandas** for data processing

### Two Agent Implementations:

#### 1. Batch Processing (StateGraph Workflow)
Linear workflow with fixed steps:
1. **read_file** - Reads Excel files and extracts all sheets
2. **find_columns** - Uses LLM to identify relevant columns despite naming variations
3. **extract_data** - Extracts and normalizes data from identified columns

#### 2. Chat Interface (React Agent)
Dynamic agent with 6 tools that can be called as needed:
- `list_excel_files` - List all Excel files
- `get_excel_sheets` - Get sheets from a file
- `get_sheet_columns` - Get columns from a sheet
- `preview_sheet_data` - Preview data
- `find_columns_with_llm` - AI-powered column identification
- `extract_data` - Extract and save data

The React Agent uses the ReAct (Reasoning + Acting) pattern to dynamically select and execute tools based on user requests.

## 🚀 Setup

### 1. Create and activate virtual environment

```bash
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
# OR
venv\Scripts\activate  # On Windows
```

### 2. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure environment variables

Create a `.env` file in the project root (or copy from `.env.example`):

```bash
cp .env.example .env
```

Edit `.env` and add your OpenAI API key:

```
OPENAI_API_KEY=your_openai_api_key_here
MODEL_NAME=gpt-4o-mini
TEMPERATURE=0
```

### 4. Add Excel files

Place your Excel files (`.xlsx` or `.xls`) in the `data/` directory, or upload them through the web interface.

## 💻 Usage

### Two Interfaces Available

This project now has **two ways** to interact with the Excel Agent:

1. **Batch Processing Interface** (`app.py`) - Process multiple files at once
2. **Chat Interface** (`chat_app.py`) - **NEW!** Conversational AI assistant

### Option 1: Batch Processing Interface

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

#### Using the batch interface

1. **Upload Files** (optional):
   - Go to the "Upload Files" tab
   - Select one or more Excel files
   - Click "Save to Data Folder"

2. **Process Files**:
   - Go to the "Process Files" tab
   - Review the list of files to be processed
   - Click "Process All Files"
   - View the results for each file
   - Download the combined CSV output

### Option 2: Chat Interface (NEW! ✨)

```bash
streamlit run chat_app.py
```

The chat interface will open at `http://localhost:8501` (or 8502 if running both)

#### Using the chat interface

Chat naturally with an AI assistant that can:
- 📋 List and explore Excel files
- 🔍 Identify relevant columns using AI
- 📊 Extract and save data interactively
- 💡 Provide guidance and insights

**Example conversation:**
```
You: List all Excel files
Agent: Found 3 Excel files: [shows list]

You: Show me the sheets in report.xlsx
Agent: [displays sheets with row counts]

You: Find order numbers and costs in Sheet1
Agent: [uses AI to identify columns]

You: Extract that data
Agent: [extracts and saves to CSV]
```

See [CHAT_INTERFACE_README.md](CHAT_INTERFACE_README.md) for detailed documentation.

### Running Both Interfaces Simultaneously

```bash
# Terminal 1: Batch processing
streamlit run app.py --server.port 8501

# Terminal 2: Chat interface
streamlit run chat_app.py --server.port 8502
```

### Output

- Results are saved to `output/combined_results.csv`
- The CSV contains three columns:
  - `Filename` - Source file name
  - `Номер заявки` - Order/Application number
  - `Итоговая Стоимость Заявки` - Total cost

## 📁 Project Structure

```
excel_agent/
├── excel_agent/          # Main package
│   ├── __init__.py
│   ├── config.py         # Configuration and settings
│   ├── excel_reader.py   # Excel file reading utilities
│   ├── column_mapper.py  # LLM-based column mapping
│   ├── graph.py          # StateGraph workflow (batch processing)
│   └── react_agent.py    # React Agent with tools (chat interface) ✨ NEW
├── tests/                # Test files
├── data/                 # Input Excel files (created automatically)
├── output/               # Output CSV files (created automatically)
├── app.py                # Streamlit batch processing app
├── chat_app.py           # Streamlit chat interface ✨ NEW
├── requirements.txt      # Python dependencies
├── .env                  # Environment variables (create this)
├── .env.example          # Example environment file
├── README.md             # This file
└── CHAT_INTERFACE_README.md  # Chat interface documentation ✨ NEW
```

## 🛠️ Development

### Run tests

```bash
pytest tests/
```

### Code formatting

```bash
black excel_agent/ app.py
```

### Linting

```bash
flake8 excel_agent/ app.py
```

## 🔧 Configuration

Edit `excel_agent/config.py` to customize:
- Data and output directories
- Target column names
- LLM model and parameters

## 📝 How It Works

1. **File Reading**: The system reads all sheets from each Excel file
2. **Column Detection**: An LLM analyzes the structure and identifies columns that match the target columns (even if they have slightly different names)
3. **Data Extraction**: Relevant data is extracted and normalized
4. **Output**: All results are combined into a single CSV file

The LLM uses context from:
- Available sheet names
- Column names in each sheet
- Preview of actual data (first 10 rows)

This allows it to handle variations in file structure intelligently.

## 🤝 Contributing

Feel free to submit issues and enhancement requests!

## 📄 License

This project is for internal use.
