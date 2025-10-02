"""React Agent для обработки Excel с использованием LangGraph's create_react_agent."""

from typing import List, Dict, Any, Optional
from pathlib import Path
import pandas as pd
import time
import os
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from excel_agent.config import OPENAI_API_KEY, MODEL_NAME, TEMPERATURE, DATA_DIR, OUTPUT_DIR, logger
from excel_agent.graph import process_excel_file as run_stategraph_pipeline
from excel_agent.db_manager import get_db_manager

# Глобальное хранилище для взаимодействия с человеком
_human_question_queue = []
_human_answer_queue = []


@tool
def list_excel_files() -> str:
    """Показать список всех Excel файлов в папке data.
    
    Returns:
        Отформатированная строка со списком найденных Excel файлов.
    """
    try:
        excel_files = list(DATA_DIR.glob("*.xlsx")) + list(DATA_DIR.glob("*.xls"))
        if not excel_files:
            return f"Excel файлы не найдены в {DATA_DIR}"
        
        file_list = "\n".join([f"- {f.name}" for f in excel_files])
        return f"Найдено {len(excel_files)} Excel файл(ов):\n{file_list}"
    except Exception as e:
        logger.error(f"Ошибка получения списка файлов: {str(e)}")
        return f"Ошибка получения списка: {str(e)}"


@tool
def run_pipeline(filename: str, branch_code: str, contractor_name: str, require_high_confidence: bool = False) -> str:
    """Запустить полный пайплайн обработки Excel файла.
    
    Этот инструмент выполняет полный StateGraph workflow (чтение → анализ → извлечение → сохранение в БД).
    
    Args:
        filename: Имя Excel файла для обработки
        branch_code: Код филиала
        contractor_name: Наименование подрядчика
        require_high_confidence: Если True, предупреждает при уверенности ниже "high"
    
    Returns:
        Результаты обработки или запрос на проверку человеком.
    """
    try:
        file_path = DATA_DIR / filename
        if not file_path.exists():
            return f"❌ Файл не найден: {filename}"
        
        logger.info(f"🚀 Запуск пайплайна для: {filename}")
        
        # Запускаем существующий StateGraph workflow с метаданными
        result = run_stategraph_pipeline(
            file_path=file_path,
            branch_code=branch_code,
            contractor_name=contractor_name
        )
        
        if result.get("error"):
            return f"❌ Ошибка обработки {filename}: {result['error']}"
        
        mapping = result.get("column_mapping", {})
        confidence = mapping.get("confidence", "low")
        extracted_data = result.get("extracted_data")
        
        # Строим сообщение с результатами
        result_msg = f"📊 Результаты обработки '{filename}':\n\n"
        result_msg += f"Лист: {mapping.get('sheet_name', 'Н/Д')}\n"
        result_msg += f"Уверенность: {confidence}\n"
        
        if extracted_data is not None and len(extracted_data) > 0:
            rows_count = len(extracted_data)
            result_msg += f"\n✅ Извлечено {rows_count} строк"
            
            # Сохраняем в БД
            try:
                db = get_db_manager()
                inserted = db.save_processed_data(
                    filename=filename,
                    data=extracted_data,
                    branch_code=branch_code,
                    contractor_name=contractor_name,
                    column_mapping=mapping
                )
                result_msg += f"\n💾 Сохранено {inserted} записей в базу данных"
            except Exception as db_error:
                logger.error(f"Ошибка сохранения в БД: {str(db_error)}")
                result_msg += f"\n⚠️ Предупреждение: Ошибка сохранения в БД: {str(db_error)}"
            
            # Показываем какие поля извлечены
            found_fields = [k for k, v in mapping.items() 
                           if v and k not in ['sheet_name', 'confidence', 'reasoning']]
            result_msg += f"\n\n📋 Извлечено полей: {len(found_fields)}"
            if found_fields:
                for field in found_fields[:5]:
                    result_msg += f"\n  • {field}"
                if len(found_fields) > 5:
                    result_msg += f"\n  ... и еще {len(found_fields) - 5}"
            
            # Проверяем уверенность
            if require_high_confidence and confidence != "high":
                result_msg += f"\n\n⚠️ Предупреждение: Уверенность '{confidence}' (не 'high'). "
                result_msg += "Возможно стоит проверить результаты."
        else:
            result_msg += "\n⚠️ Данные не извлечены"
        
        return result_msg
        
    except Exception as e:
        logger.error(f"Ошибка в run_pipeline: {str(e)}")
        return f"❌ Ошибка пайплайна: {str(e)}"


