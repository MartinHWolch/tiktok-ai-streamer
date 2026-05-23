const alertsContainer = document.getElementById("alerts");
const messagesContainer = document.getElementById("messages");
const ttsText = document.getElementById("tts-text");

// Reproductor de audio para TTS (con cola)
var ttsAudio = new Audio();
ttsAudio.volume = 1.0;
var ttsQueue = [];
var ttsPlaying = false;

function processTtsQueue() {
    if (ttsPlaying || ttsQueue.length === 0) return;
    ttsPlaying = true;
    var url = ttsQueue.shift();
    console.log("[Overlay] TTS play URL:", url, "(cola:", ttsQueue.length, ")");
    ttsAudio.src = url;
    ttsAudio.currentTime = 0;
    ttsAudio.play().then(function() {
        console.log("[Overlay] TTS reproduciendo OK");
    }).catch(function(err) {
        console.warn("[Overlay] TTS autoplay bloqueado:", err.name, err.message);
        ttsPlaying = false;
        processTtsQueue();
    });
}

ttsAudio.onended = function() {
    ttsPlaying = false;
    if (ttsQueue.length > 0) {
        setTimeout(processTtsQueue, 200);
    }
};

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

function playTts(url) {
    ttsQueue.push(url);
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
            createMessage(data.user, data.text);
        } else if (type === "overlay_alert") {
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
            console.log("[Overlay] TTS audio URL:", data.url);
            playTts(data.url);
        } else if (type === "tts_skip") {
            console.log("[Overlay] TTS skip");
            skipTts();
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
    console.error("SSE desconectado, reintentando en 3s...");
    evtSource.close();
    setTimeout(function() {
        evtSource = new EventSource("/stream");
        evtSource.onmessage = sseOnMessage;
        evtSource.onerror = sseOnError;
    }, 3000);
}

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

const evtSource = new EventSource("/stream");
evtSource.onmessage = sseOnMessage;
evtSource.onerror = sseOnError;
