<div align="center">

# 🚗 Detección de Placas Vehiculares

### Sistema OCR con Inteligencia Artificial para reconocimiento de placas

[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://github.com/juancarlos1821/deteccion-placas)
[![Flask](https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white)](https://github.com/juancarlos1821/deteccion-placas)
[![YOLOv8](https://img.shields.io/badge/YOLOv8-00FFFF?style=for-the-badge&logo=yolo&logoColor=black)](https://github.com/juancarlos1821/deteccion-placas)
[![OpenCV](https://img.shields.io/badge/OpenCV-27338e?style=for-the-badge&logo=OpenCV&logoColor=white)](https://github.com/juancarlos1821/deteccion-placas)

</div>

---

## 📌 Descripción

Sistema web de detección y reconocimiento automático de placas vehiculares usando visión por computadora. Combina el poder de **YOLOv8** para la detección de objetos y **OCR** para la extracción de texto, todo integrado en una interfaz web con Flask.

---

## ✨ Funcionalidades

- 🔍 Detección de placas vehiculares en imágenes con alta precisión
- 🔤 Reconocimiento automático de caracteres (OCR)
- 🌐 Interfaz web intuitiva para carga y análisis de imágenes
- 🗄️ Base de datos para registro y consulta de placas detectadas
- 📊 Visualización de resultados con bounding boxes
- ⚡ Procesamiento en tiempo real

---

## 🛠️ Tecnologías Utilizadas

| Tecnología | Versión | Uso |
|------------|---------|-----|
| Python | 3.x | Lenguaje principal |
| Flask | Latest | Framework web backend |
| YOLOv8 | Latest | Detección de objetos (IA) |
| OpenCV | Latest | Procesamiento de imágenes |
| Tesseract OCR | Latest | Reconocimiento de texto |
| Tailwind CSS | Latest | Estilos frontend |
| JavaScript | ES6 | Interactividad frontend |

---

## 🚀 Instalación y Configuración

```bash
# 1. Clona el repositorio
git clone https://github.com/juancarlos1821/deteccion-placas.git
cd deteccion-placas

# 2. Instala las dependencias
pip install -r requirements.txt

# 3. Ejecuta la aplicación
python app.py
```

Abre tu navegador en `http://localhost:5000`

---

## 📁 Estructura del Proyecto

```
deteccion-placas/
├── app.py                  # Aplicación Flask principal
├── ai_models/              # Modelos YOLOv8 entrenados
├── templates/              # Plantillas HTML
├── requirements.txt        # Dependencias Python
└── tailwind.config.js      # Configuración de estilos
```

---

## 🧠 ¿Cómo funciona?

1. **Carga de imagen** → El usuario sube una imagen con una placa vehicular
2. **Detección con YOLO** → El modelo identifica y localiza la placa en la imagen
3. **OCR** → Se extrae el texto de la región de la placa detectada
4. **Resultado** → Se muestra el número de placa reconocido y se guarda en BD

---

<div align="center">

**Desarrollado por [Juan Carlos](https://github.com/juancarlos1821)** 🇵🇪

⭐ ¡Si te gustó el proyecto, no olvides darle una estrella!

</div>
