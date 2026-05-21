// ===== Tab Navigation =====
document.querySelectorAll('.channel').forEach(function(ch) {
    ch.addEventListener('click', function() {
        document.querySelectorAll('.channel').forEach(function(c) { c.classList.remove('active'); });
        document.querySelectorAll('.tab').forEach(function(t) { t.classList.remove('active'); });
        ch.classList.add('active');
        var tabId = 'tab-' + ch.dataset.tab;
        var tab = document.getElementById(tabId);
        if (tab) tab.classList.add('active');

        if (ch.dataset.tab === 'setup') loadSetup();
        if (ch.dataset.tab === 'logs') loadLogs();
    });
});

// ===== Audio Player =====
var testAudio = new Audio();
testAudio.volume = 1.0;

// ===== Utility =====
function postJSON(url, data) {
    return fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: data ? JSON.stringify(data) : '{}'
    })
    .then(function(r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
    })
    .catch(function(e) {
        addLogSilent('Error: ' + e.message);
        return null;
    });
}

function setSpinner(el, show) {
    var spinner = el.querySelector('.spinner');
    var label = el.querySelector('.btn-label');
    if (spinner) spinner.classList.toggle('hidden', !show);
    if (label) label.classList.toggle('hidden', show);
    el.disabled = show;
}

// ===== Log =====
var logList = document.getElementById('log-list');

function addLogSilent(text) {
    var li = document.createElement('li');
    li.textContent = text;
    logList.prepend(li);
    while (logList.children.length > 100) logList.lastElementChild.remove();
}

function addLog(text) {
    addLogSilent(text);
    console.log(text);
}

function loadLogs() {
    fetch('/api/logs')
        .then(function(r) { return r.json(); })
        .then(function(logs) {
            logList.innerHTML = '';
            logs.reverse().forEach(function(l) { addLogSilent(l); });
        });
}

// ===== Toggles =====
var toggleTts = document.getElementById('toggle-tts');
var toggleAi = document.getElementById('toggle-ai');
var toggleTiktok = document.getElementById('toggle-tiktok');

var ttsBadge = document.getElementById('tts-badge');
var aiBadge = document.getElementById('ai-badge');
var tiktokBadge = document.getElementById('tiktok-badge');

function updateBadge(el, enabled, onText, offText) {
    el.textContent = enabled ? onText : offText;
    el.className = 'toggle-sub ' + (enabled ? 'on' : 'off');
}

toggleTts.addEventListener('click', async function(e) {
    if (e.target !== e.currentTarget) return;
    toggleTts.disabled = true;
    var res = await postJSON('/api/toggle_tts');
    if (res) {
        toggleTts.checked = res.tts_enabled;
        updateBadge(ttsBadge, res.tts_enabled, 'ACTIVADO', 'DESACTIVADO');
        addLog('TTS -> ' + (res.tts_enabled ? 'ON' : 'OFF'));
        refreshStats();
    }
    toggleTts.disabled = false;
});

toggleAi.addEventListener('click', async function(e) {
    if (e.target !== e.currentTarget) return;
    toggleAi.disabled = true;
    var res = await postJSON('/api/toggle_ai');
    if (res) {
        toggleAi.checked = res.ai_enabled;
        updateBadge(aiBadge, res.ai_enabled, 'ACTIVADO', 'DESACTIVADO');
        addLog('IA -> ' + (res.ai_enabled ? 'ON' : 'OFF'));
        refreshStats();
    }
    toggleAi.disabled = false;
});

toggleTiktok.addEventListener('click', async function(e) {
    if (e.target !== e.currentTarget) return;
    toggleTiktok.disabled = true;
    var res = await postJSON('/api/toggle_tiktok');
    if (res) {
        toggleTiktok.checked = res.tiktok_enabled;
        updateBadge(tiktokBadge, res.tiktok_enabled, 'ACTIVADO', 'PAUSADO');
        addLog('TikTok -> ' + (res.tiktok_enabled ? 'ON' : 'OFF'));
        refreshStats();
    }
    toggleTiktok.disabled = false;
});

// ===== Mode Toggle (Sim vs Real) =====
var btnToggleSim = document.getElementById('btn-toggle-sim');
var btnSimText = document.getElementById('btn-sim-text');
var modeLabel = document.getElementById('mode-label');
var modeDesc = document.getElementById('mode-desc');
var spinnerSim = document.getElementById('spinner-sim');

