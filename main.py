import logging
import threading
import time
import sys
import os

from config import Config
from event_orchestrator import EventOrchestrator
from tiktok_client import TikTokClient
from ai_client import AIClient
from tts_client import TTSClient
from vtube_client import VTubeClient
from overlay_server import OverlayServer
from control_panel_server import ControlPanelServer

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )

def main():
    setup_logging()
    logger = logging.getLogger("main")
    
    config = Config()
    os.makedirs(config.AUDIO_DIR, exist_ok=True)
    
    orchestrator = EventOrchestrator(config)
    
    ai = AIClient(config)
    tts = TTSClient(config)
    vtube = VTubeClient(config)
    
    orchestrator.set_ai_client(ai)
    orchestrator.set_tts_client(tts)
    orchestrator.set_vtube_client(vtube)
    
    tiktok = TikTokClient(orchestrator, config)
    orchestrator.set_tiktok_client(tiktok)
    
    overlay = OverlayServer(orchestrator, config)
    panel = ControlPanelServer(orchestrator, config)
    
    orchestrator.register_listener("overlay", overlay.handle_event)
    orchestrator.register_listener("panel", panel.handle_event)
    orchestrator.register_listener("vtube", vtube.handle_event)
    
    threads = [
        threading.Thread(target=tiktok.start, daemon=True, name="TikTok"),
        threading.Thread(target=overlay.run, daemon=True, name="Overlay"),
        threading.Thread(target=panel.run, daemon=True, name="Panel"),
    ]
    
    for t in threads:
        t.start()
    
    logger.info("=" * 50)
    logger.info("Sistema iniciado.")
    logger.info(f"Overlay: http://localhost:{config.OVERLAY_PORT}")
    logger.info(f"Panel:   http://localhost:{config.PANEL_PORT}")
    logger.info("Presiona Ctrl+C para detener.")
    logger.info("=" * 50)
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Deteniendo sistema...")
        tiktok.stop()

if __name__ == "__main__":
    main()
