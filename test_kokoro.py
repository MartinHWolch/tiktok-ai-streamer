import logging
import os

logging.basicConfig(level=logging.INFO)

MODEL_PATH = "models/kokoro-v1.0.fp16.onnx"
VOICES_PATH = "models/voices-v1.0.bin"

try:
    from kokoro_onnx import Kokoro

    logging.info("Kokoro instalado correctamente")

    kokoro = Kokoro(MODEL_PATH, VOICES_PATH)
    voices = kokoro.get_voices()
    logging.info(f"Voces disponibles: {len(voices)}")

    sample_voices = [v for v in voices[:10]]
    for v in sample_voices:
        logging.info(f"  - {v}")

    voices_list = kokoro.get_voices()
    logging.info(f"Voces disponibles: {len(voices_list)}")
    for v in voices_list[:5]:
        logging.info(f"  - {v}")

    test_text = "Hola, esto es una prueba de voz con Kokoro. Suena muy natural!"

    for voice in ["af_sarah", "af_bella", "am_michael"]:
        logging.info(f"\nGenerando audio con voz: {voice}")
        audio, sample_rate = kokoro.create(test_text, voice=voice, speed=1.0, lang="es")

        if audio is not None:
            filename = f"test_kokoro_{voice}.wav"
            filepath = os.path.join("audio", filename)
            import wave
            with wave.open(filepath, 'wb') as f:
                f.setnchannels(1)
                f.setsampwidth(2)
                f.setframerate(sample_rate)
                f.writeframes(audio.tobytes())
            logging.info(f"  Guardado: {filepath}")

    logging.info("\nTest completado!")

except ImportError as e:
    logging.error(f"Error importando kokoro: {e}")
except Exception as e:
    logging.error(f"Error: {e}")
    import traceback
    traceback.print_exc()