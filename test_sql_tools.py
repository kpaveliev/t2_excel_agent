"""Тестовый скрипт для проверки SQL инструментов агента."""

from excel_agent.react_agent import get_react_agent
from excel_agent.config import logger

def test_sql_tools():
    """Проверить что агент имеет доступ к SQL инструментам."""
    
    print("\n" + "="*60)
    print("ТЕСТ SQL ИНСТРУМЕНТОВ АГЕНТА")
    print("="*60 + "\n")
    
    # Получаем агента
    print("1. Создание агента...")
    agent = get_react_agent()
    print("   ✓ Агент создан\n")
    
    # Проверяем список доступных инструментов
    print("2. Проверка доступных инструментов:")
    
    # Агент создан через create_react_agent, проверим через тестовый запрос
    thread_id = "test_sql_tools"
    
    test_queries = [
        "Покажи список всех инструментов, которые у тебя есть",
        "Какие SQL инструменты у тебя доступны?",
        "Покажи список таблиц в базе данных",
        "Покажи схему таблицы processed_requests"
    ]
    
    print(f"\nЗапускаем {len(test_queries)} тестовых запроса:\n")
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*60}")
        print(f"Запрос {i}: {query}")
        print('='*60 + "\n")
        
        try:
            for step in agent.stream(
                {"messages": [{"role": "user", "content": query}]},
                config={"configurable": {"thread_id": thread_id}},
                stream_mode="values",
            ):
                # Показываем только последнее сообщение от агента
                last_msg = step["messages"][-1]
                if hasattr(last_msg, 'content'):
                    print(f"🤖 {last_msg.content}\n")
                
        except Exception as e:
            print(f"❌ Ошибка: {str(e)}\n")
    
    print("\n" + "="*60)
    print("ТЕСТ ЗАВЕРШЕН")
    print("="*60 + "\n")

if __name__ == "__main__":
    test_sql_tools()

