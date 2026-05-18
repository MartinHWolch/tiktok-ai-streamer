import random
import logging
from groq import Groq

logger = logging.getLogger(__name__)

class AIClient:
    def __init__(self, config):
        self.config = config
        self.use_groq = bool(config.GROQ_API_KEY)
        
        if self.use_groq:
            try:
                self.client = Groq(api_key=config.GROQ_API_KEY)
                logger.info("AIClient inicializado con Groq.")
            except Exception as e:
                logger.error(f"Error al inicializar Groq: {e}. Usando respuestas de fallback.")
                self.use_groq = False
                self.client = None
        else:
            self.client = None
            logger.info("AIClient inicializado sin API key de Groq (modo simulación).")
        
        self.fallback_responses = [
            "¡Qué interesante comentario!",
            "Gracias por pasarte por aquí.",
            "Jaja, totalmente de acuerdo.",
            "Eso suena genial, cuéntame más.",
            "¡Bienvenido al stream!",
            "Aprecio mucho tu mensaje.",
            "¡Eres increíble!",
            "Lo tendré en cuenta para la próxima.",
        ]

    def generate_reply(self, text, user):
        logger.info(f"AI generando respuesta para {user}: '{text}'")
        
        if not self.use_groq or not self.client:
            reply = random.choice(self.fallback_responses)
            return reply
        
        try:
            response = self.client.chat.completions.create(
                model=self.config.GROQ_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Eres un asistente de streaming para TikTok. "
                            "Responde de forma breve, divertida y en español. "
                            "Máximo 2 oraciones."
                        )
                    },
                    {
                        "role": "user",
                        "content": f"Usuario {user} dijo: {text}"
                    }
                ],
                max_tokens=100,
                temperature=0.7
            )
            reply = response.choices[0].message.content.strip()
            if not reply:
                reply = random.choice(self.fallback_responses)
            return reply
        except Exception as e:
            logger.error(f"Error al llamar a Groq API: {e}")
            return random.choice(self.fallback_responses)
