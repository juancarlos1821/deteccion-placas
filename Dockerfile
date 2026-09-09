# Imagen para desplegar la demo. Sirve para Render, Fly, Cloud Run o cualquier
# plataforma que acepte un Dockerfile: el puerto se lee del entorno.
#
# Python 3.12 y no 3.10: es la version donde se verifico la equivalencia entre
# el motor viejo y el nuevo, y ademas onnxruntime 1.29 no publica ruedas para
# 3.10 (ahi se queda en la 1.23). OpenCV 4.6 entra igual porque su rueda es
# abi3, valida de 3.6 en adelante.
FROM python:3.12-slim

# OpenCV necesita glib aunque sea la variante headless.
RUN apt-get update && apt-get install -y --no-install-recommends libglib2.0-0 libgl1 && rm -rf /var/lib/apt/lists/*

# Usuario sin privilegios: la app escribe los recortes en static/capturas.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user
ENV PATH=/home/user/.local/bin:$PATH
WORKDIR /home/user/app

COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

COPY --chown=user . .

# Nunca en produccion: el depurador de Werkzeug permite ejecutar codigo
# arbitrario desde el navegador.
ENV FLASK_DEBUG=0
ENV PORT=8080
EXPOSE 8080

# UN SOLO worker, y es deliberado: cada worker carga su propia copia de los
# modelos ONNX (~236 MB). Con dos, se pasa del limite de 512 MB del plan
# gratuito. La concurrencia se resuelve con hilos, que comparten memoria.
CMD gunicorn --bind 0.0.0.0:${PORT:-8080} --workers 1 --threads 4 --timeout 120 app:app
