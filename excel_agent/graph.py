"""LangGraph workflow для обработки Excel файлов - обновленная версия с извлечением всех полей."""

from typing import TypedDict, List, Dict, Optional
from pathlib import Path
import pandas as pd
from langgraph.graph import StateGraph, END
from excel_agent.excel_reader import (
    read_excel_file,
    extract_all_columns,
    get_sheet_preview
)
from excel_agent.column_mapper_v2 import create_extended_column_mapper, find_all_columns
from excel_agent.config import MODEL_NAME, TEMPERATURE, logger


class ExcelProcessingState(TypedDict):
    """Состояние для workflow обработки Excel."""
    file_path: Path
    filename: str
    sheets_data: Dict[str, pd.DataFrame]
    all_columns: List[str]
    column_mapping: Optional[Dict]  # Теперь содержит все 13+ полей
    extracted_data: Optional[pd.DataFrame]  # DataFrame с всеми найденными колонками
    error: Optional[str]
    # Метаданные из UI
    branch_code: Optional[str]
    contractor_name: Optional[str]


def read_file_node(state: ExcelProcessingState) -> ExcelProcessingState:
    """Узел для чтения Excel файла и извлечения листов."""
    logger.info(f"📖 Шаг 1/3: Чтение файла '{state['filename']}'...")
    try:
        file_path = state["file_path"]
        sheets_data = read_excel_file(file_path)
        all_columns = extract_all_columns(sheets_data)
        
        logger.info(f"✓ Найдено {len(sheets_data)} лист(ов) с {len(all_columns)} уникальными колонками")
        
        return {
            **state,
            "sheets_data": sheets_data,
            "all_columns": all_columns,
            "error": None
        }
    except Exception as e:
        logger.error(f"✗ Ошибка чтения файла: {str(e)}")
        return {
            **state,
            "error": f"Ошибка чтения файла: {str(e)}"
        }


def find_columns_node(state: ExcelProcessingState) -> ExcelProcessingState:
    """Узел для поиска всех релевантных колонок с помощью LLM."""
    logger.info(f"🔍 Шаг 2/3: Анализ структуры с помощью LLM...")
    try:
        sheets_data = state["sheets_data"]
        filename = state["filename"]
        
        # Создаем LLM chain для расширенного маппинга
        llm_chain = create_extended_column_mapper(MODEL_NAME, TEMPERATURE)
        
        # Ищем лучший лист с данными
        best_mapping = None
        best_confidence = None
        
        for sheet_name, df in sheets_data.items():
            logger.info(f"  → Анализ листа: '{sheet_name}'")
            columns = [col for col in df.columns if not str(col).startswith('Unnamed')]
            
            if not columns:
                logger.warning(f"  → Нет именованных колонок в листе '{sheet_name}', пропускаем")
                continue
            
            logger.info(f"  → Найдено {len(columns)} колонок")
            
            preview = get_sheet_preview(df, n_rows=10)
            
            # Используем новую функцию поиска всех колонок
            mapping = find_all_columns(
                filename=filename,
                sheets=list(sheets_data.keys()),
                current_sheet=sheet_name,
                columns=columns,
                preview=preview,
                llm_chain=llm_chain
            )
            
            logger.info(f"  → LLM вернул: request_number='{mapping.request_number}', "
                       f"request_final_cost='{mapping.request_final_cost}'")
            logger.info(f"  → Уверенность: {mapping.confidence}")
            
            # Проверяем что обязательные колонки действительно существуют
            valid_mapping = True
            if mapping.request_number and mapping.request_number not in columns:
                logger.warning(f"  ⚠️  Колонка заявки '{mapping.request_number}' не в доступных колонках!")
                valid_mapping = False
            
            if mapping.request_final_cost and mapping.request_final_cost not in columns:
                logger.warning(f"  ⚠️  Колонка стоимости '{mapping.request_final_cost}' не в доступных колонках!")
                valid_mapping = False
            
            # Оставляем маппинг с наивысшей уверенностью
            if valid_mapping and mapping.request_number and mapping.request_final_cost:
                if best_confidence is None or mapping.confidence == "high":
                    # Конвертируем Pydantic model в dict для state
                    best_mapping = mapping.dict()
                    best_mapping["sheet_name"] = sheet_name
                    best_confidence = mapping.confidence
                    
                    # Логируем все найденные поля
                    found_fields = [k for k, v in best_mapping.items() 
                                   if v and k not in ['sheet_name', 'confidence', 'reasoning']]
                    logger.info(f"  → Найдено {len(found_fields)} полей: {', '.join(found_fields[:5])}")
                    
                    if mapping.confidence == "high":
                        break
        
        if best_mapping:
            logger.info(f"✓ Найдены колонки в листе '{best_mapping['sheet_name']}'")
            logger.info(f"  → Обязательные: request_number, request_final_cost")
            optional_found = [k for k, v in best_mapping.items() 
                             if v and k not in ['sheet_name', 'confidence', 'reasoning', 
                                               'request_number', 'request_final_cost']]
            if optional_found:
                logger.info(f"  → Опциональные ({len(optional_found)}): {', '.join(optional_found[:3])}...")
        else:
            logger.warning("✗ Не удалось найти обязательные колонки")
        
        return {
            **state,
            "column_mapping": best_mapping,
            "error": None if best_mapping else "Не удалось найти обязательные колонки (номер заявки и стоимость)"
        }
    except Exception as e:
        logger.error(f"✗ Ошибка поиска колонок: {str(e)}")
        return {
            **state,
            "error": f"Ошибка поиска колонок: {str(e)}"
        }


