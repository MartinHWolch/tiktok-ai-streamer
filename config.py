import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class Config:
    HOST = os.getenv("HOST", "0.0.0.0")
    OVERLAY_PORT = int(os.getenv("OVERLAY_PORT", 5000))
    PANEL_PORT = int(os.getenv("PANEL_PORT", 5001))
    AUDIO_DIR = os.path.join(BASE_DIR, "audio")
    OVERLAY_DIR = os.path.join(BASE_DIR, "overlay")
    PANEL_DIR = os.path.join(BASE_DIR, "panel")
    
    TIKTOK_USERNAME = os.getenv("TIKTOK_USERNAME", "demo_user")
    SIMULATION_INTERVAL = 3
    
    TTS_ENABLED = os.getenv("TTS_ENABLED", "True").lower() in ("true", "1", "yes")
    TTS_COOLDOWN = int(os.getenv("TTS_COOLDOWN", 5))
    
    # TTS Engine: kokoro, piper, gtts
    TTS_ENGINE = os.getenv("TTS_ENGINE", "kokoro")
    TTS_VOICE = os.getenv("TTS_VOICE", "im_nicola")
    TTS_VOICE_BLEND = os.getenv("TTS_VOICE_BLEND", "")
    TTS_SPEED = float(os.getenv("TTS_SPEED", "1.0"))
    TTS_LANG = os.getenv("TTS_LANG", "es")
    TTS_PITCH = float(os.getenv("TTS_PITCH", "0"))
    TTS_VOLUME = float(os.getenv("TTS_VOLUME", "1.0"))
    
    # Kokoro model paths
    KOKORO_MODEL = os.getenv("KOKORO_MODEL", os.path.join(BASE_DIR, "models", "kokoro-v1.0.fp16.onnx"))
    KOKORO_MODEL_FP32 = os.getenv("KOKORO_MODEL_FP32", os.path.join(BASE_DIR, "models", "kokoro-v1.0.onnx"))
    KOKORO_VOICES = os.getenv("KOKORO_VOICES", os.path.join(BASE_DIR, "models", "voices-v1.0.bin"))
    
    # Piper model path
    PIPER_MODEL_PATH = os.getenv("PIPER_MODEL_PATH", os.path.join(BASE_DIR, "models", "piper", "model.onnx"))
    
    AI_ENABLED = os.getenv("AI_ENABLED", "False").lower() in ("true", "1", "yes")
    AI_RESPONSE_CHANCE = 0.7
    LOG_MAX_LINES = 50
    
    # AI (Groq)
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "llama3-8b-8192")
