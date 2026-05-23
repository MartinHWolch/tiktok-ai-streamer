import time
import logging
import json
import os
import threading
from collections import deque

logger = logging.getLogger(__name__)

class EventOrchestrator:
    def __init__(self, config):
        self.config = config
        self.listeners = {}
        self.tts_enabled = config.TTS_ENABLED
        self.ai_enabled = config.AI_ENABLED
        self.tiktok_enabled = True
        self.ai_client = None
        self.tts_client = None
        self.vtube_client = None
        self.tiktok_client = None
        self._cooldowns = {}
        self._cooldown_lock = threading.Lock()
        self.logs = deque(maxlen=config.LOG_MAX_LINES)
        self._presets_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tts_presets.json")
        self._presets = {}
        self._start_time = time.time()
        self._stats = {"messages": 0, "gifts": 0, "likes": 0, "joins": 0, "ai_replies": 0, "tts_played": 0}
        self._load_presets()

        # Anti-spam
        self._user_timestamps = {}
        self._user_messages = {}
        self._spam_lock = threading.Lock()
        self.spam_rate_limit = 2
        self.spam_window = 3
        self.spam_dup_window = 30
        self.spam_enabled = True
        self._max_spam_users = 1000
        self.banned_words = []
        self._banned_words_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "banned_words.json")
        self._last_spam_cleanup = time.time()
        self._load_banned_words()

        # Event rules (gift -> actions)
        self._event_rules_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "event_rules.json")
        self._event_rules = {}
        self._load_event_rules()

        # User settings persistence
        self._user_settings_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_settings.json")
        self.overlay_bg = "transparent"
        self.overlay_debug = False
        self._pending_tts_settings = {}
        self._load_user_settings()

    def set_ai_client(self, client):
        self.ai_client = client

    def set_tts_client(self, client):
        self.tts_client = client
        if self.tts_client:
            self.tts_client.set_enabled(self.tts_enabled)
            if self._pending_tts_settings:
                self._apply_tts_settings(self._pending_tts_settings)
                self._pending_tts_settings.clear()

    def set_vtube_client(self, client):
        self.vtube_client = client

    def set_tiktok_client(self, client):
        self.tiktok_client = client

    def _load_user_settings(self):
        try:
            if os.path.exists(self._user_settings_path):
                with open(self._user_settings_path, "r", encoding="utf-8") as f:
                    settings = json.load(f)
            else:
                return
        except Exception:
            return

        if "tts_enabled" in settings:
            self.tts_enabled = settings["tts_enabled"]
        if "ai_enabled" in settings:
            self.ai_enabled = settings["ai_enabled"]
        if "tiktok_enabled" in settings:
            self.tiktok_enabled = settings["tiktok_enabled"]
        if "spam_enabled" in settings:
            self.spam_enabled = settings["spam_enabled"]
        if "spam_rate_limit" in settings:
            self.spam_rate_limit = settings["spam_rate_limit"]
        if "spam_window" in settings:
            self.spam_window = settings["spam_window"]
        if "spam_dup_window" in settings:
            self.spam_dup_window = settings["spam_dup_window"]
        if "overlay_bg" in settings:
            self.overlay_bg = settings["overlay_bg"]
        if "overlay_debug" in settings:
            self.overlay_debug = settings["overlay_debug"]

        tts_keys = ["tts_engine", "tts_voice", "tts_voice_blend", "tts_speed", "tts_lang", "tts_pitch", "tts_volume", "kokoro_model"]
        self._pending_tts_settings = {k: settings[k] for k in tts_keys if k in settings}

        if self.tts_client and self._pending_tts_settings:
            self._apply_tts_settings(self._pending_tts_settings)
            self._pending_tts_settings = {}

        logger.info(f"User settings cargados: {len(settings)} keys")

    def _apply_tts_settings(self, s):
        t = self.tts_client
        if not t:
            return
        for engine in ("tts_engine", "kokoro"):
            if engine in s:
                t.set_engine(s[engine])
                break
        if "tts_voice" in s:
            t.set_voice(s["tts_voice"])
        if "tts_voice_blend" in s:
            t.set_voice_blend(s["tts_voice_blend"])
        if "tts_speed" in s:
            t.set_speed(s["tts_speed"])
        if "tts_lang" in s:
            t.set_lang(s["tts_lang"])
        if "tts_pitch" in s:
            t.set_pitch(s["tts_pitch"])
        if "tts_volume" in s:
            t.set_volume(s["tts_volume"])
        if "kokoro_model" in s:
            t.set_kokoro_model(s["kokoro_model"])

    def _save_user_settings(self):
        status = self.get_tts_status()
        settings = {
            "tts_enabled": self.tts_enabled,
            "ai_enabled": self.ai_enabled,
            "tiktok_enabled": self.tiktok_enabled,
            "spam_enabled": self.spam_enabled,
            "spam_rate_limit": self.spam_rate_limit,
            "spam_window": self.spam_window,
            "spam_dup_window": self.spam_dup_window,
            "overlay_bg": self.overlay_bg,
            "overlay_debug": self.overlay_debug,
            "tts_engine": status.get("engine", "kokoro"),
            "tts_voice": status.get("voice", ""),
            "tts_voice_blend": status.get("voice_blend", ""),
            "tts_speed": status.get("speed", 1.0),
            "tts_lang": status.get("lang", "es"),
            "tts_pitch": status.get("pitch", 0),
            "tts_volume": status.get("volume", 1.0),
            "kokoro_model": status.get("kokoro_model", ""),
        }
        try:
            with open(self._user_settings_path, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error guardando user settings: {e}")

    def set_overlay_config(self, background=None, debug=None):
        if background is not None:
            self.overlay_bg = background
        if debug is not None:
            self.overlay_debug = debug
        self._save_user_settings()

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
        parts = text.strip().lower().split(maxsplit=1)
        if not parts:
            return
        cmd = parts[0]
        arg = parts[1].strip() if len(parts) > 1 else ""
        
        if cmd == "!tts":
            if arg == "on":
                self.tts_enabled = True
                self._save_user_settings()
                self.log(f"Comando !tts on por {user}")
            elif arg == "off":
                self.tts_enabled = False
                self._save_user_settings()
                self.log(f"Comando !tts off por {user}")
            else:
                state = self.toggle_tts()
                self.log(f"Comando !tts toggle por {user} -> {'ON' if state else 'OFF'}")
        
        elif cmd == "!ai":
            if arg == "on":
                self.ai_enabled = True
                self._save_user_settings()
                self.log(f"Comando !ai on por {user}")
            elif arg == "off":
                self.ai_enabled = False
                self._save_user_settings()
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
        gift_name = event.get("gift", "")
        user = event.get("user", "unknown")
        amount = event.get("amount", 1)
        diamond_value = event.get("diamond_value", 0)

        self.publish("overlay_alert", {
            "type": "gift",
            "user": user,
            "gift": gift_name,
            "amount": amount
        })
        if self.vtube_client:
            self.publish("vtube_expression", {"expression": "happy"})

        # Dispatch event rules
        for rule in self._event_rules:
            trigger = rule.get("trigger", "")
            trigger_value = str(rule.get("trigger_value", ""))

            matched = False
            if trigger == "gift" and gift_name.lower() == trigger_value.lower():
                matched = True
            elif trigger == "diamonds" and diamond_value >= int(trigger_value or "0"):
                matched = True

            if matched:
                self._execute_rule_actions(rule, user, gift_name, diamond_value)

    def _execute_actions(self, actions, user, gift_name, diamond_value):
        for action in actions:
            action_type = action.get("type", "")
            if action_type == "tts":
                msg = action.get("message", "")
                msg = msg.replace("{user}", user).replace("{gift}", gift_name).replace("{diamonds}", str(diamond_value))
                voice_preset = action.get("voice_preset", "")
                if voice_preset and self.tts_client:
                    self.load_preset(voice_preset)
                self._trigger_tts(msg)
            elif action_type == "emoji":
                emojis = action.get("emojis", "🎉")
                count = action.get("count", 30)
                self.publish("overlay_emoji", {"emojis": emojis, "count": count})

    def _execute_rule_actions(self, rule, user, gift_name, diamond_value):
        self._execute_actions(rule.get("actions", []), user, gift_name, diamond_value)

    def test_actions(self, actions, user, gift_name, diamond_value):
        """Ejecuta acciones temporales sin guardarlas como regla."""
        self.log(f"Test actions: {len(actions)} acciones para {user}")
        self._execute_actions(actions, user, gift_name, diamond_value)

    def _is_cooldown(self, key):
        now = time.time()
        with self._cooldown_lock:
            if key in self._cooldowns:
                if now - self._cooldowns[key] < self.config.TTS_COOLDOWN:
                    return True
            self._cooldowns[key] = now
        return False

    def _trigger_tts(self, text):
        if not self.tts_enabled or not self.tts_client:
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
        self._save_user_settings()
        return self.tts_enabled

    def toggle_ai(self):
        self.ai_enabled = not self.ai_enabled
        self.log(f"AI toggled: {self.ai_enabled}")
        self._save_user_settings()
        return self.ai_enabled

    def set_tts_engine(self, engine):
        if self.tts_client and self.tts_client.set_engine(engine):
            self.log(f"TTS engine cambiado a: {engine}")
            self._save_user_settings()
            return True
        return False

    def set_tts_voice(self, voice):
        if self.tts_client:
            self.tts_client.set_voice(voice)
            self.log(f"TTS voice cambiada a: {voice}")
            self._save_user_settings()
            return True
        return False

    def set_tts_voice_blend(self, blend):
        if self.tts_client:
            self.tts_client.set_voice_blend(blend)
            self.log(f"TTS voice blend cambiado a: {blend}")
            self._save_user_settings()
            return True
        return False

    def set_tts_speed(self, speed):
        if self.tts_client:
            self.tts_client.set_speed(speed)
            self.log(f"TTS speed cambiado a: {speed}")
            self._save_user_settings()
            return True
        return False

    def set_tts_lang(self, lang):
        if self.tts_client:
            self.tts_client.set_lang(lang)
            self.log(f"TTS lang cambiado a: {lang}")
            self._save_user_settings()
            return True
        return False

    def set_tts_pitch(self, pitch):
        if self.tts_client:
            self.tts_client.set_pitch(pitch)
            self.log(f"TTS pitch cambiado a: {pitch}")
            self._save_user_settings()
            return True
        return False

    def set_tts_volume(self, volume):
        if self.tts_client:
            self.tts_client.set_volume(volume)
            self.log(f"TTS volume cambiado a: {volume}")
            self._save_user_settings()
            return True
        return False

    def set_kokoro_model(self, model_key):
        if self.tts_client:
            ok = self.tts_client.set_kokoro_model(model_key)
            if ok:
                self.log(f"Kokoro modelo cambiado a: {model_key}")
            self._save_user_settings()
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
        self._save_user_settings()
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
                    data = json.load(f)
                    if isinstance(data, list):
                        self.banned_words = data
                    else:
                        logger.warning("banned_words.json no es una lista, reiniciando")
                        self.banned_words = []
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

        with self._spam_lock:
            # Banned words
            if self.banned_words:
                text_lower = text.lower()
                for word in self.banned_words:
                    if word.lower() in text_lower:
                        self.log(f"SPAM bloqueado ({user}): palabra baneada '{word}'")
                        return True

            # Periodic cleanup
            if now - self._last_spam_cleanup > 300:
                self._cleanup_spam_data(now)
                self._last_spam_cleanup = now

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

            # Limitar cantidad de usuarios trackeados
            if len(self._user_timestamps) > self._max_spam_users:
                oldest = sorted(self._user_timestamps.items(), key=lambda x: x[1][-1] if x[1] else 0)
                for key, _ in oldest[:len(oldest) - self._max_spam_users]:
                    del self._user_timestamps[key]
                    self._user_messages.pop(key, None)

        return False

    def _cleanup_spam_data(self, now):
        for key in list(self._user_timestamps.keys()):
            self._user_timestamps[key] = [t for t in self._user_timestamps[key] if now - t < max(self.spam_window, self.spam_dup_window)]
            if not self._user_timestamps[key]:
                del self._user_timestamps[key]
                self._user_messages.pop(key, None)
        for key in list(self._user_messages.keys()):
            self._user_messages[key] = [(t, m) for t, m in self._user_messages[key] if now - t < self.spam_dup_window]
            if not self._user_messages[key]:
                del self._user_messages[key]

    def set_spam_enabled(self, enabled):
        self.spam_enabled = enabled
        self.log(f"Filtro anti-spam: {'ON' if enabled else 'OFF'}")
        self._save_user_settings()
        return enabled

    def set_spam_config(self, rate_limit=None, window=None, dup_window=None):
        if rate_limit is not None:
            self.spam_rate_limit = max(1, int(rate_limit))
        if window is not None:
            self.spam_window = max(1, int(window))
        if dup_window is not None:
            self.spam_dup_window = max(5, int(dup_window))
        self.log(f"Anti-spam config: {self.spam_rate_limit} msgs/{self.spam_window}s, duplicados {self.spam_dup_window}s")
        self._save_user_settings()
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

    # --- Event Rules ---
    def _load_event_rules(self):
        try:
            if os.path.exists(self._event_rules_path):
                with open(self._event_rules_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self._event_rules = data
                    else:
                        self._event_rules = []
        except Exception:
            self._event_rules = []

    def _save_event_rules(self):
        try:
            with open(self._event_rules_path, "w", encoding="utf-8") as f:
                json.dump(self._event_rules, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error guardando event rules: {e}")

    def get_event_rules(self):
        return self._event_rules

    def add_event_rule(self, rule):
        if not rule.get("name") or not rule.get("trigger") or not rule.get("actions"):
            return None
        name = rule["name"].strip()
        del rule["name"]
        rule["name"] = name
        self._event_rules.append(rule)
        self._save_event_rules()
        self.log(f"Regla agregada: {name}")
        return rule

    def update_event_rule(self, index, rule):
        if index < 0 or index >= len(self._event_rules):
            return False
        if not rule.get("name") or not rule.get("trigger") or not rule.get("actions"):
            return False
        self._event_rules[index] = rule
        self._save_event_rules()
        self.log(f"Regla actualizada: {rule['name']}")
        return True

    def delete_event_rule_by_index(self, index):
        if 0 <= index < len(self._event_rules):
            name = self._event_rules[index].get("name", "")
            del self._event_rules[index]
            self._save_event_rules()
            self.log(f"Regla eliminada: {name}")
            return True
        return False

    # --- Presets de TTS ---
    def _load_presets(self):
        try:
            if os.path.exists(self._presets_path):
                with open(self._presets_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self._presets = data
                        logger.info(f"Presets cargados: {len(self._presets)}")
                    else:
                        logger.warning("tts_presets.json no es un diccionario, reiniciando")
                        self._presets = {}
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
        self._save_user_settings()
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
