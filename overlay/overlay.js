const alertsContainer = document.getElementById("alerts");
const messagesContainer = document.getElementById("messages");
const ttsText = document.getElementById("tts-text");

// Reproductor de audio para TTS (con cola)
var ttsAudio = new Audio();
ttsAudio.volume = 1.0;
var ttsQueue = [];
var ttsPlaying = false;
var audioUnlocked = false; // true despues del primer click del usuario
var MAX_TTS_QUEUE = 5; // max items en cola, descartar viejos si se llena

// Lip sync: AudioContext + Analyser para mover boca del avatar
var lipSyncCtx = null;
var lipSyncAnalyser = null;
var lipSyncTimer = null;
var lipSyncSource = null;
var lastMouthVal = 0;
var lastSentMouth = -1; // para throttling
var mouthSamples = [];  // acumular muestras para batching

// Reproductor de SFX
function playSfx(file) {
    var sfx = new Audio("/sfx/" + file);
    sfx.volume = 0.7;
    sfx.play().catch(function(e) {
        console.warn("[Overlay] SFX error:", file, e.message);
    });
}

var _ttsRetries = {}; // track retries per URL to avoid infinite loops
var _lastPlayedUrl = null; // anti-duplicado: ultima URL reproducida
var _lastEndedSrc = null; // anti-duplicado onended

function processTtsQueue() {
    if (ttsQueue.length === 0) return;
    if (!audioUnlocked) {
        updateStatus("COLA", ttsQueue.length + " (esperando unlock)");
        return;
    }
    if (ttsPlaying) return;

    ttsPlaying = true;
    var next = ttsQueue[0]; // peek
    var url = next.url;
    var itemId = next.item_id || null;
    currentItemId = itemId;

    var retries = _ttsRetries[url] || 0;
    if (retries >= 2) {
        // Item fallo 2 veces: descartar y pasar al siguiente
        console.warn("[AUDIT] Descartando item fallido tras " + retries + " intentos:", url);
        ttsQueue.shift();
        _ttsRetries[url] = 0;
        updateStatus("COLA", ttsQueue.length + " (skip)");
        ttsPlaying = false;
        currentItemId = null;
        if (ttsQueue.length > 0) setTimeout(processTtsQueue, 100);
        return;
    }
    _ttsRetries[url] = retries + 1;

    updateStatus("COLA", ttsQueue.length + " (playing)");
    console.log("[AUDIT] TTS play intento #" + _ttsRetries[url] + ":", url, "item_id:", itemId, "(cola:", ttsQueue.length, ")");

    // Anti-duplicado: si esta URL ya se reprodujo, descartar
    if (url === _lastPlayedUrl) {
        console.warn("[AUDIT] URL duplicada en reproduccion, descartando:", url);
        ttsQueue.shift();
        _ttsRetries[url] = 0;
        updateStatus("COLA", ttsQueue.length + " (dedup)");
        ttsPlaying = false;
        currentItemId = null;
        if (ttsQueue.length > 0) setTimeout(processTtsQueue, 100);
        return;
    }

    try {
        ttsAudio.src = url;
        ttsAudio.currentTime = 0;
        ttsAudio.load();
        initLipSync();
    } catch(setupErr) {
        console.error("[AUDIT] Error setup audio:", setupErr.message);
        updateStatus("COLA", "ERR:" + (setupErr.message || "").slice(0, 20));
        ttsQueue.shift();
        _ttsRetries[url] = 0;
        ttsPlaying = false;
        currentItemId = null;
        if (ttsQueue.length > 0) setTimeout(processTtsQueue, 100);
        return;
    }

    var playPromise = ttsAudio.play();
    if (playPromise !== undefined) {
        playPromise.then(function() {
            console.log("[AUDIT] TTS play() resolved — audio sonando");
        }).catch(function(err) {
            console.warn("[AUDIT] TTS play() rejected:", err.name, err.message);
            updateStatus("COLA", ttsQueue.length + " (err:" + (err.name || "?").slice(0, 10) + ")");
            ttsPlaying = false;
            currentItemId = null;
            // Reintentar automaticamente (con limite de retries arriba)
            if (ttsQueue.length > 0) setTimeout(processTtsQueue, 300);
        });
    } else {
        console.log("[AUDIT] TTS play() returned undefined — navegador antiguo");
        // Asumir que funciona; onplaying o onended se encargan del resto
    }
}