@tool
def run_batch_pipeline(
    filenames: Optional[List[str]] = None,
    branch_code: str = "",
    contractor_name: str = "",
    auto_mode: bool = True,
    require_high_confidence: bool = False
) -> str:
    """Запустить пайплайн для нескольких Excel файлов.
    
    Args:
        filenames: Список имен файлов для обработки. Если None, обрабатывает все файлы.
        branch_code: Код филиала
        contractor_name: Наименование подрядчика
        auto_mode: Если True, обрабатывает все файлы автоматически.
                   Если False, останавливается для проверки при низкой уверенности.
        require_high_confidence: Если True, помечает файлы с не-высокой уверенностью.
    
    Returns:
        Сводка результатов обработки всех файлов.
    """
    try:
        # Получаем список файлов
        if filenames:
            excel_files = [DATA_DIR / f for f in filenames if (DATA_DIR / f).exists()]
        else:
            excel_files = list(DATA_DIR.glob("*.xlsx")) + list(DATA_DIR.glob("*.xls"))
        
        if not excel_files:
            return "❌ Excel файлы не найдены"
        
        logger.info(f"🚀 Начало пакетной обработки {len(excel_files)} файл(ов)")
        
        results = []
        successful = 0
        needs_review = []
        errors = []
        total_rows = 0
        
        for file_path in excel_files:
            filename = file_path.name
            logger.info(f"Обработка: {filename}")
            
            result = run_stategraph_pipeline(
                file_path=file_path,
                branch_code=branch_code,
                contractor_name=contractor_name
            )
            
            if result.get("error"):
                errors.append(filename)
                results.append(f"❌ {filename}: {result['error']}")
            else:
                mapping = result.get("column_mapping", {})
                confidence = mapping.get("confidence", "low")
                extracted_data = result.get("extracted_data")
                
                if extracted_data is not None and len(extracted_data) > 0:
                    rows = len(extracted_data)
                    
                    # Сохраняем в БД
                    try:
                        db = get_db_manager()
                        inserted = db.save_processed_data(
                            filename=filename,
                            data=extracted_data,
                            branch_code=branch_code,
                            contractor_name=contractor_name,
                            column_mapping=mapping
                        )
                        total_rows += inserted
                    except Exception as db_error:
                        logger.error(f"Ошибка сохранения в БД для {filename}: {str(db_error)}")
                        errors.append(filename)
                        results.append(f"❌ {filename}: Ошибка сохранения в БД")
                        continue
                    
                    if confidence == "high":
                        successful += 1
                        results.append(f"✅ {filename}: {rows} строк (уверенность: {confidence})")
                    else:
                        if require_high_confidence or not auto_mode:
                            needs_review.append(filename)
                            results.append(f"⚠️ {filename}: {rows} строк (уверенность: {confidence}) - может требовать проверки")
                        else:
                            successful += 1
                            results.append(f"✅ {filename}: {rows} строк (уверенность: {confidence})")
                else:
                    errors.append(filename)
                    results.append(f"❌ {filename}: Данные не извлечены")
        
        # Строим сводку
        summary = f"📊 Пакетная обработка завершена!\n\n"
        summary += f"Всего файлов: {len(excel_files)}\n"
        summary += f"✅ Успешно: {successful}\n"
        summary += f"⚠️ Требуют проверки: {len(needs_review)}\n"
        summary += f"❌ Ошибки: {len(errors)}\n"
        summary += f"💾 Всего сохранено записей в БД: {total_rows}\n"
        
        summary += "\nДетали:\n" + "\n".join(results)
        
        if needs_review:
            summary += f"\n\n💡 Файлы которые могут требовать проверки:\n"
            summary += "\n".join([f"  - {f}" for f in needs_review])
            summary += "\n\nИспользуй инструмент 'ask_human' для получения подтверждения по этим файлам."
        
        return summary
        
    except Exception as e:
        logger.error(f"Ошибка в пакетной обработке: {str(e)}")
        return f"❌ Ошибка пакетной обработки: {str(e)}"


