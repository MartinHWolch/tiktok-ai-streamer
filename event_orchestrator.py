import time
import logging
import json
import os
from collections import deque

logger = logging.getLogger(__name__)

class EventOrchestrator:
    def __init__(self, config):
        self.config = config
        self.listeners = {}
        self.tts_enabled = config.TTS_ENABLED
        self.ai_enabled = config.AI_ENABLED
        self.tiktok_enabled = False
        self.ai_client = None
        self.tts_client = None
        self.vtube_client = None
        self.tiktok_client = None
        self._cooldowns = {}
        self.logs = deque(maxlen=config.LOG_MAX_LINES)
        self._presets_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tts_presets.json")
        self._presets = {}
        self._start_time = time.time()
        self._stats = {"messages": 0, "gifts": 0, "likes": 0, "joins": 0, "ai_replies": 0, "tts_played": 0}
        self._load_presets()

        # Anti-spam
        self._user_timestamps = {}
        self._user_messages = {}
        self.spam_rate_limit = 2
        self.spam_window = 3
        self.spam_dup_window = 30
        self.spam_enabled = True
        self.banned_words = []
        self._banned_words_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "banned_words.json")
        self._load_banned_words()

    def set_ai_client(self, client):
        self.ai_client = client

    def set_tts_client(self, client):
        self.tts_client = client
        if self.tts_client:
            self.tts_client.set_enabled(self.tts_enabled)

    def set_vtube_client(self, client):
        self.vtube_client = client

    def set_tiktok_client(self, client):
        self.tiktok_client = client

    def register_listener(self, name, callback):
        self.listeners[name] = callback
        logger.info(f"Listener registrado: {name}")

    def log(self, message):
        entry = f"[{time.strftime('%H:%M:%S')}] {message}"
        self.logs.append(entry)
        logger.info(message)
        self.publish("log", {"message": entry})

    def handle_tiktok_event(self, event):
        if not self.tiktok_enabled:
            return
        event_type = event.get("type")
        user = event.get("user", "unknown")
        
        if event_type == "message":
            self._stats["messages"] += 1
        elif event_type == "gift":
            self._stats["gifts"] += 1
        elif event_type == "like":
            self._stats["likes"] += 1
        elif event_type == "join":
            self._stats["joins"] += 1
        
        self.log(f"TikTok {event_type}: {user}")
        
        if event_type == "message":
            self._process_message(event)
        elif event_type == "gift":
            self._process_gift(event)
        elif event_type == "like":
            self.publish("overlay_alert", {"type": "like", "user": user, "count": event.get("count", 1)})
        elif event_type == "join":
            self.publish("overlay_alert", {"type": "join", "user": user})
        
        self.publish("tiktok_event", event)

    def _process_message(self, event):
        text = event.get("text", "").strip()
        user = event.get("user", "")

        if self._check_spam(user, text):
            return
        
        if text.startswith("!"):
            self._handle_command(text, user)
            return
        
        reply = None
        if self.ai_enabled and self.ai_client:
            try:
                reply = self.ai_client.generate_reply(text, user)
            except Exception as e:
                logger.error(f"AI error: {e}")
        
        if reply:
            self._stats["ai_replies"] += 1
            self.log(f"AI respondió a {user}: {reply}")
            self.publish("overlay_message", {"user": "Bot", "text": reply, "original_user": user})
            self._trigger_tts(reply)
        
        self.publish("overlay_message", {"user": user, "text": text})

    def _handle_command(self, text, user):
        cmd = text.lower().split()[0]
        
        if cmd == "!tts":
            arg = text.lower().split()[1] if len(text.split()) > 1 else ""
            if arg == "on":
                self.tts_enabled = True
                self.log(f"Comando !tts on por {user}")
            elif arg == "off":
                self.tts_enabled = False
                self.log(f"Comando !tts off por {user}")
            else:
                state = self.toggle_tts()
                self.log(f"Comando !tts toggle por {user} -> {'ON' if state else 'OFF'}")
        
        elif cmd == "!ai":
            arg = text.lower().split()[1] if len(text.split()) > 1 else ""
            if arg == "on":
                self.ai_enabled = True
                self.log(f"Comando !ai on por {user}")
            elif arg == "off":
                self.ai_enabled = False
                self.log(f"Comando !ai off por {user}")
            else:
                state = self.toggle_ai()
                self.log(f"Comando !ai toggle por {user} -> {'ON' if state else 'OFF'}")
        
        elif cmd == "!skip":
            self.publish("tts_skip", {})
            self.log(f"Comando !skip por {user}")
        
        elif cmd == "!help":
            help_text = "Comandos: !tts on/off, !ai on/off, !skip, !help"
            self.publish("overlay_alert", {"type": "info", "user": "Sistema", "text": help_text})
            self.log(f"Comando !help por {user}")
        
        else:
            self.log(f"Comando desconocido por {user}: {cmd}")

    def _process_gift(self, event):
        self.publish("overlay_alert", {
            "type": "gift",
            "user": event.get("user"),
            "gift": event.get("gift"),
            "amount": event.get("amount", 1)
        })
        if self.vtube_client:
            self.publish("vtube_expression", {"expression": "happy"})

    def _is_cooldown(self, key):
        now = time.time()
        if key in self._cooldowns:
            if now - self._cooldowns[key] < self.config.TTS_COOLDOWN:
                return True
        self._cooldowns[key] = now
        return False

    def _trigger_tts(self, text):
        if not self.tts_enabled or not self.tts_client:
            return
        if self._is_cooldown("tts"):
            logger.info("TTS en cooldown. Texto no reproducido.")
            return
        
        self._stats["tts_played"] += 1
        self.publish("tts_speak", {"text": text})
        filename = self.tts_client.speak(text)
        if filename:
            self.publish("tts_audio", {"url": f"/audio/{filename}"})

    def toggle_tts(self):
        self.tts_enabled = not self.tts_enabled
        if self.tts_client:
            self.tts_client.set_enabled(self.tts_enabled)
        self.log(f"TTS toggled: {self.tts_enabled}")
        return self.tts_enabled

    def toggle_ai(self):
        self.ai_enabled = not self.ai_enabled
        self.log(f"AI toggled: {self.ai_enabled}")
        return self.ai_enabled

    def set_tts_engine(self, engine):
        if self.tts_client and self.tts_client.set_engine(engine):
            self.log(f"TTS engine cambiado a: {engine}")
            return True
        return False

    def set_tts_voice(self, voice):
        if self.tts_client:
            self.tts_client.set_voice(voice)
            self.log(f"TTS voice cambiada a: {voice}")
            return True
        return False

    def set_tts_voice_blend(self, blend):
        if self.tts_client:
            self.tts_client.set_voice_blend(blend)
            self.log(f"TTS voice blend cambiado a: {blend}")
            return True
        return False

    def set_tts_speed(self, speed):
        if self.tts_client:
            self.tts_client.set_speed(speed)
            self.log(f"TTS speed cambiado a: {speed}")
            return True
        return False

    def set_tts_lang(self, lang):
        if self.tts_client:
            self.tts_client.set_lang(lang)
            self.log(f"TTS lang cambiado a: {lang}")
            return True
        return False

    def set_tts_pitch(self, pitch):
        if self.tts_client:
            self.tts_client.set_pitch(pitch)
            self.log(f"TTS pitch cambiado a: {pitch}")
            return True
        return False

    def set_tts_volume(self, volume):
        if self.tts_client:
            self.tts_client.set_volume(volume)
            self.log(f"TTS volume cambiado a: {volume}")
            return True
        return False

    def set_kokoro_model(self, model_key):
        if self.tts_client:
            ok = self.tts_client.set_kokoro_model(model_key)
            if ok:
                self.log(f"Kokoro modelo cambiado a: {model_key}")
            return ok
        return False

    def get_tts_status(self):
        if self.tts_client:
            return self.tts_client.get_status()
        return {}

    def test_tts(self, text="Prueba de texto a voz"):
        if not self.tts_client:
            self.log("TTS no está disponible para prueba")
            return None
        self.publish("tts_speak", {"text": text})
        saved = self.tts_client._last_speak
        self.tts_client.reset_cooldown()
        try:
            filename = self.tts_client.speak(text)
        finally:
            self.tts_client._last_speak = saved
        if filename:
            self.publish("tts_audio", {"url": f"/audio/{filename}"})
            self.log(f"TTS de prueba generado: {filename}")
        return filename

    def get_tiktok_simulation(self):
        if self.tiktok_client:
            return getattr(self.tiktok_client, "simulation_enabled", True)
        return True

    def get_stats(self):
        uptime = int(time.time() - self._start_time)
        sim = self.get_tiktok_simulation()
        tiktok_mode = "simulacion" if sim else "real"
        tiktok_connected = getattr(self.tiktok_client, "_real_connected", False) if self.tiktok_client else False
        return {
            "uptime": uptime,
            "messages": self._stats["messages"],
            "gifts": self._stats["gifts"],
            "likes": self._stats["likes"],
            "joins": self._stats["joins"],
            "ai_replies": self._stats["ai_replies"],
            "tts_played": self._stats["tts_played"],
            "tts_enabled": self.tts_enabled,
            "ai_enabled": self.ai_enabled,
            "tiktok_enabled": self.tiktok_enabled,
            "tiktok_mode": tiktok_mode,
            "tiktok_connected": tiktok_connected,
            "tts_engine": self.get_tts_status().get("engine", "kokoro"),
        }

    def toggle_tiktok(self):
        self.tiktok_enabled = not self.tiktok_enabled
        self.log(f"TikTok eventos: {'ON' if self.tiktok_enabled else 'OFF'}")
        return self.tiktok_enabled

    def toggle_tiktok_simulation(self):
        if self.tiktok_client:
            state = self.tiktok_client.toggle_simulation()
            self.log(f"TikTok modo: {'simulación' if state else 'real'}")
            return state
        return True

    def simulate_gift(self, user="Admin", gift="TestGift"):
        self.handle_tiktok_event({
            "type": "gift",
            "user": user,
            "gift": gift,
            "amount": 1,
            "timestamp": time.time()
        })

    def test_message(self, text="Mensaje de prueba", user="Admin"):
        self.handle_tiktok_event({
            "type": "message",
            "user": user,
            "text": text,
            "timestamp": time.time()
        })

    def publish(self, event_type, data):
        for name, callback in self.listeners.items():
            try:
                callback(event_type, data)
            except Exception as e:
                logger.error(f"Error en listener {name}: {e}")

    # --- Anti-spam ---
    def _load_banned_words(self):
        try:
            if os.path.exists(self._banned_words_path):
                with open(self._banned_words_path, "r", encoding="utf-8") as f:
                    self.banned_words = json.load(f)
        except Exception:
            self.banned_words = []

    def _save_banned_words(self):
        try:
            with open(self._banned_words_path, "w", encoding="utf-8") as f:
                json.dump(self.banned_words, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error guardando banned words: {e}")

    def _check_spam(self, user, text):
        if not self.spam_enabled:
            return False

        now = time.time()
        user_lower = user.lower()

        # Banned words
        if self.banned_words:
            text_lower = text.lower()
            for word in self.banned_words:
                if word.lower() in text_lower:
                    self.log(f"SPAM bloqueado ({user}): palabra baneada '{word}'")
                    return True

        # Rate limit
        timestamps = self._user_timestamps.get(user_lower, [])
        timestamps = [t for t in timestamps if now - t < self.spam_window]
        timestamps.append(now)
        self._user_timestamps[user_lower] = timestamps
        if len(timestamps) > self.spam_rate_limit:
            self.log(f"SPAM bloqueado ({user}): rate limit {self.spam_rate_limit}/{self.spam_window}s")
            return True

        # Duplicate messages
        recent = self._user_messages.get(user_lower, [])
        recent = [(t, m) for t, m in recent if now - t < self.spam_dup_window]
        for _, prev_text in recent:
            if prev_text.lower().strip() == text.lower().strip():
                recent.append((now, text))
                self._user_messages[user_lower] = recent
                self.log(f"SPAM bloqueado ({user}): mensaje duplicado")
                return True
        recent.append((now, text))
        self._user_messages[user_lower] = recent
        return False

    def set_spam_enabled(self, enabled):
        self.spam_enabled = enabled
        self.log(f"Filtro anti-spam: {'ON' if enabled else 'OFF'}")
        return enabled

    def set_spam_config(self, rate_limit=None, window=None, dup_window=None):
        if rate_limit is not None:
            self.spam_rate_limit = max(1, int(rate_limit))
        if window is not None:
            self.spam_window = max(1, int(window))
        if dup_window is not None:
            self.spam_dup_window = max(5, int(dup_window))
        self.log(f"Anti-spam config: {self.spam_rate_limit} msgs/{self.spam_window}s, duplicados {self.spam_dup_window}s")
        return True

    def get_spam_config(self):
        return {
            "enabled": self.spam_enabled,
            "rate_limit": self.spam_rate_limit,
            "window": self.spam_window,
            "dup_window": self.spam_dup_window,
            "banned_words": self.banned_words,
        }

    def add_banned_word(self, word):
        word = word.strip().lower()
        if word and word not in self.banned_words:
            self.banned_words.append(word)
            self._save_banned_words()
            self.log(f"Palabra baneada agregada: {word}")
            return True
        return False

    def remove_banned_word(self, word):
        word = word.strip().lower()
        if word in self.banned_words:
            self.banned_words.remove(word)
            self._save_banned_words()
            self.log(f"Palabra baneada eliminada: {word}")
            return True
        return False

    # --- Presets de TTS ---
    def _load_presets(self):
        try:
            if os.path.exists(self._presets_path):
                with open(self._presets_path, "r", encoding="utf-8") as f:
                    self._presets = json.load(f)
                logger.info(f"Presets cargados: {len(self._presets)}")
            else:
                self._presets = {}
        except Exception as e:
            logger.error(f"Error cargando presets: {e}")
            self._presets = {}

    def _save_presets(self):
        try:
            with open(self._presets_path, "w", encoding="utf-8") as f:
                json.dump(self._presets, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error guardando presets: {e}")

    def list_presets(self):
        return self._presets

    def save_preset(self, name):
        if not name or not self.tts_client:
            return False
        status = self.tts_client.get_status()
        self._presets[name] = {
            "engine": status.get("engine", "kokoro"),
            "voice": status.get("voice", ""),
            "voice_blend": status.get("voice_blend", ""),
            "speed": status.get("speed", 1.0),
            "lang": status.get("lang", "es"),
        }
        self._save_presets()
        self.log(f"Preset guardado: {name}")
        return True

    def load_preset(self, name):
        if name not in self._presets:
            return False
        p = self._presets[name]
        if self.tts_client:
            self.tts_client.set_engine(p.get("engine", "kokoro"))
            if p.get("voice_blend"):
                with self.tts_client._state_lock:
                    self.tts_client.voice_blend = p["voice_blend"]
                    self.tts_client.voice = ""
            else:
                self.tts_client.set_voice(p.get("voice", ""))
            self.tts_client.set_speed(p.get("speed", 1.0))
            self.tts_client.set_lang(p.get("lang", "es"))
        self.log(f"Preset cargado: {name}")
        return True

    def delete_preset(self, name):
        if name in self._presets:
            del self._presets[name]
            self._save_presets()
            self.log(f"Preset eliminado: {name}")
            return True
        return False

    def preview_voice(self, voice_name):
        if not self.tts_client or not self.tts_client._kokoro:
            return None
        with self.tts_client._state_lock:
            prev_voice = self.tts_client.voice
            prev_blend = self.tts_client.voice_blend
            self.tts_client.voice = voice_name
            self.tts_client.voice_blend = ""
        try:
            filename = self.tts_client._speak_kokoro(
                "Hola, esta es una demostracion de esta voz."
            )
            return filename
        except Exception as e:
            logger.error(f"Error preview voz: {e}")
            return None
        finally:
            with self.tts_client._state_lock:
                self.tts_client.voice = prev_voice
                self.tts_client.voice_blend = prev_blend