// Timeout de seguridad: si onplaying no se dispara en 10s, liberar
ttsAudio.onplaying = function() {
    console.log("[AUDIT] TTS onplaying - audio sonando item_id:", currentItemId);
    _lastPlayedUrl = ttsAudio.src; // registrar para anti-duplicado
    startLipSync();
    if (_ttsSafetyTimeout) { clearTimeout(_ttsSafetyTimeout); _ttsSafetyTimeout = null; }
    if (currentItemId) {
        fetch('/api/playback_started', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({item_id: currentItemId})
        }).catch(function(e){ console.warn("playback_started failed:", e); });
    }
};
var _ttsSafetyTimeout = null;

// Evento onended: audio termino
ttsAudio.onended = function() {
    // Anti-duplicado: prevenir onended doble
    if (_lastEndedSrc === ttsAudio.src) {
        console.warn("[AUDIT] onended duplicado ignorado:", ttsAudio.src.split("/").pop());
        return;
    }
    _lastEndedSrc = ttsAudio.src;
    console.log("[AUDIT] TTS onended - audio termino, item_id:", currentItemId);
    stopLipSync();
    if (_ttsSafetyTimeout) { clearTimeout(_ttsSafetyTimeout); _ttsSafetyTimeout = null; }
    // Shift item (si no se hizo en play().then por alguna razon)
    if (ttsQueue.length > 0 && ttsQueue[0].url === ttsAudio.src) {
        ttsQueue.shift();
    }
    ttsPlaying = false;
    if (currentItemId) {
        fetch('/api/playback_done', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({item_id: currentItemId})
        }).catch(function(e){ console.warn("playback_done failed:", e); });
    }
    currentItemId = null;
    updateStatus("COLA", ttsQueue.length);
    if (ttsQueue.length > 0) {
        setTimeout(processTtsQueue, 200);
    }
};

// Evento onpause: audio pausado (imprevisto)
ttsAudio.onpause = function() {
    if (!ttsAudio.ended) {
        console.log("[Overlay] TTS onpause - audio pausado");
        stopLipSync();
    }
};

// Evento onerror: audio fallo (404, corrupto, etc) - no trabar la cola
ttsAudio.onerror = function() {
    var code = ttsAudio.error ? ttsAudio.error.code : '?';
    console.error("[AUDIT] TTS onerror - audio fallo, item_id:", currentItemId, "code:", code);
    stopLipSync();
    updateStatus("COLA", ttsQueue.length + " (err:" + code + ")");
    // Descartar item fallido
    if (ttsQueue.length > 0 && ttsQueue[0].url === ttsAudio.src) {
        ttsQueue.shift();
    }
    ttsPlaying = false;
    if (currentItemId) {
        fetch('/api/playback_done', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({item_id: currentItemId, error: true})
        }).catch(function(e){ console.warn("playback_done failed:", e); });
    }
    currentItemId = null;
    if (ttsQueue.length > 0) {
        setTimeout(processTtsQueue, 200);
    }
};

function initLipSync() {
    if (!lipSyncCtx) {
        try {
            lipSyncCtx = new (window.AudioContext || window.webkitAudioContext)();
            console.log("[Overlay] AudioContext created, state:", lipSyncCtx.state);
        } catch(e) {
            console.warn("[Overlay] LipSync AudioContext init failed:", e.message);
            return;
        }
    }
    // Crear analyser siempre que no exista
    if (!lipSyncAnalyser) {
        try {
            lipSyncAnalyser = lipSyncCtx.createAnalyser();
            lipSyncAnalyser.fftSize = 128;
            lipSyncAnalyser.smoothingTimeConstant = 0.3;
            lipSyncAnalyser.minDecibels = -55;
            lipSyncAnalyser.maxDecibels = 0;
        } catch(e) {
            console.warn("[Overlay] Analyser init failed:", e.message);
        }
    }
    // Conectar o reconectar la cadena de audio
    if (lipSyncCtx && lipSyncAnalyser) {
        // Asegurar que AudioContext este corriendo
        if (lipSyncCtx.state === 'suspended') {
            lipSyncCtx.resume();
        }
        if (!lipSyncSource) {
            try {
                lipSyncSource = lipSyncCtx.createMediaElementSource(ttsAudio);
                console.log("[AUDIT] MediaElementSource creado");
            } catch(e) {
                console.warn("[AUDIT] createMediaElementSource fallo:", e.message);
            }
        }
        // (Re)conectar la cadena: source → analyser → destination
        if (lipSyncSource) {
            try {
                lipSyncSource.disconnect();
                lipSyncSource.connect(lipSyncAnalyser);
                lipSyncAnalyser.disconnect();
                lipSyncAnalyser.connect(lipSyncCtx.destination);
                console.log("[AUDIT] Cadena audio: source → analyser → destination OK");
            } catch(e) {
                console.warn("[AUDIT] Cadena audio fallo:", e.message);
            }
        }
    }
}

