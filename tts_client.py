import os
import time
import logging
import uuid
import threading
import wave
import re

logger = logging.getLogger(__name__)

class TTSClient:
    def __init__(self, config):
        self.config = config
        self.enabled = config.TTS_ENABLED
        os.makedirs(self.config.AUDIO_DIR, exist_ok=True)
        self._last_speak = 0
        self._cooldown_lock = threading.Lock()
        self._cleanup_lock = threading.Lock()
        self._state_lock = threading.Lock()

        self.engine = config.TTS_ENGINE
        self.voice = config.TTS_VOICE
        self.voice_blend = config.TTS_VOICE_BLEND
        self.speed = config.TTS_SPEED
        self.lang = config.TTS_LANG
        self.pitch = config.TTS_PITCH
        self.volume = config.TTS_VOLUME
        self.kokoro_model = config.KOKORO_MODEL
        self.edge_voice = getattr(config, 'TTS_EDGE_VOICE', 'es-MX-DaliaNeural')

        self._kokoro = None
        self._kokoro_voices = []
        self._kokoro_g2p = None
        self._piper = None

        self._init_kokoro()
        self._init_piper()
    
    def _init_kokoro(self):
        try:
            from kokoro_onnx import Kokoro
            model_path = self.kokoro_model
            voices_path = self.config.KOKORO_VOICES
            
            if not os.path.exists(model_path):
                logger.warning(f"Modelo Kokoro no encontrado: {model_path}")
                return
            if not os.path.exists(voices_path):
                logger.warning(f"Voices Kokoro no encontrado: {voices_path}")
                return
            
            self._kokoro = Kokoro(model_path, voices_path)
            self._kokoro_voices = list(self._kokoro.get_voices())
            logger.info(f"Kokoro TTS inicializado. Voces disponibles: {len(self._kokoro_voices)}")
            
            # Inicializar G2P para español
            try:
                from misaki.espeak import EspeakG2P
                self._kokoro_g2p = EspeakG2P(language=self.lang)
                logger.info(f"G2P inicializado para idioma: {self.lang}")
            except Exception as e:
                logger.warning(f"No se pudo inicializar misaki G2P: {e}. Se usará texto directo.")
                self._kokoro_g2p = None
        except Exception as e:
            logger.warning(f"No se pudo inicializar Kokoro: {e}")
            self._kokoro = None
    
    def _init_piper(self):
        try:
            from piper import PiperVoice
            model_path = self.config.PIPER_MODEL_PATH
            if os.path.exists(model_path):
                self._piper = PiperVoice.load(model_path)
                logger.info("Piper TTS inicializado correctamente (español)")
            else:
                logger.warning(f"Modelo Piper no encontrado: {model_path}")
        except Exception as e:
            logger.warning(f"No se pudo inicializar Piper: {e}")
            self._piper = None
    
    def _parse_voice_blend(self, blend_str):
        """Parsea 'jf_tebukuro*0.8 + ef_dora*0.2' a un voice blend numpy array."""
        if not blend_str or not self._kokoro:
            return None
        try:
            import numpy as np
            parts = re.findall(r'([a-zA-Z0-9_]+)\s*\*\s*([0-9.]+)', blend_str)
            if not parts:
                return None
            
            total_weight = 0.0
            blend = None
            
            for voice_name, weight_str in parts:
                weight = float(weight_str)
                voice_style = self._kokoro.get_voice_style(voice_name)
                if blend is None:
                    blend = voice_style * weight
                else:
                    blend = np.add(blend, voice_style * weight)
                total_weight += weight
            
            if total_weight > 0 and total_weight != 1.0:
                blend = blend / total_weight
            
            return blend
        except Exception as e:
            logger.error(f"Error parseando voice blend '{blend_str}': {e}")
            return None
    
    def _get_kokoro_voice(self, voice=None, voice_blend=None):
        # Si se pasan parametros (snapshot thread-safe), usarlos; sino leer de self
        if voice is None:
            with self._state_lock:
                voice = self.voice
        if voice_blend is None:
            with self._state_lock:
                voice_blend = self.voice_blend
        if voice_blend:
            result = self._parse_voice_blend(voice_blend)
            if result is not None:
                return result
        return voice
    
    def speak(self, text):
        if not self.enabled:
            logger.info("TTS está deshabilitado.")
            return None
        
        with self._cooldown_lock:
            self._last_speak = time.time()
        
        # Capturar TODO el estado bajo lock para evitar race conditions
        with self._state_lock:
            engine = self.engine
            kokoro = self._kokoro
            piper = self._piper
            voice = self.voice
            voice_blend = self.voice_blend
            speed = self.speed
            pitch = self.pitch
            volume = self.volume
            lang = self.lang
            edge_voice = self.edge_voice
            kokoro_model = self.kokoro_model
        
        if engine == "kokoro" and kokoro:
            return self._speak_kokoro(text, voice, voice_blend, speed, pitch, volume, lang, kokoro_model)
        elif engine == "piper" and piper:
            return self._speak_piper(text, lang)
        elif engine == "edge":
            return self._speak_edge(text, edge_voice, speed, pitch, volume, lang)
        else:
            return self._speak_gtts(text, lang)
    
    def _speak_kokoro(self, text, voice, voice_blend, speed, pitch, volume, lang, kokoro_model):
        try:
            import numpy as np
            import soundfile as sf
            
            voice = self._get_kokoro_voice(voice, voice_blend)
            
            # Phonemize si tenemos G2P
            if self._kokoro_g2p:
                try:
                    g2p_result = self._kokoro_g2p(text)
                    if isinstance(g2p_result, tuple):
                        phonemes = g2p_result[0]
                    else:
                        phonemes = g2p_result
                    samples, sample_rate = self._kokoro.create(
                        phonemes, voice=voice, speed=speed, lang=lang, is_phonemes=True
                    )
                except Exception as e:
                    logger.warning(f"Falló phonemize, intentando texto directo: {e}")
                    samples, sample_rate = self._kokoro.create(
                        text, voice=voice, speed=speed, lang=lang
                    )
            else:
                samples, sample_rate = self._kokoro.create(
                    text, voice=voice, speed=speed, lang=lang
                )
            
            filename = f"tts_{int(time.time())}_{uuid.uuid4().hex}.wav"
            filepath = os.path.join(self.config.AUDIO_DIR, filename)
            samples = self._apply_effects(samples, sample_rate, pitch, volume)
            sf.write(filepath, samples, sample_rate)
            logger.info(f"Kokoro TTS generado: {filepath}")
            self._cleanup_old_audio()
            return filename
        except Exception as e:
            logger.error(f"Error Kokoro TTS: {e}")
            return self._speak_gtts(text, lang)
    
    def _speak_piper(self, text, lang):
        try:
            filename = f"tts_{int(time.time())}_{uuid.uuid4().hex}.wav"
            filepath = os.path.join(self.config.AUDIO_DIR, filename)
            with wave.open(filepath, 'wb') as f:
                f.setnchannels(1)
                f.setsampwidth(2)
                f.setframerate(22050)
                self._piper.synthesize_wav(text, f)
            logger.info(f"Piper TTS generado: {filepath}")
            self._cleanup_old_audio()
            return filename
        except Exception as e:
            logger.error(f"Error Piper TTS: {e}")
            return self._speak_gtts(text, lang)
    
    def _speak_gtts(self, text, lang):
        try:
            from gtts import gTTS
            filename = f"tts_{int(time.time())}_{uuid.uuid4().hex}.mp3"
            filepath = os.path.join(self.config.AUDIO_DIR, filename)
            tts = gTTS(text=text, lang=lang)
            tts.save(filepath)
            logger.info(f"gTTS generado: {filepath}")
            self._cleanup_old_audio()
            return filename
        except Exception as e:
            logger.error(f"Error gTTS: {e}")
            return None
    
    def _speak_edge(self, text, edge_voice, speed, pitch, volume, lang):
        try:
            import edge_tts, asyncio
            filename = f"tts_{int(time.time())}_{uuid.uuid4().hex}.mp3"
            filepath = os.path.join(self.config.AUDIO_DIR, filename)

            # Convertir sliders a formato SSML de Edge (solo enviar si no son defaults)
            rate = f"{(speed - 1.0) * 100:+.0f}%" if speed != 1.0 else None
            pitch_val = f"{int(pitch * 5):+d}Hz" if pitch != 0 else None
            volume_pct = f"{(volume - 1.0) * 100:+.0f}%" if volume != 1.0 else None

            async def _gen():
                kwargs = {"voice": edge_voice}
                if rate: kwargs["rate"] = rate
                if pitch_val: kwargs["pitch"] = pitch_val
                if volume_pct: kwargs["volume"] = volume_pct
                comm = edge_tts.Communicate(text, **kwargs)
                await comm.save(filepath)

            # Usar nuevo event loop para evitar crash si ya hay uno corriendo en el thread
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(_gen())
            finally:
                loop.close()
            logger.info(f"Edge TTS generado: {filepath} (rate={rate}, pitch={pitch_val}, vol={volume_pct})")
            self._cleanup_old_audio()
            return filename
        except Exception as e:
            logger.error(f"Error Edge TTS: {e}")
            return self._speak_gtts(text, lang)

    def _apply_effects(self, samples, sample_rate, pitch, volume):
        if pitch == 0 and volume == 1.0:
            return samples
        try:
            import numpy as np
            arr = np.array(samples, dtype=np.float32)
            # Pitch shift real sin cambiar velocidad (librosa)
            if pitch != 0:
                import librosa
                arr = librosa.effects.pitch_shift(
                    y=arr, sr=sample_rate, n_steps=float(pitch)
                )
            # Volumen
            if volume != 1.0:
                arr = arr * volume
                arr = np.clip(arr, -1.0, 1.0)
            return arr
        except Exception as e:
            logger.warning(f"Error aplicando efectos: {e}")
            return samples

    def _cleanup_old_audio(self):
        with self._cleanup_lock:
            now = time.time()
            max_age = 7200  # 2 horas (antes 1h, para evitar borrar audios en cola larga)
            max_files = 100
            deleted = 0
            try:
                files = []
                for fname in os.listdir(self.config.AUDIO_DIR):
                    if not (fname.endswith(".mp3") or fname.endswith(".wav")):
                        continue
                    fpath = os.path.join(self.config.AUDIO_DIR, fname)
                    try:
                        if os.path.isfile(fpath):
                            mtime = os.path.getmtime(fpath)
                            if (now - mtime) > max_age:
                                os.remove(fpath)
                                deleted += 1
                            else:
                                files.append((mtime, fpath))
                    except Exception:
                        pass
                # Limite de cantidad: mantener solo los 100 más recientes,
                # pero nunca borrar archivos generados hace menos de 5 min (pueden estar en cola de reproduccion)
                if len(files) > max_files:
                    files.sort(key=lambda x: x[0])
                    for mtime, fpath in files[:len(files) - max_files]:
                        if (now - mtime) < 300:  # < 5 min: protegido
                            continue
                        try:
                            os.remove(fpath)
                            deleted += 1
                        except Exception:
                            pass
                if deleted > 0:
                    logger.info(f"Limpieza TTS: {deleted} archivos eliminados.")
            except Exception as e:
                logger.warning(f"Error limpiando audios viejos: {e}")
    
    def set_enabled(self, enabled):
        self.enabled = enabled
        logger.info(f"TTS enabled: {enabled}")

    def reset_cooldown(self):
        with self._cooldown_lock:
            self._last_speak = 0

    def set_engine(self, engine):
        if engine in ("kokoro", "piper", "gtts", "edge"):
            with self._state_lock:
                self.engine = engine
            logger.info(f"TTS engine cambiado a: {engine}")
            return True
        return False
    
    def set_voice(self, voice):
        with self._state_lock:
            self.voice = voice
            self.voice_blend = ""
        logger.info(f"TTS voice cambiada a: {voice}")
    
    def set_voice_blend(self, blend_str):
        with self._state_lock:
            self.voice_blend = blend_str
        logger.info(f"TTS voice blend cambiado a: {blend_str}")

    def set_edge_voice(self, voice):
        with self._state_lock:
            self.edge_voice = voice
        logger.info(f"TTS edge voice cambiado a: {voice}")
    
    def set_speed(self, speed):
        try:
            with self._state_lock:
                self.speed = max(0.5, min(2.0, float(speed)))
            logger.info(f"TTS speed cambiado a: {self.speed}")
        except (ValueError, TypeError):
            logger.warning(f"TTS speed invalido: {speed}")

    def set_pitch(self, pitch):
        try:
            with self._state_lock:
                self.pitch = max(-12.0, min(12.0, float(pitch)))
            logger.info(f"TTS pitch cambiado a: {self.pitch} semitonos")
        except (ValueError, TypeError):
            logger.warning(f"TTS pitch invalido: {pitch}")

    def set_volume(self, volume):
        try:
            with self._state_lock:
                self.volume = max(0.1, min(3.0, float(volume)))
            logger.info(f"TTS volume cambiado a: {self.volume}")
        except (ValueError, TypeError):
            logger.warning(f"TTS volume invalido: {volume}")

    def set_kokoro_model(self, model_key):
        if model_key == "fp16":
            path = self.config.KOKORO_MODEL
        elif model_key == "fp32":
            path = self.config.KOKORO_MODEL_FP32
        else:
            return False
        if not os.path.exists(path):
            logger.warning(f"Modelo no encontrado: {path}")
            return False
        with self._state_lock:
            # Guardar estado anterior por si falla
            prev_kokoro = self._kokoro
            prev_voices = self._kokoro_voices
            prev_g2p = self._kokoro_g2p
            self._kokoro = None
            self._kokoro_voices = []
            self._kokoro_g2p = None
            self.kokoro_model = path
            self._init_kokoro()
            if self._kokoro is None:
                # Restaurar anterior
                self._kokoro = prev_kokoro
                self._kokoro_voices = prev_voices
                self._kokoro_g2p = prev_g2p
                logger.error(f"Fallo al cargar modelo {model_key}, restaurando anterior")
                return False
        logger.info(f"Kokoro modelo cambiado a: {model_key}")
        return True
    
    def set_lang(self, lang):
        self.lang = lang
        logger.info(f"TTS lang cambiado a: {lang}")
        # Re-inicializar G2P si cambia el idioma
        if self._kokoro and self._kokoro_g2p:
            try:
                from misaki.espeak import EspeakG2P
                self._kokoro_g2p = EspeakG2P(language=lang)
                logger.info(f"G2P re-inicializado para idioma: {lang}")
            except Exception as e:
                logger.warning(f"No se pudo re-inicializar G2P: {e}")
    
    def get_status(self):
        with self._state_lock:
            model_type = "fp16" if "fp16" in self.kokoro_model else ("fp32" if "v1.0.onnx" in self.kokoro_model else "custom")
            return {
                "enabled": self.enabled,
                "engine": self.engine,
                "voice": self.voice,
                "voice_blend": self.voice_blend,
                "speed": self.speed,
                "lang": self.lang,
                "pitch": self.pitch,
                "volume": self.volume,
                "kokoro_model": model_type,
                "kokoro_available": self._kokoro is not None,
                "piper_available": self._piper is not None,
                "kokoro_voices": self._kokoro_voices if self._kokoro else [],
                "edge_voice": self.edge_voice,
            }
    