def extract_data_node(state: ExcelProcessingState) -> ExcelProcessingState:
    """Узел для извлечения всех данных из найденных колонок."""
    logger.info(f"📊 Шаг 3/3: Извлечение данных...")
    try:
        if state.get("error"):
            return state
        
        mapping = state["column_mapping"]
        if not mapping:
            logger.error("✗ Нет маппинга колонок")
            return {
                **state,
                "error": "Нет маппинга колонок"
            }
        
        sheet_name = mapping["sheet_name"]
        df = state["sheets_data"][sheet_name]
        
        logger.info(f"  → Извлечение из листа '{sheet_name}'")
        
        # Извлекаем все найденные колонки
        extracted_dict = {}
        field_count = 0
        
        # Список всех возможных полей (кроме служебных)
        all_fields = [
            'object_code', 'object_distance_km', 'request_number', 'request_datetime',
            'contractor_arrival_datetime', 'contractor_departure_datetime',
            'work_item_number', 'work_name', 'work_description',
            'avr_cancellation_price', 'request_work_cost', 'request_total_cost',
            'request_final_cost'
        ]
        
        for field in all_fields:
            if mapping.get(field) and mapping[field] in df.columns:
                extracted_dict[field] = df[mapping[field]]
                field_count += 1
                logger.debug(f"  → Поле '{field}' из колонки '{mapping[field]}'")
        
        if not extracted_dict:
            logger.error("✗ Не извлечено ни одного поля")
            return {
                **state,
                "error": "Не удалось извлечь данные"
            }
        
        # Создаем DataFrame
        extracted_df = pd.DataFrame(extracted_dict)
        
        # Удаляем строки где нет обязательных полей
        before_count = len(extracted_df)
        if 'request_number' in extracted_df.columns and 'request_final_cost' in extracted_df.columns:
            extracted_df = extracted_df.dropna(subset=['request_number', 'request_final_cost'])
        else:
            extracted_df = extracted_df.dropna()
        
        after_count = len(extracted_df)
        
        if before_count > after_count:
            logger.info(f"  → Удалено {before_count - after_count} строк с пустыми обязательными полями")
        
        logger.info(f"✓ Извлечено {len(extracted_df)} строк с {field_count} полями")
        
        return {
            **state,
            "extracted_data": extracted_df,
            "error": None
        }
    except Exception as e:
        logger.error(f"✗ Ошибка извлечения данных: {str(e)}", exc_info=True)
        return {
            **state,
            "error": f"Ошибка извлечения данных: {str(e)}"
        }


def create_excel_processing_graph():
    """Создать LangGraph workflow для обработки Excel файлов."""
    workflow = StateGraph(ExcelProcessingState)
    
    # Добавляем узлы
    workflow.add_node("read_file", read_file_node)
    workflow.add_node("find_columns", find_columns_node)
    workflow.add_node("extract_data", extract_data_node)
    
    # Добавляем связи
    workflow.set_entry_point("read_file")
    workflow.add_edge("read_file", "find_columns")
    workflow.add_edge("find_columns", "extract_data")
    workflow.add_edge("extract_data", END)
    
    return workflow.compile()


def process_excel_file(file_path: Path, branch_code: str = None, contractor_name: str = None) -> Dict:
    """
    Обработать один Excel файл через workflow.
    
    Args:
        file_path: Путь к Excel файлу
        branch_code: Код филиала (опционально, для метаданных)
        contractor_name: Наименование подрядчика (опционально, для метаданных)
        
    Returns:
        Dictionary с результатами обработки
    """
    graph = create_excel_processing_graph()
    
    initial_state = {
        "file_path": file_path,
        "filename": file_path.name,
        "sheets_data": {},
        "all_columns": [],
        "column_mapping": None,
        "extracted_data": None,
        "error": None,
        "branch_code": branch_code,
        "contractor_name": contractor_name
    }
    
    result = graph.invoke(initial_state)
    return result
