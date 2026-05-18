const logList = document.getElementById("log-list");
const ttsStatus = document.getElementById("tts-status");
const aiStatus = document.getElementById("ai-status");
const tiktokStatus = document.getElementById("tiktok-status");

const toggleTts = document.getElementById("toggle-tts");
const toggleAi = document.getElementById("toggle-ai");
const toggleTiktok = document.getElementById("toggle-tiktok");

// Reproductor de audio para pruebas TTS
const testAudio = new Audio();
testAudio.volume = 1.0;

// TTS Config elements
const ttsEngine = document.getElementById("tts-engine");
const ttsVoice = document.getElementById("tts-voice");
const toggleBlend = document.getElementById("toggle-blend");
const ttsBlend = document.getElementById("tts-blend");
const ttsSpeed = document.getElementById("tts-speed");
const speedValue = document.getElementById("speed-value");
const ttsLang = document.getElementById("tts-lang");
const ttsTestText = document.getElementById("tts-test-text");
const btnTestTts = document.getElementById("btn-test-tts");

// Presets y preview
const btnPreviewVoice = document.getElementById("btn-preview-voice");
const presetName = document.getElementById("preset-name");
const btnSavePreset = document.getElementById("btn-save-preset");
const presetSelect = document.getElementById("preset-select");
const btnLoadPreset = document.getElementById("btn-load-preset");
const btnDeletePreset = document.getElementById("btn-delete-preset");

// Kokoro avanzado
const ttsPitch = document.getElementById("tts-pitch");
const pitchValue = document.getElementById("pitch-value");
const ttsVolume = document.getElementById("tts-volume");
const volumeValue = document.getElementById("volume-value");
const kokoroModel = document.getElementById("kokoro-model");

function updateEngineUI(engine) {
    var kOpts = document.querySelectorAll(".kokoro-opt");
    kOpts.forEach(function(el) {
        el.classList.toggle("hidden", engine !== "kokoro");
    });
}

function addLog(text) {
    const li = document.createElement("li");
    li.textContent = text;
    logList.prepend(li);
    while (logList.children.length > 50) {
        logList.lastElementChild.remove();
    }
}

async function postJSON(url, data) {
    try {
        const res = await fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: data ? JSON.stringify(data) : "{}"
        });
        if (!res.ok) {
            const text = await res.text();
            addLog(`Error HTTP ${res.status}: ${text.substring(0, 80)}`);
            return null;
        }
        return await res.json();
    } catch (e) {
        addLog(`Error red: ${e.message}`);
        return null;
    }
}

function updateBadge(el, enabled, onText, offText) {
    el.textContent = enabled ? onText : offText;
    el.className = "badge " + (enabled ? "on" : "off");
}

function populateVoices(voices, currentVoice) {
    ttsVoice.innerHTML = "";
    if (!voices || !voices.length) {
        var opt = document.createElement("option");
        opt.value = currentVoice || "im_nicola";
        opt.textContent = opt.value;
        ttsVoice.appendChild(opt);
        return;
    }
    voices.forEach(function(v) {
        var opt = document.createElement("option");
        opt.value = v;
        opt.textContent = v;
        if (v === currentVoice) opt.selected = true;
        ttsVoice.appendChild(opt);
    });
}

// Toggle handlers - ignorar clicks que vienen del label bubbling
// Solo procesar cuando el click es directo sobre el input
toggleTts.addEventListener("click", async function(e) {
    if (e.target !== e.currentTarget) return; // ignorar bubbling desde span/label
    toggleTts.disabled = true;
    var res = await postJSON("/api/toggle_tts");
    if (res) {
        toggleTts.checked = res.tts_enabled;
        updateBadge(ttsStatus, res.tts_enabled, "ACTIVADO", "DESACTIVADO");
        addLog("TTS -> " + (res.tts_enabled ? "ON" : "OFF"));
    }
    toggleTts.disabled = false;
});

toggleAi.addEventListener("click", async function(e) {
    if (e.target !== e.currentTarget) return;
    toggleAi.disabled = true;
    var res = await postJSON("/api/toggle_ai");
    if (res) {
        toggleAi.checked = res.ai_enabled;
        updateBadge(aiStatus, res.ai_enabled, "ACTIVADO", "DESACTIVADO");
        addLog("IA -> " + (res.ai_enabled ? "ON" : "OFF"));
    }
    toggleAi.disabled = false;
});

toggleTiktok.addEventListener("click", async function(e) {
    if (e.target !== e.currentTarget) return;
    toggleTiktok.disabled = true;
    var res = await postJSON("/api/toggle_tiktok");
    if (res) {
        toggleTiktok.checked = res.tiktok_enabled;
        updateBadge(tiktokStatus, res.tiktok_enabled, "ACTIVADO", "PAUSADO");
        addLog("TikTok -> " + (res.tiktok_enabled ? "ON" : "OFF"));
    }
    toggleTiktok.disabled = false;
});

