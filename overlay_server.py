import json
import logging
from flask import send_from_directory, Response, request, jsonify
from sse_server import SseFlaskServer

logger = logging.getLogger(__name__)

class OverlayServer(SseFlaskServer):
    def __init__(self, orchestrator, config):
        super().__init__(config, static_dir=config.OVERLAY_DIR)
        self.orchestrator = orchestrator
        self._setup_overlay_routes()

    def _setup_overlay_routes(self):
        @self.app.route("/")
        def index():
            return send_from_directory(self.config.OVERLAY_DIR, "index.html")

        @self.app.route("/<path:filename>")
        def static_files(filename):
            return self._serve_static(filename)

        @self.app.route("/audio/<path:filename>")
        def audio_files(filename):
            return send_from_directory(self.config.AUDIO_DIR, filename)

        @self.app.route("/api/vtube_mouth", methods=["POST"])
        def vtube_mouth():
            data = request.get_json(silent=True) or {}
            open_val = float(data.get("open", 0))
            if self.orchestrator.vtube_client:
                ok = self.orchestrator.vtube_client._inject_params(
                    {"MouthOpen": open_val, "MouthSmile": 0.02}, silent=True
                )
                return jsonify({"success": ok, "open": open_val})
            return jsonify({"success": False})

        @self.app.route("/api/playback_started", methods=["POST"])
        def playback_started():
            data = request.get_json(silent=True) or {}
            item_id = data.get("item_id", "")
            if item_id:
                self.orchestrator.pipeline.mark_playback_started(item_id)
            return jsonify({"success": True})

        @self.app.route("/api/playback_done", methods=["POST"])
        def playback_done():
            data = request.get_json(silent=True) or {}
            item_id = data.get("item_id", "")
            if item_id:
                self.orchestrator.pipeline.mark_playback_done(item_id)
            return jsonify({"success": True})

        @self.app.route("/stream")
        def stream():
            initial = {
                "type": "overlay_config",
                "data": {
                    "background": self.orchestrator.overlay_bg,
                    "debug": self.orchestrator.overlay_debug,
                }
            }
            return Response(
                self._event_stream(initial_event=initial),
                mimetype="text/event-stream; charset=utf-8"
            )

    def run(self):
        super().run(host=self.config.HOST, port=self.config.OVERLAY_PORT)
