import os
import json
import time
import logging
import threading
import websocket

logger = logging.getLogger(__name__)

VTS_DEFAULT_HOST = "localhost"
VTS_DEFAULT_PORT = 8001
VTS_TIMEOUT = 5

class VTubeStudioClient:
    """Cliente WebSocket para VTube Studio API."""

    def __init__(self, config):
        self.config = config
        self._ws = None
        self._ws_thread = None
        self._lock = threading.Lock()
        self._connected = False
        self._authenticated = False
        self._auth_token = None
        self._current_model = None
        self._expressions = []
        self._hotkeys = []
        self._enabled = True
        self._running = False
        self.host = getattr(config, 'VTS_HOST', VTS_DEFAULT_HOST)
        self.port = getattr(config, 'VTS_PORT', VTS_DEFAULT_PORT)

    def connect(self):
        if self._connected:
            return True
        self._running = True
        self._ws_thread = threading.Thread(target=self._ws_loop, daemon=True)
        self._ws_thread.start()
        return True

    def disconnect(self):
        self._running = False
        self._connected = False
        self._authenticated = False
        if self._ws:
            try: self._ws.close()
            except: pass

    def _ws_loop(self):
        try:
            url = f"ws://{self.host}:{self.port}"
            logger.info(f"VTS conectando a {url}...")
            self._ws = websocket.create_connection(url, timeout=5)
            self._connected = True
            logger.info("VTS WebSocket conectado")

            # Recibir mensajes iniciales
            self._ws.settimeout(1)
            for _ in range(5):
                try:
                    raw = self._ws.recv()
                    if raw:
                        data = json.loads(raw)
                        logger.info(f"VTS <<< {data.get('messageType')}")
                except websocket.WebSocketTimeoutException:
                    break

            # Verificar estado del API
            logger.info("VTS: Verificando estado...")
            resp = self._request("APIStateRequest")
            if resp and resp.get("data", {}).get("active"):
                logger.info("VTS: API activa")
            else:
                logger.warning("VTS: API no activa. Asegurate de activar Plugin API en VTube Studio")

            # Autenticar
            self._do_auth()

            # Loop recepcion eventos async
            while self._running and self._connected:
                try:
                    self._ws.settimeout(1)
                    raw = self._ws.recv()
                    if raw:
                        data = json.loads(raw)
                        mt = data.get("messageType", "")
                        if mt not in ("APIStateResponse",):
                            logger.debug(f"VTS event: {mt}")
                except websocket.WebSocketTimeoutException:
                    continue
                except Exception as e:
                    if self._running:
                        logger.error(f"VTS recv: {e}")
                    break
        except Exception as e:
            logger.error(f"VTS connection error: {e}")
        finally:
            self._connected = False
            self._authenticated = False
            logger.info("VTS desconectado")

    def _request(self, message_type, data=None):
        """Envía request y recibe respuesta sincrona."""
        if not self._ws:
            return None
        try:
            rid = f"req-{int(time.time()*1000)}"
            msg = {
                "apiName": "VTubeStudioPublicAPI",
                "apiVersion": "1.0",
                "requestID": rid,
                "messageType": message_type,
                "data": data or {}
            }
            self._ws.send(json.dumps(msg))
            self._ws.settimeout(VTS_TIMEOUT)
            raw = self._ws.recv()
            return json.loads(raw) if raw else None
        except websocket.WebSocketTimeoutException:
            return None
        except Exception as e:
            logger.error(f"VTS request error ({message_type}): {e}")
            return None

    def _do_auth(self):
        token_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "vts_token.json")

        # 1. Intentar con token guardado
        saved_token = None
        plugin_name = "TikTok AI Streamer"
        try:
            if os.path.exists(token_path):
                with open(token_path, "r") as f:
                    td = json.load(f)
                    saved_token = td.get("token")
                    if td.get("plugin"): plugin_name = td["plugin"]
        except: pass

        if saved_token:
            resp = self._request("AuthenticationRequest", {
                "pluginName": plugin_name,
                "pluginDeveloper": "AnomalyCo",
                "authenticationToken": saved_token
            })
            if resp and resp.get("messageType") == "AuthenticationResponse":
                data = resp.get("data", {})
                if data.get("authenticated"):
                    self._authenticated = True
                    self._auth_token = saved_token
                    logger.info("VTS: Autenticado OK (token guardado)")
                    self._refresh_model_data()
                    return

        # 2. Pedir token nuevo via AuthenticationTokenRequest
        plugin_name = "TikTok AI Streamer"
        logger.info("VTS: Solicitando token nuevo...")
        for attempt in range(1, 30):
            resp = self._request("AuthenticationTokenRequest", {
                "pluginName": plugin_name,
                "pluginDeveloper": "AnomalyCo"
            })
            if resp:
                mt = resp.get("messageType", "")
                data = resp.get("data", {})
                eid = data.get("errorID", 0)

                if mt == "AuthenticationTokenResponse":
                    token = data.get("authenticationToken")
                    if token:
                        self._auth_token = token
                        logger.info("VTS: Token recibido! Autenticando...")
                        resp2 = self._request("AuthenticationRequest", {
                            "pluginName": plugin_name,
                            "pluginDeveloper": "AnomalyCo",
                            "authenticationToken": token
                        })
                        if resp2 and resp2.get("messageType") == "AuthenticationResponse":
                            if resp2.get("data", {}).get("authenticated"):
                                self._authenticated = True
                                logger.info("VTS: Autenticado OK!")
                                break
                    else:
                        logger.info("VTS: Token vacio en respuesta")
                elif eid == 51:
                    if attempt == 1:
                        logger.info("VTS: Hay un popup de auth anterior abierto. Cerrarlo en VTube Studio y reintentar...")
                elif mt == "APIError":
                    err = data.get("message", str(eid))
                    if attempt == 1:
                        logger.info(f"VTS: {err} - Hace click en PERMITIR en VTube Studio")
            else:
                if attempt == 1:
                    logger.warning("VTS: Sin respuesta. API activa en VTube Studio?")
            if attempt % 10 == 0:
                logger.info(f"VTS: Reintentando ({attempt}/30)...")
            time.sleep(2)
        else:
            logger.warning("VTS: timeout de autenticacion (1 min)")

        # 3. Guardar token
        if self._auth_token:
            try:
                os.makedirs(os.path.dirname(token_path), exist_ok=True)
                with open(token_path, "w") as f:
                    json.dump({"token": self._auth_token, "plugin": plugin_name}, f)
            except: pass

        if self._authenticated:
            self._refresh_model_data()

    def _refresh_model_data(self):
        if not self._authenticated: return
        resp = self._request("CurrentModelRequest")
        if resp:
            data = resp.get("data", {})
            self._current_model = data.get("modelName", "")

        resp = self._request("ExpressionStateRequest")
        if resp:
            data = resp.get("data", {})
            exprs = data.get("expressions", [])
            self._expressions = [e.get("name", "") for e in exprs]

        resp = self._request("HotkeysInCurrentModelRequest")
        if resp:
            data = resp.get("data", {})
            hks = data.get("availableHotkeys", [])
            self._hotkeys = [h.get("name", "") for h in hks if h.get("name")]

        logger.info(f"VTS Modelo: {self._current_model}, Expresiones: {len(self._expressions)}, Hotkeys: {len(self._hotkeys)}")

    def trigger_expression(self, expression):
        if not self._authenticated or not self._enabled:
            logger.info(f"[VTube] Expresion '{expression}' (modo offline)")
            return False
        resp = self._request("ExpressionActivationRequest", {
            "expressionFile": expression + ".exp3.json",
            "active": True
        })
        if resp and resp.get("messageType") == "ExpressionActivationResponse":
            logger.info(f"[VTube] Expresion activada: {expression}")
            return True
        # Intentar sin extension, con extension, etc
        for fmt in [expression, expression + ".exp3.json"]:
            resp = self._request("ExpressionActivationRequest", {
                "expressionFile": fmt, "active": True
            })
            if resp and resp.get("messageType") == "ExpressionActivationResponse":
                logger.info(f"[VTube] Expresion activada: {fmt}")
                return True
        logger.warning(f"[VTube] Expresion no encontrada: {expression}")
        return False

    def trigger_hotkey(self, hotkey_id):
        if not self._authenticated or not self._enabled:
            logger.info(f"[VTube] Hotkey '{hotkey_id}' (modo offline)")
            return False
        resp = self._request("HotkeyTriggerRequest", {
            "hotkeyID": str(hotkey_id)
        })
        if resp and resp.get("messageType") == "HotkeyTriggerResponse":
            logger.info(f"[VTube] Hotkey activado: {hotkey_id}")
            return True
        logger.warning(f"[VTube] Hotkey fallo: {hotkey_id}")
        return False

    def get_status(self):
        return {
            "connected": self._connected,
            "authenticated": self._authenticated,
            "model": self._current_model or "",
            "expressions": self._expressions,
            "hotkeys": self._hotkeys,
            "enabled": self._enabled
        }

    def set_enabled(self, enabled):
        self._enabled = enabled

    def handle_event(self, event_type, data):
        if event_type == "vtube_expression":
            self.trigger_expression(data.get("expression", "happy"))
        elif event_type == "vtube_hotkey":
            hk = data.get("hotkey", "")
            if hk: self.trigger_hotkey(hk)