// TTS Config
ttsEngine.addEventListener("change", async function() {
    updateEngineUI(ttsEngine.value);
    var res = await postJSON("/api/set_tts_engine", { engine: ttsEngine.value });
    if (res && res.success) {
        addLog("TTS motor -> " + ttsEngine.value);
        populateVoices(res.status.kokoro_voices, res.status.voice);
        loadPresetList();
    }
});

ttsVoice.addEventListener("change", async function() {
    var res = await postJSON("/api/set_tts_voice", { voice: ttsVoice.value });
    if (res && res.success) {
        addLog("TTS voz -> " + ttsVoice.value);
    }
});

toggleBlend.addEventListener("change", function() {
    ttsBlend.disabled = !toggleBlend.checked;
    if (!toggleBlend.checked) {
        postJSON("/api/set_tts_voice_blend", { blend: "" });
        addLog("TTS blend -> desactivado");
    }
});

ttsBlend.addEventListener("change", async function() {
    if (toggleBlend.checked) {
        var res = await postJSON("/api/set_tts_voice_blend", { blend: ttsBlend.value });
        if (res && res.success) {
            addLog("TTS blend -> " + ttsBlend.value);
        }
    }
});

ttsSpeed.addEventListener("input", function() {
    speedValue.textContent = parseFloat(ttsSpeed.value).toFixed(1);
});

ttsSpeed.addEventListener("change", async function() {
    var speed = parseFloat(ttsSpeed.value);
    var res = await postJSON("/api/set_tts_speed", { speed: speed });
    if (res && res.success) {
        addLog("TTS velocidad -> " + speed.toFixed(1) + "x");
    }
});

ttsPitch.addEventListener("input", function() {
    pitchValue.textContent = parseInt(ttsPitch.value);
});

ttsPitch.addEventListener("change", async function() {
    var pitch = parseInt(ttsPitch.value);
    var res = await postJSON("/api/set_tts_pitch", { pitch: pitch });
    if (res && res.success) {
        addLog("TTS pitch -> " + pitch + " st");
    }
});

ttsVolume.addEventListener("input", function() {
    volumeValue.textContent = parseFloat(ttsVolume.value).toFixed(1);
});

ttsVolume.addEventListener("change", async function() {
    var vol = parseFloat(ttsVolume.value);
    var res = await postJSON("/api/set_tts_volume", { volume: vol });
    if (res && res.success) {
        addLog("TTS volumen -> " + vol.toFixed(1) + "x");
    }
});

kokoroModel.addEventListener("change", async function() {
    var prevModel = kokoroModel.dataset.current || "fp16";
    addLog("Cambiando modelo Kokoro...");
    var res = await postJSON("/api/set_kokoro_model", { model: kokoroModel.value });
    if (res && res.success) {
        kokoroModel.dataset.current = kokoroModel.value;
        addLog("Modelo Kokoro -> " + kokoroModel.value);
        populateVoices(res.status.kokoro_voices, res.status.voice);
    } else {
        addLog("Error al cambiar modelo, revirtiendo a " + prevModel);
        kokoroModel.value = prevModel;
    }
});

ttsLang.addEventListener("change", async function() {
    var res = await postJSON("/api/set_tts_lang", { lang: ttsLang.value });
    if (res && res.success) {
        addLog("TTS idioma -> " + ttsLang.value);
    }
});

// Voice preview
btnPreviewVoice.addEventListener("click", async function() {
    if (!ttsVoice.value) return;
    btnPreviewVoice.textContent = "...";
    btnPreviewVoice.disabled = true;
    var res = await postJSON("/api/preview_voice", { voice: ttsVoice.value });
    if (res && res.filename) {
        addLog("Preview voz: " + ttsVoice.value);
        testAudio.src = "/audio/" + res.filename;
        testAudio.currentTime = 0;
        testAudio.play().catch(function(){});
    }
    btnPreviewVoice.textContent = "\u25B6";
    btnPreviewVoice.disabled = false;
});

// Presets
async function loadPresetList() {
    try {
        var r = await fetch("/api/tts_presets");
        var presets = await r.json();
        presetSelect.innerHTML = '<option value="">-- Cargar preset --</option>';
        Object.keys(presets).sort().forEach(function(name) {
            var opt = document.createElement("option");
            opt.value = name;
            opt.textContent = name;
            presetSelect.appendChild(opt);
        });
    } catch(e) { console.error(e); }
}

btnSavePreset.addEventListener("click", async function() {
    var name = presetName.value.trim();
    if (!name) { addLog("Escribe un nombre para el preset"); return; }
    var res = await postJSON("/api/save_preset", { name: name });
    if (res && res.success) {
        addLog("Preset guardado: " + name);
        presetName.value = "";
        loadPresetList();
    }
});

