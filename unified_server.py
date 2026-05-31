import os
import json
import time
import logging
from functools import wraps
from flask import send_from_directory, request, jsonify, Response, make_response, redirect
from sse_server import SseFlaskServer

logger = logging.getLogger(__name__)


class UnifiedServer(SseFlaskServer):
    """
    Servidor Flask unificado que sirve overlay (OBS), panel de control,
    API REST y SSE, todo en un solo puerto.
    """

    def __init__(self, orchestrator, config):
        self.orchestrator = orchestrator
        self._panel_password = getattr(config, 'PANEL_PASSWORD', '') or os.getenv('PANEL_PASSWORD', '')
        self._overlay_dir = config.OVERLAY_DIR
        self._panel_dir = config.PANEL_DIR
        self._audio_dir = config.AUDIO_DIR
        self._sfx_dir = orchestrator._sfx_dir
        super().__init__(config)

    def _require_auth(self, f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if self._panel_password:
                token = request.headers.get('X-Panel-Token', '')
                if token != self._panel_password:
                    return make_response(jsonify({"error": "Unauthorized"}), 401)
            return f(*args, **kwargs)
        return decorated

    def _setup_routes(self):
        o = self.orchestrator

        # ------------------------------------------------------------------
        # Paginas principales
        # ------------------------------------------------------------------

        @self.app.route("/")
        def panel_index():
            return send_from_directory(self._panel_dir, "index.html")

        @self.app.route("/overlay")
        def overlay_redirect():
            return redirect("/overlay/", code=301)

        @self.app.route("/overlay/")
        def overlay_index():
            return send_from_directory(self._overlay_dir, "index.html")

        # ------------------------------------------------------------------
        # SSE stream (unico para overlay y panel)
        # ------------------------------------------------------------------

        @self.app.route("/stream")
        def stream():
            initial = {
                "type": "overlay_config",
                "data": {
                    "background": o.overlay_bg,
                    "debug": o.overlay_debug,
                }
            }
            return Response(
                self._event_stream(initial_event=initial),
                mimetype="text/event-stream; charset=utf-8"
            )

        # ------------------------------------------------------------------
        # Archivos estaticos
        # ------------------------------------------------------------------

        @self.app.route("/audio/<path:filename>")
        def audio_files(filename):
            return send_from_directory(self._audio_dir, filename)

        @self.app.route("/sfx/<path:filename>")
        def serve_sfx(filename):
            return send_from_directory(self._sfx_dir, filename)

        @self.app.route("/overlay/<path:filename>")
        def overlay_static(filename):
            return send_from_directory(self._overlay_dir, filename)

        @self.app.route("/panel/<path:filename>")
        def panel_static(filename):
            return send_from_directory(self._panel_dir, filename)

        @self.app.route("/<path:filename>")
        def catch_all_static(filename):
            # Intentar panel dir primero (por compatibilidad)
            panel_path = os.path.join(self._panel_dir, filename)
            if os.path.isfile(panel_path) and not filename.startswith("overlay/"):
                return send_from_directory(self._panel_dir, filename)
            return "Not found", 404

        # ------------------------------------------------------------------
        # Playback API (overlay)
        # ------------------------------------------------------------------

        @self.app.route("/api/playback_started", methods=["POST"])
        def playback_started():
            data = request.get_json(silent=True) or {}
            item_id = data.get("item_id", "")
            if item_id:
                o.pipeline.mark_playback_started(item_id)
            return jsonify({"success": True})

        @self.app.route("/api/playback_done", methods=["POST"])
        def playback_done():
            data = request.get_json(silent=True) or {}
            item_id = data.get("item_id", "")
            if item_id:
                o.pipeline.mark_playback_done(item_id)
            return jsonify({"success": True})

        @self.app.route("/api/vtube_mouth", methods=["POST"])
        def vtube_mouth():
            data = request.get_json(silent=True) or {}
            open_val = float(data.get("open", 0))
            if o.vtube_client:
                ok = o.vtube_client._inject_params(
                    {"MouthOpen": open_val, "MouthSmile": 0.02}, silent=True
                )
                return jsonify({"success": ok, "open": open_val})
            return jsonify({"success": False})

        # ------------------------------------------------------------------
        # API: Status & Toggles
        # ------------------------------------------------------------------

        @self.app.route("/api/status", methods=["GET"])
        @self._require_auth
        def status():
            return jsonify({
                "tts_enabled": o.tts_enabled,
                "ai_enabled": o.ai_enabled,
                "tiktok_enabled": o.tiktok_enabled
            })

        @self.app.route("/api/toggle_tts", methods=["POST"])
        @self._require_auth
        def toggle_tts():
            state = o.toggle_tts()
            return jsonify({"tts_enabled": state})

        @self.app.route("/api/toggle_ai", methods=["POST"])
        @self._require_auth
        def toggle_ai():
            state = o.toggle_ai()
            return jsonify({"ai_enabled": state})

        @self.app.route("/api/toggle_tiktok", methods=["POST"])
        @self._require_auth
        def toggle_tiktok():
            state = o.toggle_tiktok()
            return jsonify({"tiktok_enabled": state})

        @self.app.route("/api/toggle_simulation", methods=["POST"])
        @self._require_auth
        def toggle_simulation():
            state = o.toggle_tiktok_simulation()
            return jsonify({"simulation": state})

        @self.app.route("/api/simulation_speed", methods=["POST"])
        @self._require_auth
        def set_simulation_speed():
            data = request.get_json() or {}
            speed = float(data.get("speed", 1.0))
            o.set_simulation_speed(speed)
            return jsonify({"simulation_speed": speed})

        @self.app.route("/api/stats", methods=["GET"])
        @self._require_auth
        def stats():
            return jsonify(o.get_stats())

        @self.app.route("/api/setup_status", methods=["GET"])
        @self._require_auth
        def setup_status():
            kokoro_fp16 = os.path.exists(self.config.KOKORO_MODEL)
            kokoro_fp32 = os.path.exists(self.config.KOKORO_MODEL_FP32)
            kokoro_voices = os.path.exists(self.config.KOKORO_VOICES)
            piper_model = os.path.exists(self.config.PIPER_MODEL_PATH)
            groq_configured = bool(self.config.GROQ_API_KEY)
            tiktok_username = self.config.TIKTOK_USERNAME
            TikTokLive_installed = False
            try:
                from TikTokLive import TikTokLiveClient
                TikTokLive_installed = True
            except ImportError:
                pass
            return jsonify({
                "kokoro_fp16": kokoro_fp16,
                "kokoro_fp32": kokoro_fp32,
                "kokoro_voices": kokoro_voices,
                "piper_model": piper_model,
                "groq_configured": groq_configured,
                "groq_model": self.config.GROQ_MODEL if groq_configured else "",
                "tiktok_username": tiktok_username,
                "TikTokLive_installed": TikTokLive_installed,
                "tts_enabled": o.tts_enabled,
                "ai_enabled": o.ai_enabled,
                "tts_engine": self.config.TTS_ENGINE,
            })

        # ------------------------------------------------------------------
        # API: Simulacion
        # ------------------------------------------------------------------

        @self.app.route("/api/simulate_gift", methods=["POST"])
        @self._require_auth
        def simulate_gift():
            data = request.get_json(silent=True) or {}
            o.simulate_gift(
                user=data.get("user", "Admin"),
                gift=data.get("gift", "TestGift")
            )
            return jsonify({"status": "ok"})

        @self.app.route("/api/test_message", methods=["POST"])
        @self._require_auth
        def test_message():
            data = request.get_json(silent=True) or {}
            o.test_message(
                text=data.get("text", "Mensaje de prueba"),
                user=data.get("user", "Admin")
            )
            return jsonify({"status": "ok"})

        @self.app.route("/api/simulate_bulk", methods=["POST"])
        @self._require_auth
        def simulate_bulk():
            import random
            data = request.get_json(silent=True) or {}
            count = min(int(data.get("count", 10)), 50)
            names = ["Juan", "Maria", "Carlos", "Ana", "Luis", "Sofia", "Pedro", "Elena",
                     "Diego", "Valeria", "Mateo", "Lucia", "Andres", "Paula", "Gabriel",
                     "Carmen", "Rafael", "Isabel", "Fernando", "Gloria"]
            gifts = ["Rosa", "Panda", "Dinosaurio", "Corazon", "Estrella", "Galaxia",
                     "Universo", "Cohete", "Diamante", "Corona"]
            diamonds_map = {"Rosa": 1, "Panda": 5, "Dinosaurio": 10, "Corazon": 5,
                           "Estrella": 10, "Galaxia": 100, "Universo": 500,
                           "Cohete": 200, "Diamante": 50, "Corona": 300}
            msgs = ["hola!", "que tal?", "buen stream!", "me encanta!", "🔥🔥🔥",
                    "jajaja", "vamos!", "gg", "que buen contenido", "sigue asi!"]
            for _ in range(count):
                user = random.choice(names)
                r = random.random()
                if r < 0.45:
                    name = random.choice(gifts)
                    o.handle_tiktok_event({
                        "type": "gift", "user": user, "gift": name, "amount": 1,
                        "diamond_value": diamonds_map.get(name, 1), "timestamp": time.time()
                    })
                elif r < 0.8:
                    o.handle_tiktok_event({
                        "type": "message", "user": user,
                        "text": random.choice(msgs), "timestamp": time.time()
                    })
                elif r < 0.95:
                    o.handle_tiktok_event({
                        "type": "like", "user": user,
                        "count": random.randint(1, 10), "timestamp": time.time()
                    })
                else:
                    o.handle_tiktok_event({
                        "type": "join", "user": user, "timestamp": time.time()
                    })
                time.sleep(0.01)
            o.log(f"Simulacion masiva: {count} eventos generados")
            return jsonify({"success": True, "events_generated": count})

        # ------------------------------------------------------------------
        # API: TTS
        # ------------------------------------------------------------------

        @self.app.route("/api/tts_status", methods=["GET"])
        @self._require_auth
        def tts_status():
            return jsonify(o.get_tts_status())

        @self.app.route("/api/pipeline_state", methods=["GET"])
        @self._require_auth
        def pipeline_state():
            return jsonify(o.get_pipeline_state())

        @self.app.route("/api/test_pipeline", methods=["POST"])
        def test_pipeline():
            """Test endpoint para verificar el flujo completo del pipeline."""
            data = request.get_json() or {}
            text = data.get("text", "Hola, este es un mensaje de prueba")
            user = data.get("user", "TestUser")

            initial_state = o.pipeline.get_state()

            o.handle_tiktok_event({
                "type": "message",
                "user": user,
                "text": text,
                "timestamp": time.time()
            })

            time.sleep(0.5)

            final_state = o.pipeline.get_state()

            return jsonify({
                "success": True,
                "message": f"Mensaje enviado: {text}",
                "initial_state": {
                    "incoming_queue_size": len(initial_state.get("incoming_queue", [])),
                    "generated_queue_size": len(initial_state.get("generated_queue", [])),
                    "playback_queue_size": len(initial_state.get("playback_queue", [])),
                },
                "final_state": {
                    "incoming_queue_size": len(final_state.get("incoming_queue", [])),
                    "generated_queue_size": len(final_state.get("generated_queue", [])),
                    "playback_queue_size": len(final_state.get("playback_queue", [])),
                    "generating": final_state.get("generating"),
                    "making_tts": final_state.get("making_tts"),
                    "playing": final_state.get("playing"),
                },
                "flags": {
                    "ai_enabled": o.pipeline.ai_enabled,
                    "tts_enabled": o.pipeline.tts_enabled,
                    "tiktok_enabled": o.tiktok_enabled,
                }
            })

        @self.app.route("/api/pipeline_debug", methods=["GET"])
        def pipeline_debug():
            """Endpoint de debug para ver el estado detallado del pipeline."""
            state = o.pipeline.get_state()
            return jsonify({
                "flags": {
                    "ai_enabled": o.pipeline.ai_enabled,
                    "tts_enabled": o.pipeline.tts_enabled,
                },
                "callbacks": {
                    "ai_generate": o.pipeline.ai_generate is not None,
                    "tts_speak": o.pipeline.tts_speak is not None,
                    "dispatch_emotion": o.pipeline.dispatch_emotion is not None,
                    "dispatch_sfx": o.pipeline.dispatch_sfx is not None,
                    "on_change": o.pipeline.on_change is not None,
                },
                "queues": {
                    "incoming": len(state.get("incoming_queue", [])),
                    "generated": len(state.get("generated_queue", [])),
                    "playback": len(state.get("playback_queue", [])),
                },
                "current": {
                    "generating": state.get("generating"),
                    "making_tts": state.get("making_tts"),
                    "playing": state.get("playing"),
                },
                "logs": {
                    "incoming_log": state.get("incoming_log", [])[-5:],
                    "generated_log": state.get("generated_log", [])[-5:],
                    "playback_log": state.get("playback_log", [])[-5:],
                }
            })

            # Esperar un momento para que el pipeline procese
            time.sleep(0.5)

            # Obtener estado final
            final_state = o.pipeline.get_state()

            return jsonify({
                "success": True,
                "message": f"Mensaje enviado: {text}",
                "initial_state": {
                    "incoming_queue_size": len(initial_state.get("incoming_queue", [])),
                    "generated_queue_size": len(initial_state.get("generated_queue", [])),
                    "playback_queue_size": len(initial_state.get("playback_queue", [])),
                },
                "final_state": {
                    "incoming_queue_size": len(final_state.get("incoming_queue", [])),
                    "generated_queue_size": len(final_state.get("generated_queue", [])),
                    "playback_queue_size": len(final_state.get("playback_queue", [])),
                    "generating": final_state.get("generating"),
                    "making_tts": final_state.get("making_tts"),
                    "playing": final_state.get("playing"),
                },
                "flags": {
                    "ai_enabled": o.pipeline.ai_enabled,
                    "tts_enabled": o.pipeline.tts_enabled,
                    "tiktok_enabled": o.tiktok_enabled,
                }
            })

        @self.app.route("/api/set_tts_engine", methods=["POST"])
        @self._require_auth
        def set_tts_engine():
            data = request.get_json(silent=True) or {}
            success = o.set_tts_engine(data.get("engine", "kokoro"))
            return jsonify({"success": success, "status": o.get_tts_status()})

        @self.app.route("/api/set_tts_voice", methods=["POST"])
        @self._require_auth
        def set_tts_voice():
            data = request.get_json(silent=True) or {}
            success = o.set_tts_voice(data.get("voice", "im_nicola"))
            return jsonify({"success": success, "status": o.get_tts_status()})

        @self.app.route("/api/set_tts_voice_blend", methods=["POST"])
        @self._require_auth
        def set_tts_voice_blend():
            data = request.get_json(silent=True) or {}
            success = o.set_tts_voice_blend(data.get("blend", ""))
            return jsonify({"success": success, "status": o.get_tts_status()})

        @self.app.route("/api/set_tts_edge_voice", methods=["POST"])
        @self._require_auth
        def set_tts_edge_voice():
            data = request.get_json(silent=True) or {}
            success = o.set_tts_edge_voice(data.get("voice", "es-MX-DaliaNeural"))
            return jsonify({"success": success, "status": o.get_tts_status()})

        @self.app.route("/api/set_tts_speed", methods=["POST"])
        @self._require_auth
        def set_tts_speed():
            data = request.get_json(silent=True) or {}
            success = o.set_tts_speed(data.get("speed", 1.0))
            return jsonify({"success": success, "status": o.get_tts_status()})

        @self.app.route("/api/set_tts_lang", methods=["POST"])
        @self._require_auth
        def set_tts_lang():
            data = request.get_json(silent=True) or {}
            success = o.set_tts_lang(data.get("lang", "es"))
            return jsonify({"success": success, "status": o.get_tts_status()})

        @self.app.route("/api/set_tts_pitch", methods=["POST"])
        @self._require_auth
        def set_tts_pitch():
            data = request.get_json(silent=True) or {}
            success = o.set_tts_pitch(data.get("pitch", 0))
            return jsonify({"success": success, "status": o.get_tts_status()})

        @self.app.route("/api/set_tts_volume", methods=["POST"])
        @self._require_auth
        def set_tts_volume():
            data = request.get_json(silent=True) or {}
            success = o.set_tts_volume(data.get("volume", 1.0))
            return jsonify({"success": success, "status": o.get_tts_status()})

        @self.app.route("/api/set_kokoro_model", methods=["POST"])
        @self._require_auth
        def set_kokoro_model():
            data = request.get_json(silent=True) or {}
            success = o.set_kokoro_model(data.get("model", "fp16"))
            return jsonify({"success": success, "status": o.get_tts_status()})

        @self.app.route("/api/test_tts", methods=["POST"])
        @self._require_auth
        def test_tts():
            data = request.get_json(silent=True) or {}
            filename = o.test_tts(data.get("text", "Prueba de texto a voz"))
            return jsonify({"filename": filename, "status": "ok" if filename else "error"})

        @self.app.route("/api/logs", methods=["GET"])
        @self._require_auth
        def get_logs():
            return jsonify(list(o.logs))

        # ------------------------------------------------------------------
        # API: Presets
        # ------------------------------------------------------------------

        @self.app.route("/api/tts_presets", methods=["GET"])
        @self._require_auth
        def tts_presets():
            return jsonify(o.list_presets())

        @self.app.route("/api/save_preset", methods=["POST"])
        @self._require_auth
        def save_preset():
            data = request.get_json(silent=True) or {}
            ok = o.save_preset(data.get("name", ""))
            return jsonify({"success": ok, "presets": o.list_presets()})

        @self.app.route("/api/load_preset", methods=["POST"])
        @self._require_auth
        def load_preset():
            data = request.get_json(silent=True) or {}
            ok = o.load_preset(data.get("name", ""))
            return jsonify({"success": ok, "status": o.get_tts_status()})

        @self.app.route("/api/delete_preset", methods=["POST"])
        @self._require_auth
        def delete_preset():
            data = request.get_json(silent=True) or {}
            ok = o.delete_preset(data.get("name", ""))
            return jsonify({"success": ok, "presets": o.list_presets()})

        @self.app.route("/api/preview_voice", methods=["POST"])
        @self._require_auth
        def preview_voice():
            data = request.get_json(silent=True) or {}
            filename = o.preview_voice(data.get("voice", ""))
            return jsonify({"filename": filename})

        # ------------------------------------------------------------------
        # API: Spam
        # ------------------------------------------------------------------

        @self.app.route("/api/spam_config", methods=["GET"])
        @self._require_auth
        def spam_config():
            return jsonify(o.get_spam_config())

        @self.app.route("/api/spam_toggle", methods=["POST"])
        @self._require_auth
        def spam_toggle():
            state = o.set_spam_enabled(not o.spam_enabled)
            return jsonify({"enabled": state})

        @self.app.route("/api/spam_set", methods=["POST"])
        @self._require_auth
        def spam_set():
            data = request.get_json(silent=True) or {}
            ok = o.set_spam_config(
                rate_limit=data.get("rate_limit"),
                window=data.get("window"),
                dup_window=data.get("dup_window"),
            )
            return jsonify({"success": ok})

        @self.app.route("/api/banned_words", methods=["GET"])
        @self._require_auth
        def banned_words():
            return jsonify(o.banned_words)

        @self.app.route("/api/banned_words", methods=["POST"])
        @self._require_auth
        def add_banned_word():
            data = request.get_json(silent=True) or {}
            ok = o.add_banned_word(data.get("word", ""))
            return jsonify({"success": ok, "words": o.banned_words})

        @self.app.route("/api/banned_words", methods=["DELETE"])
        @self._require_auth
        def remove_banned_word():
            data = request.get_json(silent=True) or {}
            ok = o.remove_banned_word(data.get("word", ""))
            return jsonify({"success": ok, "words": o.banned_words})

        # ------------------------------------------------------------------
        # API: Event Rules
        # ------------------------------------------------------------------

        @self.app.route("/api/event_rules", methods=["GET"])
        @self._require_auth
        def event_rules():
            return jsonify(o.get_event_rules())

        @self.app.route("/api/event_rules", methods=["POST"])
        @self._require_auth
        def add_event_rule():
            data = request.get_json(silent=True) or {}
            result = o.add_event_rule(data)
            if result is None:
                return jsonify({"success": False, "error": "Datos invalidos"}), 400
            return jsonify({"success": True, "rules": o.get_event_rules()})

        @self.app.route("/api/event_rules/<int:index>", methods=["PUT"])
        @self._require_auth
        def update_event_rule(index):
            data = request.get_json(silent=True) or {}
            ok = o.update_event_rule(index, data)
            return jsonify({"success": ok, "rules": o.get_event_rules()})

        @self.app.route("/api/event_rules/<int:index>", methods=["DELETE"])
        @self._require_auth
        def delete_event_rule(index):
            ok = o.delete_event_rule_by_index(index)
            return jsonify({"success": ok, "rules": o.get_event_rules()})

        @self.app.route("/api/test_rule", methods=["POST"])
        @self._require_auth
        def test_rule():
            data = request.get_json(silent=True) or {}
            gift = data.get("gift", "Test")
            user = data.get("user", "TestUser")
            diamonds = data.get("diamonds", 0)

            matched = []
            for rule in o._event_rules:
                trigger = rule.get("trigger", "")
                trigger_value = str(rule.get("trigger_value", ""))
                is_match = False
                if trigger == "gift" and gift.lower() == trigger_value.lower():
                    is_match = True
                elif trigger == "diamonds" and diamonds >= int(trigger_value or "0"):
                    is_match = True
                if is_match:
                    actions_summary = [a.get("type") for a in rule.get("actions", [])]
                    matched.append({"name": rule["name"], "actions": actions_summary})

            o.handle_tiktok_event({
                "type": "gift",
                "user": user,
                "gift": gift,
                "amount": 1,
                "diamond_value": diamonds,
                "timestamp": time.time()
            })
            return jsonify({
                "status": "ok",
                "matched_rules": matched,
                "tts_enabled": o.tts_enabled,
                "tiktok_enabled": o.tiktok_enabled,
            })

        @self.app.route("/api/test_actions", methods=["POST"])
        @self._require_auth
        def test_actions():
            data = request.get_json(silent=True) or {}
            actions = data.get("actions", [])
            gift = data.get("gift", "Test")
            user = data.get("user", "TestUser")
            diamonds = data.get("diamonds", 0)

            if not actions:
                return jsonify({"success": False, "error": "No hay acciones"}), 400
            if len(actions) > 20:
                return jsonify({"success": False, "error": "Maximo 20 acciones permitidas"}), 400

            o.test_actions(actions, user, gift, diamonds)
            return jsonify({
                "success": True,
                "tts_enabled": o.tts_enabled,
                "tiktok_enabled": o.tiktok_enabled,
            })

        @self.app.route("/api/overlay_config", methods=["POST"])
        @self._require_auth
        def overlay_config():
            data = request.get_json(silent=True) or {}
            bg = data.get("background", "transparent")
            debug = data.get("debug", False)
            o.set_overlay_config(background=bg, debug=debug)
            o.publish("overlay_config", {
                "background": bg,
                "debug": debug,
            })
            return jsonify({"status": "ok"})

        # ------------------------------------------------------------------
        # API: Export / Import
        # ------------------------------------------------------------------

        @self.app.route("/api/export_config", methods=["GET"])
        @self._require_auth
        def export_config():
            tts_status = o.get_tts_status()
            spam = o.get_spam_config()
            presets = o.list_presets()
            env_vars = {}
            for key in ["TIKTOK_USERNAME", "GROQ_API_KEY", "GROQ_MODEL", "TTS_ENABLED",
                         "TTS_COOLDOWN", "TTS_ENGINE", "TTS_VOICE", "TTS_VOICE_BLEND",
                         "TTS_SPEED", "TTS_LANG", "TTS_PITCH", "TTS_VOLUME",
                         "OVERLAY_PORT", "PANEL_PORT", "HOST"]:
                val = os.getenv(key, "")
                if key == "GROQ_API_KEY" and val:
                    val = "***REDACTED***"
                env_vars[key] = val
            return jsonify({
                "env": env_vars,
                "tts": tts_status,
                "spam": spam,
                "presets": presets,
                "exported_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            })

        @self.app.route("/api/import_config", methods=["POST"])
        @self._require_auth
        def import_config():
            data = request.get_json(silent=True) or {}
            tts = data.get("tts", {})
            if tts:
                tts_client = o.tts_client
                if tts_client:
                    if tts.get("engine"):
                        tts_client.set_engine(tts["engine"])
                    if tts.get("voice_blend"):
                        tts_client.set_voice_blend(tts["voice_blend"])
                        tts_client.set_voice("")
                    elif tts.get("voice"):
                        tts_client.set_voice(tts["voice"])
                    if tts.get("speed"):
                        tts_client.set_speed(tts["speed"])
                    if tts.get("lang"):
                        tts_client.set_lang(tts["lang"])
                    if tts.get("pitch") is not None:
                        tts_client.set_pitch(tts["pitch"])
                    if tts.get("volume") is not None:
                        tts_client.set_volume(tts["volume"])
            spam = data.get("spam", {})
            if spam:
                o.spam_enabled = spam.get("enabled", True)
                if spam.get("rate_limit"):
                    o.spam_rate_limit = spam["rate_limit"]
                if spam.get("window"):
                    o.spam_window = spam["window"]
                if spam.get("dup_window"):
                    o.spam_dup_window = spam["dup_window"]
                if spam.get("banned_words"):
                    o.banned_words = spam["banned_words"]
                    o._save_banned_words()
            presets = data.get("presets", {})
            if presets:
                o._presets.update(presets)
                o._save_presets()
            o._save_user_settings()
            o.log("Configuracion importada correctamente")
            return jsonify({"success": True})

        # ------------------------------------------------------------------
        # API: Points / Leaderboard
        # ------------------------------------------------------------------

        @self.app.route("/api/points", methods=["GET"])
        @self._require_auth
        def points():
            user = request.args.get("user", "")
            return jsonify({"user": user, "points": o.get_user_points(user)})

        @self.app.route("/api/leaderboard", methods=["GET"])
        @self._require_auth
        def leaderboard():
            limit = int(request.args.get("limit", 10))
            return jsonify(o.get_leaderboard(limit))

        # ------------------------------------------------------------------
        # API: Welcome Config
        # ------------------------------------------------------------------

        @self.app.route("/api/welcome_config", methods=["GET"])
        @self._require_auth
        def welcome_config_get():
            return jsonify({
                "enabled": o.welcome_enabled,
                "template": o.welcome_template,
            })

        @self.app.route("/api/welcome_config", methods=["POST"])
        @self._require_auth
        def welcome_config_post():
            data = request.get_json(silent=True) or {}
            o.set_welcome_config(
                enabled=data.get("enabled"),
                template=data.get("template"),
            )
            return jsonify({"success": True})

        # ------------------------------------------------------------------
        # API: VTube Studio
        # ------------------------------------------------------------------

        @self.app.route("/api/vtube_status", methods=["GET"])
        @self._require_auth
        def vtube_status():
            if o.vtube_client:
                return jsonify(o.vtube_client.get_status())
            return jsonify({"connected": False, "enabled": False})

        @self.app.route("/api/vtube_connect", methods=["POST"])
        @self._require_auth
        def vtube_connect():
            if o.vtube_client:
                ok = o.vtube_client.connect()
                return jsonify({"success": ok})
            return jsonify({"success": False, "error": "VTube client no disponible"})

        @self.app.route("/api/vtube_disconnect", methods=["POST"])
        @self._require_auth
        def vtube_disconnect():
            if o.vtube_client:
                o.vtube_client.disconnect()
                return jsonify({"success": True})
            return jsonify({"success": False})

        @self.app.route("/api/vtube_expression", methods=["POST"])
        @self._require_auth
        def vtube_expression():
            data = request.get_json(silent=True) or {}
            expr = data.get("expression", "happy")
            if o.vtube_client:
                ok = o.vtube_client.trigger_expression(expr)
                return jsonify({"success": ok, "expression": expr})
            return jsonify({"success": False, "error": "VTube client no disponible"})

        @self.app.route("/api/vtube_hotkey", methods=["POST"])
        @self._require_auth
        def vtube_hotkey():
            data = request.get_json(silent=True) or {}
            hk = data.get("hotkey", "")
            if not hk:
                return jsonify({"success": False, "error": "Falta nombre de hotkey"}), 400
            if o.vtube_client:
                ok = o.vtube_client.trigger_hotkey(hk)
                return jsonify({"success": ok, "hotkey": hk})
            return jsonify({"success": False, "error": "VTube client no disponible"})

        # ------------------------------------------------------------------
        # API: SFX
        # ------------------------------------------------------------------

        @self.app.route("/api/sfx_files", methods=["GET"])
        @self._require_auth
        def sfx_files():
            return jsonify(o.list_sfx_files())

        @self.app.route("/api/sfx_config", methods=["GET"])
        @self._require_auth
        def sfx_config_get():
            return jsonify(o.get_sfx_config())

        @self.app.route("/api/sfx_config", methods=["POST"])
        @self._require_auth
        def sfx_config_post():
            data = request.get_json(silent=True) or {}
            event_type = data.get("event", "")
            filename = data.get("file", "")
            if not event_type or not filename:
                return jsonify({"success": False, "error": "Faltan event o file"}), 400
            o.set_sfx(event_type, filename)
            return jsonify({"success": True})

        @self.app.route("/api/sfx_config", methods=["DELETE"])
        @self._require_auth
        def sfx_config_delete():
            data = request.get_json(silent=True) or {}
            event_type = data.get("event", "")
            if not event_type:
                return jsonify({"success": False, "error": "Falta event"}), 400
            o.remove_sfx(event_type)
            return jsonify({"success": True})

    def run(self):
        host = getattr(self.config, 'HOST', '127.0.0.1')
        port = getattr(self.config, 'OVERLAY_PORT', 5000)
        super().run(host=host, port=port)
