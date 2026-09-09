# Desplegar la demo (gratis, sin tarjeta)

La demo publica es **subir una foto y ver la placa detectada** (`/subir`), que
funciona sin registro gracias al decorador `@sesion_invitado`.

## Por que cabe en un plan gratuito

La inferencia se migro de PyTorch + PaddlePaddle a **ONNX Runtime**. Los
modelos son los mismos; solo cambio el motor que los ejecuta.

| | Antes | Ahora |
|---|---|---|
| Deteccion | ultralytics + torch (468 MB) | onnxruntime (45 MB) |
| OCR | paddleocr + paddle (299 MB) | el mismo onnxruntime |
| Paquetes | 85 | 8 |
| RAM en el pico | ~1,5 GB | **236 MB** |

Render da 512 MB gratis, asi que entra con margen.

La equivalencia esta verificada, no supuesta:

- `comparar_motores.py` — el OCR devuelve el mismo texto que PaddleOCR (2 de 2).
- `comparar_deteccion.py` — 12 escenas: mismo numero de cajas, desviacion de 0
  a 5 px sobre imagenes de 1280 px.

## Desplegar en Render

1. Entra en <https://render.com> y crea una cuenta (no pide tarjeta).
2. **New → Web Service** y conecta el repositorio de GitHub.
3. Render detecta el `Dockerfile` solo. Si pregunta, elige **Docker**.
4. Plan: **Free**.
5. **Create Web Service**.

La primera construccion tarda unos minutos. Cuando termine tendras una URL del
estilo `https://deteccion-placas.onrender.com`.

## Credenciales (opcional)

**La demo funciona sin base de datos.** Si Supabase no responde, la aplicacion
entra en modo demo: detecta la placa y muestra el resultado igual, y lo unico
que no hace es guardar el historial. Importa porque el plan gratuito de
Supabase pausa los proyectos inactivos.

Para tener historial y reportes, en Render ve a *Environment* y anade las
variables de tu `.env`:

- `SUPABASE_DB_HOST`, `SUPABASE_DB_PORT`, `SUPABASE_DB_USER`,
  `SUPABASE_DB_PASSWORD`, `SUPABASE_DB_NAME`
- `SECRET_KEY`

Nunca las pongas en el `Dockerfile` ni las subas al repositorio.

## Conectar con el portafolio

Copia la URL y pegala en `lib/proyectos.ts` del portafolio:

```ts
enlaceDemo: "https://deteccion-placas.onrender.com/subir",
estado: "En linea",
```

El boton **Ir a demo** aparece solo.

## Notas

- El plan gratuito de Render duerme el servicio tras 15 minutos sin visitas. La
  primera peticion despues tarda entre 30 y 60 segundos en responder.
- `static/capturas/` es efimero: se borra en cada reinicio. Las detecciones
  quedan en la base de datos si esta configurada.
- **El video en directo no esta disponible en el servidor.** Usa
  `model.track()` de ultralytics, que necesita PyTorch, y ademas depende de un
  `muni03.mp4` que no esta en el repositorio. En local, con
  `pip install ultralytics torch`, la app lo detecta y lo activa sola.