@tool
def ask_human(question: str, options: Optional[List[str]] = None, context: Optional[str] = None) -> str:
    """Задать вопрос пользователю и дождаться ответа.
    
    Этот инструмент приостанавливает выполнение агента и представляет вопрос пользователю в чат интерфейсе.
    Агент будет ждать ответа пользователя перед продолжением.
    
    Args:
        question: Вопрос для пользователя
        options: Опциональный список предлагаемых вариантов ответа
        context: Опциональный дополнительный контекст для помощи в принятии решения
    
    Returns:
        Ответ пользователя в виде строки
    
    Пример:
        ask_human(
            question="Какую колонку использовать для номеров заявок?",
            options=["Номер заявки", "№ заявки", "Order Number"],
            context="Файл: report.xlsx, Лист: Основной"
        )
    """
    global _human_question_queue, _human_answer_queue
    
    # Форматируем вопрос
    formatted_question = {
        "question": question,
        "options": options or [],
        "context": context,
        "timestamp": time.time()
    }
    
    # Добавляем в очередь вопросов
    _human_question_queue.append(formatted_question)
    
    logger.info(f"❓ Задан вопрос человеку: {question}")
    
    # Создаем маркер который Streamlit обнаружит
    marker = "🤔 **[ОЖИДАНИЕ ОТВЕТА ОТ ПОЛЬЗОВАТЕЛЯ]**"
    
    if context:
        marker += f"\n\n**Контекст:** {context}"
    
    marker += f"\n\n**Вопрос:** {question}"
    
    if options:
        marker += f"\n\n**Варианты:**\n"
        for i, opt in enumerate(options, 1):
            marker += f"{i}. {opt}\n"
    
    marker += "\n\n*Пожалуйста, предоставьте ваш ответ ниже...*"
    
    # Возвращаем маркер - Streamlit обработает ожидание
    return marker