function startLipSync() {
    if (!lipSyncCtx) { console.warn("[Overlay] LipSync: AudioContext no inicializado"); return; }
    if (lipSyncCtx.state === 'suspended') {
        lipSyncCtx.resume().then(function() {
            console.log("[Overlay] AudioContext resumed for lip sync");
        }).catch(function(e) {
            console.warn("[Overlay] AudioContext resume failed:", e);
        });
    }
    lastMouthVal = 0;
    lastSentMouth = -1;
    mouthSamples = [];
    var dataArray = new Uint8Array(lipSyncAnalyser.fftSize);
    if (lipSyncTimer) clearInterval(lipSyncTimer);
    var tickCount = 0;
    lipSyncTimer = setInterval(function() {
        // Solo analizar si el audio REALMENTE esta sonando
        if (ttsAudio.paused || ttsAudio.ended) {
            clearInterval(lipSyncTimer);
            lipSyncTimer = null;
            fetch('/api/vtube_mouth', {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({open: 0})
            }).catch(function(){});
            lastMouthVal = 0;
            lastSentMouth = -1;
            mouthSamples = [];
            return;
        }
        lipSyncAnalyser.getByteTimeDomainData(dataArray);
        var sum = 0;
        for (var i = 0; i < dataArray.length; i++) {
            sum += Math.abs(dataArray[i] - 128);
        }
        var avg = sum / dataArray.length;
        var mouth = Math.min(1.0, (avg / 50) * 1.4);
        mouth = Math.max(0, mouth);
        // Smoothing rapido para mas respuesta (0.15 prev + 0.85 current)
        mouth = lastMouthVal * 0.15 + mouth * 0.85;
        lastMouthVal = mouth;
        mouthSamples.push(mouth);
        tickCount++;
        // Enviar cada 2 ticks (~60ms) con el promedio de las muestras acumuladas
        if (tickCount % 2 === 0 && mouthSamples.length > 0) {
            var avgMouth = mouthSamples.reduce(function(a, b) { return a + b; }, 0) / mouthSamples.length;
            mouthSamples = [];
            // Solo enviar si cambio significativo (>0.03)
            if (Math.abs(avgMouth - lastSentMouth) > 0.03) {
                lastSentMouth = avgMouth;
                fetch('/api/vtube_mouth', {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({open: Math.round(avgMouth * 100) / 100})
                }).catch(function(){});
            }
        }
    }, 30);
}

function stopLipSync() {
    if (lipSyncTimer) { clearInterval(lipSyncTimer); lipSyncTimer = null; }
    lastMouthVal = 0;
    fetch('/api/vtube_mouth', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({open: 0})
    }).catch(function(){});
}

function createAlert(html) {
    const div = document.createElement("div");
    div.className = "alert";
    div.innerHTML = html;
    alertsContainer.appendChild(div);
    setTimeout(() => div.remove(), 5000);
}

function createMessage(user, text) {
    const div = document.createElement("div");
    div.className = "message";
    div.innerHTML = `<span class="user">${escapeHtml(user)}:</span> ${escapeHtml(text)}`;
    messagesContainer.prepend(div);
    if (messagesContainer.children.length > 20) {
        messagesContainer.lastElementChild.remove();
    }
}

function showTts(text) {
    ttsText.textContent = text;
    ttsText.style.opacity = "1";
    setTimeout(() => {
        ttsText.style.opacity = "0";
    }, 4000);
}

var currentItemId = null;

