from flask import Flask, render_template, Response, url_for, request, redirect, session, jsonify, flash
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import cv2
from ultralytics import YOLO
import mysql.connector 
import datetime
import base64
import numpy as np
import time
import re
from paddleocr import PaddleOCR
import os

# Ruta absoluta (más segura)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "ai_models", "Paddleocr")

# ←←← AQUÍ ESTÁ EL CAMBIO IMPORTANTE ←←←
ocr = PaddleOCR(
    use_angle_cls=True,          # si usas detección de ángulo
    lang='latin',                # o 'en' según lo que entrenaste
    rec_model_dir=MODEL_DIR,     # ← carpeta con tus inference.*
    rec_char_dict_path=os.path.join(MODEL_DIR, "dict_cix.txt"),  # ← tu diccionario custom
    show_log=False,              # para que no llene la consola
    det_model_dir=None,          # si solo usas reconocimiento (recomendado si ya tienes det en YOLO)
)

app = Flask(__name__)
app.secret_key = "tu_clave_secreta_super_segura"

# Decorador para proteger rutas
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# 1. INICIALIZACIÓN DE MODELO YOLO
# ------------------------------------------------------
from ultralytics import YOLO

print("Cargando modelo YOLO...")
try:
    # Construimos la ruta dinámica: D:\loginflask\ai_models\yolov8s\bestsmall.pt
    ruta_yolo = os.path.join(BASE_DIR, "ai_models", "yolov8s", "bestsmall.pt")
    model = YOLO(ruta_yolo)  
    print(f"¡Modelo {ruta_yolo} cargado con éxito!")
except Exception as e:
    print(f"Error: No se encontró el modelo. Detalle: {e}")
    model = None

# ------------------------------------------------------
# 2. VARIABLES GLOBALES Y DE CONTROL
# ------------------------------------------------------
ultima_placa = {
    "imagen": None,
    "hora": None,
    "id": 0,
    "texto": "ESPERANDO..."
}
contador_id = 0

# Variables para evitar duplicados sin OCR ni ID
# Guardaremos: (centro_x, centro_y, tiempo_unix)
autos_ya_capturados = set() # Guardaremos los IDs de YOLO que ya fueron procesados
# ------------------------------------------------------
# 3. BASE DE DATOS
# ------------------------------------------------------
def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host='127.0.0.1',
            user='root',
            password='',
            database='control_vehicular'
        )
        return connection
    except mysql.connector.Error as err:
        print(f"Error conectando a MySQL: {err}")
        return None

# ------------------------------------------------------
# 4. RUTAS DE NAVEGACIÓN
# ------------------------------------------------------

@app.route('/', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username_form = request.form['username']
        password_form = request.form['password']
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor(dictionary=True) 
            # CONSULTA PARAMETRIZADA (OK)
            cursor.execute('SELECT * FROM usuarios WHERE username = %s', (username_form,))
            user = cursor.fetchone()
            cursor.close()
            conn.close()

            # Verificación de contraseña con Hash
            if user and check_password_hash(user['password'], password_form):
                session.clear() # Limpiar sesión anterior por seguridad
                session['user_id'] = user['id']
                session['usuario'] = user['username']
                return redirect(url_for('home'))
            
            flash('Credenciales inválidas')
    return render_template('auth/login.html')

@app.route('/home')
@login_required
def home():
    total = 0
    ultima = None
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT COUNT(*) AS total FROM detecciones")
        resultado = cursor.fetchone()
        total = resultado['total'] if resultado else 0

        cursor.execute("SELECT placa, hora FROM detecciones ORDER BY id DESC LIMIT 1")
        ultima = cursor.fetchone()
        cursor.close()
        conn.close()
    return render_template('home.html', total=total, ultima=ultima)

@app.route('/camaras')
@login_required
def camaras():
    return render_template('operaciones/camaras.html')

@app.route('/forgot-password')
def forgot_password():
    return render_template('auth/forgot_password.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form.get('confirm_password', '')

        # Validación servidor: contraseñas deben coincidir
        if password != confirm_password:
            flash('Las contraseñas no coinciden.')
            return redirect(url_for('register'))
        
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)
            
            # Verificar si existe
            cursor.execute('SELECT * FROM usuarios WHERE username = %s', (username,))
            existing_user = cursor.fetchone()
            
            if existing_user:
                flash('El nombre de usuario ya existe')
                cursor.close()
                conn.close()
                return redirect(url_for('register'))
            
            # Crear usuario con hash
            hashed_password = generate_password_hash(password)
            cursor.execute('INSERT INTO usuarios (username, password) VALUES (%s, %s)', (username, hashed_password))
            conn.commit()
            cursor.close()
            conn.close()
            
            flash('Usuario creado exitosamente. Por favor inicia sesión.')
            return redirect(url_for('login'))
            
    return render_template('auth/register.html')

@app.route('/reportes', methods=['GET'])
@login_required
def reportes():
    # 1. Obtenemos los valores (strip elimina espacios accidentales)
    placa_busqueda = request.args.get('placa_busqueda', '').strip()
    f_inicio = request.args.get('f_inicio', '').strip()
    f_fin = request.args.get('f_fin', '').strip()
    
    registros = []
    conn = get_db_connection()
    
    if conn:
        cursor = conn.cursor(dictionary=True)
        # 2. Iniciamos la consulta base
        query = "SELECT id, placa, fecha, hora, imagen FROM detecciones WHERE 1=1"
        params = []

        # 3. Filtro de Placa (Si el usuario escribió algo)
        if placa_busqueda:
            query += " AND placa LIKE %s"
            params.append(f"%{placa_busqueda}%")
        
        # 4. Filtro de Fecha Inicial (Si solo pone 'Desde')
        if f_inicio and not f_fin:
            query += " AND fecha >= %s"
            params.append(f_inicio)
            
        # 5. Filtro de Fecha Final (Si solo pone 'Hasta')
        elif f_fin and not f_inicio:
            query += " AND fecha <= %s"
            params.append(f_fin)
            
        # 6. Rango Completo (Si pone ambas)
        elif f_inicio and f_fin:
            query += " AND fecha BETWEEN %s AND %s"
            params.extend([f_inicio, f_fin])

        # Ordenar por lo más reciente siempre
        query += " ORDER BY fecha DESC, hora DESC"
        
        cursor.execute(query, tuple(params))
        registros = cursor.fetchall()
        cursor.close()
        conn.close()

    return render_template('areadedescargas/reportes.html', 
                           registros=registros, 
                           placa_busqueda=placa_busqueda,
                           f_inicio=f_inicio, 
                           f_fin=f_fin)

@app.route('/logout')
def logout():
    session.pop('usuario', None)
    return redirect(url_for('login'))

# ------------------------------------------------------
# 5. LÓGICA DE VIDEO EN TIEMPO REAL (ESPERA 3 SEGUNDOS Y TOMA MEJOR CONFIDENCIA)
# ------------------------------------------------------
import time
from collections import defaultdict

def generate_frames():
    global ultima_placa, contador_id, autos_ya_capturados

    camera = cv2.VideoCapture("muni03.mp4")
    if not camera.isOpened():
        print("Error: No se pudo abrir el video")
        return

    frame_count = 0
    PROCESAR_CADA_N_FRAMES = 3
    MIN_WIDTH = 60
    MIN_HEIGHT = 20
    MAX_SET_SIZE = 50
    TIEMPO_ESPERA_SEGUNDOS = 3  # Tiempo de espera para tomar mejor frame
    
    # Diccionario para trackear vehículos en "período de observación"
    # Estructura: {obj_id: {'primer_deteccion': timestamp, 'mejor_conf': float, 
    #                       'mejor_frame': frame, 'mejor_box': box, 'procesado': bool}}
    vehiculos_observando = {}
    
    # FPS aproximados para calcular frames de espera (ajústalo si conoces el real)
    FPS_ESTIMADO = 30
    FRAMES_ESPERA = int(TIEMPO_ESPERA_SEGUNDOS * FPS_ESTIMADO)

    try:
        while True:
            success, frame = camera.read()
            if not success:
                camera.set(cv2.CAP_PROP_POS_FRAMES, 0)
                autos_ya_capturados.clear()
                vehiculos_observando.clear()
                continue

            annotated_frame = frame.copy()
            frame_count += 1
            tiempo_actual = time.time()

            if not model:
                ret, buffer_frame = cv2.imencode('.jpg', annotated_frame)
                if ret:
                    yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + 
                           buffer_frame.tobytes() + b'\r\n')
                continue

            # Detección con YOLO
            try:
                results = model.track(frame, persist=True, conf=0.78, verbose=False)
            except Exception as e:
                print(f"Error en YOLO track: {e}")
                results = None

            # Set de IDs detectados en este frame
            ids_detectados_este_frame = set()

            if results and results[0].boxes is not None:
                boxes = results[0].boxes.xyxy.int().cpu().tolist()
                confidences = results[0].boxes.conf.cpu().tolist()
                ids = (results[0].boxes.id.int().cpu().tolist() 
                       if results[0].boxes.id is not None 
                       else [None] * len(boxes))

                for i, box in enumerate(boxes):
                    x1, y1, x2, y2 = box
                    conf = confidences[i]
                    obj_id = ids[i]

                    if obj_id is None:
                        continue

                    ids_detectados_este_frame.add(obj_id)

                    # Dibujar bounding box (siempre visible)
                    label = f"ID: {obj_id} Conf: {conf:.2f}"
                    color = (0, 255, 0)  # Verde por defecto
                    
                    # Si está en observación, cambiar color a amarillo
                    if obj_id in vehiculos_observando and not vehiculos_observando[obj_id]['procesado']:
                        tiempo_restante = TIEMPO_ESPERA_SEGUNDOS - (tiempo_actual - vehiculos_observando[obj_id]['primer_deteccion'])
                        label = f"ID: {obj_id} Conf: {conf:.2f} [ESPERA: {tiempo_restante:.1f}s]"
                        color = (0, 255, 255)  # Amarillo
                    
                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(annotated_frame, label, (x1, y1 - 10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

                    # Filtro de tamaño mínimo
                    w, h = x2 - x1, y2 - y1
                    if h < MIN_HEIGHT or w < MIN_WIDTH:
                        continue

                    # Validar coordenadas
                    height, width = frame.shape[:2]
                    x1_clipped, y1_clipped = max(0, x1), max(0, y1)
                    x2_clipped, y2_clipped = min(width, x2), min(height, y2)
                    
                    if x1_clipped >= x2_clipped or y1_clipped >= y2_clipped:
                        continue

                    # --- LÓGICA DE ESPERA Y MEJOR CONFIDENCIA ---
                    
                    # Si ya fue procesado o ya está en autos_ya_capturados, ignorar
                    if obj_id in autos_ya_capturados:
                        continue

                    # Si es la primera vez que vemos este ID, iniciar observación
                    if obj_id not in vehiculos_observando:
                        vehiculos_observando[obj_id] = {
                            'primer_deteccion': tiempo_actual,
                            'mejor_conf': conf,
                            'mejor_frame': frame.copy(),
                            'mejor_box': (x1_clipped, y1_clipped, x2_clipped, y2_clipped),
                            'procesado': False
                        }
                        print(f"🔍 Nuevo vehículo ID:{obj_id} - Iniciando observación de {TIEMPO_ESPERA_SEGUNDOS}s")
                        continue

                    info = vehiculos_observando[obj_id]
                    
                    # Si ya fue procesado, saltar
                    if info['procesado']:
                        continue

                    # Actualizar si esta confianza es mejor que la anterior
                    if conf > info['mejor_conf']:
                        info['mejor_conf'] = conf
                        info['mejor_frame'] = frame.copy()
                        info['mejor_box'] = (x1_clipped, y1_clipped, x2_clipped, y2_clipped)
                        print(f"📈 Mejor confianza actualizada ID:{obj_id} -> {conf:.3f}")

                    # Verificar si ya pasaron los 3 segundos
                    tiempo_transcurrido = tiempo_actual - info['primer_deteccion']
                    
                    if tiempo_transcurrido >= TIEMPO_ESPERA_SEGUNDOS:
                        # ¡Tiempo cumplido! Procesar con la mejor confianza obtenida
                        info['procesado'] = True
                        
                        # Usar el frame y box con mejor confianza
                        frame_a_procesar = info['mejor_frame']
                        x1_m, y1_m, x2_m, y2_m = info['mejor_box']
                        mejor_conf = info['mejor_conf']
                        
                        recorte = frame_a_procesar[y1_m:y2_m, x1_m:x2_m]
                        
                        if recorte.size == 0:
                            print(f"⚠️ Recorte vacío para ID:{obj_id}")
                            continue

                        print(f"⏱️ Tiempo cumplido ID:{obj_id} - Mejor confianza: {mejor_conf:.3f} - Procesando OCR...")

                        # --- OCR ---
                        try:
                            ocr_result = ocr.ocr(recorte, det=False, cls=True)
                            plate_text = "DESCONOCIDO"
                            
                            if ocr_result and ocr_result[0] and len(ocr_result[0]) > 0:
                                raw_text = ocr_result[0][0][0]
                                if raw_text:
                                    plate_text = re.sub(r'[^A-Z0-9]', '', raw_text.upper())

                            # Marcar como capturado
                            autos_ya_capturados.add(obj_id)

                            # Generar nombre de archivo
                            now = datetime.datetime.now()
                            fecha_str = now.strftime('%Y%m%d')
                            hora_str = now.strftime('%H%M%S')
                            safe_plate = re.sub(r'[^\w]', '_', plate_text)[:20]
                            filename = f"{safe_plate}_{fecha_str}_{hora_str}_ID{obj_id}_CONF{mejor_conf:.2f}.jpg"
                            
                            capturas_dir = os.path.join(BASE_DIR, "static", "capturas")
                            os.makedirs(capturas_dir, exist_ok=True)
                            filepath = os.path.join(capturas_dir, filename)
                            
                            success_save = cv2.imwrite(filepath, recorte)
                            if not success_save:
                                print(f"⚠️ Error al guardar imagen: {filepath}")
                                continue

                            contador_id += 1
                            ultima_placa = {
                                "imagen": filename,
                                "hora": now.strftime('%H:%M:%S'),
                                "id": contador_id,
                                "texto": plate_text,
                                "obj_id": obj_id,
                                "confianza_yolo": round(mejor_conf, 3),
                                "tiempo_observacion": round(tiempo_transcurrido, 2)
                            }

                            # Guardar en BD
                            conn = None
                            try:
                                conn = get_db_connection()
                                if conn:
                                    cursor = conn.cursor()
                                    cursor.execute(
                                        "INSERT INTO detecciones (placa, fecha, hora, imagen, confianza, track_id, tiempo_observacion) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                                        (plate_text, now.strftime('%Y-%m-%d'), 
                                         now.strftime('%H:%M:%S'), filename, 
                                         mejor_conf, obj_id, tiempo_transcurrido)
                                    )
                                    conn.commit()
                                    cursor.close()
                            except Exception as db_error:
                                print(f"❌ Error en base de datos: {db_error}")
                            finally:
                                if conn:
                                    conn.close()

                            print(f"✅ RECORTE GUARDADO: {plate_text} (ID:{obj_id}) Conf:{mejor_conf:.3f} en {filepath}")

                            # Limpiar set si crece mucho
                            if len(autos_ya_capturados) > MAX_SET_SIZE:
                                autos_ya_capturados = set(list(autos_ya_capturados)[1:])

                        except Exception as e:
                            print(f"❌ Error en OCR o guardado: {e}")
                            import traceback
                            traceback.print_exc()

            # Limpiar vehículos que ya no están en frame y no fueron procesados (opcional)
            # Esto evita memoria infinita si un vehículo desaparece antes de los 3 segundos
            ids_a_limpiar = []
            for obj_id, info in vehiculos_observando.items():
                if not info['procesado'] and obj_id not in ids_detectados_este_frame:
                    # Si pasaron más de 5 segundos desde la primera detección y no se vio más, eliminar
                    if tiempo_actual - info['primer_deteccion'] > 5:
                        ids_a_limpiar.append(obj_id)
            
            for obj_id in ids_a_limpiar:
                del vehiculos_observando[obj_id]
                print(f"🗑️ Limpiado ID:{obj_id} - Ya no visible")

            # Enviar frame al navegador
            ret, buffer_frame = cv2.imencode('.jpg', annotated_frame)
            if not ret:
                print("Error al codificar frame")
                continue
                
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + 
                   buffer_frame.tobytes() + b'\r\n')

    finally:
        camera.release()
        print("Cámara liberada")
@app.route('/get_latest_detection')
def get_latest_detection():
    return jsonify(ultima_placa)

@app.route('/api/flujo-vehicular')
@login_required
def api_flujo_vehicular():
    """Devuelve detecciones agrupadas por hora del día actual para el gráfico."""
    hoy = datetime.datetime.now().strftime('%Y-%m-%d')
    # Preparar las 24 horas con 0 por defecto
    datos_por_hora = {f"{h:02d}:00": 0 for h in range(24)}

    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT SUBSTRING(hora, 1, 2) AS h, COUNT(*) AS total "
            "FROM detecciones WHERE fecha = %s GROUP BY h ORDER BY h",
            (hoy,)
        )
        for row in cursor.fetchall():
            clave = f"{int(row['h']):02d}:00"
            if clave in datos_por_hora:
                datos_por_hora[clave] = row['total']
        cursor.close()
        conn.close()

    labels = list(datos_por_hora.keys())
    values = list(datos_por_hora.values())
    return jsonify({"labels": labels, "data": values})

@app.route('/historial')
@login_required
def historial():
    # Límite dinámico desde el query string, con validación
    limite_permitidos = [10, 25, 50, 100]
    limit = request.args.get('limit', 50, type=int)
    if limit not in limite_permitidos:
        limit = 50

    conn = get_db_connection()
    detecciones = []
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, placa, fecha, hora, imagen FROM detecciones ORDER BY id DESC LIMIT %s", (limit,))
        detecciones = cursor.fetchall()
        cursor.close()
        conn.close()
    return render_template('historial.html', detecciones=detecciones, limit=limit)


@app.route('/video_feed')
def video_feed():
    """Ruta que sirve el stream de video con detección de placas"""
    return Response(generate_frames(), 
                   mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/perfil')
def perfil():
    # Solo una página simple para que no de error
    return "<h1>Perfil de Usuario</h1><p>Usuario: " + session.get('usuario', 'Invitado') + "</p><a href='/home'>Volver</a>"

if __name__ == '__main__':
    app.run(debug=True, port=5000, use_reloader=False)