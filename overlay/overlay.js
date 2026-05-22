const alertsContainer = document.getElementById("alerts");
const messagesContainer = document.getElementById("messages");
const ttsText = document.getElementById("tts-text");

// Reproductor de audio para TTS
const ttsAudio = new Audio();
ttsAudio.volume = 1.0;

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
    ttsAudio.src = url;
    ttsAudio.currentTime = 0;
    ttsAudio.play().catch(err => {
        console.warn("No se pudo reproducir audio TTS:", err);
    });
}

function skipTts() {
    ttsAudio.pause();
    ttsAudio.currentTime = 0;
    ttsText.style.opacity = "0";
}

function emojiExplosion(emojis, count) {
    var layer = document.getElementById("emoji-layer");
    if (!layer) return;
    var emojiList = Array.from(emojis);
    if (!emojiList.length) emojiList = ["🎉"];

    for (var i = 0; i < count; i++) {
        var particle = document.createElement("div");
        particle.className = "emoji-particle";
        particle.textContent = emojiList[Math.floor(Math.random() * emojiList.length)];

        var startX = 40 + Math.random() * 20;
        var startY = 40 + Math.random() * 20;
        var endX = (Math.random() - 0.5) * 400;
        var endY = -(80 + Math.random() * 250);
        var rot = (Math.random() - 0.5) * 720;
        var size = 1.5 + Math.random() * 2.5;
        var delay = Math.random() * 0.3;

        particle.style.left = startX + "%";
        particle.style.top = startY + "%";
        particle.style.fontSize = size + "rem";
        particle.style.animation = "none";

        layer.appendChild(particle);

        // Force reflow and animate with requestAnimationFrame
        particle.offsetHeight;

        var start = null;
        var duration = 2000 + delay * 1000;

        function step(timestamp) {
            if (!start) start = timestamp;
            var progress = Math.min((timestamp - start) / duration, 1);
            var eased = 1 - Math.pow(1 - progress, 3);

            var x = endX * eased;
            var y = endY * eased;
            var scale = 1.2 - 0.9 * eased;
            var rotVal = rot * eased;
            var opacity = progress < 0.2 ? 1 : 1 - (progress - 0.2) / 0.8;

            particle.style.transform = "translate(" + x + "px, " + y + "px) scale(" + scale + ") rotate(" + rotVal + "deg)";
            particle.style.opacity = opacity;

            if (progress < 1) {
                requestAnimationFrame(step);
            } else {
                particle.remove();
            }
        }

        setTimeout(function() {
            requestAnimationFrame(step);
        }, delay * 1000);
    }
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
            showTts(data.text);
        } else if (type === "tts_audio") {
            playTts(data.url);
        } else if (type === "tts_skip") {
            skipTts();
        } else if (type === "overlay_emoji") {
            emojiExplosion(data.emojis || "🎉", data.count || 10);
        }
    } catch (err) {
        console.error("Error procesando evento:", err);
    }
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

const evtSource = new EventSource("/stream");
evtSource.onmessage = sseOnMessage;
evtSource.onerror = sseOnError;
