"""
ResponsePipeline: cola de procesamiento 3-etapas.

Etapa 1 - Incoming: mensajes TikTok recibidos, esperando respuesta de IA
Etapa 2 - Generated: respuestas IA listas, esperando generacion de audio TTS
Etapa 3 - Playback: audio TTS generado, esperando o siendo reproducido por el overlay
"""

import json
import time
import queue
import logging
import threading
import uuid

logger = logging.getLogger(__name__)

MAX_HISTORY = 50
MAX_QUEUE_SIZE = 20


class ResponseItem:
    """Una respuesta en el pipeline con timestamps de cada etapa."""

    __slots__ = ("id", "user", "trigger", "original_text", "text",
                 "emotion", "sfx", "audio_file", "status", "error",
                 "received_at", "generated_at", "tts_at", "played_at")

    def __init__(self, user, trigger, original_text="", text="", emotion="neutral", sfx=None):
        self.id = uuid.uuid4().hex[:12]
        self.user = user
        self.trigger = trigger
        self.original_text = original_text
        self.text = text
        self.emotion = emotion
        self.sfx = sfx
        self.audio_file = None
        self.status = "received"  # received → generating → generated → tts_queued → playing → done/error
        self.error = None
        self.received_at = time.time()
        self.generated_at = None
        self.tts_at = None
        self.played_at = None

    def to_dict(self):
        return {
            "id": self.id,
            "user": self.user,
            "trigger": self.trigger,
            "original_text": self.original_text[:100],
            "text": self.text[:200],
            "emotion": self.emotion,
            "sfx": self.sfx,
            "audio_file": self.audio_file,
            "status": self.status,
            "error": self.error,
            "received_at": self.received_at,
            "generated_at": self.generated_at,
            "tts_at": self.tts_at,
            "played_at": self.played_at,
        }


