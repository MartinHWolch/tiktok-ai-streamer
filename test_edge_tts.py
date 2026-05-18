import asyncio
import logging
import os
import edge_tts

logging.basicConfig(level=logging.INFO)

async def test_edge_tts():
    text = "Hola! Esto es una prueba de voz con Microsoft Edge TTS."
    voice = "es-MX-AngelaNeural"
    communicate = edge_tts.Communicate(text, voice)
    filepath = os.path.join("audio", "test_edge_short.mp3")
    await communicate.save(filepath)
    logging.info(f"Guardado: {filepath}")
    logging.info("Test completado!")

if __name__ == "__main__":
    asyncio.run(test_edge_tts())