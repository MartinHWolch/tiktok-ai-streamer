const evtSource = new EventSource("/stream");

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

evtSource.onmessage = (e) => {
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
        }
    } catch (err) {
        console.error("Error procesando evento:", err);
    }
};

evtSource.onerror = (err) => {
    console.error("SSE error:", err);
};
