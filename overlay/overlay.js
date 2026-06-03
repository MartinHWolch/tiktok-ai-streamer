var alertsContainer = document.getElementById("alerts");
var messagesContainer = document.getElementById("messages");
var ttsText = document.getElementById("tts-text");

var audioUnlocked = false;
var currentItemId = null;

var lipSyncCtx = null;
var lipSyncAnalyser = null;
var lipSyncTimer = null;
var lipSyncSource = null;
var lastMouthVal = 0;
var lastSentMouth = -1;
var mouthSamples = [];

function playSfx(file) {
    var sfx = new Audio("/sfx/" + file);
    sfx.volume = 0.7;
    sfx.play().catch(function(e) {
        console.warn("[Overlay] SFX error:", file, e.message);
    });
}

var ttsPlayer = {
    audio: new Audio(),
    queue: [],
    playing: false,
    playedUrls: {},

    enqueue: function(data) {
        var url = (typeof data === 'string') ? data : (data.url || '');
        if (!url) return;
        if (this.playedUrls[url]) {
            console.log("[TTS] Dedup ignorado:", url.split("/").pop());
            return;
        }
        this.playedUrls[url] = true;
        var itemId = (typeof data === 'object') ? (data.item_id || '') : '';
        this.queue.push({url: url, item_id: itemId});
        updateStatus("COLA", this.queue.length);
        this._tryNext();
    },

    _tryNext: function() {
        if (this.playing || this.queue.length === 0 || !audioUnlocked) return;
        this.playing = true;
        var item = this.queue.shift();
        currentItemId = item.item_id || null;
        updateStatus("COLA", this.queue.length + " (playing)");
        var self = this;
        this.audio.src = item.url;
        this.audio.play().then(function() {
            console.log("[TTS] Play:", item.url.split("/").pop());
            startLipSync();
            if (item.item_id) {
                fetch('/api/playback_started', {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({item_id: item.item_id})
                }).catch(function(){});
            }
        }).catch(function(err) {
            console.warn("[TTS] Play failed:", err.name);
            self.playing = false;
            currentItemId = null;
            setTimeout(function() { self._tryNext(); }, 500);
        });
    },

    _onEnded: function() {
        stopLipSync();
        if (currentItemId) {
            fetch('/api/playback_done', {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({item_id: currentItemId})
            }).catch(function(){});
        }
        this.playing = false;
        currentItemId = null;
        updateStatus("COLA", this.queue.length);
        this._tryNext();
    },

    skip: function() {
        this.queue = [];
        this.audio.pause();
        this.audio.currentTime = 0;
        stopLipSync();
        this.playing = false;
        currentItemId = null;
        updateStatus("COLA", 0);
    },

    unlock: function() {
        audioUnlocked = true;
        this._tryNext();
    }
};

ttsPlayer.audio.volume = 1.0;
ttsPlayer.audio.onended = function() { ttsPlayer._onEnded(); };
ttsPlayer.audio.onerror = function() {
    console.error("[TTS] Audio error, code:", ttsPlayer.audio.error ? ttsPlayer.audio.error.code : '?');
    stopLipSync();
    ttsPlayer.playing = false;
    currentItemId = null;
    ttsPlayer._tryNext();
};

function initLipSync() {
    if (!lipSyncCtx) {
        try {
            lipSyncCtx = new (window.AudioContext || window.webkitAudioContext)();
        } catch(e) { return; }
    }
    if (!lipSyncAnalyser) {
        try {
            lipSyncAnalyser = lipSyncCtx.createAnalyser();
            lipSyncAnalyser.fftSize = 128;
            lipSyncAnalyser.smoothingTimeConstant = 0.3;
            lipSyncAnalyser.minDecibels = -55;
            lipSyncAnalyser.maxDecibels = 0;
        } catch(e) { return; }
    }
    if (lipSyncCtx.state === 'suspended') lipSyncCtx.resume();
    if (!lipSyncSource) {
        try { lipSyncSource = lipSyncCtx.createMediaElementSource(ttsPlayer.audio); } catch(e) {}
    }
    if (lipSyncSource) {
        try {
            lipSyncSource.disconnect();
            lipSyncSource.connect(lipSyncAnalyser);
            lipSyncAnalyser.disconnect();
            lipSyncAnalyser.connect(lipSyncCtx.destination);
        } catch(e) {}
    }
}

