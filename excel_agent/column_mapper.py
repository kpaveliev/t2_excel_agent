"""Module for mapping columns using LLM."""

from typing import List, Dict, Optional
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field


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

{format_instructions}"""),
        ("user", """Here is the information about the Excel file:

File: {filename}

Available sheets: {sheets}

Sheet: {current_sheet}
Columns in this sheet: {columns}

Data preview:
{preview}

Please identify which columns correspond to:
1. Order/Application Number (Номер заявки)
2. Total Cost (Итоговая Стоимость Заявки)

Return the exact column names from the list above.""")
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
    result = llm_chain.invoke({
        "filename": filename,
        "sheets": ", ".join(sheets),
        "current_sheet": current_sheet,
        "columns": ", ".join(columns),
        "preview": preview,
        "format_instructions": PydanticOutputParser(pydantic_object=ColumnMapping).get_format_instructions()
    })
    
    return result

