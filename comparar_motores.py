"""Compara el motor viejo (PyTorch + PaddlePaddle) con el nuevo (ONNX).

No forma parte de la aplicacion: es la red de seguridad para no cambiar el
motor a ciegas. Se ejecuta a mano, con el entorno completo todavia instalado.

    python comparar_motores.py
"""

import os
import re
import sys

import cv2
import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

from inferencia import DetectorPlacas, LectorPlacas  # noqa: E402

RECORTES = [
    ("static/capturas/9N475_20260707_123550_UP0_CONF0.67.jpg", "9N475"),
    ("static/capturas/AEF710_20260707_123301_UP0_CONF0.68.jpg", "AEF710"),
]
IMAGEN_COMPLETA = "runs/detect/predict/pruebaaa.jpg"


def limpiar(texto):
    return re.sub(r"[^A-Z0-9]", "", (texto or "").upper())


def probar_ocr():
    print("=" * 62)
    print("OCR  ·  recorte -> texto")
    print("=" * 62)

    lector = LectorPlacas()

    from paddleocr import PaddleOCR

    carpeta = os.path.join(BASE, "ai_models", "Paddleocr")
    viejo = PaddleOCR(
        use_angle_cls=True,
        lang="latin",
        rec_model_dir=carpeta,
        rec_char_dict_path=os.path.join(carpeta, "dict_cix.txt"),
        show_log=False,
        det_model_dir=None,
    )

    aciertos = 0
    for ruta, esperado in RECORTES:
        img = cv2.imread(os.path.join(BASE, ruta))
        if img is None:
            print(f"  [!] no se pudo leer {ruta}")
            continue

        nuevo_texto, nueva_conf = lector.leer(img)
        nuevo_texto = limpiar(nuevo_texto)

        try:
            r = viejo.ocr(img, det=False, cls=True)
            viejo_texto = limpiar(r[0][0][0]) if r and r[0] else ""
        except Exception as e:  # noqa: BLE001
            viejo_texto = f"error: {e}"

        igual = "OK " if nuevo_texto == viejo_texto else "DIF"
        acierto = "si" if nuevo_texto == esperado else "NO"
        if nuevo_texto == esperado:
            aciertos += 1

        print(f"  esperado : {esperado}")
        print(f"  viejo    : {viejo_texto}")
        print(f"  ONNX     : {nuevo_texto}  (confianza {nueva_conf:.2f})")
        print(f"  coinciden: {igual}   acierta: {acierto}")
        print("-" * 62)

    print(f"  ONNX acierta {aciertos}/{len(RECORTES)}")
    return aciertos


def probar_deteccion():
    print()
    print("=" * 62)
    print("DETECCION  ·  imagen -> cajas")
    print("=" * 62)

    ruta = os.path.join(BASE, IMAGEN_COMPLETA)
    img = cv2.imread(ruta)
    if img is None:
        print(f"  [!] no hay imagen de prueba en {IMAGEN_COMPLETA}")
        return

    detector = DetectorPlacas()
    nuevas = detector.detectar(img)

    from ultralytics import YOLO

    modelo = YOLO(os.path.join(BASE, "ai_models", "yolov8s", "bestsmall.pt"))
    salida = modelo(img, conf=0.4, verbose=False)[0]
    viejas = []
    if salida.boxes is not None and len(salida.boxes):
        for i, caja in enumerate(salida.boxes.xyxy.int().cpu().tolist()):
            viejas.append((*caja, float(salida.boxes.conf[i])))
    viejas.sort(key=lambda c: c[0])

    print(f"  cajas motor viejo: {len(viejas)}")
    print(f"  cajas motor ONNX : {len(nuevas)}")

    for i in range(max(len(viejas), len(nuevas))):
        v = viejas[i] if i < len(viejas) else None
        n = nuevas[i] if i < len(nuevas) else None
        print(f"  --- caja {i + 1} ---")
        print(f"    viejo: {v}")
        print(f"    ONNX : {n}")
        if v and n:
            desvio = max(abs(v[j] - n[j]) for j in range(4))
            print(f"    desviacion maxima: {desvio} px")


if __name__ == "__main__":
    probar_ocr()
    probar_deteccion()
