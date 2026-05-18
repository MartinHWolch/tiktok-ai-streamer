import os
import json
import queue
import logging
from flask import Flask, send_from_directory, request, jsonify, Response

logger = logging.getLogger(__name__)

class ControlPanelServer:
    def __init__(self, orchestrator, config):
        self.orchestrator = orchestrator
        self.config = config
        self.app = Flask(__name__, static_folder=None)
        self.event_queue = queue.Queue()
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
                while True:
                    msg = self.event_queue.get()
                    yield f"data: {json.dumps(msg)}\n\n"
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

        @self.app.route("/<path:filename>")
        def static_files(filename):
            return send_from_directory(self.config.PANEL_DIR, filename)

    def handle_event(self, event_type, data):
        self.event_queue.put({"type": event_type, "data": data})

    def run(self):
        logger.info(f"ControlPanelServer iniciado en http://{self.config.HOST}:{self.config.PANEL_PORT}")
        self.app.run(
            host=self.config.HOST,
            port=self.config.PANEL_PORT,
            threaded=True,
            debug=False,
            use_reloader=False
        )
