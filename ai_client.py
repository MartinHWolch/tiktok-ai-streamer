import random
import logging
from groq import Groq

logger = logging.getLogger(__name__)

SALUDOS = [
    "¡Hola! Bienvenido al stream.",
    "¡Qué tal! Gracias por pasarte.",
    "¡Saludos! Qué bueno verte por aquí.",
    "¡Hey! Bienvenido/a, gracias por unirte.",
    "¡Hola, hola! Aquí andamos.",
]

AGRADECIMIENTOS = [
    "¡Muchas gracias por tu mensaje!",
    "Aprecio mucho que estés aquí.",
    "Gracias por el apoyo, de verdad.",
    "¡Eres increíble, gracias!",
    "Se agradece mucho el cariño.",
]

REACCIONES = [
    "Jaja, qué buena esa.",
    "Totalmente de acuerdo contigo.",
    "Eso está interesante, ¿no?",
    "¡Qué buen punto! No lo había pensado.",
    "Justo eso mismo digo yo.",
    "Increíble, ¿verdad?",
    "Me encanta esa energía.",
]

PREGUNTAS = [
    "Buena pregunta. Déjame pensarlo.",
    "Mmm, interesante. ¿Qué opinan los demás?",
    "No estoy seguro, pero suena bien.",
    "Eso depende, jaja. ¿Tú qué crees?",
    "Qué buena pregunta. Habría que investigarlo.",
]

ANIMO = [
    "¡Vamos con toda la actitud!",
    "Esa es la energía que me gusta.",
    "¡Así se hace! Con todo.",
    "Me motivas un montón, gracias.",
    "Qué buena vibra traes.",
]

DESPEDIDAS = [
    "¡Nos vemos! Cuídate mucho.",
    "Gracias por acompañarnos, ¡hasta pronto!",
    "Un abrazo, vuelve cuando quieras.",
    "Chao, gracias por estar aquí.",
]


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

    def _detect_intent(self, text):
        t = text.lower().strip()
        if any(w in t for w in ["hola", "buenas", "hey", "saludos", "buenos días", "buenas tardes", "buenas noches"]):
            return "saludo"
        if any(w in t for w in ["gracias", "te agradezco", "thank", "thx", "genial"]):
            return "agradecimiento"
        if any(w in t for w in ["?", "pregunta", "cómo", "cuándo", "dónde", "por qué", "quién", "cuál"]):
            return "pregunta"
        if any(w in t for w in ["adiós", "chao", "bye", "hasta luego", "nos vemos", "me voy"]):
            return "despedida"
        if any(w in t for w in ["vamos", "ánimo", "fuerza", "con todo", "dale"]):
            return "animo"
        if any(w in t for w in ["jaja", "jeje", "lol", "xd", "😂", "🤣"]):
            return "reaccion"
        return None

    def _fallback_reply(self, text):
        intent = self._detect_intent(text)
        if intent == "saludo":
            return random.choice(SALUDOS)
        elif intent == "agradecimiento":
            return random.choice(AGRADECIMIENTOS)
        elif intent == "pregunta":
            return random.choice(PREGUNTAS)
        elif intent == "despedida":
            return random.choice(DESPEDIDAS)
        elif intent == "animo":
            return random.choice(ANIMO)
        else:
            pool = REACCIONES + AGRADECIMIENTOS + ANIMO
            return random.choice(pool)

    def generate_reply(self, text, user):
        logger.info(f"AI generando respuesta para {user}: '{text}'")

        if not self.use_groq or not self.client:
            return self._fallback_reply(text)

        try:
            response = self.client.chat.completions.create(
                model=self.config.GROQ_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": self.config.AI_SYSTEM_PROMPT
                    },
                    {
                        "role": "user",
                        "content": f"Usuario {user} dijo: {text}"
                    }
                ],
                max_tokens=self.config.AI_MAX_TOKENS,
                temperature=self.config.AI_TEMPERATURE,
                timeout=20.0
            )
            reply = response.choices[0].message.content.strip()
            if not reply:
                return self._fallback_reply(text)
            return reply
        except Exception as e:
            logger.error(f"Error al llamar a Groq API: {e}")
            return self._fallback_reply(text)
