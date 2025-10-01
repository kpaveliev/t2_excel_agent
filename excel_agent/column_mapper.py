"""Module for mapping columns using LLM."""

from typing import List, Dict, Optional
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from excel_agent.config import logger


class ColumnMapping(BaseModel):
    """Model for column mapping results."""
    order_number_column: Optional[str] = Field(
        description="The column name that contains order/application numbers (Номер заявки)"
    )
    total_cost_column: Optional[str] = Field(
        description="The column name that contains total cost/price (Итоговая Стоимость Заявки)"
    )
    sheet_name: Optional[str] = Field(
        description="The name of the sheet that contains the data"
    )
    confidence: str = Field(
        description="Confidence level: high, medium, or low"
    )


def create_column_mapper(model_name: str = "gpt-4o-mini", temperature: float = 0):
    """Create an LLM-based column mapper."""
    llm = ChatOpenAI(model=model_name, temperature=temperature)
    
    parser = PydanticOutputParser(pydantic_object=ColumnMapping)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert at analyzing Excel file structures.
Your task is to identify which columns in the spreadsheet correspond to:
1. Order/Application Number (Номер заявки) - usually contains IDs, numbers, or order references
2. Total Cost (Итоговая Стоимость Заявки) - usually contains prices, costs, or monetary values

The column names might be slightly different but have similar meaning.
Analyze the available columns and the data preview to make the best match.

CRITICAL INSTRUCTIONS:
- You MUST return the EXACT column name from the "Columns in this sheet" list
- Do NOT return the target names like "Номер заявки" or "Итоговая Стоимость Заявки"
- Return the ACTUAL column name that exists in the Excel file
- Look for similar meanings, not exact text matches
- Column names might have slight variations, extra spaces, or different wording

{format_instructions}"""),
        ("user", """Here is the information about the Excel file:

File: {filename}

Available sheets: {sheets}

Sheet: {current_sheet}

Columns available in this sheet:
{columns}

Data preview (first few rows):
{preview}

Please identify which EXACT column names from the "Columns available" list above correspond to:
1. Order/Application Number (Номер заявки) - look for columns with IDs, order numbers, application numbers
2. Total Cost (Итоговая Стоимость Заявки) - look for columns with prices, costs, total amounts

Return ONLY the exact column names as they appear in the list above, not the target names.""")
    ])
    
    chain = prompt | llm | parser
    return chain


def find_relevant_columns(
    filename: str,
    sheets: List[str],
    current_sheet: str,
    columns: List[str],
    preview: str,
    llm_chain
) -> ColumnMapping:
    """
    Use LLM to find relevant columns in the Excel file.
    
    Args:
        filename: Name of the Excel file
        sheets: List of all sheet names
        current_sheet: Current sheet being analyzed
        columns: List of column names in current sheet
        preview: Preview of the data
        llm_chain: LangChain chain for mapping
        
    Returns:
        ColumnMapping object with identified columns
    """
    logger.debug(f"Sending LLM request for sheet '{current_sheet}' with {len(columns)} columns")
    
    result = llm_chain.invoke({
        "filename": filename,
        "sheets": ", ".join(sheets),
        "current_sheet": current_sheet,
        "columns": ", ".join(columns),
        "preview": preview,
        "format_instructions": PydanticOutputParser(pydantic_object=ColumnMapping).get_format_instructions()
    })
    
    logger.debug(f"LLM returned: order='{result.order_number_column}', cost='{result.total_cost_column}', confidence='{result.confidence}'")
    
    return result

