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
from vtube_client import VTubeStudioClient
from unified_server import UnifiedServer

# ANSI colors
C = {
    "RST": "\033[0m",
    "RED": "\033[91m", "GRN": "\033[92m", "YEL": "\033[93m",
    "BLU": "\033[94m", "MAG": "\033[95m", "CYN": "\033[96m",
    "WHT": "\033[97m", "GRY": "\033[90m",
    "BOLD": "\033[1m", "DIM": "\033[2m",
}

class ColoredFormatter(logging.Formatter):
    def format(self, record):
        msg = record.getMessage()
        name = record.name
        level = record.levelname

        # Color por nivel
        lvl_color = C["WHT"]
        if level == "WARNING": lvl_color = C["YEL"]
        elif level == "ERROR": lvl_color = C["RED"]
        elif level == "DEBUG": lvl_color = C["GRY"]

        # Color por contenido del mensaje
        msg_color = C["WHT"]
        if "vtube" in name or "VTube" in msg or "VTS" in msg:
            msg_color = C["MAG"]
        elif "tts" in name or "TTS" in msg or "Kokoro" in msg or "gTTS" in msg:
            msg_color = C["GRN"]
        elif "ai" in name:
            msg_color = C["BLU"]
        elif "tiktok" in name:
            msg_color = C["CYN"]
        elif name == "event_orchestrator":
            if "TikTok" in msg:
                if "gift" in msg.lower() or "donac" in msg.lower() or "diam" in msg.lower():
                    msg_color = C["MAG"]
                elif "message" in msg.lower() or "mensaje" in msg.lower():
                    msg_color = C["CYN"]
                elif "like" in msg.lower():
                    msg_color = C["BLU"]
                elif "join" in msg.lower():
                    msg_color = C["GRN"]
                else:
                    msg_color = C["WHT"]
            elif "VTube" in msg or "expresion" in msg.lower():
                msg_color = C["MAG"]
            elif "SPAM" in msg or "bloqueado" in msg.lower():
                msg_color = C["RED"]
            elif "AI" in msg or "respondi" in msg.lower():
                msg_color = C["BLU"]
            elif "Regla" in msg or "regla" in msg.lower() or "Preset" in msg:
                msg_color = C["GRN"]
            else:
                msg_color = C["GRY"]
        elif name == "werkzeug":
            msg_color = C["DIM"]
        elif name == "websocket":
            msg_color = C["DIM"]

        # Formatear
        time_str = self.formatTime(record, "%H:%M:%S")
        lvl_str = f"{lvl_color}{level:<7}{C['RST']}"
        name_str = f"{C['DIM']}{name}{C['RST']}"

        # Acortar nombres largos
        if name == "event_orchestrator": name_str = f"{C['DIM']}events{C['RST']}"
        elif name == "tts_client": name_str = f"{C['DIM']}tts{C['RST']}"
        elif name == "vtube_client": name_str = f"{C['DIM']}vtube{C['RST']}"
        elif name == "tiktok_client": name_str = f"{C['DIM']}tiktok{C['RST']}"
        elif name == "ai_client": name_str = f"{C['DIM']}ai{C['RST']}"
        elif name == "werkzeug": name_str = f"{C['DIM']}http{C['RST']}"
        elif name == "websocket": name_str = f"{C['DIM']}ws{C['RST']}"

        return f"{C['DIM']}{time_str}{C['RST']} {lvl_str} {name_str} {msg_color}{msg}{C['RST']}"

def setup_logging():
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(ColoredFormatter())
    logging.basicConfig(level=logging.INFO, handlers=[handler])
    # Bajar nivel de werkzeug y websocket para menos ruido
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    logging.getLogger("websocket").setLevel(logging.WARNING)

def main():
    setup_logging()
    logger = logging.getLogger("main")
    
    config = Config()
    os.makedirs(config.AUDIO_DIR, exist_ok=True)
    
    orchestrator = EventOrchestrator(config)
    
    ai = AIClient(config)
    tts = TTSClient(config)
    vtube = VTubeStudioClient(config)
    
    orchestrator.set_ai_client(ai)
    orchestrator.set_tts_client(tts)
    orchestrator.set_vtube_client(vtube)
    
    tiktok = TikTokClient(orchestrator, config)
    orchestrator.set_tiktok_client(tiktok)
    
    server = UnifiedServer(orchestrator, config)

    orchestrator.register_listener("server", server.handle_event)
    orchestrator.register_listener("vtube", vtube.handle_event)

    threads = [
        threading.Thread(target=tiktok.start, daemon=True, name="TikTok"),
        threading.Thread(target=server.run, daemon=True, name="Server"),
    ]

    for t in threads:
        t.start()

    logger.info("=" * 50)
    logger.info("Sistema iniciado.")
    logger.info(f"Panel:   http://localhost:{config.OVERLAY_PORT}")
    logger.info(f"Overlay: http://localhost:{config.OVERLAY_PORT}/overlay")
    logger.info("Presiona Ctrl+C para detener.")
    logger.info("=" * 50)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Deteniendo sistema...")
        tiktok.stop()
        server.stop()

if __name__ == "__main__":
    main()
