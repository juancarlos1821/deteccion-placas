
import mysql.connector

try:
    connection = mysql.connector.connect(
        host='127.0.0.1',
        user='root',
        password='',
        database='control_vehicular'
    )
    cursor = connection.cursor(dictionary=True)
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
