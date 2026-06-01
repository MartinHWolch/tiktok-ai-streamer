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
    HOST = os.getenv("HOST", "127.0.0.1")
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
    TTS_EDGE_VOICE = _get("tts_edge_voice", "TTS_EDGE_VOICE", "es-MX-DaliaNeural")
    TTS_VOICE_BLEND = _get("tts_voice_blend", "TTS_VOICE_BLEND", "")
    TTS_SPEED = float(_get("tts_speed", "TTS_SPEED", "1.0"))
    TTS_LANG = _get("tts_lang", "TTS_LANG", "es")
    TTS_PITCH = float(_get("tts_pitch", "TTS_PITCH", "0"))
    TTS_VOLUME = float(_get("tts_volume", "TTS_VOLUME", "1.0"))
    
    READ_COMMENTS_ENABLED = str(_get("read_comments_enabled", "READ_COMMENTS_ENABLED", True)).lower() in ("true", "1", "yes")
    COMMENT_VOICE = _get("comment_voice", "COMMENT_VOICE", "")
    COMMENT_SPEED = float(_get("comment_speed", "COMMENT_SPEED", "1.0"))
    COMMENT_PITCH = float(_get("comment_pitch", "COMMENT_PITCH", "0"))
    COMMENT_VOLUME = float(_get("comment_volume", "COMMENT_VOLUME", "1.0"))
    COMMENT_LANG = _get("comment_lang", "COMMENT_LANG", "es")
    
    KOKORO_MODEL = os.getenv("KOKORO_MODEL", os.path.join(BASE_DIR, "models", "kokoro-v1.0.fp16.onnx"))
    KOKORO_MODEL_FP32 = os.getenv("KOKORO_MODEL_FP32", os.path.join(BASE_DIR, "models", "kokoro-v1.0.onnx"))
    KOKORO_VOICES = os.getenv("KOKORO_VOICES", os.path.join(BASE_DIR, "models", "voices-v1.0.bin"))
    
    PIPER_MODEL_PATH = os.getenv("PIPER_MODEL_PATH", os.path.join(BASE_DIR, "models", "piper", "model.onnx"))
    
    AI_ENABLED = str(_get("ai_enabled", "AI_ENABLED", "False")).lower() in ("true", "1", "yes")
    LOG_MAX_LINES = int(_get("log_max_lines", "LOG_MAX_LINES", 50))
    
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL = os.getenv("GROQ_MODEL", _get("ai_model", "GROQ_MODEL", "llama-3.1-8b-instant"))
    AI_MAX_TOKENS = int(_get("ai_max_tokens", "AI_MAX_TOKENS", 100))
    AI_TEMPERATURE = float(_get("ai_temperature", "AI_TEMPERATURE", 0.7))
    AI_SYSTEM_PROMPT = _get("ai_system_prompt", "AI_SYSTEM_PROMPT",
        "Eres un streamer virtual en TikTok. Responde de forma breve, divertida y en español. "
        "Maximo 2 oraciones. "
        "Puedes incluir al inicio de tu respuesta etiquetas de emocion y sonido en este formato:\n"
        "[emotion:happy] para feliz\n"
        "[emotion:angry] para enojado\n"
        "[emotion:surprised] para sorprendido\n"
        "[emotion:sad] para triste\n"
        "[emotion:laughing] para risa\n"
        "[emotion:wink] para guino\n"
        "Disponibles: happy, very_happy, angry, furious, surprised, shocked, sad, crying, wink, blush, "
        "neutral, laughing, scared, sleepy, smug, curious, tongue_out, focused.\n"
        "Ejemplo: [emotion:happy][sfx:ding] Que bueno verte por aqui!"
    )
    
    PANEL_PASSWORD = os.getenv("PANEL_PASSWORD", _config.get("panel_password", ""))
