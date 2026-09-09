# Desplegar la demo en Hugging Face Spaces

La demo pública es **subir una foto y ver la placa detectada** (`/subir`), que ya
funciona sin registro gracias al decorador `@sesion_invitado`.

El streaming de vídeo (`/video_feed`) queda fuera: depende de `muni03.mp4`, que
no está en el repositorio, y transmitir vídeo a visitantes arbitrarios consume
mucho más de lo que da un plan gratuito.

## Antes de empezar

Sube a GitHub lo que tienes pendiente, sobre todo `templates/subir.html`, que
está sin trackear. Sin ese archivo la demo no tiene página.

```bash
git add templates/subir.html app.py requirements.txt database.sql database_supabase.sql Dockerfile .dockerignore DESPLIEGUE.md
git commit -m "Modo invitado, esquema de base de datos y configuracion de despliegue"
git push
```

## Crear el Space

1. Entra en <https://huggingface.co/new-space>.
2. Nombre: `deteccion-placas`. Licencia: la que prefieras.
3. **Space SDK: Docker** → plantilla *Blank*.
4. Hardware: *CPU basic*, gratuito (2 vCPU, 16 GB de RAM).
5. Visibilidad: *Public*, para que el enlace del portafolio funcione.

## Subir el código

```bash
git remote add space https://huggingface.co/spaces/juancarlos1821/deteccion-placas
git push space main
```

Los modelos (`ai_models/`) pesan 36 MB en total, así que entran sin problema.

## Configurar las credenciales (opcional)

**La demo funciona sin base de datos.** Si Supabase no responde, la aplicación
entra en modo demo: detecta la placa y muestra el resultado igual, y lo único
que no hace es guardar el historial. Esto importa porque el plan gratuito de
Supabase pausa los proyectos inactivos — sin esa tolerancia, un reclutador
podría abrir tu demo y encontrarse un error.

Así que puedes desplegar primero y configurar esto después.

Para tener historial y reportes, en el Space ve a *Settings → Variables and
secrets* y añade como **Secrets** los mismos valores de tu `.env`:

- `SUPABASE_DB_HOST`
- `SUPABASE_DB_PORT`
- `SUPABASE_DB_USER`
- `SUPABASE_DB_PASSWORD`
- `SUPABASE_DB_NAME`
- `SECRET_KEY`

Nunca los pongas en el `Dockerfile` ni los subas al repositorio.

## Conectar con el portafolio

Cuando el Space esté en verde, copia su URL (tiene la forma
`https://juancarlos1821-deteccion-placas.hf.space`) y pégala en el portafolio,
en `lib/proyectos.ts`:

```ts
enlaceDemo: "https://juancarlos1821-deteccion-placas.hf.space",
estado: "En línea",
```

El botón **Ir a demo** aparece solo.

## Notas

- El primer arranque tarda: instalar torch y paddlepaddle lleva varios minutos.
- Un Space gratuito se duerme tras un rato sin visitas y tarda unos segundos en
  despertar. Para un portafolio es aceptable.
- `static/capturas/` es efímero: se borra en cada reinicio. No pasa nada, las
  detecciones quedan registradas en la base de datos.