btnLoadPreset.addEventListener("click", async function() {
    var name = presetSelect.value;
    if (!name) { addLog("Selecciona un preset"); return; }
    var res = await postJSON("/api/load_preset", { name: name });
    if (res && res.success) {
        addLog("Preset cargado: " + name);
        var s = res.status;
        if (s.engine) { ttsEngine.value = s.engine; updateEngineUI(s.engine); }
        if (s.voice) ttsVoice.value = s.voice;
        if (s.voice_blend) {
            ttsBlend.value = s.voice_blend;
            toggleBlend.checked = true;
            ttsBlend.disabled = false;
        } else {
            ttsBlend.value = "";
            toggleBlend.checked = false;
            ttsBlend.disabled = true;
        }
        if (s.speed !== undefined) { ttsSpeed.value = s.speed; speedValue.textContent = s.speed.toFixed(1); }
        if (s.lang) ttsLang.value = s.lang;
        populateVoices(s.kokoro_voices, s.voice);
    }
});

btnDeletePreset.addEventListener("click", async function() {
    var name = presetSelect.value;
    if (!name) { addLog("Selecciona un preset para eliminar"); return; }
    if (!confirm("Eliminar preset \"" + name + "\"?")) return;
    var res = await postJSON("/api/delete_preset", { name: name });
    if (res && res.success) {
        addLog("Preset eliminado: " + name);
        loadPresetList();
    }
});

btnTestTts.addEventListener("click", async function() {
    btnTestTts.textContent = "Generando...";
    btnTestTts.disabled = true;
    var res = await postJSON("/api/test_tts", { text: ttsTestText.value });
    if (res === null) {
        addLog("Error de conexion. Verifica que main.py este corriendo.");
    } else if (res.filename) {
        addLog("TTS generado: " + res.filename + " - reproduciendo...");
        testAudio.src = "/audio/" + res.filename;
        testAudio.currentTime = 0;
        testAudio.play().catch(function(err) {
            addLog("No se pudo reproducir audio: " + err.message);
        });
    } else {
        addLog("Error TTS: " + (res.status || "revisa logs del servidor"));
    }
    btnTestTts.textContent = "Probar TTS";
    btnTestTts.disabled = false;
});

// Actions
document.getElementById("btn-gift").addEventListener("click", async function() {
    await postJSON("/api/simulate_gift", { user: "Admin", gift: "Panda" });
    addLog("Simulacion de regalo enviada.");
});

document.getElementById("btn-message").addEventListener("click", async function() {
    await postJSON("/api/test_message", { user: "Admin", text: "Hola desde el panel" });
    addLog("Mensaje de prueba enviado.");
});

// SSE
var evtSource = new EventSource("/stream");
evtSource.onmessage = function(e) {
    try {
        var payload = JSON.parse(e.data);
        if (payload.type === "log") {
            addLog(payload.data.message);
        }
    } catch (err) {
        console.error(err);
    }
};
evtSource.onerror = function() { console.error("SSE desconectado"); };

// Init
fetch("/api/logs")
    .then(function(r) { return r.json(); })
    .then(function(logs) {
        logs.reverse().forEach(function(l) { addLog(l); });
    });

fetch("/api/status")
    .then(function(r) { return r.json(); })
    .then(function(s) {
        toggleTts.checked = s.tts_enabled;
        toggleAi.checked = s.ai_enabled;
        toggleTiktok.checked = s.tiktok_enabled;
        updateBadge(ttsStatus, s.tts_enabled, "ACTIVADO", "DESACTIVADO");
        updateBadge(aiStatus, s.ai_enabled, "ACTIVADO", "DESACTIVADO");
        updateBadge(tiktokStatus, s.tiktok_enabled, "ACTIVADO", "PAUSADO");
    });

fetch("/api/tts_status")
    .then(function(r) { return r.json(); })
    .then(function(status) {
        if (status.engine) {
            ttsEngine.value = status.engine;
            updateEngineUI(status.engine);
        }
        if (status.speed !== undefined) {
            ttsSpeed.value = status.speed;
            speedValue.textContent = status.speed.toFixed(1);
        }
        if (status.lang) {
            ttsLang.value = status.lang;
        }
        if (status.pitch !== undefined) {
            ttsPitch.value = status.pitch;
            pitchValue.textContent = parseInt(status.pitch);
        }
        if (status.volume !== undefined) {
            ttsVolume.value = status.volume;
            volumeValue.textContent = status.volume.toFixed(1);
        }
        if (status.kokoro_model) {
            kokoroModel.value = status.kokoro_model;
            kokoroModel.dataset.current = status.kokoro_model;
        }
        if (status.voice_blend) {
            ttsBlend.value = status.voice_blend;
            toggleBlend.checked = true;
            ttsBlend.disabled = false;
        }
        populateVoices(status.kokoro_voices, status.voice);
    });

loadPresetList();
