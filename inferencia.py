"""Motor de inferencia sobre ONNX Runtime.

Sustituye a `ultralytics` (que arrastra PyTorch, 468 MB) y a `paddleocr` (que
arrastra PaddlePaddle, 299 MB) por `onnxruntime`, que ocupa 45 MB. Los modelos
son los mismos, solo cambia el motor que los ejecuta: se exportaron con
`yolo export format=onnx` y con `paddle2onnx`.

El objetivo es que la aplicacion quepa en un servidor gratuito de 512 MB de
RAM. Sin esto necesita mas de 1,5 GB, que ya no regala nadie.

Todo el pre y postprocesado esta reimplementado en numpy, porque era la parte
que hacian las librerias que hemos quitado.
"""

import math
import os

import cv2
import numpy as np
import onnxruntime as ort

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Un solo hilo por sesion: en un servidor gratuito no hay nucleos que repartir,
# y varios hilos solo anaden memoria y cambios de contexto.
_OPCIONES = ort.SessionOptions()
_OPCIONES.intra_op_num_threads = 1
_OPCIONES.inter_op_num_threads = 1


def _sesion(ruta):
    return ort.InferenceSession(
        ruta, sess_options=_OPCIONES, providers=["CPUExecutionProvider"]
    )


# ---------------------------------------------------------------------------
# Deteccion de placas (YOLOv8)
# ---------------------------------------------------------------------------


class DetectorPlacas:
    """Localiza placas en una imagen. Devuelve cajas en coordenadas originales.

    El modelo espera 640x640, asi que la imagen se encaja con bandas grises
    (letterbox) para no deformarla. Se guarda la escala y el desplazamiento
    usados, porque hay que deshacerlos al devolver las coordenadas.
    """

    TAM = 640
    RELLENO = 114  # el gris que usa YOLO para las bandas

    def __init__(self, ruta_modelo=None, confianza=0.4, iou=0.45):
        ruta_modelo = ruta_modelo or os.path.join(
            BASE_DIR, "ai_models", "yolov8s", "bestsmall.onnx"
        )
        self.sesion = _sesion(ruta_modelo)
        self.entrada = self.sesion.get_inputs()[0].name
        self.confianza = confianza
        self.iou = iou

    def _encajar(self, img):
        alto, ancho = img.shape[:2]
        escala = min(self.TAM / alto, self.TAM / ancho)
        nuevo_w, nuevo_h = int(round(ancho * escala)), int(round(alto * escala))
        redim = cv2.resize(img, (nuevo_w, nuevo_h), interpolation=cv2.INTER_LINEAR)

        lienzo = np.full((self.TAM, self.TAM, 3), self.RELLENO, dtype=np.uint8)
        dx, dy = (self.TAM - nuevo_w) // 2, (self.TAM - nuevo_h) // 2
        lienzo[dy : dy + nuevo_h, dx : dx + nuevo_w] = redim

        # BGR -> RGB, 0..1, y de HWC a CHW con lote de 1.
        tensor = lienzo[:, :, ::-1].astype(np.float32) / 255.0
        tensor = np.ascontiguousarray(tensor.transpose(2, 0, 1))[None]
        return tensor, escala, dx, dy

    @staticmethod
    def _nms(cajas, puntuaciones, umbral_iou):
        """Supresion de no maximos: se queda con la mejor caja de cada grupo
        solapado. Es lo que hacia ultralytics por dentro."""
        if len(cajas) == 0:
            return []

        x1, y1, x2, y2 = cajas[:, 0], cajas[:, 1], cajas[:, 2], cajas[:, 3]
        areas = (x2 - x1) * (y2 - y1)
        orden = puntuaciones.argsort()[::-1]

        elegidas = []
        while orden.size > 0:
            i = orden[0]
            elegidas.append(i)
            if orden.size == 1:
                break

            resto = orden[1:]
            ix1 = np.maximum(x1[i], x1[resto])
            iy1 = np.maximum(y1[i], y1[resto])
            ix2 = np.minimum(x2[i], x2[resto])
            iy2 = np.minimum(y2[i], y2[resto])

            solape = np.maximum(0, ix2 - ix1) * np.maximum(0, iy2 - iy1)
            iou = solape / (areas[i] + areas[resto] - solape + 1e-9)
            orden = resto[iou <= umbral_iou]

        return elegidas

    def detectar(self, img):
        """Devuelve [(x1, y1, x2, y2, confianza), ...] ordenado de izquierda a
        derecha, en coordenadas de la imagen original."""
        tensor, escala, dx, dy = self._encajar(img)
        salida = self.sesion.run(None, {self.entrada: tensor})[0]

        # (1, 4+clases, 8400) -> (8400, 4+clases)
        pred = salida[0].T
        if pred.shape[1] < 5:
            return []

        puntuaciones = pred[:, 4:].max(axis=1)
        utiles = puntuaciones > self.confianza
        if not utiles.any():
            return []

        pred, puntuaciones = pred[utiles], puntuaciones[utiles]

        # De centro+tamano a esquinas.
        cx, cy, w, h = pred[:, 0], pred[:, 1], pred[:, 2], pred[:, 3]
        cajas = np.stack([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], axis=1)

        # Deshacer el letterbox para volver a la imagen original.
        cajas[:, [0, 2]] = (cajas[:, [0, 2]] - dx) / escala
        cajas[:, [1, 3]] = (cajas[:, [1, 3]] - dy) / escala

        alto, ancho = img.shape[:2]
        cajas[:, [0, 2]] = cajas[:, [0, 2]].clip(0, ancho)
        cajas[:, [1, 3]] = cajas[:, [1, 3]].clip(0, alto)

        elegidas = self._nms(cajas, puntuaciones, self.iou)
        resultado = [
            (
                int(cajas[i][0]),
                int(cajas[i][1]),
                int(cajas[i][2]),
                int(cajas[i][3]),
                float(puntuaciones[i]),
            )
            for i in elegidas
        ]
        # De izquierda a derecha, para que el orden sea estable entre motores.
        resultado.sort(key=lambda c: c[0])
        return resultado


