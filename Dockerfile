# Imagen para desplegar la demo en Hugging Face Spaces (SDK: Docker).
FROM python:3.10-slim

# OpenCV no arranca sin estas librerías del sistema: `import cv2` falla con
# "libGL.so.1: cannot open shared object file".
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*

# Spaces ejecuta el contenedor con el usuario 1000; sin esto, la app no puede
# escribir las imágenes anotadas.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user
ENV PATH=/home/user/.local/bin:$PATH
WORKDIR /home/user/app

COPY --chown=user requirements.txt .

# torch y torchvision desde el índice de CPU. La rueda por defecto de PyPI trae
# CUDA: más de 2 GB de GPU que en un Space gratuito no se usan para nada.
RUN pip install --no-cache-dir --user --index-url https://download.pytorch.org/whl/cpu torch==2.9.1 torchvision==0.24.1
RUN pip install --no-cache-dir --user -r requirements.txt

COPY --chown=user . .

# Spaces publica el contenedor en el 7860. FLASK_DEBUG=0 es obligatorio: el
# depurador de Werkzeug permite ejecutar código arbitrario desde el navegador.
ENV PORT=7860
ENV FLASK_DEBUG=0
EXPOSE 7860

CMD ["python", "app.py"]
