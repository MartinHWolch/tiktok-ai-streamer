import os
import json
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def _load_config_json():
    path = os.path.join(BASE_DIR, "config.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

_config = _load_config_json()

def _get(key, env_key, default):
    env_val = os.getenv(env_key)
    if env_val is not None and env_val != "":
        return env_val
    return _config.get(key, default)

class Config:
    HOST = os.getenv("HOST", "0.0.0.0")
    OVERLAY_PORT = int(os.getenv("OVERLAY_PORT", 5000))
    PANEL_PORT = int(os.getenv("PANEL_PORT", 5001))
    AUDIO_DIR = os.path.join(BASE_DIR, "audio")
    OVERLAY_DIR = os.path.join(BASE_DIR, "overlay")
    PANEL_DIR = os.path.join(BASE_DIR, "panel")
    
    TIKTOK_USERNAME = os.getenv("TIKTOK_USERNAME", "demo_user")
    SIMULATION_INTERVAL = int(_get("simulation_interval", "SIMULATION_INTERVAL", 3))
    
    TTS_ENABLED = str(_get("tts_enabled", "TTS_ENABLED", True)).lower() in ("true", "1", "yes")
    TTS_COOLDOWN = int(_get("tts_cooldown", "TTS_COOLDOWN", 5))
    
    TTS_ENGINE = _get("tts_engine", "TTS_ENGINE", "kokoro")
    TTS_VOICE = _get("tts_voice", "TTS_VOICE", "im_nicola")
    TTS_VOICE_BLEND = _get("tts_voice_blend", "TTS_VOICE_BLEND", "")
    TTS_SPEED = float(_get("tts_speed", "TTS_SPEED", "1.0"))
    TTS_LANG = _get("tts_lang", "TTS_LANG", "es")
    TTS_PITCH = float(_get("tts_pitch", "TTS_PITCH", "0"))
    TTS_VOLUME = float(_get("tts_volume", "TTS_VOLUME", "1.0"))
    
    KOKORO_MODEL = os.getenv("KOKORO_MODEL", os.path.join(BASE_DIR, "models", "kokoro-v1.0.fp16.onnx"))
    KOKORO_MODEL_FP32 = os.getenv("KOKORO_MODEL_FP32", os.path.join(BASE_DIR, "models", "kokoro-v1.0.onnx"))
    KOKORO_VOICES = os.getenv("KOKORO_VOICES", os.path.join(BASE_DIR, "models", "voices-v1.0.bin"))
    
    PIPER_MODEL_PATH = os.getenv("PIPER_MODEL_PATH", os.path.join(BASE_DIR, "models", "piper", "model.onnx"))
    
    AI_ENABLED = str(_get("ai_enabled", "AI_ENABLED", "False")).lower() in ("true", "1", "yes")
    LOG_MAX_LINES = int(_get("log_max_lines", "LOG_MAX_LINES", 50))
    
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL = os.getenv("GROQ_MODEL", _get("ai_model", "GROQ_MODEL", "llama3-8b-8192"))
    AI_MAX_TOKENS = int(_get("ai_max_tokens", "AI_MAX_TOKENS", 100))
    AI_TEMPERATURE = float(_get("ai_temperature", "AI_TEMPERATURE", 0.7))
    AI_SYSTEM_PROMPT = _get("ai_system_prompt", "AI_SYSTEM_PROMPT", "Eres un asistente de streaming para TikTok. Responde de forma breve, divertida y en español. Maximo 2 oraciones.")
