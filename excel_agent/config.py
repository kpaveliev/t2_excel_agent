"""Configuration settings for the Excel Agent."""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger('excel_agent')

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# OpenAI API configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Целевые колонки для извлечения (русские названия для поиска в Excel)
TARGET_COLUMNS_RU = {
    "object_code": ["Номер объекта", "№ объекта", "Объект", "Код объекта"],
    "object_distance_km": ["Расстояние до объекта", "Расстояние", "км", "Километраж"],
    "request_number": ["Номер заявки", "№ заявки", "Заявка"],
    "request_datetime": ["Дата заявки", "Дата и время заявки", "Дата"],
    "contractor_arrival_datetime": ["Дата прибытия", "Время прибытия", "Прибытие подрядчика"],
    "contractor_departure_datetime": ["Дата убытия", "Время убытия", "Уход подрядчика"],
    "work_item_number": ["№ п/п", "Номер работы", "№ работ"],
    "work_name": ["Наименование работ", "Название работ", "Работы"],
    "work_description": ["Описание работ", "Фактически выполненные работы"],
    "avr_cancellation_price": ["Отмена АВР", "Стоимость отмены"],
    "request_work_cost": ["Стоимость работ", "Стоимость"],
    "request_total_cost": ["Стоимость заявки", "Общая стоимость", "Сумма"],
    "request_final_cost": ["Итоговая стоимость", "Итого", "Финальная стоимость"],
}

# LLM configuration
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")
TEMPERATURE = float(os.getenv("TEMPERATURE", "0"))

# Chat configuration
DEFAULT_THREAD_ID = "excel_agent_chat_session"

