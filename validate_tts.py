from config import Config
from tts_client import TTSClient

def main():
    print("Validando TTS...")
    config = Config()
    tts = TTSClient(config)
    result = tts.speak("Hola, este es un mensaje de prueba del sistema TTS.")
    if result:
        print(f"OK: Archivo generado -> {result}")
    else:
        print("ERROR: No se pudo generar audio.")

if __name__ == "__main__":
    main()
