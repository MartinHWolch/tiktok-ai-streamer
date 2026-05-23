import os
import json
import queue
import logging
import threading
from flask import Flask, send_from_directory, Response

logger = logging.getLogger(__name__)

class SseFlaskServer:
    """Clase base para servidores Flask con SSE (Server-Sent Events)."""

    def __init__(self, config, static_dir=None):
        self.config = config
        self.static_dir = static_dir
        self.app = Flask(__name__, static_folder=None)
        self.event_queue = queue.Queue()
        self._running = False
        self._stream_threads = []
        self._stream_lock = threading.Lock()
        self._shutdown_sentinel = object()
        self._setup_routes()

    def _setup_routes(self):
        """Sobrescribir en subclases para definir rutas adicionales."""
        pass

    def _event_stream(self, initial_event=None):
        """Generador SSE genérico. Opcionalmente envía un evento inicial."""
        with self._stream_lock:
            self._stream_threads.append(threading.current_thread())
        try:
            if initial_event is not None:
                yield f"data: {json.dumps(initial_event, ensure_ascii=False)}\n\n"

            while self._running:
                try:
                    msg = self.event_queue.get(timeout=1)
                    if msg is self._shutdown_sentinel:
                        break
                    yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                except queue.Empty:
                    continue
        finally:
            with self._stream_lock:
                t = threading.current_thread()
                if t in self._stream_threads:
                    self._stream_threads.remove(t)

    def _serve_static(self, filename):
        """Sirve archivos estáticos desde static_dir."""
        if self.static_dir:
            return send_from_directory(self.static_dir, filename)
        return "Not found", 404

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

    def run(self, host=None, port=None):
        self.start()
        host = host or getattr(self.config, 'HOST', '127.0.0.1')
        port = port or getattr(self.config, 'OVERLAY_PORT', 5000)
        logger.info(f"{self.__class__.__name__} iniciado en http://{host}:{port}")
        self.app.run(
            host=host,
            port=port,
            threaded=True,
            debug=False,
            use_reloader=False
        )
