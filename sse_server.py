import os
import json
import queue
import logging
import threading
from flask import Flask, send_from_directory, Response

logger = logging.getLogger(__name__)

class SseFlaskServer:
    """Clase base para servidores Flask con SSE (Server-Sent Events).
    
    Usa broadcast a todos los suscriptores activos. Cada conexion SSE
    tiene su propia cola, asi que nunca se pierden eventos por reconexiones."""

    def __init__(self, config, static_dir=None):
        self.config = config
        self.static_dir = static_dir
        self.app = Flask(__name__, static_folder=None)
        self._subscribers = []          # lista de Queue (una por conexion SSE)
        self._subscribers_lock = threading.Lock()
        self._running = False
        self._shutdown_sentinel = object()
        self._setup_routes()

    def _setup_routes(self):
        """Sobrescribir en subclases para definir rutas adicionales."""
        pass

    def _event_stream(self, initial_event=None):
        """Generador SSE con cola propia para cada cliente."""
        client_q = queue.Queue(maxsize=500)
        with self._subscribers_lock:
            self._subscribers.append(client_q)
        client_id = id(client_q)
        logger.info(f"[SSE] Client #{client_id} connected to {self.__class__.__name__}. Subscribers: {len(self._subscribers)}")
        try:
            if initial_event is not None:
                yield f"data: {json.dumps(initial_event, ensure_ascii=False)}\n\n"

            event_count = 0
            while self._running:
                try:
                    msg = client_q.get(timeout=2)
                    if msg is self._shutdown_sentinel:
                        break
                    event_count += 1
                    yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                except queue.Empty:
                    # Heartbeat cada 2s para mantener vivo el navegador
                    yield f":heartbeat\n\n"
                    continue
            logger.info(f"[SSE] Client #{client_id} loop ended. Events yielded: {event_count}")
        finally:
            with self._subscribers_lock:
                if client_q in self._subscribers:
                    self._subscribers.remove(client_q)
            logger.info(f"[SSE] Client #{client_id} disconnected. Remaining: {len(self._subscribers)}")

    def _serve_static(self, filename):
        """Sirve archivos estáticos desde static_dir."""
        if self.static_dir:
            return send_from_directory(self.static_dir, filename)
        return "Not found", 404

    def handle_event(self, event_type, data):
        """Broadcast a todos los suscriptores activos (no bloquea con suscriptores lentos)."""
        msg = {"type": event_type, "data": data}
        # Snapshot de suscriptores bajo lock para no bloquear publicaciones concurrentes
        with self._subscribers_lock:
            subscribers_snapshot = list(self._subscribers)
        
        dead = []
        for client_q in subscribers_snapshot:
            try:
                client_q.put_nowait(msg)
            except queue.Full:
                dead.append(client_q)
        # Limpiar colas bloqueadas fuera del lock
        if dead:
            with self._subscribers_lock:
                for d in dead:
                    if d in self._subscribers:
                        try:
                            d.put_nowait(self._shutdown_sentinel)
                        except Exception:
                            pass
                        try:
                            self._subscribers.remove(d)
                        except ValueError:
                            pass

    def start(self):
        self._running = True

    def stop(self):
        self._running = False
        with self._subscribers_lock:
            for client_q in self._subscribers:
                try:
                    client_q.put_nowait(self._shutdown_sentinel)
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
