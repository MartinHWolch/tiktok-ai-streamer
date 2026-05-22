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
        if (ch.dataset.tab === 'rules') loadRules();
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
var voiceGender = 'all';

function getVoiceGender(voiceName) {
    if (!voiceName) return 'unknown';
    var parts = voiceName.split('_');
    if (parts.length >= 2) {
        var g = parts[0].slice(-1).toLowerCase();
        if (g === 'f') return 'female';
        if (g === 'm') return 'male';
    }
    var v = voiceName.toLowerCase();
    if (v.indexOf('_f_') !== -1 || v.startsWith('af_') || v.startsWith('bf_') || v.startsWith('cf_') || v.startsWith('df_') || v.startsWith('ef_') || v.startsWith('ff_') || v.startsWith('gf_') || v.startsWith('hf_') || v.startsWith('if_') || v.startsWith('jf_') || v.startsWith('kf_') || v.startsWith('lf_') || v.startsWith('mf_') || v.startsWith('nf_') || v.startsWith('of_') || v.startsWith('pf_') || v.startsWith('qf_') || v.startsWith('rf_') || v.startsWith('sf_') || v.startsWith('tf_') || v.startsWith('uf_') || v.startsWith('vf_') || v.startsWith('wf_') || v.startsWith('xf_') || v.startsWith('yf_') || v.startsWith('zf_')) return 'female';
    if (v.indexOf('_m_') !== -1 || v.startsWith('am_') || v.startsWith('bm_') || v.startsWith('cm_') || v.startsWith('dm_') || v.startsWith('em_') || v.startsWith('fm_') || v.startsWith('gm_') || v.startsWith('hm_') || v.startsWith('im_') || v.startsWith('jm_') || v.startsWith('km_') || v.startsWith('lm_') || v.startsWith('mm_') || v.startsWith('nm_') || v.startsWith('om_') || v.startsWith('pm_') || v.startsWith('qm_') || v.startsWith('rm_') || v.startsWith('sm_') || v.startsWith('tm_') || v.startsWith('um_') || v.startsWith('vm_') || v.startsWith('wm_') || v.startsWith('xm_') || v.startsWith('ym_') || v.startsWith('zm_')) return 'male';
    return 'unknown';
}

function updateEngineUI(engine) {
    var kOpts = document.querySelectorAll('.kokoro-opt');
    kOpts.forEach(function(el) {
        el.classList.toggle('hidden', engine !== 'kokoro');
    });
}

function populateVoices(voices, selectedVoice) {
    allVoices = voices || [];
    currentVoice = selectedVoice || '';
    voiceGender = 'all';
    document.querySelectorAll('.gender-btn').forEach(function(b) {
        b.classList.toggle('active', b.dataset.gender === 'all');
    });
    updateVoiceCount();
    renderVoiceOptions();
}

function updateVoiceCount() {
    var female = allVoices.filter(function(v) { return getVoiceGender(v) === 'female'; }).length;
    var male = allVoices.filter(function(v) { return getVoiceGender(v) === 'male'; }).length;
    var el = document.getElementById('voice-count');
    if (el) el.textContent = female + ' F | ' + male + ' M';
}

function renderVoiceOptions(filter) {
    var dropdown = document.getElementById('voice-dropdown');
    dropdown.innerHTML = '';

    var filtered = allVoices;

    if (voiceGender === 'female') {
        filtered = filtered.filter(function(v) { return getVoiceGender(v) === 'female'; });
    } else if (voiceGender === 'male') {
        filtered = filtered.filter(function(v) { return getVoiceGender(v) === 'male'; });
    }

    var q = (filter || '').toLowerCase();
    if (q) {
        filtered = filtered.filter(function(v) { return v.toLowerCase().indexOf(q) !== -1; });
    }

    if (filtered.length === 0) {
        var empty = document.createElement('div');
        empty.className = 'voice-option-empty';
        empty.textContent = 'Sin resultados';
        dropdown.appendChild(empty);
    } else {
        filtered.forEach(function(v) {
            var item = document.createElement('div');
            item.className = 'voice-option';
            if (v === currentVoice) item.classList.add('selected');
            var gender = getVoiceGender(v);
            var tag = gender === 'female' ? 'F' : (gender === 'male' ? 'M' : '');
            item.innerHTML = '<span>' + v + '</span>' + (tag ? '<span class="voice-gender-tag">' + tag + '</span>' : '');
            item.addEventListener('mousedown', function(e) {
                e.preventDefault();
                selectVoice(v);
            });
            dropdown.appendChild(item);
        });
    }
}