function playTts(data) {
    var url = typeof data === 'string' ? data : (data.url || '');
    var itemId = typeof data === 'object' ? (data.item_id || '') : '';
    if (!url) return;
    console.log("[AUDIT] playTts: url=" + url + " item_id=" + itemId + " unlocked=" + audioUnlocked + " cola=" + ttsQueue.length);
    updateStatus("LAST", url.split("/").pop().substring(0, 20) + "...");
    // Dedup: si esta URL ya esta en la cola o reproduciendose, ignorar
    if (ttsAudio.src && ttsAudio.src.endsWith(url.split("/").pop())) {
        console.log("[AUDIT] playTts: URL duplicada (en reproduccion), ignorando:", url);
        return;
    }
    for (var i = 0; i < ttsQueue.length; i++) {
        if (ttsQueue[i].url === url) {
            console.log("[AUDIT] playTts: URL duplicada (en cola pos " + i + "), ignorando:", url);
            return;
        }
    }
    if (ttsQueue.length >= MAX_TTS_QUEUE) {
        var dropped = ttsQueue.length - MAX_TTS_QUEUE + 1;
        var droppedItems = ttsQueue.slice(0, dropped);
        ttsQueue = ttsQueue.slice(dropped);
        console.log("[Overlay] Cola TTS llena, descartados", dropped, "items viejos");
        // Notificar al backend para que el pipeline libere slots
        droppedItems.forEach(function(item){
            if (item.item_id) {
                fetch('/api/playback_done', {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({item_id: item.item_id, dropped: true})
                }).catch(function(e){});
            }
        });
    }
    ttsQueue.push({url: url, item_id: itemId});
    updateStatus("COLA", ttsQueue.length);
    processTtsQueue();
}

function skipTts() {
    ttsQueue = [];
    ttsAudio.pause();
    ttsAudio.currentTime = 0;
    ttsText.style.opacity = "0";
    ttsPlaying = false;
}

function hasNonAscii(str) {
    for (var i = 0; i < str.length; i++) {
        if (str.charCodeAt(i) > 127) return true;
    }
    return false;
}

function emojiExplosion(emojis, count) {
    var layer = document.getElementById("emoji-layer");
    if (!layer) {
        console.log("[Overlay] ERROR: emoji-layer no encontrado");
        return;
    }
    var raw = String(emojis || "").trim();
    var emojiList;
    if (typeof Intl !== "undefined" && Intl.Segmenter) {
        var segmenter = new Intl.Segmenter("en", { granularity: "grapheme" });
        emojiList = Array.from(segmenter.segment(raw)).map(function(s) { return s.segment; });
    } else {
        emojiList = Array.from(raw);
    }
    if (!emojiList.length || !hasNonAscii(raw)) {
        console.log("[Overlay] Fallback a emojis por defecto");
        emojiList = ["🎉", "🌹", "✨", "💫", "⭐"];
    }

    var gravity = 420;
    var spawned = 0;

    // Cada particula tiene SU PROPIO scope (closure) via spawnOne
    function spawnOne(emoji) {
        var particle = document.createElement("div");
        particle.className = "emoji-particle";
        particle.textContent = emoji;

        var centerX = 46 + Math.random() * 8;
        var centerY = 36 + Math.random() * 8;
        var size = 1.8 + Math.random() * 2.8;
        var angle = Math.random() * Math.PI * 2;
        var speed = 280 + Math.random() * 520;

        var state = {
            x: 0, y: 0,
            vx: Math.cos(angle) * speed,
            vy: Math.sin(angle) * speed - 380 - Math.random() * 250,
            rot: 0,
            rotSpeed: (Math.random() - 0.5) * 650,
            lastTs: null,
            age: 0,
            born: false
        };

        particle.style.left = centerX + "%";
        particle.style.top = centerY + "%";
        particle.style.fontSize = size + "rem";
        particle.style.opacity = "0";

        layer.appendChild(particle);

        function tick(ts) {
            if (!state.born) {
                particle.style.opacity = "1";
                state.born = true;
                state.lastTs = ts;
                requestAnimationFrame(tick);
                return;
            }
            var dt = Math.min((ts - state.lastTs) / 1000, 0.05);
            state.lastTs = ts;
            state.age += dt;

            state.vy += gravity * dt;
            state.x += state.vx * dt;
            state.y += state.vy * dt;
            state.rot += state.rotSpeed * dt;
            state.vx *= 0.997;

            var scale = 1.2;
            var opacity = 1;
            if (state.age < 0.15) {
                scale = 0.3 + (state.age / 0.15) * 0.9;
                opacity = state.age / 0.15;
            } else if (state.age > 2.2) {
                var fade = (state.age - 2.2) / 0.6;
                opacity = Math.max(0, 1 - fade);
                scale = 1.2 - fade * 0.8;
            }

            particle.style.transform = "translate(" + Math.round(state.x) + "px, " + Math.round(state.y) + "px) rotate(" + Math.round(state.rot) + "deg) scale(" + scale.toFixed(2) + ")";
            particle.style.opacity = Math.round(opacity * 100) / 100;

            if (state.age < 2.8 && opacity > 0.01) {
                requestAnimationFrame(tick);
            } else {
                particle.remove();
            }
        }

        var delay = Math.random() * 0.25;
        setTimeout(function() {
            requestAnimationFrame(tick);
        }, delay * 1000);

        spawned++;
    }

    for (var i = 0; i < count; i++) {
        spawnOne(emojiList[Math.floor(Math.random() * emojiList.length)]);
    }
    console.log("[Overlay] Spawned " + spawned + " particles");
}

