import os
import json
import queue
import logging
import threading
from flask import Flask, send_from_directory, Response

logger = logging.getLogger(__name__)

class OverlayServer:
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
            return send_from_directory(self.config.OVERLAY_DIR, "index.html")

        @self.app.route("/<path:filename>")
        def static_files(filename):
            return send_from_directory(self.config.OVERLAY_DIR, filename)

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
        logger.info(f"OverlayServer iniciado en http://{self.config.HOST}:{self.config.OVERLAY_PORT}")
        self.app.run(
            host=self.config.HOST,
            port=self.config.OVERLAY_PORT,
            threaded=True,
            debug=False,
            use_reloader=False
        )