class ResponsePipeline:
    """Pipeline 3-etapas: incoming → generated → playback."""

    def __init__(self):
        # 3 colas
        self._incoming_queue = queue.Queue(maxsize=MAX_QUEUE_SIZE)
        self._generated_queue = queue.Queue(maxsize=MAX_QUEUE_SIZE)
        self._playback_queue = queue.Queue(maxsize=MAX_QUEUE_SIZE)

        # Item actual en cada etapa
        self._generating = None   # item siendo procesado por IA
        self._making_tts = None   # item siendo procesado por TTS
        self._playing = None      # item siendo reproducido

        # Historiales para auditoria
        self._incoming_log = []    # todos los mensajes recibidos
        self._generated_log = []   # respuestas generadas por IA
        self._playback_log = []    # items que se reprodujeron o estan en playback

        self._lock = threading.Lock()
        self._running = False
        self._incoming_thread = None
        self._tts_thread = None

        # Callbacks
        self.ai_generate = None     # fn(text, user) -> dict|str|None
        self.tts_speak = None       # fn(text) -> filename|None
        self.on_change = None       # fn(pipeline) notifica al panel
        self.dispatch_sfx = None
        self.dispatch_emotion = None
        self.mouth_open_fn = None   # fn() abre boca avatar
        self.mouth_close_fn = None  # fn() cierra boca avatar

    def start(self):
        if self._running:
            return
        self._running = True
        self._incoming_thread = threading.Thread(target=self._incoming_loop, daemon=True, name="pipeline-incoming")
        self._tts_thread = threading.Thread(target=self._tts_loop, daemon=True, name="pipeline-tts")
        self._incoming_thread.start()
        self._tts_thread.start()
        logger.info("Pipeline iniciado (3 etapas)")

    def stop(self):
        self._running = False
        for q in (self._incoming_queue, self._generated_queue, self._playback_queue):
            try: q.put_nowait(None)
            except queue.Full: pass

    # --- Public API ---

    def receive_message(self, user, trigger, original_text):
        """Llamado cuando llega un mensaje de TikTok."""
        item = ResponseItem(user=user, trigger=trigger, original_text=original_text)
        self._incoming_log.append(item)
        if len(self._incoming_log) > MAX_HISTORY:
            self._incoming_log = self._incoming_log[-MAX_HISTORY:]
        try:
            self._incoming_queue.put_nowait(item)
            self._notify()
        except queue.Full:
            logger.warning(f"Pipeline: cola incoming llena, descartando mensaje de {user}")

    def enqueue_direct_tts(self, user, trigger, text, emotion="neutral", sfx=None):
        """Para comandos/bienvenidas que ya tienen texto (saltan IA)."""
        item = ResponseItem(user=user, trigger=trigger, text=text, emotion=emotion, sfx=sfx)
        item.status = "generated"
        item.generated_at = time.time()
        self._generated_log.append(item)
        if len(self._generated_log) > MAX_HISTORY:
            self._generated_log = self._generated_log[-MAX_HISTORY:]
        try:
            self._generated_queue.put_nowait(item)
            self._notify()
        except queue.Full:
            logger.warning(f"Pipeline: cola generated llena, descartando TTS directo de {user}")

    def mark_playback_started(self, item_id):
        """Llamado cuando el overlay confirma que empezo a reproducir."""
        with self._lock:
            if self._playing and self._playing.id == item_id:
                self._playing.played_at = time.time()
                self._playing.status = "playing"
                self._notify()

    def mark_playback_done(self, item_id):
        """Llamado cuando el overlay confirma que termino de reproducir."""
        with self._lock:
            if self._playing and self._playing.id == item_id:
                self._playing.status = "done"
                self._playback_log.append(self._playing)
                if len(self._playback_log) > MAX_HISTORY:
                    self._playback_log = self._playback_log[-MAX_HISTORY:]
                self._playing = None
                self._notify()

    def skip_current(self):
        with self._lock:
            if self._playing:
                self._playing.status = "skipped"
                self._playback_log.append(self._playing)
                if len(self._playback_log) > MAX_HISTORY:
                    self._playback_log = self._playback_log[-MAX_HISTORY:]
                self._playing = None
                self._notify()

    def get_state(self):
        with self._lock:
            incoming_q = [i.to_dict() for i in list(self._incoming_queue.queue) if i is not None]
            generated_q = [i.to_dict() for i in list(self._generated_queue.queue) if i is not None]
            playback_q = [i.to_dict() for i in list(self._playback_queue.queue) if i is not None]
            return {
                # Colas activas (nuevas 3 etapas)
                "incoming_queue": incoming_q,
                "generating": self._generating.to_dict() if self._generating else None,
                "generated_queue": generated_q,
                "making_tts": self._making_tts.to_dict() if self._making_tts else None,
                "playback_queue": playback_q,
                "playing": self._playing.to_dict() if self._playing else None,
                # Backwards compatibility para panel viejo
                "gen_queue": incoming_q + ([self._generating.to_dict()] if self._generating else []),
                "tts_queue": generated_q + ([self._making_tts.to_dict()] if self._making_tts else []),
                "history": [i.to_dict() for i in self._playback_log[-20:]],
                # Historiales
                "incoming_log": [i.to_dict() for i in self._incoming_log[-20:]],
                "generated_log": [i.to_dict() for i in self._generated_log[-20:]],
                "playback_log": [i.to_dict() for i in self._playback_log[-20:]],
            }

    def _notify(self):
        if self.on_change:
            try:
                self.on_change(self)
            except Exception as e:
                logger.error(f"Pipeline notify error: {e}")

    # --- Etapa 1: Procesar mensajes entrantes (IA) ---

    def _incoming_loop(self):
        while self._running:
            try:
                item = self._incoming_queue.get(timeout=1)
            except queue.Empty:
                continue
            if item is None:
                continue

            with self._lock:
                self._generating = item
            item.status = "generating"
            self._notify()

            try:
                if self.ai_generate:
                    result = self.ai_generate(item.original_text, item.user)
                    if isinstance(result, dict):
                        item.text = result.get("text", "")
                        item.emotion = result.get("emotion", "neutral")
                        item.sfx = result.get("sfx")
                    else:
                        item.text = str(result) if result else ""
                else:
                    item.text = ""

                if item.text:
                    item.status = "generated"
                    item.generated_at = time.time()
                    self._generated_log.append(item)
                    if len(self._generated_log) > MAX_HISTORY:
                        self._generated_log = self._generated_log[-MAX_HISTORY:]
                    self._generated_queue.put(item)
                    self._notify()
                    logger.info(f"Pipeline gen: {item.user} -> '{item.text[:60]}' ({item.emotion})")
                else:
                    item.status = "done"
                    self._notify()
            except Exception as e:
                logger.error(f"Pipeline gen error: {e}")
                item.error = str(e)[:200]
                item.status = "error"
                self._notify()
            finally:
                with self._lock:
                    self._generating = None

    # --- Etapa 2: Generar TTS y pasar a playback ---

    def _tts_loop(self):
        TTS_MIN_GAP = 1.5

        while self._running:
            try:
                item = self._generated_queue.get(timeout=1)
            except queue.Empty:
                continue
            if item is None:
                continue

            with self._lock:
                self._making_tts = item
            item.status = "tts_queued"
            self._notify()

            try:
                # Generar audio TTS
                if self.tts_speak:
                    item.tts_at = time.time()
                    item.status = "making_tts"
                    self._notify()
                    filename = self.tts_speak(item)
                    if filename:
                        item.audio_file = filename

                # Mover a playback queue
                item.status = "playback_queued"
                self._playback_queue.put(item)
                self._notify()
            except Exception as e:
                logger.error(f"Pipeline TTS error: {e}")
                item.error = str(e)[:200]
                item.status = "error"
                self._notify()
            finally:
                with self._lock:
                    self._making_tts = None

            # Esperar a que overlay termine de reproducir
            # El overlay debe llamar mark_playback_done() via API
            # Mientras tanto, dormimos y revisamos
            playback_waited = 0
            while self._running and item.status not in ("done", "error", "skipped"):
                time.sleep(0.5)
                playback_waited += 0.5
                # Timeout de seguridad: si pasaron 30s, forzar done
                if playback_waited > 30:
                    with self._lock:
                        if self._playing and self._playing.id == item.id:
                            self._playing.status = "done"
                            self._playback_log.append(self._playing)
                            if len(self._playback_log) > MAX_HISTORY:
                                self._playback_log = self._playback_log[-MAX_HISTORY:]
                            self._playing = None
                            self._notify()
                    break

            # Gap minimo entre TTS consecutivos
            time.sleep(TTS_MIN_GAP)