function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

function sseOnMessage(e) {
    try {
        const payload = JSON.parse(e.data);
        const type = payload.type;
        const data = payload.data;

        if (type === "overlay_message") {
            console.log("[Overlay] Chat msg:", data.user, "->", data.text ? data.text.slice(0,40) : '');
            createMessage(data.user, data.text);
        } else if (type === "overlay_alert") {
            console.log("[Overlay] Alert:", data.type, data.user);
            if (data.type === "gift") {
                createAlert(`🎁 ${escapeHtml(data.user)} envió ${escapeHtml(data.gift)} x${data.amount}`);
            } else if (data.type === "like") {
                createAlert(`❤️ ${escapeHtml(data.user)} dio ${data.count} likes`);
            } else if (data.type === "join") {
                createAlert(`👋 ${escapeHtml(data.user)} se unió`);
            } else if (data.type === "info") {
                createAlert(`ℹ️ ${escapeHtml(data.text)}`);
            }
        } else if (type === "tts_speak") {
            console.log("[Overlay] TTS speak text:", data.text);
            showTts(data.text);
        } else if (type === "tts_audio") {
            console.log("[AUDIT] SSE tts_audio: url=" + data.url + " item_id=" + data.item_id + " comment=" + (data.comment || false));
            playTts(data);
        } else if (type === "tts_skip") {
            console.log("[Overlay] TTS skip");
            skipTts();
        } else if (type === "play_sfx") {
            console.log("[Overlay] SFX:", data.file);
            playSfx(data.file);
        } else if (type === "overlay_emoji") {
            var raw = data.emojis || "🎉";
            console.log("[Overlay] Emoji event recibido:", raw, "count:", data.count);
            console.log("[Overlay] Primer char code:", raw.charCodeAt(0), "length:", raw.length);
            if (raw.length >= 2) {
                console.log("[Overlay] Segundo char code:", raw.charCodeAt(1));
            }
            // Debug: mostrar en overlay que emojis llegaron (visible solo con fondo solido)
            ensureDebugLog();
            logDebug("Emoji raw: " + raw);
            emojiExplosion(raw, data.count || 10);
        } else if (type === "overlay_config") {
            if (data.background) {
                document.body.style.background = data.background === "transparent" ? "transparent" : data.background;
                document.documentElement.style.background = data.background === "transparent" ? "transparent" : data.background;
            }
            if (data.debug === true) {
                ensureDebugLog();
                logDebug("Debug mode ON");
            } else if (data.debug === false) {
                logDebug("Debug mode OFF");
            }
        } else if (type === "log" && data && data.message) {
            if (document.getElementById("debug-log")) {
                logDebug(data.message);
            }
        }
    } catch (err) {
        console.error("Error procesando evento:", err);
    }
}

function ensureDebugLog() {
    if (!document.getElementById("debug-log")) {
        var dl = document.createElement("div");
        dl.id = "debug-log";
        dl.style.cssText = "position:absolute;top:10px;left:10px;width:300px;max-height:200px;overflow-y:auto;background:rgba(0,0,0,0.7);color:#0f0;font-family:monospace;font-size:12px;padding:8px;border-radius:6px;z-index:9999;pointer-events:none;";
        document.body.appendChild(dl);
    }
}

function logDebug(msg) {
    var dl = document.getElementById("debug-log");
    if (!dl) return;
    var line = document.createElement("div");
    line.textContent = new Date().toLocaleTimeString() + " " + msg;
    dl.appendChild(line);
    while (dl.children.length > 20) dl.firstElementChild.remove();
    dl.scrollTop = dl.scrollHeight;
}

function sseOnError() {
    console.error("[AUDIT] SSE desconectado, reintentando en 3s...");
    updateStatus("SSE", "ERROR");
    evtSource.close();
    setTimeout(function() {
        evtSource = new EventSource("/stream");
        evtSource.onopen = function() { updateStatus("SSE", "OK"); console.log("[AUDIT] SSE reconectado"); };
        evtSource.onmessage = sseOnMessage;
        evtSource.onerror = sseOnError;
    }, 3000);
}

