"""Compara motor viejo (YOLO+PyTorch) y nuevo (ONNX) en la deteccion.

No hay ninguna foto de vehiculo en el repositorio, asi que se fabrican escenas
sinteticas pegando los recortes de placa reales sobre un fondo. Lo que se mide
no es el acierto absoluto del modelo, sino que **los dos motores vean lo mismo**:
si coinciden, el cambio de motor es seguro.
"""

import os

import cv2
import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))

RECORTES = [
    "static/capturas/9N475_20260707_123550_UP0_CONF0.67.jpg",
    "static/capturas/AEF710_20260707_123301_UP0_CONF0.68.jpg",
]


def escena(recorte, ancho=1280, alto=720, escala=0.28, pos=(0.5, 0.6)):
    """Pega la placa sobre un fondo gris con ruido, al tamano y sitio pedidos."""
    fondo = np.full((alto, ancho, 3), 90, dtype=np.uint8)
    ruido = np.random.default_rng(7).integers(-18, 18, fondo.shape, dtype=np.int16)
    fondo = np.clip(fondo.astype(np.int16) + ruido, 0, 255).astype(np.uint8)

    nuevo_w = int(ancho * escala)
    nuevo_h = max(1, int(recorte.shape[0] * nuevo_w / recorte.shape[1]))
    placa = cv2.resize(recorte, (nuevo_w, nuevo_h))

    x = int(ancho * pos[0]) - nuevo_w // 2
    y = int(alto * pos[1]) - nuevo_h // 2
    x, y = max(0, min(x, ancho - nuevo_w)), max(0, min(y, alto - nuevo_h))
    fondo[y : y + nuevo_h, x : x + nuevo_w] = placa
    return fondo, (x, y, x + nuevo_w, y + nuevo_h)


def main():
    from inferencia import DetectorPlacas
    from ultralytics import YOLO

    nuevo = DetectorPlacas()
    viejo = YOLO(os.path.join(BASE, "ai_models", "yolov8s", "bestsmall.pt"))

    casos = []
    for ruta in RECORTES:
        img = cv2.imread(os.path.join(BASE, ruta))
        if img is None:
            continue
        for escala in (0.22, 0.35, 0.5):
            for pos in ((0.5, 0.5), (0.3, 0.65)):
                casos.append(escena(img, escala=escala, pos=pos))

    print("=" * 66)
    print(f"DETECCION  ·  {len(casos)} escenas sinteticas")
    print("=" * 66)

    iguales = coincidencias = 0
    for i, (img, real) in enumerate(casos, 1):
        n = nuevo.detectar(img)

        s = viejo(img, conf=0.4, verbose=False)[0]
        v = []
        if s.boxes is not None and len(s.boxes):
            for j, c in enumerate(s.boxes.xyxy.int().cpu().tolist()):
                v.append((*c, float(s.boxes.conf[j])))
        v.sort(key=lambda c: c[0])

        mismo_numero = len(v) == len(n)
        if mismo_numero:
            iguales += 1

        desvio = None
        if v and n:
            desvio = max(abs(v[0][k] - n[0][k]) for k in range(4))
            if desvio <= 4:
                coincidencias += 1

        estado = "OK " if mismo_numero and (desvio is None or desvio <= 4) else "DIF"
        detalle = f"desvio {desvio} px" if desvio is not None else "sin cajas"
        print(f"  escena {i:>2}: viejo={len(v)}  onnx={len(n)}  {estado}  {detalle}")

    print("-" * 66)
    print(f"  mismo numero de cajas : {iguales}/{len(casos)}")
    print(f"  cajas casi identicas  : {coincidencias}")


if __name__ == "__main__":
    main()
