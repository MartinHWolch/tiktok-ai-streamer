"""
ResponsePipeline: cola de procesamiento 2-etapas.

Etapa 1 - Generacion: eventos TikTok → AI genera texto → enqueue para TTS
Etapa 2 - Reproduccion: genera audio TTS → overlay lo reproduce secuencialmente

Cada respuesta tiene formato JSON estructurado:
{
    "id": "uuid",
    "user": "username",
    "trigger": "chat|gift|like|join|command",
    "original_text": "mensaje original",
    "text": "respuesta generada",
    "emotion": "happy|angry|surprised|...",
    "sfx": "sound_file o null",
    "status": "generating|queued|playing|done|error",
    "timestamp": 1234567890.123
}
"""

import json
import time
import queue
import logging
import threading
import uuid

logger = logging.getLogger(__name__)

MAX_HISTORY = 50
MAX_QUEUE_SIZE = 20  # max items waiting for TTS


class ResponseItem:
    """Una respuesta en el pipeline."""

    __slots__ = ("id", "user", "trigger", "original_text", "text",
                 "emotion", "sfx", "audio_file", "status", "timestamp", "error")

    def __init__(self, user, trigger, original_text="", text="", emotion="neutral",
                 sfx=None, status="generating"):
        self.id = uuid.uuid4().hex[:12]
        self.user = user
        self.trigger = trigger
        self.original_text = original_text
        self.text = text
        self.emotion = emotion
        self.sfx = sfx
        self.audio_file = None
        self.status = status
        self.timestamp = time.time()
        self.error = None

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
            "timestamp": self.timestamp,
        }


class ResponsePipeline:
    """Pipeline 2-etapas: generacion → TTS."""

    def __init__(self):
        self._gen_queue = queue.Queue(maxsize=MAX_QUEUE_SIZE)
        self._tts_queue = queue.Queue(maxsize=MAX_QUEUE_SIZE)
        self._playing = None
        self._history = []
        self._lock = threading.Lock()
        self._running = False
        self._gen_thread = None
        self._tts_thread = None

        # Callbacks injectados por el orchestrator
        self.ai_generate = None     # fn(text, user) -> str
        self.tts_speak = None       # fn(text) -> filename|None
        self.on_change = None       # fn(pipeline) notifica al panel
        self.dispatch_sfx = None    # fn(sfx_name) reproduce SFX
        self.dispatch_emotion = None  # fn(emotion) activa VTube

    def start(self):
        if self._running:
            return
        self._running = True
        self._gen_thread = threading.Thread(target=self._gen_loop, daemon=True, name="pipeline-gen")
        self._tts_thread = threading.Thread(target=self._tts_loop, daemon=True, name="pipeline-tts")
        self._gen_thread.start()
        self._tts_thread.start()
        logger.info("Pipeline iniciado (2 etapas)")

    def stop(self):
        self._running = False
        # Desencolar para desbloquear threads
        try:
            self._gen_queue.put_nowait(None)
        except queue.Full:
            pass
        try:
            self._tts_queue.put_nowait(None)
        except queue.Full:
            pass

    def enqueue(self, item: ResponseItem):
        """Agrega un item a la cola de generacion."""
        try:
            self._gen_queue.put_nowait(item)
        except queue.Full:
            logger.warning(f"Pipeline: cola de generacion llena, descartando item de {item.user}")
        self._notify()

    def enqueue_tts(self, item: ResponseItem):
        """Agrega un item YA generado directo a la cola TTS (para comandos, bienvenidas)."""
        item.status = "queued"
        try:
            self._tts_queue.put_nowait(item)
        except queue.Full:
            logger.warning(f"Pipeline: cola TTS llena, descartando item de {item.user}")
        self._notify()

    def skip_current(self):
        """Salta el TTS actual."""
        with self._lock:
            if self._playing:
                self._playing.status = "done"
                self._playing = None

    def get_state(self):
        """Devuelve el estado completo para el panel."""
        with self._lock:
            gen_items = list(self._gen_queue.queue)
            tts_items = list(self._tts_queue.queue)
            return {
                "playing": self._playing.to_dict() if self._playing else None,
                "gen_queue": [i.to_dict() for i in gen_items if i is not None],
                "tts_queue": [i.to_dict() for i in tts_items if i is not None],
                "history": [i.to_dict() for i in self._history[-10:]],
            }

    def _notify(self):
        if self.on_change:
            try:
                self.on_change(self)
            except Exception as e:
                logger.error(f"Pipeline notify error: {e}")

    # --- Etapa 1: Generacion ---

    def _gen_loop(self):
        while self._running:
            try:
                item = self._gen_queue.get(timeout=1)
            except queue.Empty:
                continue
            if item is None:
                continue

            try:
                if self.ai_generate:
                    result = self.ai_generate(item.original_text, item.user)
                    if isinstance(result, dict):
                        # IA devolvio JSON estructurado
                        item.text = result.get("text", "")
                        item.emotion = result.get("emotion", "neutral")
                        item.sfx = result.get("sfx")
                    else:
                        item.text = str(result) if result else ""
                else:
                    item.text = ""

                if item.text:
                    item.status = "queued"
                    self._tts_queue.put(item)
                    logger.info(f"Pipeline gen: {item.user} -> '{item.text[:60]}' (emotion={item.emotion})")
                else:
                    item.status = "done"
                    self._add_history(item)
            except Exception as e:
                logger.error(f"Pipeline gen error: {e}")
                item.error = str(e)[:200]
                item.status = "error"
                self._add_history(item)
            self._notify()

    # --- Etapa 2: TTS ---

    def _tts_loop(self):
        while self._running:
            try:
                item = self._tts_queue.get(timeout=1)
            except queue.Empty:
                continue
            if item is None:
                continue

            with self._lock:
                self._playing = item
            item.status = "playing"
            self._notify()

            try:
                if item.sfx and self.dispatch_sfx:
                    self.dispatch_sfx(item.sfx)
                if item.emotion and self.dispatch_emotion:
                    self.dispatch_emotion(item.emotion)
                if self.tts_speak:
                    filename = self.tts_speak(item.text)
                    if filename:
                        item.audio_file = filename
                item.status = "done"
            except Exception as e:
                logger.error(f"Pipeline TTS error: {e}")
                item.error = str(e)[:200]
                item.status = "error"

            with self._lock:
                self._playing = None
            self._add_history(item)
            self._notify()

    def _add_history(self, item):
        self._history.append(item)
        if len(self._history) > MAX_HISTORY:
            self._history = self._history[-MAX_HISTORY:]
