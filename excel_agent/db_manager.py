"""Модуль для работы с базой данных DuckDB."""

import os
import duckdb
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from dotenv import load_dotenv
from excel_agent.config import logger

load_dotenv()

# Путь к БД из переменных окружения
DB_PATH = os.getenv("DUCKDB_PATH", "db/excel_data.duckdb")


class DatabaseManager:
    """Менеджер для работы с БД DuckDB."""
    
    def __init__(self, db_path: str = DB_PATH):
        """Инициализация менеджера БД.
        
        Args:
            db_path: Путь к файлу базы данных
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"📊 Подключение к БД: {self.db_path}")
    
    def get_connection(self):
        """Получить соединение с БД."""
        return duckdb.connect(str(self.db_path))
    
    def save_processed_data(
        self,
        filename: str,
        data: pd.DataFrame,
        branch_code: str,
        contractor_name: str,
        column_mapping: Dict[str, str],
        period: Optional[str] = None
    ) -> int:
        """Сохранить обработанные данные в БД.
        
        Args:
            filename: Имя исходного файла
            data: DataFrame с извлеченными данными
            branch_code: Код филиала
            contractor_name: Наименование подрядчика
            column_mapping: Маппинг колонок (исходное имя -> стандартное)
            period: Отчетный период (дата в формате 'YYYY-MM-DD' или datetime)
        
        Returns:
            Количество вставленных записей
        """
        conn = self.get_connection()
        
        try:
            # Подготовка данных для вставки
            records = []
            
            for _, row in data.iterrows():
                record = {
                    'filename': filename,
                    'period': period,
                    'branch_code': branch_code,
                    'counterparty': contractor_name,
                    'object_code': self._get_value(row, column_mapping, 'object_code'),
                    'object_distance_km': self._get_numeric_value(row, column_mapping, 'object_distance_km'),
                    'request_number': self._get_value(row, column_mapping, 'request_number'),
                    'request_datetime': self._get_datetime_value(row, column_mapping, 'request_datetime'),
                    'contractor_arrival_datetime': self._get_datetime_value(row, column_mapping, 'contractor_arrival_datetime'),
                    'contractor_departure_datetime': self._get_datetime_value(row, column_mapping, 'contractor_departure_datetime'),
                    'work_item_number': self._get_value(row, column_mapping, 'work_item_number'),
                    'work_name': self._get_value(row, column_mapping, 'work_name'),
                    'work_description': self._get_value(row, column_mapping, 'work_description'),
                    'avr_cancellation_price': self._get_numeric_value(row, column_mapping, 'avr_cancellation_price'),
                    'request_work_cost': self._get_numeric_value(row, column_mapping, 'request_work_cost'),
                    'request_total_cost': self._get_numeric_value(row, column_mapping, 'request_total_cost'),
                    'request_final_cost': self._get_numeric_value(row, column_mapping, 'request_final_cost'),
                }
                records.append(record)
            
            if not records:
                logger.warning("⚠️ Нет данных для сохранения")
                return 0
            
            # Преобразуем в DataFrame для массовой вставки
            df_to_insert = pd.DataFrame(records)
            
            # Вставка в БД
            # Зарегистрировать временную таблицу из DataFrame для использования в SQL
            conn.register("df_to_insert", df_to_insert)
            conn.execute("""
                INSERT INTO processed_requests (
                    filename, period, branch_code, counterparty, object_code, object_distance_km,
                    request_number, request_datetime, contractor_arrival_datetime,
                    contractor_departure_datetime, work_item_number, work_name,
                    work_description, avr_cancellation_price, request_work_cost,
                    request_total_cost, request_final_cost
                )
                SELECT * FROM df_to_insert
            """)
            
            inserted_count = len(records)
            logger.info(f"✅ Сохранено {inserted_count} записей в БД")
            
            return inserted_count
            
        except Exception as e:
            logger.error(f"❌ Ошибка при сохранении в БД: {str(e)}", exc_info=True)
            raise
        finally:
            conn.close()
    
    def _get_value(self, row: pd.Series, mapping: Dict[str, str], field: str) -> Optional[str]:
        """Получить значение поля из строки.
        
        Примечание: в `extracted_data` названия колонок уже нормализованы под имена полей
        (request_number, object_code и т.д.), поэтому читаем напрямую по `field`.
        """
        if field in row.index:
            value = row[field]
            return str(value) if pd.notna(value) else None
        return None
    
    def _get_numeric_value(self, row: pd.Series, mapping: Dict[str, str], field: str) -> Optional[float]:
        """Получить числовое значение поля."""
        if field in row.index:
            value = row[field]
            if pd.notna(value):
                try:
                    return float(value)
                except (ValueError, TypeError):
                    return None
        return None
    
    def _get_datetime_value(self, row: pd.Series, mapping: Dict[str, str], field: str) -> Optional[datetime]:
        """Получить datetime значение поля."""
        if field in row.index:
            value = row[field]
            if pd.notna(value):
                try:
                    if isinstance(value, datetime):
                        return value
                    return pd.to_datetime(value)
                except (ValueError, TypeError):
                    return None
        return None
    
    def get_statistics(self) -> Dict[str, any]:
        """Получить статистику по БД."""
        conn = self.get_connection()
        
        try:
            stats = {}
            
            # Общее количество записей
            stats['total_records'] = conn.execute(
                "SELECT COUNT(*) FROM processed_requests"
            ).fetchone()[0]
            
            # Количество файлов
            stats['total_files'] = conn.execute(
                "SELECT COUNT(DISTINCT filename) FROM processed_requests"
            ).fetchone()[0]
            
            # Количество по филиалам
            branch_stats = conn.execute("""
                SELECT branch_code, COUNT(*) as count
                FROM processed_requests
                GROUP BY branch_code
                ORDER BY count DESC
            """).fetchall()
            stats['by_branch'] = {row[0]: row[1] for row in branch_stats}
            
            # Последние обработанные файлы
            recent_files = conn.execute("""
                SELECT DISTINCT filename, MAX(created_at) as last_processed
                FROM processed_requests
                GROUP BY filename
                ORDER BY last_processed DESC
                LIMIT 5
            """).fetchall()
            stats['recent_files'] = [
                {'filename': row[0], 'processed_at': row[1]}
                for row in recent_files
            ]
            
            return stats
            
        finally:
            conn.close()
    
    def query_requests(
        self,
        branch_code: Optional[str] = None,
        contractor: Optional[str] = None,
        limit: int = 100
    ) -> pd.DataFrame:
        """Запросить заявки из БД с фильтрами."""
        conn = self.get_connection()
        
        try:
            query = "SELECT * FROM processed_requests WHERE 1=1"
            params = []
            
            if branch_code:
                query += " AND branch_code = ?"
                params.append(branch_code)
            
            if contractor:
                query += " AND counterparty LIKE ?"
                params.append(f"%{contractor}%")
            
            query += f" ORDER BY created_at DESC LIMIT {limit}"
            
            if params:
                result = conn.execute(query, params).fetchdf()
            else:
                result = conn.execute(query).fetchdf()
            
            return result
            
        finally:
            conn.close()


# Singleton instance
_db_manager = None


def get_db_manager() -> DatabaseManager:
    """Получить экземпляр менеджера БД."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager

