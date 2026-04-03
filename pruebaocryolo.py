import cv2
import os
from ultralytics import YOLO
from paddleocr import PaddleOCR

# Configuración de rutas según tu estructura
PATH_YOLO = r'D:\loginflask\ai_models\yolov8s\bestsmall.pt'
PATH_PADDLE_DIR = r'D:\loginflask\ai_models\Paddleocr'
PATH_DICT = r'D:\loginflask\ai_models\Paddleocr\dict_cix.txt'
IMAGE_PATH = r'D:\loginflask\yoloocr.jpeg'
CARPETA_RECORTES = r'D:\loginflask\recortes'

def ejecucion_final():
    if not os.path.exists(CARPETA_RECORTES):
        os.makedirs(CARPETA_RECORTES)

    print("--- Ejecutando con Ajuste de Tensores y Diccionario ---")
    
    # Inicializamos con rec_image_shape de 32 de altura (3840 / 120 / 1 = 32)
    ocr = PaddleOCR(
        rec_model_dir=PATH_PADDLE_DIR,
        det_model_dir=PATH_PADDLE_DIR,
        rec_char_dict_path=PATH_DICT, 
        use_angle_cls=True,
        lang='es',
        rec_image_shape="3, 32, 120", # Ajustado para resolver el error de 3840
        show_log=False
    )

    model_yolo = YOLO(PATH_YOLO)
    img = cv2.imread(IMAGE_PATH)
    
    results = model_yolo(img)

    for i, r in enumerate(results):
        for j, box in enumerate(r.boxes):
            b = box.xyxy[0].cpu().numpy().astype(int)
            # Recorte con margen para evitar bordes pegados
            roi = img[max(0, b[1]-5):min(img.shape[0], b[3]+5), 
                      max(0, b[0]-5):min(img.shape[1], b[2]+5)]
            
            if roi.size > 0:
                ruta_img = os.path.join(CARPETA_RECORTES, f"placa_{i}_{j}.jpg")
                cv2.imwrite(ruta_img, roi)

                try:
                    # Usamos det=False para que no intente redimensionar 
                    # cajas internas y solo 'lea' el recorte de YOLO
                    resultado = ocr.ocr(roi, det=False, cls=True)
                    
                    if resultado and resultado[0]:
                        texto_final, score = resultado[0][0]
                        print(f"\n[+] Recorte: {ruta_img}")
                        print(f"===> PLACA LEÍDA: {texto_final}")
                        print(f"===> CONFIANZA: {score:.2f}")
                    else:
                        print("\n[-] No se pudo extraer texto claro.")
                except Exception as e:
                    print(f"\n[!] Error de compatibilidad: {e}")

if __name__ == '__main__':
    ejecucion_final()