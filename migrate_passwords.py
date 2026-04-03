import mysql.connector
from werkzeug.security import generate_password_hash

def migrate_passwords():
    print("Iniciando migración de contraseñas...")
    
    conn = None
    try:
        # Conectar a la base de datos
        conn = mysql.connector.connect(
            host='127.0.0.1',
            user='root',
            password='',
            database='control_vehicular'
        )
        cursor = conn.cursor(dictionary=True)
        
        # Obtener todos los usuarios
        cursor.execute("SELECT id, username, password FROM usuarios")
        users = cursor.fetchall()
        
        migrated_count = 0
        
        for user in users:
            # Forzamos a que sea string para que el editor no marque error de tipos
            plain_password = str(user['password'])
            username = str(user['username'])
            user_id = user['id']
            
            # Verificación mejorada del formato del hash
            if not plain_password.startswith(('scrypt:', 'pbkdf2:', 'argon2:')):
                print(f"Encriptando contraseña para usuario: {username}")
                hashed_password = generate_password_hash(plain_password)
                
                # Usamos el mismo cursor para optimizar
                cursor.execute(
                    "UPDATE usuarios SET password = %s WHERE id = %s",
                    (hashed_password, user_id)
                )
                conn.commit()
                migrated_count += 1
            else:
                print(f"Usuario {username} ya tiene contraseña encriptada. Saltando.")
        
        print(f"\nMigración completada. Usuarios actualizados: {migrated_count}")
        cursor.close()
        
    except mysql.connector.Error as err:
        print(f"Error de base de datos: {err}")
    except Exception as e:
        print(f"Error inesperado: {e}")
    finally:
        # Cerramos la conexión siempre, ocurra o no un error
        if conn and conn.is_connected():
            conn.close()

if __name__ == "__main__":
    migrate_passwords()