function selectVoice(voiceName) {
    currentVoice = voiceName;
    var input = document.getElementById('tts-voice-search');
    input.value = voiceName;
    input.dataset.selected = voiceName;
    closeDropdown();
    postJSON('/api/set_tts_voice', { voice: voiceName }).then(function(res) {
        if (res && res.success) addLog('TTS voz -> ' + voiceName);
    });
}

function openDropdown() {
    var dropdown = document.getElementById('voice-dropdown');
    dropdown.classList.add('open');
    var input = document.getElementById('tts-voice-search');
    input.select();
    renderVoiceOptions('');
}

function closeDropdown() {
    var dropdown = document.getElementById('voice-dropdown');
    dropdown.classList.remove('open');
}

// Toggle dropdown on input click
document.getElementById('tts-voice-search').addEventListener('click', function() {
    var dropdown = document.getElementById('voice-dropdown');
    if (dropdown.classList.contains('open')) {
        closeDropdown();
        if (currentVoice) ttsVoiceSearch.value = currentVoice;
    } else {
        openDropdown();
    }
});

// Filter on input
ttsVoiceSearch.addEventListener('input', function() {
    var dropdown = document.getElementById('voice-dropdown');
    if (!dropdown.classList.contains('open')) openDropdown();
    renderVoiceOptions(ttsVoiceSearch.value);
});

// Keyboard navigation
ttsVoiceSearch.addEventListener('keydown', function(e) {
    var dropdown = document.getElementById('voice-dropdown');
    var items = dropdown.querySelectorAll('.voice-option');
    var active = dropdown.querySelector('.voice-option.active');
    var idx = Array.from(items).indexOf(active);

    if (e.key === 'ArrowDown') {
        e.preventDefault();
        if (!dropdown.classList.contains('open')) { openDropdown(); return; }
        if (active) active.classList.remove('active');
        var next = idx + 1 < items.length ? idx + 1 : 0;
        items[next].classList.add('active');
        items[next].scrollIntoView({ block: 'nearest' });
    } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        if (!dropdown.classList.contains('open')) { openDropdown(); return; }
        if (active) active.classList.remove('active');
        var prev = idx - 1 >= 0 ? idx - 1 : items.length - 1;
        items[prev].classList.add('active');
        items[prev].scrollIntoView({ block: 'nearest' });
    } else if (e.key === 'Enter') {
        e.preventDefault();
        if (active) {
            selectVoice(active.textContent.replace(/\s[FM]$/, '').trim());
        } else if (items.length > 0) {
            selectVoice(items[0].textContent.replace(/\s[FM]$/, '').trim());
        }
    } else if (e.key === 'Escape') {
        closeDropdown();
        ttsVoiceSearch.value = currentVoice || '';
    }
});

// Blur - close dropdown and restore selection
ttsVoiceSearch.addEventListener('blur', function() {
    setTimeout(function() {
        closeDropdown();
        if (currentVoice) {
            ttsVoiceSearch.value = currentVoice;
        }
    }, 150);
});

// Close when clicking outside
document.addEventListener('click', function(e) {
    var container = document.getElementById('voice-select-container');
    if (container && !container.contains(e.target)) {
        closeDropdown();
        if (currentVoice) {
            ttsVoiceSearch.value = currentVoice;
        }
    }
});

