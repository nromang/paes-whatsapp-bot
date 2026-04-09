# Bot PAES v2.4

Versión estable con corrección de imágenes parciales, división de contextos largos y exclusión de preguntas visuales inválidas.

# Bot PAES WhatsApp Pro v2.0

Bot para estudiar PAES por WhatsApp con menú numérico, prácticas cortas, simulacros, ensayos y repaso inteligente.

## Mejoras principales
- menú corto por números
- submenú por materia
- práctica 10, simulacro 30 y ensayo oficial
- repaso inteligente con preguntas erradas u omitidas
- render mixto texto/imagen para preguntas visuales
- división automática de textos largos para WhatsApp
- puntaje PAES exacto o proyectado según el bloque
- manejo más robusto de errores del webhook

## Señal visual de versión
Al escribir `MENU`, el primer mensaje debe comenzar con:

`🎓 Bot PAES v2.0`

## Variables de entorno
```env
WHATSAPP_VERIFY_TOKEN=paes_verify_token
WHATSAPP_ACCESS_TOKEN=...
WHATSAPP_PHONE_NUMBER_ID=...
WHATSAPP_GRAPH_VERSION=v23.0
PUBLIC_BASE_URL=https://tu-app.onrender.com
```

## Inicio local
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Deploy en Render
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Root Directory: vacío si el repo tiene `app`, `data`, `static` y `requirements.txt` en la raíz
