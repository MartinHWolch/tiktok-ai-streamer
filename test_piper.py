import logging
import os
import wave
from piper import PiperVoice

logging.basicConfig(level=logging.INFO)

model_path = r"C:\Users\marti\.cache\huggingface\hub\models--Trelis--piper-es-es-davefx-medium\snapshots\6bd38786b799a7ee433951e30ed9e46384cdc53c\model.onnx"

text = "Hola! Esto es una prueba de voz con Piper en español. Suena muy natural!"

logging.info(f"Cargando modelo: {model_path}")
voice = PiperVoice.load(model_path)

output_path = os.path.join("audio", "test_piper_spanish.wav")
logging.info(f"Generando audio...")

with wave.open(output_path, "wb") as wav_file:
    voice.synthesize_wav(text, wav_file)

logging.info(f"Guardado: {output_path}")
logging.info("Test completado!")