document.querySelectorAll('.gender-btn').forEach(function(btn) {
    btn.addEventListener('click', function() {
        document.querySelectorAll('.gender-btn').forEach(function(b) { b.classList.remove('active'); });
        btn.classList.add('active');
        voiceGender = btn.dataset.gender;
        ttsVoiceSearch.value = '';
        renderVoiceOptions();
    });
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
    var voice = currentVoice || ttsVoiceSearch.value.trim();
    if (!voice || voice === 'Sin resultados') return;
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
        if (s.voice) { currentVoice = s.voice; ttsVoiceSearch.value = s.voice; document.getElementById('voice-dropdown').innerHTML = ''; }
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
        { label: 'TikTokLive', ok: data.TikTokLive_installed, value: data.TikTokLive_installed ? 'Instalado' : 'No instalado (pip install TikTokLive)', isWarn: !data.TikTokLive_installed },
        { label: 'Usuario TikTok', ok: true, value: data.tiktok_username || 'No configurado', isWarn: !data.tiktok_username || data.tiktok_username === 'demo_user' },
        { label: 'TTS Engine', ok: true, value: data.tts_engine ? data.tts_engine.toUpperCase() : 'kokoro' },
    ];

    grid.innerHTML = items.map(function(item) {
        var cls = item.ok ? 'ok' : (item.isWarn ? 'warn' : 'fail');
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

// ===== Live Chat Helpers =====
function addChatMsg(user, text, isAI) {
    var container = document.getElementById('live-chat');
    if (!container) return;
    var ph = container.querySelector('.chat-placeholder');
    if (ph) ph.remove();
    var div = document.createElement('div');
    div.className = 'chat-msg' + (isAI ? ' ai-msg' : '');
    div.innerHTML = '<span class="chat-user">' + escapeHtml(user) + '</span>'
        + '<span class="chat-text">' + escapeHtml(text) + '</span>';
    container.appendChild(div);
    while (container.children.length > 50) {
        container.firstElementChild.remove();
    }
    container.scrollTop = container.scrollHeight;
}

function escapeHtml(text) {
    var map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
    return String(text).replace(/[&<>"']/g, function(m) { return map[m]; });
}

// ===== SSE =====
var evtSource = new EventSource('/stream');
function sseOnMessage(e) {
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
}
function sseOnError() {
    console.error('SSE desconectado, reintentando en 3s...');
    evtSource.close();
    setTimeout(function() {
        evtSource = new EventSource('/stream');
        evtSource.onmessage = sseOnMessage;
        evtSource.onerror = sseOnError;
    }, 3000);
}
evtSource.onmessage = sseOnMessage;
evtSource.onerror = sseOnError;

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
        if (status.voice) {
            ttsVoiceSearch.value = status.voice;
        }
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

// ===== Event Rules =====
var actionCounter = 1;

function loadRules() {
    fetch('/api/event_rules')
        .then(function(r) { return r.json(); })
        .then(renderRules);
}

function renderRules(rules) {
    var grid = document.getElementById('rules-grid');
    if (!rules || !rules.length) {
        grid.innerHTML = '<p style="color:var(--text-muted);text-align:center;padding:20px">No hay reglas configuradas. Crea una abajo.</p>';
        return;
    }
    grid.innerHTML = rules.map(function(rule, i) {
        var triggerLabel = rule.trigger === 'gift' ? 'Regalo: ' + rule.trigger_value : 'Diamantes >= ' + rule.trigger_value;
        var actionsHtml = rule.actions.map(function(a) {
            if (a.type === 'tts') return '<span class="rule-action-tag tts-tag">TTS' + (a.voice_preset ? ' [' + a.voice_preset + ']' : '') + ': ' + escapeHtml((a.message || '').substring(0, 25)) + '</span>';
            if (a.type === 'emoji') return '<span class="rule-action-tag emoji-tag">' + escapeHtml(a.emojis || '🎉') + ' x' + (a.count || 10) + '</span>';
            return '<span class="rule-action-tag">' + a.type + '</span>';
        }).join('');
        return '<div class="rule-card">'
            + '<div class="rule-info">'
            + '<span class="rule-gift-name">' + escapeHtml(rule.name) + '</span>'
            + '<span style="font-size:11px;color:var(--text-muted)">' + escapeHtml(triggerLabel) + '</span>'
            + '<div class="rule-actions-list">' + actionsHtml + '</div>'
            + '</div>'
            + '<div class="rule-btns">'
            + '<button class="btn-sm-blurple rule-edit" data-index="' + i + '">Editar</button>'
            + '<button class="btn-sm-blurple rule-test" data-index="' + i + '">Probar</button>'
            + '<button class="btn-sm-danger rule-delete" data-index="' + i + '">Eliminar</button>'
            + '</div>'
            + '</div>';
    }).join('');

    document.querySelectorAll('.rule-delete').forEach(function(btn) {
        btn.addEventListener('click', function() {
            var idx = btn.dataset.index;
            if (!confirm('Eliminar esta regla?')) return;
            fetch('/api/event_rules/' + idx, { method: 'DELETE' })
                .then(function(r) { return r.json(); })
                .then(function(res) {
                    if (res.success) { renderRules(res.rules); addLog('Regla eliminada'); resetRuleForm(); }
                });
        });
    });

    document.querySelectorAll('.rule-test').forEach(function(btn) {
        btn.addEventListener('click', async function() {
            var idx = parseInt(btn.dataset.index);
            btn.disabled = true;
            btn.textContent = '...';
            addLog('Probando regla indice ' + idx + '...');
            try {
                var r = await fetch('/api/event_rules');
                var rules = await r.json();
                addLog('Reglas cargadas: ' + rules.length);
                var rule = rules[idx];
                if (rule) {
                    var gift = rule.trigger === 'gift' ? rule.trigger_value : 'TestGift';
                    var diamonds = rule.trigger === 'diamonds' ? parseInt(rule.trigger_value) || 0 : 0;
                    addLog('Disparando: gift=' + gift + ' diamonds=' + diamonds);
                    var res = await postJSON('/api/test_rule', { gift: gift, user: 'TestUser', diamonds: diamonds });
                    if (res) {
                        if (res.matched_rules && res.matched_rules.length > 0) {
                            addLog('Regla probada: ' + rule.name + ' - ' + res.matched_rules.length + ' reglas coincidieron');
                            res.matched_rules.forEach(function(m) {
                                addLog('  > ' + m.name + ': ' + m.actions.join(', '));
                            });
                        } else {
                            addLog('Regla probada: ' + rule.name + ' - NINGUNA regla coincidio (verifica el gatillo)');
                        }
                        if (!res.tts_enabled) addLog('  [!] TTS esta desactivado en el panel');
                        if (!res.tiktok_enabled) addLog('  [!] TikTok eventos estan pausados');
                    } else {
                        addLog('Error al probar regla (sin respuesta del servidor)');
                    }
                } else {
                    addLog('Regla no encontrada en indice ' + idx);
                }
            } catch(e) {
                addLog('Error probando regla: ' + e.message);
            }
            btn.disabled = false;
            btn.textContent = 'Probar';
        });
    });

    document.querySelectorAll('.rule-edit').forEach(function(btn) {
        btn.addEventListener('click', function() {
            var idx = parseInt(btn.dataset.index);
            fetch('/api/event_rules').then(function(r) { return r.json(); }).then(function(rules) {
                var rule = rules[idx];
                if (!rule) return;
                document.getElementById('rule-edit-index').value = idx;
                document.getElementById('rule-name').value = rule.name || '';
                document.getElementById('rule-trigger').value = rule.trigger || 'gift';
                document.getElementById('rule-trigger-value').value = rule.trigger_value || '';
                updateTriggerLabel();
                document.getElementById('rule-form-title').textContent = 'Editar Regla';
                document.getElementById('btn-cancel-edit').style.display = '';
                document.getElementById('btn-save-rule').textContent = 'Actualizar Regla';

                // Load actions
                var editor = document.getElementById('actions-editor');
                editor.querySelectorAll('.action-row:not(#action-row-template)').forEach(function(r) { r.remove(); });
                (rule.actions || []).forEach(function(a) { addActionRow(a); });
            });
        });
    });
}

function updateTriggerLabel() {
    var trigger = document.getElementById('rule-trigger').value;
    var label = document.getElementById('rule-trigger-label');
    var input = document.getElementById('rule-trigger-value');
    if (trigger === 'gift') {
        label.textContent = 'Nombre del Regalo';
        input.placeholder = 'ej: Rosa, Panda, Universo...';
    } else {
        label.textContent = 'Valor minimo en Diamantes';
        input.placeholder = 'ej: 100, 500, 1000...';
    }
}

document.getElementById('rule-trigger').addEventListener('change', updateTriggerLabel);

function createActionConfig(type, existingData) {
    var div = document.createElement('div');
    div.className = 'action-config';
    if (type === 'tts') {
        div.innerHTML = '<div style="display:flex;flex-direction:column;gap:6px;flex:1">'
            + '<input type="text" class="input-discord action-tts-msg" placeholder="Mensaje TTS..." value="' + escapeHtml(existingData.message || 'Gracias {user} por el {gift}!') + '">'
            + '<select class="input-discord action-tts-preset"><option value="">Voz por defecto</option></select>'
            + '</div>';
        // Load presets
        fetch('/api/tts_presets').then(function(r) { return r.json(); }).then(function(presets) {
            var sel = div.querySelector('.action-tts-preset');
            Object.keys(presets).sort().forEach(function(name) {
                var opt = document.createElement('option');
                opt.value = name;
                opt.textContent = name;
                if (name === (existingData.voice_preset || '')) opt.selected = true;
                sel.appendChild(opt);
            });
        });
    } else {
        div.innerHTML = '<div style="display:flex;gap:6px;flex:1">'
            + '<input type="text" class="input-discord action-emoji-list" placeholder="Emojis" value="' + escapeHtml(existingData.emojis || '🎉✨') + '" style="flex:1">'
            + '<input type="number" class="input-discord action-emoji-count" placeholder="Cantidad" value="' + (existingData.count || 10) + '" min="1" max="100" style="width:80px">'
            + '</div>';
    }
    return div;
}

function addActionRow(existing) {
    var editor = document.getElementById('actions-editor');
    var template = document.getElementById('action-row-template');
    var row = template.cloneNode(true);
    row.removeAttribute('id');
    row.style.display = '';

    var existingData = existing || {};
    var actionType = existingData.type || 'tts';
    var typeSel = row.querySelector('.action-type');
    typeSel.value = actionType;

    var configDiv = row.querySelector('.action-config');
    var newConfig = createActionConfig(actionType, existingData);
    configDiv.replaceWith(newConfig);

    typeSel.addEventListener('change', function() {
        var oldConfig = row.querySelector('.action-config');
        var newConfigDiv = createActionConfig(typeSel.value, {});
        oldConfig.replaceWith(newConfigDiv);
    });

    row.querySelector('.action-remove').addEventListener('click', function() {
        row.remove();
    });

    editor.appendChild(row);
}

function getActionsFromForm() {
    var rows = document.querySelectorAll('#actions-editor .action-row:not(#action-row-template)');
    var actions = [];
    rows.forEach(function(row) {
        var type = row.querySelector('.action-type').value;
        if (type === 'tts') {
            var msg = (row.querySelector('.action-tts-msg') || {}).value || '';
            var preset = (row.querySelector('.action-tts-preset') || {}).value || '';
            if (msg) actions.push({ type: 'tts', message: msg, voice_preset: preset });
        } else if (type === 'emoji') {
            var emojis = (row.querySelector('.action-emoji-list') || {}).value || '🎉';
            var count = parseInt((row.querySelector('.action-emoji-count') || {}).value || '10') || 10;
            if (emojis) actions.push({ type: 'emoji', emojis: emojis, count: count });
        }
    });
    return actions;
}

function resetRuleForm() {
    document.getElementById('rule-edit-index').value = '-1';
    document.getElementById('rule-name').value = '';
    document.getElementById('rule-trigger').value = 'gift';
    document.getElementById('rule-trigger-value').value = '';
    updateTriggerLabel();
    document.getElementById('rule-form-title').textContent = 'Nueva Regla';
    document.getElementById('btn-cancel-edit').style.display = 'none';
    document.getElementById('btn-save-rule').textContent = 'Guardar Regla';
    var editor = document.getElementById('actions-editor');
    editor.querySelectorAll('.action-row:not(#action-row-template)').forEach(function(r) { r.remove(); });
    addActionRow({ type: 'tts', message: 'Gracias {user} por el {gift}!' });
}

document.getElementById('btn-add-action').addEventListener('click', function() {
    addActionRow({ type: 'tts', message: 'Gracias {user} por el {gift}!' });
});

document.getElementById('btn-cancel-edit').addEventListener('click', function() {
    resetRuleForm();
});

document.getElementById('btn-save-rule').addEventListener('click', async function() {
    var name = document.getElementById('rule-name').value.trim();
    var trigger = document.getElementById('rule-trigger').value;
    var triggerVal = document.getElementById('rule-trigger-value').value.trim();
    if (!name) { addLog('Escribe un nombre para la regla'); return; }
    if (!triggerVal) { addLog('Especifica el valor del gatillo'); return; }
    var actions = getActionsFromForm();
    if (!actions.length) { addLog('Agrega al menos una accion'); return; }

    var rule = { name: name, trigger: trigger, trigger_value: triggerVal, actions: actions };
    var editIdx = parseInt(document.getElementById('rule-edit-index').value);

    var url = '/api/event_rules';
    var method = 'POST';
    if (editIdx >= 0) {
        url = '/api/event_rules/' + editIdx;
        method = 'PUT';
    }

    var res = await (method === 'POST'
        ? postJSON(url, rule)
        : fetch(url, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(rule) }).then(function(r) { return r.json(); }));

    if (res && res.success) {
        addLog('Regla guardada: ' + name);
        resetRuleForm();
        renderRules(res.rules);
    }
});

document.getElementById('btn-test-rule').addEventListener('click', async function() {
    var name = document.getElementById('rule-name').value.trim();
    var trigger = document.getElementById('rule-trigger').value;
    var triggerVal = document.getElementById('rule-trigger-value').value.trim();
    var actions = getActionsFromForm();
    if (!name || !triggerVal) { addLog('Completa nombre y gatillo'); return; }
    if (!actions.length) { addLog('Agrega al menos una accion. Acciones encontradas: ' + actions.length); return; }

    addLog('Probando regla: ' + name + ' (' + trigger + '=' + triggerVal + ') con ' + actions.length + ' acciones');
    var rule = { name: name, trigger: trigger, trigger_value: triggerVal, actions: actions };
    var saveRes = await postJSON('/api/event_rules', rule);
    if (!saveRes || !saveRes.success) { addLog('Error al guardar regla temporal'); return; }
    
    var gift = trigger === 'gift' ? triggerVal : 'TestGift';
    var diamonds = trigger === 'diamonds' ? parseInt(triggerVal) || 10 : 0;
    addLog('Enviando test: gift=' + gift + ' diamonds=' + diamonds);
    var testRes = await postJSON('/api/test_rule', { gift: gift, user: 'TestUser', diamonds: diamonds });
    if (testRes) {
        if (testRes.matched_rules && testRes.matched_rules.length > 0) {
            addLog('Regla probada: ' + name + ' - ' + testRes.matched_rules.length + ' reglas coincidieron');
            testRes.matched_rules.forEach(function(m) {
                addLog('  > ' + m.name + ': ' + m.actions.join(', '));
            });
        } else {
            addLog('Regla probada: ' + name + ' - NINGUNA regla coincidio. Revisa el gatillo.');
        }
        if (!testRes.tts_enabled) addLog('  [!] TTS esta desactivado. Activalo en el Dashboard.');
    } else {
        addLog('Error del servidor al probar regla');
    }
    loadRules();
});

// Auto-load when tab opened
(function() {
    var rulesChannel = document.querySelector('.channel[data-tab="rules"]');
    if (rulesChannel) {
        var loaded = false;
        rulesChannel.addEventListener('click', function() {
            loadRules();
            if (!loaded) { resetRuleForm(); loaded = true; }
        });
    }
})();