btnToggleSim.addEventListener('click', async function() {
    setSpinner(btnToggleSim, true);
    var res = await postJSON('/api/toggle_simulation');
    setSpinner(btnToggleSim, false);
    if (res) {
        updateModeUI(res.simulation);
        addLog('TikTok modo -> ' + (res.simulation ? 'Simulacion' : 'Real'));
        refreshStats();
    }
});

function updateModeUI(isSim) {
    if (isSim) {
        modeLabel.textContent = 'Simulacion';
        modeLabel.className = 'mode-value sim';
        modeDesc.textContent = 'Eventos generados automaticamente';
        btnSimText.textContent = 'Cambiar a Real';
    } else {
        modeLabel.textContent = 'TikTok Real';
        modeLabel.className = 'mode-value real';
        modeDesc.textContent = 'Conectado al live de TikTok';
        btnSimText.textContent = 'Cambiar a Simulacion';
    }
}

// ===== TTS Config =====
var ttsEngine = document.getElementById('tts-engine');
var ttsVoice = document.getElementById('tts-voice');
var ttsVoiceSearch = document.getElementById('tts-voice-search');
var toggleBlend = document.getElementById('toggle-blend');
var ttsBlend = document.getElementById('tts-blend');
var ttsSpeed = document.getElementById('tts-speed');
var speedValueEl = document.getElementById('speed-value');
var ttsPitch = document.getElementById('tts-pitch');
var pitchValueEl = document.getElementById('pitch-value');
var ttsVolume = document.getElementById('tts-volume');
var volumeValueEl = document.getElementById('volume-value');
var ttsLang = document.getElementById('tts-lang');
var ttsTestText = document.getElementById('tts-test-text');
var btnTestTts = document.getElementById('btn-test-tts');
var kokoroModel = document.getElementById('kokoro-model');
var btnPreviewVoice = document.getElementById('btn-preview-voice');
var voiceCountEl = document.getElementById('voice-count');

var allVoices = [];
var currentVoice = '';

function updateEngineUI(engine) {
    var kOpts = document.querySelectorAll('.kokoro-opt');
    kOpts.forEach(function(el) {
        el.classList.toggle('hidden', engine !== 'kokoro');
    });
}

function populateVoices(voices, selectedVoice) {
    allVoices = voices || [];
    currentVoice = selectedVoice || '';
    voiceCountEl.textContent = allVoices.length + ' voces';
    renderVoiceOptions();
}

function renderVoiceOptions(filter) {
    ttsVoice.innerHTML = '';
    var filtered = allVoices;
    if (filter) {
        var q = filter.toLowerCase();
        filtered = allVoices.filter(function(v) { return v.toLowerCase().indexOf(q) !== -1; });
    }
    filtered.forEach(function(v) {
        var opt = document.createElement('option');
        opt.value = v;
        opt.textContent = v;
        if (v === currentVoice) opt.selected = true;
        ttsVoice.appendChild(opt);
    });
    if (filtered.length === 0) {
        var opt = document.createElement('option');
        opt.value = '';
        opt.textContent = 'Sin resultados';
        opt.disabled = true;
        ttsVoice.appendChild(opt);
    }
}

ttsVoiceSearch.addEventListener('input', function() {
    renderVoiceOptions(ttsVoiceSearch.value);
});

ttsVoice.addEventListener('change', async function() {
    var voice = ttsVoice.value;
    if (!voice) return;
    currentVoice = voice;
    var res = await postJSON('/api/set_tts_voice', { voice: voice });
    if (res && res.success) addLog('TTS voz -> ' + voice);
});

ttsEngine.addEventListener('change', async function() {
    updateEngineUI(ttsEngine.value);
    var res = await postJSON('/api/set_tts_engine', { engine: ttsEngine.value });
    if (res && res.success) {
        addLog('TTS motor -> ' + ttsEngine.value);
        populateVoices(res.status.kokoro_voices, res.status.voice);
        loadPresetList();
    }
});

toggleBlend.addEventListener('change', function() {
    ttsBlend.disabled = !toggleBlend.checked;
    if (!toggleBlend.checked) {
        postJSON('/api/set_tts_voice_blend', { blend: '' });
        addLog('TTS blend -> desactivado');
    }
});

