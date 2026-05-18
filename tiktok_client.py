import threading
import time
import random
import logging

logger = logging.getLogger(__name__)

# Intentar importar TikTokLive (opcional)
try:
    from TikTokLive import TikTokLiveClient
    from TikTokLive.events import ConnectEvent, CommentEvent, GiftEvent, LikeEvent, JoinEvent
    TIKTOK_LIVE_AVAILABLE = True
except ImportError:
    TikTokLiveClient = None
    ConnectEvent = CommentEvent = GiftEvent = LikeEvent = JoinEvent = None
    TIKTOK_LIVE_AVAILABLE = False
    logger.info("TikTokLive no instalado. Modo real no disponible. Ejecuta: pip install TikTokLive")

class TikTokClient:
    def __init__(self, orchestrator, config):
        self.orchestrator = orchestrator
        self.config = config
        self._running = False
        self._thread = None
        self.simulation_enabled = True
        self._sim_running = False
        self._sim_thread = None
        self._real_client = None
        
        self.target_username = getattr(config, "TIKTOK_USERNAME", "demo_user")
        
        self.demo_users = ["user1", "fan_tiktok", "gamer123", "anonymous", "supporter"]
        self.demo_messages = ["¡Hola!", "¿Cómo estás?", "Saludos desde México", "Me encanta este stream", "jajaja", "wow"]
        self.demo_gifts = ["Rosa", "Panda", "Corazón", "León", "Universo"]

    def start(self):
        if self._running:
            return
        self._running = True
        if self.simulation_enabled:
            self._start_simulation()
        else:
            self._start_real()
        logger.info(f"TikTokClient iniciado. Modo: {'simulación' if self.simulation_enabled else 'real'} (@{self.target_username})")

    def stop(self):
        self._running = False
        self._stop_simulation()
        self._stop_real()
        logger.info("TikTokClient detenido.")

    def toggle_simulation(self):
        if not self._running:
            self.simulation_enabled = not self.simulation_enabled
            return self.simulation_enabled
        
        was_sim = self.simulation_enabled
        self.simulation_enabled = not self.simulation_enabled
        
        if was_sim and not self.simulation_enabled:
            self._stop_simulation()
            self._start_real()
        elif not was_sim and self.simulation_enabled:
            self._stop_real()
            self._start_simulation()
        
        logger.info(f"TikTokClient modo cambiado a: {'simulación' if self.simulation_enabled else 'real'}")
        return self.simulation_enabled

    # === Simulación ===
    def _start_simulation(self):
        self._sim_running = True
        self._sim_thread = threading.Thread(target=self._sim_loop, daemon=True)
        self._sim_thread.start()

    def _stop_simulation(self):
        self._sim_running = False
        if self._sim_thread:
            self._sim_thread.join(timeout=2)
            self._sim_thread = None

    def _sim_loop(self):
        while self._sim_running and self._running:
            time.sleep(self.config.SIMULATION_INTERVAL)
            if not self._sim_running or not self._running:
                break
            self._emit_random_event()

    def _emit_random_event(self):
        r = random.random()
        user = random.choice(self.demo_users)
        
        if r < 0.6:
            event = {"type": "message", "user": user, "text": random.choice(self.demo_messages), "timestamp": time.time()}
        elif r < 0.8:
            event = {"type": "gift", "user": user, "gift": random.choice(self.demo_gifts), "amount": random.randint(1, 5), "timestamp": time.time()}
        elif r < 0.9:
            event = {"type": "like", "user": user, "count": random.randint(1, 10), "timestamp": time.time()}
        else:
            event = {"type": "join", "user": user, "timestamp": time.time()}
        
        logger.debug(f"Evento simulado: {event['type']} de {user}")
        self.orchestrator.handle_tiktok_event(event)

    # === Real (TikTokLive) ===
    def _start_real(self):
        if not TIKTOK_LIVE_AVAILABLE:
            logger.error("TikTokLive no está instalado. No se puede iniciar modo real. Ejecuta: pip install TikTokLive")
            self.simulation_enabled = True
            self._start_simulation()
            return
        
        try:
            self._real_client = TikTokLiveClient(unique_id=f"@{self.target_username}")
            
            @self._real_client.on(ConnectEvent)
            async def on_connect(event):
                logger.info(f"Conectado al live de @{self.target_username}")
            
            @self._real_client.on(CommentEvent)
            async def on_comment(event):
                self.orchestrator.handle_tiktok_event({
                    "type": "message",
                    "user": event.user.nickname or event.user.unique_id,
                    "text": event.comment,
                    "timestamp": time.time()
                })
            
            @self._real_client.on(GiftEvent)
            async def on_gift(event):
                self.orchestrator.handle_tiktok_event({
                    "type": "gift",
                    "user": event.user.nickname or event.user.unique_id,
                    "gift": event.gift.name if hasattr(event.gift, 'name') else "Regalo",
                    "amount": event.gift.repeat_count if hasattr(event.gift, 'repeat_count') else 1,
                    "timestamp": time.time()
                })
            
            @self._real_client.on(LikeEvent)
            async def on_like(event):
                self.orchestrator.handle_tiktok_event({
                    "type": "like",
                    "user": event.user.nickname or event.user.unique_id,
                    "count": event.count if hasattr(event, 'count') else 1,
                    "timestamp": time.time()
                })
            
            @self._real_client.on(JoinEvent)
            async def on_join(event):
                self.orchestrator.handle_tiktok_event({
                    "type": "join",
                    "user": event.user.nickname or event.user.unique_id,
                    "timestamp": time.time()
                })
            
            self._real_thread = threading.Thread(target=self._run_real_client, daemon=True)
            self._real_thread.start()
        except Exception as e:
            logger.error(f"Error al iniciar TikTokLive: {e}")
            self.simulation_enabled = True
            self._start_simulation()

    def _run_real_client(self):
        try:
            import asyncio
            asyncio.run(self._real_client.run())
        except Exception as e:
            logger.error(f"Error en TikTokLive run: {e}")

    def _stop_real(self):
        if self._real_client:
            try:
                self._real_client.stop()
            except Exception as e:
                logger.warning(f"Error al detener TikTokLive: {e}")
            self._real_client = None
