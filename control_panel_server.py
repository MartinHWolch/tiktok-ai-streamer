import os
import json
import queue
import logging
import threading
import time
from flask import Flask, send_from_directory, request, jsonify, Response

logger = logging.getLogger(__name__)

class ControlPanelServer:
    def __init__(self, orchestrator, config):
        self.orchestrator = orchestrator
        self.config = config
        self.app = Flask(__name__, static_folder=None)
        self.event_queue = queue.Queue()
        self._running = False
        self._stream_threads = []
        self._stream_lock = threading.Lock()
        self._shutdown_sentinel = object()
        self._setup_routes()

    def _setup_routes(self):
        @self.app.route("/")
        def index():
            return send_from_directory(self.config.PANEL_DIR, "index.html")

        @self.app.route("/audio/<path:filename>")
        def audio_files(filename):
            return send_from_directory(self.config.AUDIO_DIR, filename)

        @self.app.route("/stream")
        def stream():
            def event_stream():
                with self._stream_lock:
                    self._stream_threads.append(threading.current_thread())
                try:
                    while self._running:
                        try:
                            msg = self.event_queue.get(timeout=1)
                            if msg is self._shutdown_sentinel:
                                break
                            yield f"data: {json.dumps(msg)}\n\n"
                        except queue.Empty:
                            continue
                finally:
                    with self._stream_lock:
                        t = threading.current_thread()
                        if t in self._stream_threads:
                            self._stream_threads.remove(t)
            return Response(event_stream(), mimetype="text/event-stream")

        @self.app.route("/api/status", methods=["GET"])
        def status():
            return jsonify({
                "tts_enabled": self.orchestrator.tts_enabled,
                "ai_enabled": self.orchestrator.ai_enabled,
                "tiktok_enabled": self.orchestrator.tiktok_enabled
            })

        @self.app.route("/api/toggle_tts", methods=["POST"])
        def toggle_tts():
            state = self.orchestrator.toggle_tts()
            return jsonify({"tts_enabled": state})

        @self.app.route("/api/toggle_ai", methods=["POST"])
        def toggle_ai():
            state = self.orchestrator.toggle_ai()
            return jsonify({"ai_enabled": state})

        @self.app.route("/api/toggle_tiktok", methods=["POST"])
        def toggle_tiktok():
            state = self.orchestrator.toggle_tiktok()
            return jsonify({"tiktok_enabled": state})

        @self.app.route("/api/toggle_simulation", methods=["POST"])
        def toggle_simulation():
            state = self.orchestrator.toggle_tiktok_simulation()
            return jsonify({"simulation": state})

        @self.app.route("/api/stats", methods=["GET"])
        def stats():
            return jsonify(self.orchestrator.get_stats())

        @self.app.route("/api/setup_status", methods=["GET"])
        def setup_status():
            import os as _os
            kokoro_fp16 = _os.path.exists(self.config.KOKORO_MODEL)
            kokoro_fp32 = _os.path.exists(self.config.KOKORO_MODEL_FP32)
            kokoro_voices = _os.path.exists(self.config.KOKORO_VOICES)
            piper_model = _os.path.exists(self.config.PIPER_MODEL_PATH)
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
                "tts_enabled": self.orchestrator.tts_enabled,
                "ai_enabled": self.orchestrator.ai_enabled,
                "tts_engine": self.config.TTS_ENGINE,
            })

        @self.app.route("/api/simulate_gift", methods=["POST"])
        def simulate_gift():
            data = request.get_json(silent=True) or {}
            self.orchestrator.simulate_gift(
                user=data.get("user", "Admin"),
                gift=data.get("gift", "TestGift")
            )
            return jsonify({"status": "ok"})

        @self.app.route("/api/test_message", methods=["POST"])
        def test_message():
            data = request.get_json(silent=True) or {}
            self.orchestrator.test_message(
                text=data.get("text", "Mensaje de prueba"),
                user=data.get("user", "Admin")
            )
            return jsonify({"status": "ok"})

        @self.app.route("/api/tts_status", methods=["GET"])
        def tts_status():
            return jsonify(self.orchestrator.get_tts_status())

        @self.app.route("/api/set_tts_engine", methods=["POST"])
        def set_tts_engine():
            data = request.get_json(silent=True) or {}
            success = self.orchestrator.set_tts_engine(data.get("engine", "kokoro"))
            return jsonify({"success": success, "status": self.orchestrator.get_tts_status()})

        @self.app.route("/api/set_tts_voice", methods=["POST"])
        def set_tts_voice():
            data = request.get_json(silent=True) or {}
            success = self.orchestrator.set_tts_voice(data.get("voice", "im_nicola"))
            return jsonify({"success": success, "status": self.orchestrator.get_tts_status()})

        @self.app.route("/api/set_tts_voice_blend", methods=["POST"])
        def set_tts_voice_blend():
            data = request.get_json(silent=True) or {}
            success = self.orchestrator.set_tts_voice_blend(data.get("blend", ""))
            return jsonify({"success": success, "status": self.orchestrator.get_tts_status()})

        @self.app.route("/api/set_tts_speed", methods=["POST"])
        def set_tts_speed():
            data = request.get_json(silent=True) or {}
            success = self.orchestrator.set_tts_speed(data.get("speed", 1.0))
            return jsonify({"success": success, "status": self.orchestrator.get_tts_status()})

        @self.app.route("/api/set_tts_lang", methods=["POST"])
        def set_tts_lang():
            data = request.get_json(silent=True) or {}
            success = self.orchestrator.set_tts_lang(data.get("lang", "es"))
            return jsonify({"success": success, "status": self.orchestrator.get_tts_status()})

        @self.app.route("/api/set_tts_pitch", methods=["POST"])
        def set_tts_pitch():
            data = request.get_json(silent=True) or {}
            success = self.orchestrator.set_tts_pitch(data.get("pitch", 0))
            return jsonify({"success": success, "status": self.orchestrator.get_tts_status()})

        @self.app.route("/api/set_tts_volume", methods=["POST"])
        def set_tts_volume():
            data = request.get_json(silent=True) or {}
            success = self.orchestrator.set_tts_volume(data.get("volume", 1.0))
            return jsonify({"success": success, "status": self.orchestrator.get_tts_status()})

        @self.app.route("/api/set_kokoro_model", methods=["POST"])
        def set_kokoro_model():
            data = request.get_json(silent=True) or {}
            success = self.orchestrator.set_kokoro_model(data.get("model", "fp16"))
            return jsonify({"success": success, "status": self.orchestrator.get_tts_status()})

        @self.app.route("/api/test_tts", methods=["POST"])
        def test_tts():
            data = request.get_json(silent=True) or {}
            filename = self.orchestrator.test_tts(data.get("text", "Prueba de texto a voz"))
            return jsonify({"filename": filename, "status": "ok" if filename else "error"})

        @self.app.route("/api/logs", methods=["GET"])
        def get_logs():
            return jsonify(list(self.orchestrator.logs))

        # --- Presets TTS ---
        @self.app.route("/api/tts_presets", methods=["GET"])
        def tts_presets():
            return jsonify(self.orchestrator.list_presets())

        @self.app.route("/api/save_preset", methods=["POST"])
        def save_preset():
            data = request.get_json(silent=True) or {}
            ok = self.orchestrator.save_preset(data.get("name", ""))
            return jsonify({"success": ok, "presets": self.orchestrator.list_presets()})

        @self.app.route("/api/load_preset", methods=["POST"])
        def load_preset():
            data = request.get_json(silent=True) or {}
            ok = self.orchestrator.load_preset(data.get("name", ""))
            return jsonify({"success": ok, "status": self.orchestrator.get_tts_status()})

        @self.app.route("/api/delete_preset", methods=["POST"])
        def delete_preset():
            data = request.get_json(silent=True) or {}
            ok = self.orchestrator.delete_preset(data.get("name", ""))
            return jsonify({"success": ok, "presets": self.orchestrator.list_presets()})

        @self.app.route("/api/preview_voice", methods=["POST"])
        def preview_voice():
            data = request.get_json(silent=True) or {}
            filename = self.orchestrator.preview_voice(data.get("voice", ""))
            return jsonify({"filename": filename})

        # --- Spam ---
        @self.app.route("/api/spam_config", methods=["GET"])
        def spam_config():
            return jsonify(self.orchestrator.get_spam_config())

        @self.app.route("/api/spam_toggle", methods=["POST"])
        def spam_toggle():
            state = self.orchestrator.set_spam_enabled(not self.orchestrator.spam_enabled)
            return jsonify({"enabled": state})

        @self.app.route("/api/spam_set", methods=["POST"])
        def spam_set():
            data = request.get_json(silent=True) or {}
            ok = self.orchestrator.set_spam_config(
                rate_limit=data.get("rate_limit"),
                window=data.get("window"),
                dup_window=data.get("dup_window"),
            )
            return jsonify({"success": ok})

        @self.app.route("/api/banned_words", methods=["GET"])
        def banned_words():
            return jsonify(self.orchestrator.banned_words)

        @self.app.route("/api/banned_words", methods=["POST"])
        def add_banned_word():
            data = request.get_json(silent=True) or {}
            ok = self.orchestrator.add_banned_word(data.get("word", ""))
            return jsonify({"success": ok, "words": self.orchestrator.banned_words})

        @self.app.route("/api/banned_words", methods=["DELETE"])
        def remove_banned_word():
            data = request.get_json(silent=True) or {}
            ok = self.orchestrator.remove_banned_word(data.get("word", ""))
            return jsonify({"success": ok, "words": self.orchestrator.banned_words})

        # --- Event Rules ---
        @self.app.route("/api/event_rules", methods=["GET"])
        def event_rules():
            return jsonify(self.orchestrator.get_event_rules())

        @self.app.route("/api/event_rules", methods=["POST"])
        def add_event_rule():
            data = request.get_json(silent=True) or {}
            result = self.orchestrator.add_event_rule(data)
            if result is None:
                return jsonify({"success": False, "error": "Datos invalidos"}), 400
            return jsonify({"success": True, "rules": self.orchestrator.get_event_rules()})

        @self.app.route("/api/event_rules/<int:index>", methods=["PUT"])
        def update_event_rule(index):
            data = request.get_json(silent=True) or {}
            ok = self.orchestrator.update_event_rule(index, data)
            return jsonify({"success": ok, "rules": self.orchestrator.get_event_rules()})

        @self.app.route("/api/event_rules/<int:index>", methods=["DELETE"])
        def delete_event_rule(index):
            ok = self.orchestrator.delete_event_rule_by_index(index)
            return jsonify({"success": ok, "rules": self.orchestrator.get_event_rules()})

        @self.app.route("/api/test_rule", methods=["POST"])
        def test_rule():
            data = request.get_json(silent=True) or {}
            gift = data.get("gift", "Test")
            user = data.get("user", "TestUser")
            diamonds = data.get("diamonds", 0)
            
            matched = []
            for rule in self.orchestrator._event_rules:
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
            
            self.orchestrator.handle_tiktok_event({
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
                "tts_enabled": self.orchestrator.tts_enabled,
                "tiktok_enabled": self.orchestrator.tiktok_enabled,
            })

        @self.app.route("/api/overlay_config", methods=["POST"])
        def overlay_config():
            data = request.get_json(silent=True) or {}
            self.orchestrator.publish("overlay_config", {
                "background": data.get("background", "transparent"),
                "debug": data.get("debug", False),
            })
            return jsonify({"status": "ok"})
            return jsonify({
                "status": "ok",
                "matched_rules": matched,
                "tts_enabled": self.orchestrator.tts_enabled,
                "tiktok_enabled": self.orchestrator.tiktok_enabled,
            })

        # --- Export / Import ---
        @self.app.route("/api/export_config", methods=["GET"])
        def export_config():
            import os as _os
            tts_status = self.orchestrator.get_tts_status()
            spam = self.orchestrator.get_spam_config()
            presets = self.orchestrator.list_presets()
            env_vars = {}
            for key in ["TIKTOK_USERNAME", "GROQ_API_KEY", "GROQ_MODEL", "TTS_ENABLED",
                         "TTS_COOLDOWN", "TTS_ENGINE", "TTS_VOICE", "TTS_VOICE_BLEND",
                         "TTS_SPEED", "TTS_LANG", "TTS_PITCH", "TTS_VOLUME",
                         "OVERLAY_PORT", "PANEL_PORT", "HOST"]:
                env_vars[key] = _os.getenv(key, "")
            return jsonify({
                "env": env_vars,
                "tts": tts_status,
                "spam": spam,
                "presets": presets,
                "exported_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            })

        @self.app.route("/api/import_config", methods=["POST"])
        def import_config():
            data = request.get_json(silent=True) or {}
            errors = []
            # Aplicar config TTS
            tts = data.get("tts", {})
            if tts:
                tts_client = self.orchestrator.tts_client
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
            # Aplicar spam config
            spam = data.get("spam", {})
            if spam:
                self.orchestrator.spam_enabled = spam.get("enabled", True)
                if spam.get("rate_limit"):
                    self.orchestrator.spam_rate_limit = spam["rate_limit"]
                if spam.get("window"):
                    self.orchestrator.spam_window = spam["window"]
                if spam.get("dup_window"):
                    self.orchestrator.spam_dup_window = spam["dup_window"]
                if spam.get("banned_words"):
                    self.orchestrator.banned_words = spam["banned_words"]
                    self.orchestrator._save_banned_words()
            # Guardar presets
            presets = data.get("presets", {})
            if presets:
                self.orchestrator._presets.update(presets)
                self.orchestrator._save_presets()
            self.orchestrator.log("Configuracion importada correctamente")
            return jsonify({"success": True, "errors": errors})

        @self.app.route("/<path:filename>")
        def static_files(filename):
            return send_from_directory(self.config.PANEL_DIR, filename)

    def handle_event(self, event_type, data):
        self.event_queue.put({"type": event_type, "data": data})

    def start(self):
        self._running = True

    def stop(self):
        self._running = False
        for _ in range(len(self._stream_threads) + 1):
            try:
                self.event_queue.put_nowait(self._shutdown_sentinel)
            except queue.Full:
                pass

    def run(self):
        self.start()
        logger.info(f"ControlPanelServer iniciado en http://{self.config.HOST}:{self.config.PANEL_PORT}")
        self.app.run(
            host=self.config.HOST,
            port=self.config.PANEL_PORT,
            threaded=True,
            debug=False,
            use_reloader=False
        )
