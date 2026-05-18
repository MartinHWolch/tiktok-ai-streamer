# TikTok AI Streamer

Aplicación de streaming para TikTok que conecta chat en tiempo real, orquesta eventos, genera respuestas con IA, convierte texto a voz y controla un overlay para OBS.

## Características

- Chat de TikTok (simulado o conexión real vía TikTokLive).
- Motor de orquestación de eventos con filtros y cooldowns.
- Cliente TTS desacoplado con soporte para **Kokoro ONNX** (voice blending, español, speed control), Piper y gTTS.
- Cliente AI para respuestas automáticas (con Groq).
- Cliente VTube para expresiones.
- Overlay HTML/CSS/JS para OBS (vía navegador).
- Panel de control web para gestionar módulos (TTS, IA, TikTok).

## Requisitos

- Python 3.8+
- (Opcional) Node.js si quieres usar scripts de `package.json`

## Instalación

1. Clona o descarga el proyecto.
2. Crea un entorno virtual (opcional pero recomendado):
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```
3. Instala dependencias de Python:
   ```bash
   pip install -r requirements.txt
   ```
4. Configura tus variables de entorno en el archivo `.env`:
   ```bash
   cp .env .env.local  # Opcional: copia para personalizar
   ```
   Edita `.env` y añade:
   - `GROQ_API_KEY`: tu API key de [Groq](https://console.groq.com/keys).
   - `TIKTOK_USERNAME`: el usuario de TikTok al que conectar.

## Ejecución

### Backend completo
```bash
python main.py
```

Esto levanta:
- Overlay en http://localhost:5000
- Panel de control en http://localhost:5001

### Validar TTS solamente
```bash
python validate_tts.py
```

## Uso

1. Abre el **Overlay** en OBS como navegador (URL: `http://localhost:5000`).
2. Abre el **Panel** en tu navegador (`http://localhost:5001`).
3. Desde el panel puedes:
   - Activar/desactivar **TTS**.
   - Configurar **motor TTS** (Kokoro, Piper, gTTS) en tiempo real.
   - Seleccionar **voz** y crear **mezclas de voces** (Voice Blend) tipo `jf_tebukuro*0.8 + ef_dora*0.2`.
   - Ajustar **velocidad** del habla (speed).
   - Probar TTS directamente desde el panel.
   - Activar/desactivar respuestas de **IA**.
   - Cambiar modo **TikTok** entre Simulación y Real.
   - Simular regalos.
   - Enviar mensajes de prueba.
   - Ver logs de eventos en tiempo real.

## Modo TikTok Real

Para conectar a un live real de TikTok en lugar de la simulación:

1. Asegúrate de que `TikTokLive` esté instalado:
   ```bash
   pip install TikTokLive
   ```
2. Configura `TIKTOK_USERNAME` en el archivo `.env` con tu usuario de TikTok (sin `@`).
3. Inicia el proyecto y abre el **Panel** (`http://localhost:5001`).
4. Pulsa el botón **"Modo Simulación / Real TikTok"** para cambiar a modo real.
5. Si el usuario no está en live o hay errores de conexión, volverá automáticamente a simulación.

## Estructura

```
tiktok-ai-streamer/
├── audio/                # Archivos de audio generados por TTS
├── overlay/              # Frontend del overlay
│   ├── index.html
│   ├── style.css
│   └── overlay.js
├── panel/                # Frontend del panel de control
│   ├── index.html
│   ├── panel.css
│   └── panel.js
├── main.py               # Punto de entrada
├── config.py             # Configuración central
├── tiktok_client.py      # Cliente TikTok (simulado)
├── event_orchestrator.py # Orquestador de eventos
├── ai_client.py          # Cliente IA
├── tts_client.py         # Cliente TTS
├── validate_tts.py       # Validador de TTS
├── vtube_client.py       # Cliente VTube
├── overlay_server.py     # Servidor del overlay
├── control_panel_server.py # Servidor del panel
├── requirements.txt
├── package.json
└── README.md
```

## Variables de entorno (`.env`)

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `TIKTOK_USERNAME` | Usuario de TikTok al que conectar | `mi_usuario` |
| `GROQ_API_KEY` | API Key de Groq | `gsk_...` |
| `GROQ_MODEL` | Modelo de Groq a usar | `llama3-8b-8192` |
| `TTS_ENABLED` | Activar/desactivar TTS | `True` |
| `TTS_COOLDOWN` | Segundos de cooldown entre TTS | `5` |
| `TTS_ENGINE` | Motor TTS: `kokoro`, `piper`, `gtts` | `kokoro` |
| `TTS_VOICE` | Voz por defecto (ej. `im_nicola` para español) | `im_nicola` |
| `TTS_VOICE_BLEND` | Fórmula de mezcla de voces (opcional) | `jf_tebukuro*0.8 + ef_dora*0.2` |
| `TTS_SPEED` | Velocidad de habla (0.5 - 2.0) | `1.0` |
| `TTS_LANG` | Idioma del TTS | `es` |
| `KOKORO_MODEL` | Ruta al modelo Kokoro ONNX | `models/kokoro-v1.0.fp16.onnx` |
| `KOKORO_VOICES` | Ruta al archivo de voces Kokoro | `models/voices-v1.0.bin` |
| `PIPER_MODEL_PATH` | Ruta al modelo Piper ONNX | `models/piper/model.onnx` |
| `OVERLAY_PORT` | Puerto del overlay | `5000` |
| `PANEL_PORT` | Puerto del panel | `5001` |
| `HOST` | Host de los servidores | `0.0.0.0` |

## Notas

- El proyecto soporta **Groq** para respuestas de IA. Si no configuras `GROQ_API_KEY`, usa respuestas de fallback.
- El chat de TikTok está en modo simulación por defecto.
- El motor TTS principal es **Kokoro ONNX** (local, rápido, soporte de voice blending). Si Kokoro no está disponible, hace fallback a **Piper** y luego a **gTTS**.
- Para español con Kokoro se recomienda tener instalado **espeak-ng** en el sistema (usado por `misaki` para phonemización).