ttsBlend.addEventListener('change', async function() {
    if (toggleBlend.checked) {
        var res = await postJSON('/api/set_tts_voice_blend', { blend: ttsBlend.value });
        if (res && res.success) addLog('TTS blend -> ' + ttsBlend.value);
    }
});

ttsSpeed.addEventListener('input', function() { speedValueEl.textContent = parseFloat(ttsSpeed.value).toFixed(1); });
ttsSpeed.addEventListener('change', async function() {
    var speed = parseFloat(ttsSpeed.value);
    var res = await postJSON('/api/set_tts_speed', { speed: speed });
    if (res && res.success) addLog('TTS velocidad -> ' + speed.toFixed(1) + 'x');
});

ttsPitch.addEventListener('input', function() { pitchValueEl.textContent = parseInt(ttsPitch.value); });
ttsPitch.addEventListener('change', async function() {
    var pitch = parseInt(ttsPitch.value);
    var res = await postJSON('/api/set_tts_pitch', { pitch: pitch });
    if (res && res.success) addLog('TTS pitch -> ' + pitch + ' st');
});

ttsVolume.addEventListener('input', function() { volumeValueEl.textContent = parseFloat(ttsVolume.value).toFixed(1); });
ttsVolume.addEventListener('change', async function() {
    var vol = parseFloat(ttsVolume.value);
    var res = await postJSON('/api/set_tts_volume', { volume: vol });
    if (res && res.success) addLog('TTS volumen -> ' + vol.toFixed(1) + 'x');
});

kokoroModel.addEventListener('change', async function() {
    var prevModel = kokoroModel.dataset.current || 'fp16';
    addLog('Cambiando modelo Kokoro...');
    var res = await postJSON('/api/set_kokoro_model', { model: kokoroModel.value });
    if (res && res.success) {
        kokoroModel.dataset.current = kokoroModel.value;
        addLog('Modelo Kokoro -> ' + kokoroModel.value);
        populateVoices(res.status.kokoro_voices, res.status.voice);
    } else {
        addLog('Error al cambiar modelo, revirtiendo a ' + prevModel);
        kokoroModel.value = prevModel;
    }
});

ttsLang.addEventListener('change', async function() {
    var res = await postJSON('/api/set_tts_lang', { lang: ttsLang.value });
    if (res && res.success) addLog('TTS idioma -> ' + ttsLang.value);
});

// Voice preview
btnPreviewVoice.addEventListener('click', async function() {
    var voice = ttsVoice.value;
    if (!voice) return;
    setSpinner(btnPreviewVoice, true);
    var res = await postJSON('/api/preview_voice', { voice: voice });
    setSpinner(btnPreviewVoice, false);
    if (res && res.filename) {
        addLog('Preview voz: ' + voice);
        testAudio.src = '/audio/' + res.filename;
        testAudio.currentTime = 0;
        testAudio.play().catch(function(){});
    }
});

// Test TTS
btnTestTts.addEventListener('click', async function() {
    setSpinner(btnTestTts, true);
    var res = await postJSON('/api/test_tts', { text: ttsTestText.value });
    setSpinner(btnTestTts, false);
    if (!res) {
        addLog('Error de conexion. Verifica que main.py este corriendo.');
    } else if (res.filename) {
        addLog('TTS generado: ' + res.filename + ' - reproduciendo...');
        testAudio.src = '/audio/' + res.filename;
        testAudio.currentTime = 0;
        testAudio.play().catch(function(err) { addLog('No se pudo reproducir: ' + err.message); });
    } else {
        addLog('Error TTS: revisa logs del servidor');
    }
});

// ===== Presets =====
var presetName = document.getElementById('preset-name');
var presetSelect = document.getElementById('preset-select');

async function loadPresetList() {
    try {
        var r = await fetch('/api/tts_presets');
        var presets = await r.json();
        presetSelect.innerHTML = '<option value="">-- Cargar preset --</option>';
        Object.keys(presets).sort().forEach(function(name) {
            var opt = document.createElement('option');
            opt.value = name;
            opt.textContent = name;
            presetSelect.appendChild(opt);
        });
    } catch(e) { console.error(e); }
}

document.getElementById('btn-save-preset').addEventListener('click', async function() {
    var name = presetName.value.trim();
    if (!name) { addLog('Escribe un nombre para el preset'); return; }
    var res = await postJSON('/api/save_preset', { name: name });
    if (res && res.success) {
        addLog('Preset guardado: ' + name);
        presetName.value = '';
        loadPresetList();
    }
});

