# 🚀 Руководство по обновлению до версии с БД

## ⚠️ ВАЖНО

Это **большое обновление** которое меняет:
1. Язык интерфейса на русский
2. Извлечение 13 полей вместо 2
3. Сохранение в DuckDB вместо CSV

## 📋 Пошаговая миграция

### Шаг 1: Создайте базу данных

```bash
python3 -m db.create_base_table
```

Ожидаемый вывод:
```
📊 Creating base table in: db/excel_data.duckdb
  ✅ Table 'processed_requests' created successfully
```

### Шаг 2: Обновите .env файл

Добавьте (если еще нет):
```bash
DUCKDB_PATH=db/excel_data.duckdb
```

### Шаг 3: Перезапустите приложение

```bash
streamlit run chat_app.py
```

## 🔄 Что изменилось

### Новые модули
- `excel_agent/db_manager.py` - работа с БД
- `excel_agent/column_mapper_v2.py` - поиск всех полей

### Обновленные модули
- `excel_agent/config.py` - новые целевые колонки
- `excel_agent/graph.py` - извлечение всех полей (ТРЕБУЕТ ОБНОВЛЕНИЯ)
- `excel_agent/react_agent.py` - русский язык, БД (ТРЕБУЕТ ОБНОВЛЕНИЯ)
- `chat_app.py` - русский интерфейс (УЖЕ ОБНОВЛЕН)

## ⚡ Быстрый старт

### Если у вас есть тестовые файлы:

1. Положите Excel файлы в `data/`
2. Запустите `streamlit run chat_app.py`
3. В sidebar:
   - Выберите файлы
   - Введите код филиала: `TEST001`
   - Введите подрядчика: `ООО «Тест»`
4. Нажмите "▶️ Начать обработку"

### Проверка БД после обработки:

```python
from excel_agent.db_manager import get_db_manager

db = get_db_manager()
stats = db.get_statistics()

print(f"Всего записей: {stats['total_records']}")
print(f"Обработано файлов: {stats['total_files']}")
```

## 🔍 Что извлекается

### Обязательные поля:
- ✅ Номер заявки
- ✅ Итоговая стоимость заявки

### Опциональные поля:
- Номер объекта
- Расстояние до объекта (км)
- Дата и время заявки
- Дата прибытия подрядчика
- Дата убытия подрядчика
- Номер пункта работ
- Наименование работ
- Описание работ
- Стоимость отмены АВР
- Стоимость работ
- Общая стоимость заявки

## 📊 Работа с БД

### Запросы через Python:

```python
from excel_agent.db_manager import get_db_manager
import pandas as pd

db = get_db_manager()

# Получить все заявки конкретного филиала
df = db.query_requests(branch_code="BRN001", limit=100)
print(df[['request_number', 'request_final_cost']])

# Статистика
stats = db.get_statistics()
for branch, count in stats['by_branch'].items():
    print(f"{branch}: {count} заявок")
```

### Запросы через DuckDB CLI:

```bash
duckdb db/excel_data.duckdb

# Подсчет записей
SELECT COUNT(*) FROM processed_requests;

# Топ 10 самых дорогих заявок
SELECT request_number, request_final_cost 
FROM processed_requests 
ORDER BY request_final_cost DESC 
LIMIT 10;

# Статистика по филиалам
SELECT branch_code, COUNT(*) as count, SUM(request_final_cost) as total
FROM processed_requests
GROUP BY branch_code;
```

## ⚠️ Известные проблемы

### 1. Не все поля извлекаются
**Причина**: Не все Excel файлы содержат все поля  
**Решение**: Это нормально. Обязательны только `request_number` и `request_final_cost`

### 2. LLM не находит колонки
**Причина**: Названия колонок сильно отличаются от ожидаемых  
**Решение**: Добавьте варианты в `TARGET_COLUMNS_RU` в `config.py`

### 3. Ошибка "Table does not exist"
**Причина**: БД не создана  
**Решение**: Запустите `python3 -m db.create_base_table`

## 🔙 Откат к предыдущей версии

Если что-то пошло не так:

```bash
# Вернитесь к предыдущему коммиту
git log --oneline  # найдите нужный коммит
git checkout <commit-hash>

# Или сохраните текущую версию и откатитесь
git stash
git checkout HEAD~1
```

Старые CSV файлы в `output/` не затрагиваются и остаются доступными.

## 📞 Поддержка

Если возникли проблемы:
1. Проверьте логи в консоли
2. Убедитесь что БД создана
3. Проверьте что API ключ OpenAI работает
4. Посмотрите примеры Excel файлов - возможно структура нестандартная

## ✅ Чеклист готовности

- [ ] БД создана (`db/excel_data.duckdb` существует)
- [ ] `.env` обновлен (DUCKDB_PATH добавлен)
- [ ] Streamlit перезапущен
- [ ] Тестовый файл обработан успешно
- [ ] Данные появились в БД (проверено запросом)

Если все пункты ✅ - вы готовы к работе!

