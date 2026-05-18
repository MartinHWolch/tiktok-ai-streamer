import logging

logger = logging.getLogger(__name__)

class VTubeClient:
    def __init__(self, config):
        self.config = config
        self.expressions = ["happy", "surprised", "angry", "sad", "neutral"]

    def trigger_expression(self, expression):
        if expression not in self.expressions:
            expression = "neutral"
        logger.info(f"[VTube] Activando expresión: {expression}")

    def handle_event(self, event_type, data):
        if event_type == "vtube_expression":
            expr = data.get("expression", "happy")
            self.trigger_expression(expr)