document.getElementById('btn-load-preset').addEventListener('click', async function() {
    var name = presetSelect.value;
    if (!name) { addLog('Selecciona un preset'); return; }
    var res = await postJSON('/api/load_preset', { name: name });
    if (res && res.success) {
        addLog('Preset cargado: ' + name);
        var s = res.status;
        if (s.engine) { ttsEngine.value = s.engine; updateEngineUI(s.engine); }
        if (s.voice) { currentVoice = s.voice; ttsVoiceSearch.value = ''; renderVoiceOptions(); }
        if (s.voice_blend) {
            ttsBlend.value = s.voice_blend;
            toggleBlend.checked = true;
            ttsBlend.disabled = false;
        } else {
            ttsBlend.value = '';
            toggleBlend.checked = false;
            ttsBlend.disabled = true;
        }
        if (s.speed !== undefined) { ttsSpeed.value = s.speed; speedValueEl.textContent = s.speed.toFixed(1); }
        if (s.lang) ttsLang.value = s.lang;
        populateVoices(s.kokoro_voices, s.voice);
    }
});

document.getElementById('btn-delete-preset').addEventListener('click', async function() {
    var name = presetSelect.value;
    if (!name) { addLog('Selecciona un preset para eliminar'); return; }
    if (!confirm('Eliminar preset "' + name + '"?')) return;
    var res = await postJSON('/api/delete_preset', { name: name });
    if (res && res.success) {
        addLog('Preset eliminado: ' + name);
        loadPresetList();
    }
});

// ===== Dashboard Actions =====
document.getElementById('btn-gift').addEventListener('click', async function() {
    await postJSON('/api/simulate_gift', { user: 'Admin', gift: 'Panda' });
    addLog('Regalo simulado enviado.');
});

document.getElementById('btn-message').addEventListener('click', async function() {
    await postJSON('/api/test_message', { user: 'Admin', text: 'Hola desde el panel' });
    addLog('Mensaje de prueba enviado.');
});

// ===== Setup =====
function loadSetup() {
    var grid = document.getElementById('setup-grid');
    grid.innerHTML = '<div class="spinner-lg"></div>';
    fetch('/api/setup_status')
        .then(function(r) { return r.json(); })
        .then(renderSetup)
        .catch(function() {
            grid.innerHTML = '<p style="color:var(--red)">Error al cargar estado del sistema.</p>';
        });
}

function renderSetup(data) {
    var grid = document.getElementById('setup-grid');
    var items = [
        { label: 'Kokoro FP16', ok: data.kokoro_fp16, value: data.kokoro_fp16 ? 'Modelo encontrado' : 'No encontrado' },
        { label: 'Kokoro FP32', ok: data.kokoro_fp32, value: data.kokoro_fp32 ? 'Modelo encontrado' : 'No encontrado' },
        { label: 'Kokoro Voces', ok: data.kokoro_voices, value: data.kokoro_voices ? 'Archivo de voces OK' : 'No encontrado' },
        { label: 'Piper Modelo', ok: data.piper_model, value: data.piper_model ? 'Modelo encontrado' : 'No encontrado' },
        { label: 'Groq API Key', ok: data.groq_configured, value: data.groq_configured ? 'Configurada (' + data.groq_model + ')' : 'No configurada', isWarn: !data.groq_configured },
        { label: 'TikTokLive', ok: data.tts_enabled || true, value: data.tts_enabled ? 'Instalado' : 'No instalado', isWarn: !data.tts_enabled, actualOk: data.tts_enabled },
        { label: 'Usuario TikTok', ok: true, value: data.tiktok_username || 'No configurado', isWarn: !data.tiktok_username || data.tiktok_username === 'demo_user', actualOk: data.tiktok_username && data.tiktok_username !== 'demo_user' },
        { label: 'TTS Engine', ok: true, value: data.tts_engine ? data.tts_engine.toUpperCase() : 'kokoro' },
    ];

    // Fix TikTokLive check
    items[5].ok = data.TikTokLive_installed;
    items[5].value = data.TikTokLive_installed ? 'Instalado' : 'No instalado (pip install TikTokLive)';
    items[5].isWarn = !data.TikTokLive_installed;

    grid.innerHTML = items.map(function(item) {
        var ok = item.actualOk !== undefined ? item.actualOk : item.ok;
        var cls = ok ? 'ok' : (item.isWarn ? 'warn' : 'fail');
        return '<div class="setup-item">'
            + '<div class="setup-icon ' + cls + '"></div>'
            + '<div class="setup-info">'
            + '<span class="setup-label">' + item.label + '</span>'
            + '<span class="setup-value">' + item.value + '</span>'
            + '</div></div>';
    }).join('');
}