function startLipSync() {
    if (!lipSyncCtx || !lipSyncAnalyser) return;
    if (lipSyncCtx.state === 'suspended') lipSyncCtx.resume();
    lastMouthVal = 0;
    lastSentMouth = -1;
    mouthSamples = [];
    var dataArray = new Uint8Array(lipSyncAnalyser.fftSize);
    if (lipSyncTimer) clearInterval(lipSyncTimer);
    var tickCount = 0;
    lipSyncTimer = setInterval(function() {
        if (ttsPlayer.audio.paused || ttsPlayer.audio.ended) {
            clearInterval(lipSyncTimer);
            lipSyncTimer = null;
            fetch('/api/vtube_mouth', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({open: 0})}).catch(function(){});
            return;
        }
        lipSyncAnalyser.getByteTimeDomainData(dataArray);
        var sum = 0;
        for (var i = 0; i < dataArray.length; i++) sum += Math.abs(dataArray[i] - 128);
        var mouth = Math.min(1.0, (sum / dataArray.length / 50) * 1.4);
        mouth = lastMouthVal * 0.15 + mouth * 0.85;
        lastMouthVal = mouth;
        mouthSamples.push(mouth);
        tickCount++;
        if (tickCount % 2 === 0 && mouthSamples.length > 0) {
            var avg = mouthSamples.reduce(function(a, b) { return a + b; }, 0) / mouthSamples.length;
            mouthSamples = [];
            if (Math.abs(avg - lastSentMouth) > 0.03) {
                lastSentMouth = avg;
                fetch('/api/vtube_mouth', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({open: Math.round(avg * 100) / 100})}).catch(function(){});
            }
        }
    }, 30);
}

function stopLipSync() {
    if (lipSyncTimer) { clearInterval(lipSyncTimer); lipSyncTimer = null; }
    lastMouthVal = 0;
    fetch('/api/vtube_mouth', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({open: 0})}).catch(function(){});
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
    if (messagesContainer.children.length > 20) messagesContainer.lastElementChild.remove();
}

function showTts(text) {
    ttsText.textContent = text;
    ttsText.style.opacity = "1";
    setTimeout(() => { ttsText.style.opacity = "0"; }, 4000);
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
            console.log("[TTS] SSE audio:", data.url, "item:", data.item_id);
            updateStatus("LAST", (data.url || "").split("/").pop().substring(0, 20) + "...");
            ttsPlayer.enqueue(data);
        } else if (type === "tts_skip") {
            console.log("[TTS] Skip");
            ttsPlayer.skip();
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

function unlockAudio() {
    var overlay = document.getElementById('click-to-start');
    ttsPlayer.unlock();
    updateStatus("AUDIO", "OK");

    try {
        if (!lipSyncCtx) {
            lipSyncCtx = new (window.AudioContext || window.webkitAudioContext)();
        }
        if (lipSyncCtx.state === 'suspended') lipSyncCtx.resume();
        initLipSync();
        if (lipSyncCtx) {
            var testBuffer = lipSyncCtx.createBuffer(1, lipSyncCtx.sampleRate * 0.2, lipSyncCtx.sampleRate);
            var data = testBuffer.getChannelData(0);
            for (var i = 0; i < data.length; i++) data[i] = Math.sin(2 * Math.PI * 440 * i / lipSyncCtx.sampleRate) * 0.3;
            var testSource = lipSyncCtx.createBufferSource();
            testSource.buffer = testBuffer;
            testSource.connect(lipSyncCtx.destination);
            testSource.start(0);
        }
    } catch(e) {
        console.warn("[Overlay] Audio unlock failed:", e.message);
    }
    
    if (overlay) overlay.style.display = 'none';
}

document.addEventListener('click', function() {
    if (!audioUnlocked) {
        ttsPlayer.unlock();
        updateStatus("AUDIO", "OK (click)");
    }
    if (lipSyncCtx && lipSyncCtx.state === 'suspended') lipSyncCtx.resume();
}, { once: true });

document.addEventListener('touchstart', function() {
    if (!audioUnlocked) {
        ttsPlayer.unlock();
        updateStatus("AUDIO", "OK (touch)");
    }
    if (lipSyncCtx && lipSyncCtx.state === 'suspended') lipSyncCtx.resume();
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