def create_excel_react_agent():
    """Создать React агента с инструментами для обработки Excel и памятью.
    
    Returns:
        Скомпилированный LangGraph React агент с персистентной памятью.
    """
    # Инициализируем LLM
    llm = ChatOpenAI(
        model=MODEL_NAME,
        temperature=TEMPERATURE,
        api_key=OPENAI_API_KEY
    )
    
    # Определяем инструменты - только высокоуровневые инструменты оркестрации
    tools = [
        list_excel_files,      # Показать список файлов
        run_pipeline,          # Обработать один файл
        run_batch_pipeline,    # Обработать все файлы сразу
        ask_human             # Спросить человека при неопределенности
    ]
    
    # Добавляем SQL инструменты для работы с базой данных
    try:
        # Создаем собственные SQL инструменты используя db_manager
        from excel_agent.db_manager import get_db_manager
        
        @tool
        def sql_list_tables() -> str:
            """Показать список всех таблиц в базе данных DuckDB.
            
            Returns:
                Список таблиц в базе данных.
            """
            try:
                db = get_db_manager()
                conn = db.get_connection()
                tables = conn.execute("SHOW TABLES").fetchall()
                if not tables:
                    return "В базе данных нет таблиц."
                
                table_list = "\n".join([f"- {t[0]}" for t in tables])
                return f"Таблицы в базе данных:\n{table_list}"
            except Exception as e:
                return f"❌ Ошибка получения списка таблиц: {str(e)}"
        
        @tool
        def sql_get_schema(table_name: str) -> str:
            """Получить схему таблицы (названия колонок, типы данных, комментарии).
            
            Args:
                table_name: Имя таблицы для получения схемы
                
            Returns:
                Описание схемы таблицы с комментариями к колонкам.
            """
            try:
                db = get_db_manager()
                conn = db.get_connection()
                
                # Получаем структуру таблицы
                columns = conn.execute(f"DESCRIBE {table_name}").fetchdf()
                
                schema_info = f"Схема таблицы '{table_name}':\n\n"
                for _, row in columns.iterrows():
                    col_name = row['column_name']
                    col_type = row['column_type']
                    nullable = "NULL" if row['null'] == 'YES' else "NOT NULL"
                    schema_info += f"- {col_name}: {col_type} ({nullable})\n"
                
                # Пытаемся получить комментарии (если есть)
                try:
                    comments_query = f"""
                    SELECT column_name, comment
                    FROM duckdb_columns()
                    WHERE table_name = '{table_name}' AND comment IS NOT NULL
                    """
                    comments = conn.execute(comments_query).fetchdf()
                    if len(comments) > 0:
                        schema_info += "\nКомментарии к полям:\n"
                        for _, row in comments.iterrows():
                            schema_info += f"- {row['column_name']}: {row['comment']}\n"
                except:
                    pass  # Комментарии недоступны
                
                return schema_info
            except Exception as e:
                return f"❌ Ошибка получения схемы таблицы: {str(e)}"
        
        @tool
        def sql_query(query: str) -> str:
            """Выполнить SQL запрос к базе данных DuckDB.
            
            Поддерживаемые типы запросов:
            - SELECT - выборка данных
            - INSERT - вставка данных
            - UPDATE - обновление данных
            - DELETE - удаление данных
            - CREATE TABLE - создание таблиц
            - DROP TABLE - удаление таблиц
            - ALTER TABLE - изменение структуры таблиц
            
            ⚠️ ВАЖНО: 
            - Запросы DROP TABLE и DELETE требуют осторожности!
            - Всегда используй WHERE в UPDATE/DELETE для избежания изменения всех строк
            - Для массовых операций лучше сначала показать COUNT для проверки
            
            Args:
                query: SQL запрос для выполнения
                
            Returns:
                Результаты запроса или сообщение об успешном выполнении.
            """
            try:
                db = get_db_manager()
                conn = db.get_connection()
                
                # Определяем тип запроса
                query_upper = query.strip().upper()
                query_type = query_upper.split()[0] if query_upper else ""
                
                # Запрещаем опасные операции без явного подтверждения
                dangerous_patterns = [
                    "DROP DATABASE",
                    "DROP SCHEMA",
                    "TRUNCATE",
                ]
                
                for pattern in dangerous_patterns:
                    if pattern in query_upper:
                        return f"❌ Запрос содержит опасную операцию '{pattern}'. Эта операция запрещена для безопасности."
                
                # Предупреждения для потенциально опасных операций
                if query_type in ["DELETE", "UPDATE"] and "WHERE" not in query_upper:
                    return (
                        f"⚠️ ВНИМАНИЕ: {query_type} запрос без WHERE условия!\n"
                        f"Это изменит ВСЕ строки в таблице.\n"
                        f"Если вы уверены, добавьте 'WHERE 1=1' в конец запроса для подтверждения.\n"
                        f"Или используйте ask_human для подтверждения этой операции."
                    )
                
                # Выполняем запрос
                result = conn.execute(query)
                
                # Обрабатываем результаты в зависимости от типа запроса
                if query_type == "SELECT":
                    df = result.fetchdf()
                    
                    if len(df) == 0:
                        return "Запрос выполнен успешно, но не вернул результатов."
                    
                    # Ограничиваем вывод первыми 100 строками
                    if len(df) > 100:
                        result_str = df.head(100).to_string(index=False)
                        result_str += f"\n\n... и еще {len(df) - 100} строк"
                    else:
                        result_str = df.to_string(index=False)
                    
                    return f"Результаты запроса ({len(df)} строк):\n\n{result_str}"
                
                elif query_type in ["INSERT", "UPDATE", "DELETE"]:
                    # Для модифицирующих запросов возвращаем количество затронутых строк
                    try:
                        rows_affected = result.fetchone()
                        if rows_affected and len(rows_affected) > 0:
                            return f"✅ Запрос успешно выполнен. Затронуто строк: {rows_affected[0]}"
                        else:
                            return f"✅ Запрос {query_type} успешно выполнен."
                    except:
                        return f"✅ Запрос {query_type} успешно выполнен."
                
                elif query_type in ["CREATE", "DROP", "ALTER"]:
                    return f"✅ DDL запрос ({query_type}) успешно выполнен."
                
                else:
                    return f"✅ Запрос успешно выполнен."
                
            except Exception as e:
                return f"❌ Ошибка выполнения запроса: {str(e)}"
        
        # Добавляем SQL инструменты
        sql_tools = [sql_list_tables, sql_get_schema, sql_query]
        tools.extend(sql_tools)
        
        logger.info(f"✓ Добавлено SQL инструментов: {len(sql_tools)}")
        for sql_tool in sql_tools:
            logger.info(f"  - {sql_tool.name}")
        
    except Exception as e:
        logger.warning(f"⚠️ Не удалось подключить SQL инструменты: {str(e)}")
        logger.warning("   Агент будет работать без SQL инструментов")
    
    # Создаем системное сообщение
    system_message = """
Ты ассистент по обработке Excel файлов и работе с базой данных DuckDB.

**Твои основные инструменты:**
1. **list_excel_files** - Показать список всех Excel файлов в директории
2. **run_pipeline** - Обработать ОДИН файл через полный workflow (чтение → анализ → извлечение → сохранение в БД)
3. **run_batch_pipeline** - Обработать НЕСКОЛЬКО или ВСЕ файлы сразу
4. **ask_human** - Задать вопрос пользователю при неопределенности

**SQL инструменты:**
- **sql_list_tables** - Показать список всех таблиц в базе данных
- **sql_get_schema** - Получить схему таблицы (колонки, типы, комментарии)
- **sql_query** - Выполнить любой SQL запрос (SELECT, INSERT, UPDATE, DELETE, CREATE TABLE, DROP TABLE, ALTER TABLE и др.)

**Пайплайн обработки автоматически:**
- Читает Excel файл и все листы
- Использует AI для поиска 13+ полей данных
- Извлекает данные
- Сохраняет результаты в базу данных DuckDB (таблица processed_requests)

**Работа с SQL:**
- Поддерживаются все типы запросов: SELECT, INSERT, UPDATE, DELETE, CREATE TABLE, DROP TABLE, ALTER TABLE
- Запрещены опасные операции: DROP DATABASE, DROP SCHEMA, TRUNCATE
- DELETE и UPDATE без WHERE требуют явного подтверждения (добавь WHERE 1=1 или используй ask_human)
- Для массовых операций сначала показывай COUNT для проверки масштаба изменений
- Всегда изучай схему таблицы (sql_get_schema) перед запросами

**Лучшие практики:**
- Когда пользователь говорит "обработай файлы" или нажимает "Начать обработку", используй run_batch_pipeline
- Для конкретного файла используй run_pipeline
- **ВАЖНО:** Перед обработкой файла проверяй через sql_query, не был ли такой файл уже обработан (проверь filename в таблице processed_requests)
- Всегда объясняй что делаешь и показывай понятные результаты
- Используй ask_human проактивно при сомнениях или опасных операциях, не угадывай
- Помни историю разговора и контекст
- Отвечай на русском языке
"""
    
    # Создаем memory saver для персистентности разговора
    memory = MemorySaver()
    
    # Создаем агента с чекпоинтингом
    agent = create_react_agent(llm, tools, state_modifier=system_message, checkpointer=memory)
    
    logger.info("✓ React Agent создан успешно с памятью")
    return agent


# Singleton instance
_agent_instance = None


def get_react_agent():
    """Получить или создать экземпляр React агента."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = create_excel_react_agent()
    return _agent_instance
