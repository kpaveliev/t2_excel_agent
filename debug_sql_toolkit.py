"""Отладочный скрипт для проверки SQL toolkit."""

import os
from pathlib import Path
from langchain_openai import ChatOpenAI
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from excel_agent.config import OPENAI_API_KEY, MODEL_NAME, TEMPERATURE, PROJECT_ROOT

def test_sql_toolkit():
    """Проверить подключение к DuckDB и создание SQL toolkit."""
    
    print("\n" + "="*60)
    print("ОТЛАДКА SQL TOOLKIT")
    print("="*60 + "\n")
    
    # 1. Проверяем путь к базе данных
    db_path = os.getenv("DUCKDB_PATH", "db/excel_data.duckdb")
    absolute_db_path = PROJECT_ROOT / db_path
    
    print(f"1. Пути к базе данных:")
    print(f"   DUCKDB_PATH из .env: {os.getenv('DUCKDB_PATH', 'не задано')}")
    print(f"   db_path: {db_path}")
    print(f"   PROJECT_ROOT: {PROJECT_ROOT}")
    print(f"   absolute_db_path: {absolute_db_path}")
    print(f"   Существует: {absolute_db_path.exists()}")
    print()
    
    # 2. Пробуем создать URI для DuckDB
    db_uri = f"duckdb:///{absolute_db_path}"
    print(f"2. URI для SQLAlchemy:")
    print(f"   {db_uri}")
    print()
    
    # 3. Пробуем подключиться к базе через SQLDatabase
    print("3. Попытка подключения к DuckDB через SQLDatabase...")
    try:
        from sqlalchemy import create_engine
        engine = create_engine(db_uri)
        db = SQLDatabase(engine, view_support=False)
        print("   ✓ Подключение успешно!")
        print(f"   Диалект: {db.dialect}")
        print(f"   Доступные таблицы: {db.get_usable_table_names()}")
        print()
    except Exception as e:
        print(f"   ❌ Ошибка подключения: {str(e)}")
        print(f"   Тип ошибки: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return
    
    # 4. Создаем LLM
    print("4. Создание LLM...")
    try:
        llm = ChatOpenAI(
            model=MODEL_NAME,
            temperature=TEMPERATURE,
            api_key=OPENAI_API_KEY
        )
        print("   ✓ LLM создан")
        print()
    except Exception as e:
        print(f"   ❌ Ошибка создания LLM: {str(e)}")
        return
    
    # 5. Создаем SQL toolkit
    print("5. Создание SQL toolkit...")
    try:
        sql_toolkit = SQLDatabaseToolkit(db=db, llm=llm)
        sql_tools = sql_toolkit.get_tools()
        print(f"   ✓ SQL toolkit создан")
        print(f"   Количество инструментов: {len(sql_tools)}")
        print()
        
        print("6. Список SQL инструментов:")
        for i, tool in enumerate(sql_tools, 1):
            print(f"   {i}. {tool.name}")
            print(f"      Описание: {tool.description[:100]}...")
            print()
            
    except Exception as e:
        print(f"   ❌ Ошибка создания SQL toolkit: {str(e)}")
        import traceback
        traceback.print_exc()
        return
    
    print("="*60)
    print("ОТЛАДКА ЗАВЕРШЕНА УСПЕШНО")
    print("="*60 + "\n")

if __name__ == "__main__":
    test_sql_toolkit()

