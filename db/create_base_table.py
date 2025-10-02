"""Create base table in DuckDB for storing processed Excel data.

Usage:
    python3 -m db.create_base_table
"""

import os
import duckdb
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database path from environment
# IMPORTANT: default must match runtime (db_manager.py) to avoid mismatched files
DB_PATH = os.getenv("DUCKDB_PATH", "db/excel_data.duckdb")


def create_base_table():
    """Create the base table for storing processed Excel data."""
    
    # Ensure the database directory exists
    db_path = Path(DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"📊 Creating base table in: {DB_PATH}")
    
    # Connect to DuckDB
    conn = duckdb.connect(str(db_path))
    
    try:
        # Drop objects if exist (for clean slate)
        conn.execute("DROP TABLE IF EXISTS processed_requests")
        conn.execute("DROP SEQUENCE IF EXISTS processed_requests_id_seq")
        print("  → Dropped existing table (if any)")
        
        # Create sequence for auto-increment id
        conn.execute("CREATE SEQUENCE processed_requests_id_seq START 1")

        # Create table with all fields
        create_table_sql = """
        CREATE TABLE processed_requests (
            id BIGINT PRIMARY KEY DEFAULT nextval('processed_requests_id_seq'),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            -- Имя файла
            filename VARCHAR NOT NULL,
            
            -- Код филиала
            branch_code VARCHAR,
            
            -- Наименование контрагента
            counterparty VARCHAR,
            
            -- Номер объекта
            object_code VARCHAR,
            
            -- Расстояние до объекта, км
            object_distance_km DECIMAL(10, 2),
            
            -- Номер заявки
            request_number VARCHAR,
            
            -- Дата и время заявки
            request_datetime TIMESTAMP,
            
            -- Дата и время появления Подрядчика на объекте
            contractor_arrival_datetime TIMESTAMP,
            
            -- Дата и время ухода Подрядчика с объекта
            contractor_departure_datetime TIMESTAMP,
            
            -- № п/п работ, по приложению №10
            work_item_number VARCHAR,
            
            -- Наименование работ, по приложению №10
            work_name TEXT,
            
            -- Описание фактически выполненных работ
            work_description TEXT,
            
            -- Отмена задания АВР, в т.ч. по врем. электроснабжению — стоимость, руб. без НДС
            avr_cancellation_price DECIMAL(15, 2),
            
            -- Стоимость работ в заявке, руб. без НДС
            request_work_cost DECIMAL(15, 2),
            
            -- Стоимость заявки с учётом километража, материалов и локации объекта, руб. без НДС
            request_total_cost DECIMAL(15, 2),
            
            -- Итоговая стоимость заявки с учётом штрафных санкций, руб. без НДС
            request_final_cost DECIMAL(15, 2)
        )
        """
        
        conn.execute(create_table_sql)
        print("  ✅ Table 'processed_requests' created successfully")
        
        # Add column comments (Russian descriptions)
        print("  → Adding column comments...")
        column_comments = {
            'filename': 'Имя файла',
            'branch_code': 'Код филиала',
            'counterparty': 'Наименование контрагента',
            'object_code': 'Номер объекта',
            'object_distance_km': 'Расстояние до объекта, км',
            'request_number': 'Номер заявки',
            'request_datetime': 'Дата и время заявки',
            'contractor_arrival_datetime': 'Дата и время появления Подрядчика на объекте',
            'contractor_departure_datetime': 'Дата и время ухода Подрядчика с объекта',
            'work_item_number': '№ п/п работ, по приложению №10',
            'work_name': 'Наименование работ, по приложению №10',
            'work_description': 'Описание фактически выполненных работ',
            'avr_cancellation_price': 'Отмена задания АВР, в т.ч. по врем. электроснабжению — стоимость, руб. без НДС',
            'request_work_cost': 'Стоимость работ в заявке, руб. без НДС',
            'request_total_cost': 'Стоимость заявки с учётом километража, материалов и локации объекта, руб. без НДС',
            'request_final_cost': 'Итоговая стоимость заявки с учётом штрафных санкций, руб. без НДС'
        }
        
        for column, comment in column_comments.items():
            try:
                conn.execute(f"COMMENT ON COLUMN processed_requests.{column} IS '{comment}'")
            except Exception as e:
                # DuckDB might not support COMMENT ON in all versions
                print(f"    ⚠️  Could not add comment for {column}: {e}")
        
        print("    ✓ Column comments added")
        
        # Create indexes for better query performance
        print("  → Creating indexes...")
        
        conn.execute("""
            CREATE INDEX idx_filename ON processed_requests(filename)
        """)
        print("    ✓ Index on filename")
        
        conn.execute("""
            CREATE INDEX idx_request_number ON processed_requests(request_number)
        """)
        print("    ✓ Index on request_number")
        
        conn.execute("""
            CREATE INDEX idx_request_datetime ON processed_requests(request_datetime)
        """)
        print("    ✓ Index on request_datetime")
        
        # Show table info
        print("\n📋 Table structure:")
        result = conn.execute("DESCRIBE processed_requests").fetchall()
        for row in result:
            print(f"  {row[0]:<35} {row[1]:<15}")
        
        # Show row count
        count = conn.execute("SELECT COUNT(*) FROM processed_requests").fetchone()[0]
        print(f"\n📊 Current row count: {count}")
        
        print(f"\n✅ Database ready at: {db_path.absolute()}")
        
    except Exception as e:
        print(f"❌ Error creating table: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    create_base_table()

