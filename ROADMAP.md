# TikTok AI Streamer — Ideas y Roadmap

> ✅ = Completado | 🔲 = Pendiente

---

## Seguridad

| # | Feature | Estado | Notas |
|---|---|---|---|
| 1 | API Key redacted en exportación | ✅ | `GROQ_API_KEY` → `***REDACTED***` |
| 2 | Autenticación en panel (contraseña opcional) | ✅ | `PANEL_PASSWORD` en `.env` o `config.json` |
| 3 | HOST default `127.0.0.1` (no exponer red) | ✅ | |
| 4 | Límite en generación masiva TTS (anti-DoS) | ✅ | Máx 20 acciones por `/api/test_actions` |

## Estabilidad

| # | Feature | Estado | Notas |
|---|---|---|---|
| 5 | Race condition cooldown TTS (lock) | ✅ | `_cooldown_lock` |
| 6 | Race condition banned words (lock) | ✅ | Dentro de `_spam_lock` |
| 7 | Race condition cambio modelo Kokoro (lock) | ✅ | `_state_lock` en todo el swap |
| 8 | Colisión nombres archivos audio | ✅ | UUID completo (32 chars) |
| 9 | Cola reproducción TTS overlay | ✅ | Array + `onended` |
| 10 | Emojis compuestos (grapheme clusters) | ✅ | `Intl.Segmenter` con fallback |
| 11 | Inputs panel inicializados con valores servidor | ✅ | `initPanel()` |
| 12 | Límite archivos audio (100 máx) | ✅ | Tiempo + cantidad |
| 13 | Límite usuarios anti-spam (1000 máx) | ✅ | LRU automático |
| 14 | Validación tipo en JSON (presets/banned_words) | ✅ | `isinstance` check |
| 15 | Validación inputs numéricos TTS | ✅ | `try/except ValueError` |
| 16 | Comandos `!` robustos | ✅ | `split(maxsplit=1)` |

## UX / UI

| # | Feature | Estado | Notas |
|---|---|---|---|
| 17 | Toast "Deshacer" al eliminar reglas/presets | ✅ | Animado, 5s |
| 18 | Preservar datos al cambiar tipo acción en reglas | ✅ | Lee DOM antes de reemplazar |
| 19 | Debug mode no sobrescribe background | ✅ | Solo envía `debug`, no `background` |
| 20 | Chat en vivo muestra likes/joins | ✅ | Panel SSE |
| 21 | `getVoiceGender` con regex | ✅ | 52 líneas → 5 líneas |
| 22 | Preview de emojis en reglas | ✅ | Botón 👁, animación temporal |
| 23 | Filtros por tipo en Logs | ✅ | Todos / Mensajes / Gifts / Likes / Joins / Sistema |
| 24 | Persistencia de settings del usuario | ✅ | `user_settings.json` |

## Arquitectura

| # | Feature | Estado | Notas |
|---|---|---|---|
| 25 | Clase base `SseFlaskServer` | ✅ | `sse_server.py` unifica SSE |
| 26 | Cleanup de archivos innecesarios | ✅ | Tests viejos, leftover scripts |

---

## Tier 1 — Impacto alto, esfuerzo medio

| # | Feature | Estado | Notas |
|---|---|---|---|
| 27 | **Leaderboard de viewers** | ✅ | Comando `!top`, endpoint `/api/leaderboard` |
| 28 | **Sistema de puntos/coins** | ✅ | `points_manager.py`, `!puntos`, persiste en `data/points.json` |
| 29 | **Sonidos de alerta (SFX)** | ✅ | `data/sfx_config.json`, overlay `playSfx()`, carpeta `sfx/` |
| 30 | **Integración OBS WebSocket** | 🔲 | Cambiar escenas automáticamente por evento (gift grande → escena) |
| 31 | **Custom CSS en overlay** | 🔲 | Textarea en panel → inyectar `<style>` en overlay |
| 32 | **Mensajes de bienvenida** | ✅ | TTS al unirse, template configurable `{user}` |
| 33 | **Gestión de hotkeys** | 🔲 | Atajos de teclado configurables (Ctrl+T, etc.) |
| 34 | **Backup automático** | ✅ | `backups/YYYY-MM-DD/`, cleanup >30 días |

## Tier 2 — Calidad de vida

| # | Feature | Estado | Notas |
|---|---|---|---|
| 35 | **Blacklist de usuarios** | 🔲 | Ignorar mensajes de usuarios específicos (no solo palabras) |
| 36 | **Cooldown por usuario** | 🔲 | Rate limit individual. Que un solo usuario no spamee el TTS |
| 37 | **Schedules / programación** | 🔲 | "Cada 5 min decir X", "A las 21:00 cambiar escena" |
| 38 | **Dashboard resumen en overlay** | 🔲 | Mini panel siempre visible (gifts total, viewers, uptime) |
| 39 | **Feedback visual TTS en panel** | 🔲 | Mostrar texto actual que se está reproduciendo + cola |
| 40 | **Preview de voz con un click** | 🔲 | Al hacer hover en una voz → generar audio de preview |
| 41 | **Formateo del chat en overlay** | 🔲 | Nombre en color, emojis grandes en gifts, animaciones |

## Tier 3 — Pro / Avanzado

| # | Feature | Estado | Notas |
|---|---|---|---|
| 42 | **Webhooks** | 🔲 | POST a URL externa cuando ocurre un evento (Discord, etc.) |
| 43 | **Plugin system** | 🔲 | Carpeta `plugins/` con `.py` que se cargan dinámicamente |
| 44 | **Múltiples overlays** | 🔲 | Soporte para 2+ overlays (chat separado de alerts) |
| 45 | **Modo "solo audio"** | 🔲 | Bot responde por voz sin escribir en el chat de TikTok |
| 46 | **Integración Spotify** | 🔲 | "¿Qué está sonando?" en overlay, cambiar volumen por eventos |
| 47 | **API REST pública** | 🔲 | Documentar endpoints para que otros devs integren |
| 48 | **Métricas y analytics** | 🔲 | Guardar stats a SQLite, gráficos de crecimiento |

## Tier 4 — Locuras

| # | Feature | Estado | Notas |
|---|---|---|---|
| 49 | **Roulette / Rifa** | 🔲 | `!rifa` para entrar, `!sortear` con TTS dramático |
| 50 | **Tamagotchi virtual** | 🔲 | Pet en overlay que crece con interacciones, reacciona a gifts |
| 51 | **Votaciones en tiempo real** | 🔲 | `!votar A` / `!votar B`, overlay muestra barras de progreso |
| 52 | **Minijuegos en overlay** | 🔲 | Quiz, trivia, adivina el número con rewards en puntos |
| 53 | **Caption automático** | 🔲 | Speech-to-text para mostrar lo que dice el streamer en overlay |
| 54 | **Weather / clima overlay** | 🔲 | Widget de clima (para streams IRL / outdoor) |

---

## Resumen por batch

| Batch | Items | Estado |
|---|---|---|
| Batch 1: Seguridad + Estabilidad | 1–10, 12, 13 | ✅ |
| Batch 2: UX/UI + Robustez | 14–24 | ✅ |
| Batch 3: Arquitectura + Preview + Filtros | 25–26 | ✅ |
| Batch 4: Tier 1 (Puntos + Leaderboard + SFX + Welcome + Backup) | 27–29, 32, 34 | ✅ |
| Batch 5: Tier 1 (pendiente) | 30, 31, 33 | 🔲 |

---

*Última actualización: 2026-05-22*
