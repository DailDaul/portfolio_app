import psycopg2
import json

# Подключение к БД Render
conn = psycopg2.connect(
    host="dpg-d8gm9bgjo6nc73engd40-a",
    database="portfolio_db_qmlr",
    user="portfolio_db_qmlr_user",
    password="KxcLBsEsb0KGbbRTO3tbXFBK1PGco3Ws"
)
cursor = conn.cursor()

# Загружаем данные из JSON
with open('import.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for table_name, table_data in data.items():
    columns = table_data['columns']
    rows = table_data['rows']
    
    if not rows:
        continue
    
    placeholders = ','.join(['%s'] * len(columns))
    col_names = ','.join(columns)
    
    # Очищаем таблицу
    cursor.execute(f"TRUNCATE TABLE {table_name} RESTART IDENTITY CASCADE;")
    
    # Вставляем данные
    for row in rows:
        try:
            cursor.execute(
                f"INSERT INTO {table_name} ({col_names}) VALUES ({placeholders})",
                row
            )
        except Exception as e:
            print(f"Ошибка в {table_name}: {e}")
    
    conn.commit()
    print(f"✅ Импортировано {len(rows)} записей в {table_name}")

cursor.close()
conn.close()
print("\n✅ Импорт завершён!")