// Status bar para debug visual
function updateStatus(label, value) {
    var el = document.getElementById(
        label === "SSE" ? "sse-status" :
        label === "AUDIO" ? "audio-status" :
        label === "COLA" ? "queue-status" :
        label === "LAST" ? "last-event" : null
    );
    if (el) el.textContent = label + ": " + value;
}

// Desbloquear AudioContext en el primer click/touch (politica del navegador)
function unlockAudio() {
    var overlay = document.getElementById('click-to-start');
    audioUnlocked = true;
    updateStatus("AUDIO", "OK");

    // Crear/resumir AudioContext
    try {
        if (!lipSyncCtx) {
            lipSyncCtx = new (window.AudioContext || window.webkitAudioContext)();
        }
        if (lipSyncCtx.state === 'suspended') {
            lipSyncCtx.resume().then(function() {
                console.log("[Overlay] AudioContext unlocked by user gesture");
            });
        }
        // Inicializar cadena de lip sync AHORA (antes causaba audio mudo)
        initLipSync();
        // Reproducir un beep audible de prueba para confirmar que audio funciona
        var testBuffer = lipSyncCtx.createBuffer(1, lipSyncCtx.sampleRate * 0.2, lipSyncCtx.sampleRate);
        var data = testBuffer.getChannelData(0);
        for (var i = 0; i < data.length; i++) {
            data[i] = Math.sin(2 * Math.PI * 440 * i / lipSyncCtx.sampleRate) * 0.3;
        }
        var testSource = lipSyncCtx.createBufferSource();
        testSource.buffer = testBuffer;
        testSource.connect(lipSyncCtx.destination);
        testSource.start(0);
        testSource.onended = function() {
            console.log("[AUDIT] Test beep completado — audio OK");
        };
    } catch(e) {
        console.warn("[Overlay] Audio unlock failed:", e.message);
    }
    
    // Ocultar el overlay de click-to-start
    if (overlay) {
        overlay.style.display = 'none';
    }
    
    // Procesar la cola TTS pendiente si hay items
    if (ttsQueue.length > 0 && !ttsPlaying) {
        processTtsQueue();
    }
}

document.addEventListener('click', function unlockAudioLegacy() {
    if (!audioUnlocked) {
        audioUnlocked = true;
        updateStatus("AUDIO", "OK (fallback)");
        console.log("[AUDIT] Audio unlocked via click fallback");
    }
    if (lipSyncCtx && lipSyncCtx.state === 'suspended') {
        lipSyncCtx.resume().then(function() {
            console.log("[Overlay] AudioContext unlocked by user gesture");
        });
    }
    if (ttsQueue.length > 0 && !ttsPlaying) {
        processTtsQueue();
    }
}, { once: true });
document.addEventListener('touchstart', function unlockAudioTouch() {
    if (!audioUnlocked) {
        audioUnlocked = true;
        updateStatus("AUDIO", "OK (touch)");
        console.log("[AUDIT] Audio unlocked via touch");
    }
    if (lipSyncCtx && lipSyncCtx.state === 'suspended') {
        lipSyncCtx.resume();
    }
    if (ttsQueue.length > 0 && !ttsPlaying) {
        processTtsQueue();
    }
}, { once: true });

// Test emoji rendering on load
(function testEmojiRender() {
    var testDiv = document.createElement("div");
    testDiv.style.cssText = "position:absolute;top:10px;right:10px;font-size:24px;z-index:9999;";
    testDiv.textContent = "🎉🌹✨";
    testDiv.id = "emoji-test";
    document.body.appendChild(testDiv);
    setTimeout(function() {
        var testEl = document.getElementById("emoji-test");
        if (testEl) {
            var w = testEl.offsetWidth;
            console.log("[Overlay] Emoji test render width:", w, "px (si es ~30-50px, las fuentes emojis funcionan)");
            testEl.remove();
        }
    }, 2000);
})();

var evtSource = new EventSource("/stream");
evtSource.onmessage = sseOnMessage;
evtSource.onerror = sseOnError;
evtSource.onopen = function() {
    console.log("[AUDIT] SSE conexion abierta");
    updateStatus("SSE", "OK");
};
console.log("[AUDIT] SSE conectado a /stream");
updateStatus("SSE", "conectando...");
