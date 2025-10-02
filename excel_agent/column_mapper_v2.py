"""Модуль для маппинга колонок с использованием LLM - версия для всех полей."""

from typing import List, Dict, Optional
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from excel_agent.config import logger, TARGET_COLUMNS_RU


class ExtendedColumnMapping(BaseModel):
    """Модель для результатов маппинга колонок."""
    
    # Обязательные поля
    request_number: Optional[str] = Field(
        description="Колонка с номером заявки"
    )
    request_final_cost: Optional[str] = Field(
        description="Колонка с итоговой стоимостью заявки"
    )
    
    # Опциональные поля объекта
    object_code: Optional[str] = Field(
        description="Колонка с номером объекта"
    )
    object_distance_km: Optional[str] = Field(
        description="Колонка с расстоянием до объекта в км"
    )
    
    # Опциональные поля времени
    request_datetime: Optional[str] = Field(
        description="Колонка с датой и временем заявки"
    )
    contractor_arrival_datetime: Optional[str] = Field(
        description="Колонка с датой и временем прибытия подрядчика"
    )
    contractor_departure_datetime: Optional[str] = Field(
        description="Колонка с датой и временем убытия подрядчика"
    )
    
    # Опциональные поля работ
    work_item_number: Optional[str] = Field(
        description="Колонка с номером пункта работ"
    )
    work_name: Optional[str] = Field(
        description="Колонка с наименованием работ"
    )
    work_description: Optional[str] = Field(
        description="Колонка с описанием выполненных работ"
    )
    
    # Опциональные поля стоимости
    avr_cancellation_price: Optional[str] = Field(
        description="Колонка со стоимостью отмены АВР"
    )
    request_work_cost: Optional[str] = Field(
        description="Колонка со стоимостью работ в заявке"
    )
    request_total_cost: Optional[str] = Field(
        description="Колонка с общей стоимостью заявки"
    )
    
    # Метаданные
    sheet_name: Optional[str] = Field(
        description="Название листа с данными"
    )
    confidence: str = Field(
        description="Уровень уверенности: high, medium, low"
    )
    reasoning: Optional[str] = Field(
        description="Обоснование выбора колонок"
    )


def create_extended_column_mapper(model_name: str = "gpt-4o-mini", temperature: float = 0):
    """Создать LLM-маппер для всех колонок."""
    llm = ChatOpenAI(model=model_name, temperature=temperature)
    
    parser = PydanticOutputParser(pydantic_object=ExtendedColumnMapping)
    
    # Формируем список ожидаемых названий для промпта
    expected_names = []
    for field, variants in TARGET_COLUMNS_RU.items():
        expected_names.append(f"- {field}: {', '.join(variants[:3])}")
    expected_text = "\n".join(expected_names)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", f"""Ты эксперт по анализу структуры Excel файлов.

Твоя задача - определить, какие колонки в таблице соответствуют следующим полям:

ОБЯЗАТЕЛЬНЫЕ ПОЛЯ:
- request_number (Номер заявки) - обычно содержит ID, номера заявок
- request_final_cost (Итоговая стоимость заявки) - итоговая сумма с учетом всех надбавок/скидок

ОПЦИОНАЛЬНЫЕ ПОЛЯ (ищи только если есть):
- object_code (Номер объекта)
- object_distance_km (Расстояние до объекта в км)
- request_datetime (Дата и время заявки)
- contractor_arrival_datetime (Дата прибытия подрядчика на объект)
- contractor_departure_datetime (Дата убытия подрядчика с объекта)
- work_item_number (Номер пункта работ)
- work_name (Наименование работ)
- work_description (Описание фактически выполненных работ)
- avr_cancellation_price (Стоимость отмены АВР)
- request_work_cost (Стоимость работ в заявке)
- request_total_cost (Общая стоимость заявки с километражем и материалами)

Возможные названия колонок:
{expected_text}

КРИТИЧЕСКИ ВАЖНО:
- Возвращай ТОЧНОЕ название колонки из списка "Доступные колонки"
- НЕ возвращай целевые названия типа "Номер заявки"
- Ищи похожие по смыслу названия, не только точные совпадения
- Если колонка не найдена, оставь поле пустым (null)
- Обязательно заполни request_number и request_final_cost

{{format_instructions}}"""),
        ("user", """Информация об Excel файле:

Файл: {filename}

Доступные листы: {sheets}

Текущий лист: {current_sheet}

Доступные колонки в этом листе:
{columns}

Превью данных (первые строки):
{preview}

Определи, какие ТОЧНЫЕ названия колонок из списка "Доступные колонки" соответствуют целевым полям.
Верни только те колонки, которые действительно присутствуют в списке.""")
    ])
    
    chain = prompt | llm | parser
    return chain


def find_all_columns(
    filename: str,
    sheets: List[str],
    current_sheet: str,
    columns: List[str],
    preview: str,
    llm_chain
) -> ExtendedColumnMapping:
    """
    Использовать LLM для поиска всех релевантных колонок.
    
    Args:
        filename: Имя Excel файла
        sheets: Список всех листов
        current_sheet: Текущий анализируемый лист
        columns: Список названий колонок
        preview: Превью данных
        llm_chain: LangChain цепочка для маппинга
        
    Returns:
        ExtendedColumnMapping с найденными колонками
    """
    logger.debug(f"Отправка запроса к LLM для листа '{current_sheet}' с {len(columns)} колонками")
    
    # Создаем parser для format_instructions
    parser = PydanticOutputParser(pydantic_object=ExtendedColumnMapping)
    
    result = llm_chain.invoke({
        "filename": filename,
        "sheets": ", ".join(sheets),
        "current_sheet": current_sheet,
        "columns": ", ".join(columns),
        "preview": preview,
        "format_instructions": parser.get_format_instructions()
    })
    
    logger.debug(f"LLM вернул: request_number='{result.request_number}', "
                f"request_final_cost='{result.request_final_cost}', "
                f"confidence='{result.confidence}'")
    
    return result

