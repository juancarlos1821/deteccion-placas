
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

try:
    connection = psycopg2.connect(
        host=os.environ.get('SUPABASE_DB_HOST'),
        port=os.environ.get('SUPABASE_DB_PORT', '6543'),
        user=os.environ.get('SUPABASE_DB_USER'),
        password=os.environ.get('SUPABASE_DB_PASSWORD'),
        dbname=os.environ.get('SUPABASE_DB_NAME', 'postgres'),
        sslmode='require'
    )
    cursor = connection.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT id, imagen FROM detecciones ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    
    if row:
        img_data = row['imagen']
        print(f"ID: {row['id']}")
        print(f"Length: {len(img_data)}")
        print(f"Starts with: '{img_data[:50]}'")
        print(f"Ends with: '{img_data[-50:]}'")
        
        if img_data.startswith('data:image'):
            print("WARNING: Data already has prefix!")
        elif '\n' in img_data:
            print("WARNING: Data contains newlines!")
        else:
            print("INFO: Data looks like raw base64 string.")
    else:
        print("No records found.")
        
    cursor.close()
    connection.close()
except Exception as e:
    print(f"Error: {e}")
