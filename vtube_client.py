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
        self._params = []
        self._enabled = True
        self._running = False
        self._last_mouth_log = 0  # log silencioso cada 2s
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
        while self._running:
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
                    break

                # Autenticar
                self._do_auth()

                if not self._authenticated:
                    break

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
            except websocket.WebSocketException as e:
                if self._running:
                    logger.warning(f"VTS connection: {e}")
            except Exception as e:
                if self._running:
                    logger.error(f"VTS connection error: {e}")
            finally:
                self._connected = False
                self._authenticated = False
                self._params = []
                if self._ws:
                    try: self._ws.close()
                    except: pass
                self._ws = None
                if self._running:
                    logger.info("VTS desconectado, reconectando en 3s...")
                    time.sleep(3)

    def _request(self, message_type, data=None):
        """Envia request y recibe respuesta sincrona."""
        if not self._ws:
            return None
        try:
            if not self._ws.connected:
                self._on_disconnect()
                return None
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
            msg_str = str(e)
            if "closed" in msg_str.lower():
                self._on_disconnect()
            else:
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

        resp = self._request("InputParameterListRequest")
        if resp:
            data = resp.get("data", {})
            custom = [p.get("name","") for p in data.get("customParameters", [])]
            default = [p.get("name","") for p in data.get("defaultParameters", [])]
            self._params = custom + default

        logger.info(f"VTS Modelo: {self._current_model}, Expresiones: {len(self._expressions)}, Hotkeys: {len(self._hotkeys)}, Params: {len(self._params)}")

    # Presets de expresion via parametros reales del modelo (filtrados en _inject_params)
    _EXPRESSION_PRESETS = {
        "happy":      {"MouthSmile": 1.0, "EyeOpenLeft": 0.7, "CheekPuff": 0.5},
        "very_happy": {"MouthSmile": 1.0, "EyeOpenLeft": 0.5, "CheekPuff": 1.0, "MouthOpen": 0.5},
        "angry":      {"FaceAngry": 1.0, "MouthSmile": -1.0, "BrowLeftY": -1.0, "BrowRightY": -1.0, "EyeOpenLeft": 0.5},
        "furious":    {"FaceAngry": 1.0, "MouthSmile": -1.0, "BrowLeftY": -1.0, "BrowRightY": -1.0, "EyeOpenLeft": 0.3, "MouthOpen": 0.6},
        "surprised":  {"MouthOpen": 1.0, "EyeOpenLeft": 1.0, "BrowLeftY": 1.0, "BrowRightY": 1.0},
        "shocked":    {"MouthOpen": 1.0, "EyeOpenLeft": 1.0, "BrowLeftY": 1.0, "BrowRightY": 1.0, "FaceAngry": 0.0},
        "sad":        {"MouthSmile": -1.0, "BrowLeftY": 0.5, "BrowRightY": 0.5, "EyeOpenLeft": 0.4, "CheekPuff": 0.0},
        "crying":     {"MouthSmile": -1.0, "BrowLeftY": 0.7, "BrowRightY": 0.7, "EyeOpenLeft": 0.2, "MouthOpen": 0.7, "CheekPuff": 0.3},
        "wink":       {"EyeOpenLeft": 0.0, "MouthSmile": 0.7, "CheekPuff": 0.3},
        "blush":      {"CheekPuff": 1.0, "MouthSmile": 0.5, "EyeOpenLeft": 0.6},
        "neutral":    {"MouthSmile": 0.0, "MouthOpen": 0.0, "EyeOpenLeft": 0.8, "CheekPuff": 0.0,
                        "FaceAngry": 0.0, "BrowLeftY": 0.0, "BrowRightY": 0.0},
        "laughing":   {"MouthSmile": 1.0, "MouthOpen": 1.0, "EyeOpenLeft": 0.3, "CheekPuff": 0.8},
        "scared":     {"EyeOpenLeft": 1.0, "MouthOpen": 0.4, "FaceAngry": 0.7, "BrowLeftY": -0.5, "BrowRightY": -0.5},
        "sleepy":     {"EyeOpenLeft": 0.15, "MouthSmile": -0.2, "MouthOpen": 0.1, "BrowLeftY": -0.3, "BrowRightY": -0.3},
        "smug":       {"MouthSmile": 0.8, "BrowLeftY": 0.0, "BrowRightY": 0.8, "EyeOpenLeft": 0.5, "CheekPuff": 0.2},
        "curious":    {"BrowLeftY": 0.8, "BrowRightY": 0.0, "EyeOpenLeft": 0.9, "MouthOpen": 0.15},
        "tongue_out": {"TongueOut": 1.0, "MouthSmile": 0.4, "MouthOpen": 0.6},
        "focused":    {"EyeOpenLeft": 0.9, "BrowLeftY": -0.6, "BrowRightY": -0.6, "MouthSmile": 0.0, "FaceAngry": 0.4},
    }

    def _get_params(self):
        """Lista parametros disponibles del modelo."""
        try:
            resp = self._request("InputParameterListRequest")
            if resp:
                data = resp.get("data", {})
                custom = [p.get("name","") for p in data.get("customParameters", [])]
                default = [p.get("name","") for p in data.get("defaultParameters", [])]
                return custom + default
        except: pass
        return []

    def _inject_params(self, params_dict, silent=False):
        """Inyecta valores de parametros al modelo. silent=True no loguea."""
        if not self._params:
            return False
        avail = set(self._params)
        filtered = []
        skipped = []
        for name, value in params_dict.items():
            if name in avail:
                filtered.append({"id": name, "value": float(value), "weight": 1.0})
            else:
                skipped.append(name)
        if not filtered:
            if not silent:
                logger.warning(f"[VTube] Ningun parametro valido para el modelo '{self._current_model}'. "
                              f"Ignorados: {skipped}. Parametros del modelo: {self._params[:15]}")
            return False
        if not silent:
            if skipped:
                logger.info(f"[VTube] Inyectando {list([f['id'] for f in filtered])}, ignorados: {skipped}")
            else:
                logger.info(f"[VTube] Inyectando params: {list(params_dict.keys())}")
        resp = self._request("InjectParameterDataRequest", {
            "faceFound": True,
            "mode": "set",
            "parameterValues": filtered
        })
        if resp:
            mt = resp.get("messageType", "?")
            if mt == "InjectParameterDataResponse":
                if silent:
                    now = time.time()
                    if now - self._last_mouth_log > 2:
                        logger.debug("[VTube] Boca sync OK")
                        self._last_mouth_log = now
                return True
            if not silent:
                err_data = resp.get("data", {})
                logger.warning(f"[VTube] Injection: {mt} - {err_data.get('message', err_data.get('errorID', '?'))}")
            return False
        if not silent:
            logger.warning("[VTube] Injection: sin respuesta del servidor")
        return False

    def trigger_expression(self, expression):
        if not self._enabled:
            logger.info(f"[VTube] Expresion '{expression}' (deshabilitado)")
            return False
        if not self._authenticated:
            logger.info(f"[VTube] Expresion '{expression}' (modo offline)")
            # Intentar con presets igual (funciona en modo offline)
            return False

        # 1. Buscar en expresiones del modelo
        expr_lower = expression.lower().replace(".exp3.json", "").strip()
        for e in self._expressions:
            if e.lower() == expr_lower or e.lower().replace(".exp3.json", "") == expr_lower:
                filename = e if e.endswith(".exp3.json") else e + ".exp3.json"
                resp = self._request("ExpressionActivationRequest", {
                    "expressionFile": filename, "active": True
                })
                if resp and resp.get("messageType") == "ExpressionActivationResponse":
                    logger.info(f"[VTube] Expresion activada: {filename}")
                    return True

        # 2. Intentar como nombre directo
        for fmt in [expression, expression + ".exp3.json"]:
            resp = self._request("ExpressionActivationRequest", {
                "expressionFile": fmt, "active": True
            })
            if resp and resp.get("messageType") == "ExpressionActivationResponse":
                logger.info(f"[VTube] Expresion activada: {fmt}")
                return True

        # 3. Usar presets de parametros (inyeccion directa)
        preset = self._EXPRESSION_PRESETS.get(expr_lower)
        if preset:
            ok = self._inject_params(preset)
            if ok:
                logger.info(f"[VTube] Preset inyectado: {expr_lower} -> {list(preset.keys())}")
                return True

        logger.warning(f"[VTube] No encontrada: '{expression}'. "
                       f"Expresiones modelo: {self._expressions or 'ninguna'}. "
                       f"Presets: {list(self._EXPRESSION_PRESETS.keys())}. "
                       f"Params del modelo: {self._params[:10] if self._params else 'no consultados'}")
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
            "params": self._params,
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