// ===== Stats Refresh =====
function formatUptime(seconds) {
    if (seconds < 60) return seconds + 's';
    var m = Math.floor(seconds / 60);
    if (m < 60) return m + 'm';
    var h = Math.floor(m / 60);
    m = m % 60;
    return h + 'h ' + m + 'm';
}

function refreshStats() {
    fetch('/api/stats')
        .then(function(r) { return r.json(); })
        .then(function(s) {
            document.getElementById('stat-messages').textContent = s.messages;
            document.getElementById('stat-gifts').textContent = s.gifts;
            document.getElementById('stat-likes').textContent = s.likes;
            document.getElementById('stat-joins').textContent = s.joins;
            document.getElementById('stat-ai').textContent = s.ai_replies;
            document.getElementById('stat-tts').textContent = s.tts_played;
            document.getElementById('stat-uptime').textContent = formatUptime(s.uptime);
            updateModeUI(s.tiktok_mode === 'simulacion');
        });
}

// ===== SSE =====
var evtSource = new EventSource('/stream');
evtSource.onmessage = function(e) {
    try {
        var payload = JSON.parse(e.data);
        if (payload.type === 'log') {
            addLogSilent(payload.data.message);
        } else if (payload.type === 'tiktok_event' && payload.data) {
            var d = payload.data;
            var user = d.user || 'anon';
            if (d.type === 'message') {
                addChatMsg(user, d.text, false);
            } else if (d.type === 'gift') {
                addChatMsg('GIFT', user + ' envió ' + (d.gift || '?') + ' x' + (d.amount || 1), false);
            }
        } else if (payload.type === 'overlay_message' && payload.data) {
            var isAI = payload.data.original_user ? true : false;
            addChatMsg(payload.data.user, payload.data.text, isAI);
        }
    } catch(err) { console.error(err); }
};
evtSource.onerror = function() { console.error('SSE desconectado'); };

// ===== Init =====
fetch('/api/status')
    .then(function(r) { return r.json(); })
    .then(function(s) {
        toggleTts.checked = s.tts_enabled;
        toggleAi.checked = s.ai_enabled;
        toggleTiktok.checked = s.tiktok_enabled;
        updateBadge(ttsBadge, s.tts_enabled, 'ACTIVADO', 'DESACTIVADO');
        updateBadge(aiBadge, s.ai_enabled, 'ACTIVADO', 'DESACTIVADO');
        updateBadge(tiktokBadge, s.tiktok_enabled, 'ACTIVADO', 'PAUSADO');
    });

fetch('/api/tts_status')
    .then(function(r) { return r.json(); })
    .then(function(status) {
        if (status.engine) { ttsEngine.value = status.engine; updateEngineUI(status.engine); }
        if (status.speed !== undefined) { ttsSpeed.value = status.speed; speedValueEl.textContent = status.speed.toFixed(1); }
        if (status.lang) ttsLang.value = status.lang;
        if (status.pitch !== undefined) { ttsPitch.value = status.pitch; pitchValueEl.textContent = parseInt(status.pitch); }
        if (status.volume !== undefined) { ttsVolume.value = status.volume; volumeValueEl.textContent = status.volume.toFixed(1); }
        if (status.kokoro_model) { kokoroModel.value = status.kokoro_model; kokoroModel.dataset.current = status.kokoro_model; }
        if (status.voice_blend) {
            ttsBlend.value = status.voice_blend;
            toggleBlend.checked = true;
            ttsBlend.disabled = false;
        }
        populateVoices(status.kokoro_voices, status.voice);
    });

refreshStats();
setInterval(refreshStats, 10000);
loadPresetList();
loadLogs();
loadSpamConfig();
loadTheme();

// ===== Spam Config =====
var toggleSpam = document.getElementById('toggle-spam');
var spamRate = document.getElementById('spam-rate');
var spamWindow = document.getElementById('spam-window');
var spamDup = document.getElementById('spam-dup');
var bannedInput = document.getElementById('banned-input');
var bannedTags = document.getElementById('banned-tags');

