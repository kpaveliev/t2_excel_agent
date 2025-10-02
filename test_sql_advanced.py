"""Тестирование расширенных SQL возможностей агента."""

from excel_agent.react_agent import get_react_agent

def test_advanced_sql():
    """Тест различных типов SQL запросов."""
    
    print("\n" + "="*60)
    print("ТЕСТ РАСШИРЕННЫХ SQL ВОЗМОЖНОСТЕЙ")
    print("="*60 + "\n")
    
    agent = get_react_agent()
    thread_id = "test_advanced_sql"
    
    test_queries = [
        # 1. CREATE TABLE
        "Создай тестовую таблицу test_table с полями id (integer) и name (varchar)",
        
        # 2. INSERT
        "Вставь в таблицу test_table строку с id=1 и name='Test'",
        
        # 3. SELECT
        "Покажи все данные из таблицы test_table",
        
        # 4. UPDATE с WHERE
        "Обнови в таблице test_table строку с id=1, установи name='Updated'",
        
        # 5. SELECT для проверки UPDATE
        "Покажи все данные из таблицы test_table еще раз",
        
        # 6. DELETE без WHERE (должно предупредить)
        "Удали все данные из таблицы test_table",
        
        # 7. DELETE с WHERE
        "Удали из таблицы test_table строку где id=1",
        
        # 8. DROP TABLE
        "Удали таблицу test_table",
        
        # 9. Проверка списка таблиц
        "Покажи список таблиц, test_table должна исчезнуть",
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*60}")
        print(f"Тест {i}: {query}")
        print('='*60 + "\n")
        
        try:
            for step in agent.stream(
                {"messages": [{"role": "user", "content": query}]},
                config={"configurable": {"thread_id": thread_id}},
                stream_mode="values",
            ):
                last_msg = step["messages"][-1]
                if hasattr(last_msg, 'content'):
                    # Показываем только финальный ответ агента
                    if last_msg.type == "ai" and not hasattr(last_msg, 'tool_calls'):
                        print(f"🤖 {last_msg.content}\n")
                
        except Exception as e:
            print(f"❌ Ошибка: {str(e)}\n")
    
    print("\n" + "="*60)
    print("ТЕСТ ЗАВЕРШЕН")
    print("="*60 + "\n")

if __name__ == "__main__":
    test_advanced_sql()