# ---------------------------------------------------------------------------
# Lectura de caracteres (PaddleOCR, modelo de reconocimiento)
# ---------------------------------------------------------------------------


class LectorPlacas:
    """Lee el texto de un recorte de placa.

    El modelo de reconocimiento de PaddleOCR espera 48 px de alto y ancho
    variable, normalizado a [-1, 1]. La salida son T pasos temporales sobre
    39 clases, que se decodifican con CTC: el indice 0 es el 'blank', del 1 al
    37 van los caracteres del diccionario y el 38 es el espacio.
    """

    ALTO = 48
    ANCHO_MAX = 320

    def __init__(self, ruta_modelo=None, ruta_diccionario=None):
        carpeta = os.path.join(BASE_DIR, "ai_models", "Paddleocr")
        self.sesion = _sesion(ruta_modelo or os.path.join(carpeta, "rec.onnx"))
        self.entrada = self.sesion.get_inputs()[0].name

        ruta_diccionario = ruta_diccionario or os.path.join(carpeta, "dict_cix.txt")
        with open(ruta_diccionario, encoding="utf-8") as f:
            caracteres = [linea.rstrip("\n\r") for linea in f]
        # Mismo montaje que hace PaddleOCR: blank delante, espacio al final.
        self.simbolos = ["blank"] + caracteres + [" "]

    def _preparar(self, recorte):
        alto, ancho = recorte.shape[:2]
        proporcion = ancho / max(alto, 1)
        nuevo_w = min(self.ANCHO_MAX, max(1, int(math.ceil(self.ALTO * proporcion))))

        redim = cv2.resize(recorte, (nuevo_w, self.ALTO)).astype(np.float32)
        redim = redim.transpose(2, 0, 1) / 255.0
        redim = (redim - 0.5) / 0.5

        # Se rellena a lo ancho con ceros: el modelo acepta ancho variable pero
        # un tamano fijo hace la salida comparable entre llamadas.
        lienzo = np.zeros((3, self.ALTO, self.ANCHO_MAX), dtype=np.float32)
        lienzo[:, :, :nuevo_w] = redim
        return lienzo[None]

    def leer(self, recorte):
        """Devuelve (texto, confianza). Texto vacio si no se reconoce nada."""
        if recorte is None or recorte.size == 0:
            return "", 0.0

        salida = self.sesion.run(None, {self.entrada: self._preparar(recorte)})[0][0]

        indices = salida.argmax(axis=1)
        certezas = salida.max(axis=1)

        texto, confianzas, anterior = [], [], -1
        for indice, certeza in zip(indices, certezas):
            # CTC: se ignora el blank y las repeticiones consecutivas.
            if indice != 0 and indice != anterior:
                if indice < len(self.simbolos):
                    texto.append(self.simbolos[indice])
                    confianzas.append(float(certeza))
            anterior = indice

        media = float(np.mean(confianzas)) if confianzas else 0.0
        return "".join(texto).strip(), media