function loadSpamConfig() {
    fetch('/api/spam_config')
        .then(function(r) { return r.json(); })
        .then(function(cfg) {
            toggleSpam.checked = cfg.enabled;
            spamRate.value = cfg.rate_limit;
            spamWindow.value = cfg.window;
            spamDup.value = cfg.dup_window;
            renderBannedTags(cfg.banned_words);
        });
}

function renderBannedTags(words) {
    bannedTags.innerHTML = '';
    (words || []).forEach(function(w) {
        var tag = document.createElement('span');
        tag.className = 'banned-tag';
        tag.innerHTML = w + '<span class="tag-remove" data-word="' + w + '">&times;</span>';
        bannedTags.appendChild(tag);
    });
}

toggleSpam.addEventListener('click', async function(e) {
    if (e.target !== e.currentTarget) return;
    toggleSpam.disabled = true;
    var res = await postJSON('/api/spam_toggle');
    if (res !== null) {
        toggleSpam.checked = res.enabled;
        addLog('Anti-spam -> ' + (res.enabled ? 'ON' : 'OFF'));
    }
    toggleSpam.disabled = false;
});

spamRate.addEventListener('change', function() { saveSpamConfig(); });
spamWindow.addEventListener('change', function() { saveSpamConfig(); });
spamDup.addEventListener('change', function() { saveSpamConfig(); });

function saveSpamConfig() {
    postJSON('/api/spam_set', {
        rate_limit: parseInt(spamRate.value),
        window: parseInt(spamWindow.value),
        dup_window: parseInt(spamDup.value),
    });
}

document.getElementById('btn-add-banned').addEventListener('click', async function() {
    var word = bannedInput.value.trim();
    if (!word) return;
    var res = await postJSON('/api/banned_words', { word: word });
    if (res && res.success) {
        bannedInput.value = '';
        renderBannedTags(res.words);
        addLog('Palabra baneada: ' + word);
    }
});

bannedInput.addEventListener('keydown', function(e) {
    if (e.key === 'Enter') document.getElementById('btn-add-banned').click();
});

bannedTags.addEventListener('click', function(e) {
    if (e.target.classList.contains('tag-remove')) {
        var word = e.target.dataset.word;
        fetch('/api/banned_words', {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ word: word })
        })
        .then(function(r) { return r.json(); })
        .then(function(res) {
            if (res.success) {
                renderBannedTags(res.words);
                addLog('Palabra eliminada: ' + word);
            }
        });
    }
});

// ===== Themes =====
function loadTheme() {
    var saved = localStorage.getItem('tts-theme') || 'discord';
    applyTheme(saved);
}

function applyTheme(theme) {
    document.body.className = document.body.className.replace(/theme-\w+/g, '').trim();
    if (theme !== 'discord') document.body.classList.add('theme-' + theme);
    document.querySelectorAll('.theme-btn').forEach(function(btn) {
        btn.classList.toggle('active', btn.dataset.theme === theme);
    });
    localStorage.setItem('tts-theme', theme);
}

document.querySelectorAll('.theme-btn').forEach(function(btn) {
    btn.addEventListener('click', function() {
        applyTheme(btn.dataset.theme);
    });
});

// ===== Export / Import =====
document.getElementById('btn-export').addEventListener('click', async function() {
    try {
        var r = await fetch('/api/export_config');
        var data = await r.json();
        var blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        var url = URL.createObjectURL(blob);
        var a = document.createElement('a');
        a.href = url;
        a.download = 'tiktok-ai-config-' + new Date().toISOString().slice(0,10) + '.json';
        a.click();
        URL.revokeObjectURL(url);
        addLog('Configuracion exportada.');
    } catch(e) {
        addLog('Error al exportar: ' + e.message);
    }
});

document.getElementById('import-file').addEventListener('change', async function() {
    var file = this.files[0];
    if (!file) return;
    try {
        var text = await file.text();
        var data = JSON.parse(text);
        var res = await postJSON('/api/import_config', data);
        if (res && res.success) {
            addLog('Configuracion importada correctamente. Recarga la pagina para ver todos los cambios.');
            setTimeout(function() { location.reload(); }, 1500);
        }
    } catch(e) {
        addLog('Error al importar: ' + e.message);
    }
    this.value = '';
});
