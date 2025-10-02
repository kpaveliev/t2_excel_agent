# Database Table Structure

## Creating the Base Table

To create the DuckDB table for storing processed Excel data:

```bash
python3 -m db.create_base_table
```

## Configuration

Add to your `.env` file:

```bash
DUCKDB_PATH=db/excel_data.duckdb
```

## Table: `processed_requests`

Stores all processed Excel request data with the following structure:

| Field Name | Type | Description (Russian) |
|------------|------|----------------------|
| `id` | INTEGER (PK) | Auto-increment ID |
| `created_at` | TIMESTAMP | Record creation timestamp |
| `filename` | VARCHAR | Имя файла |
| `branch_code` | VARCHAR | Код филиала |
| `counterparty` | VARCHAR | Наименование контрагента |
| `object_code` | VARCHAR | Номер объекта |
| `object_distance_km` | DECIMAL(10,2) | Расстояние до объекта, км |
| `request_number` | VARCHAR | Номер заявки |
| `request_datetime` | TIMESTAMP | Дата и время заявки |
| `contractor_arrival_datetime` | TIMESTAMP | Дата и время появления Подрядчика на объекте |
| `contractor_departure_datetime` | TIMESTAMP | Дата и время ухода Подрядчика с объекта |
| `work_item_number` | VARCHAR | № п/п работ, по приложению №10 |
| `work_name` | TEXT | Наименование работ, по приложению №10 |
| `work_description` | TEXT | Описание фактически выполненных работ |
| `avr_cancellation_price` | DECIMAL(15,2) | Отмена задания АВР — стоимость, руб. без НДС |
| `request_work_cost` | DECIMAL(15,2) | Стоимость работ в заявке, руб. без НДС |
| `request_total_cost` | DECIMAL(15,2) | Стоимость заявки с учётом километража, материалов и локации объекта, руб. без НДС |
| `request_final_cost` | DECIMAL(15,2) | Итоговая стоимость заявки с учётом штрафных санкций, руб. без НДС |

## Indexes

The table includes indexes on:
- `filename` - for quick file lookups
- `request_number` - for request searches
- `request_datetime` - for time-based queries

## Usage Example

```python
import duckdb

# Connect to database
conn = duckdb.connect('db/excel_data.duckdb')

# Insert data
conn.execute("""
    INSERT INTO processed_requests (
        filename, request_number, request_final_cost
    ) VALUES (?, ?, ?)
""", ['report.xlsx', '12345', 150000.00])

# Query data
result = conn.execute("""
    SELECT filename, request_number, request_final_cost
    FROM processed_requests
    WHERE request_final_cost > 100000
    ORDER BY request_datetime DESC
""").fetchall()

conn.close()
```

## Viewing Data

```bash
# Using DuckDB CLI
duckdb db/excel_data.duckdb

# Run queries
SELECT COUNT(*) FROM processed_requests;
SELECT * FROM processed_requests LIMIT 10;
```

