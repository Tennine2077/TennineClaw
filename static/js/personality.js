// ============================================================
// TennineClaw - 人格管理 + 技能装备 前端逻辑
// ============================================================

// ── 状态 ──
var personalityState = {
    traits: { openness: 50, conscientiousness: 50, extraversion: 50, agreeableness: 50, neuroticism: 50 },
    style: { formality: 50, humor: 50, conciseness: 50, enthusiasm: 50, technical_depth: 50 },
    prefs: { decision_style: 'balanced', risk_tolerance: 50, collaboration_level: 50 },
    equippedSkills: [],
    registry: [],
    templates: {},
    customTemplates: {},
};

// ── 面板开关 ──

async function apiDelete(path) {
    const res = await fetch(path, { method: 'DELETE' });
    return res.json();
}

async function apiGet(path) {
    const res = await fetch(path);
    return res.json();
}

async function apiPost(path, data) {
    const res = await fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data || {}) });
    return res.json();
}

async function apiPut(path, data) {
    const res = await fetch(path, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data || {}) });
    return res.json();
}

function closeModal() {
    const m = document.getElementById('personality-modal');
    if (m) m.classList.remove('active');
}

// ============================================================
// 文档加载完成后初始化
// ============================================================
document.addEventListener('DOMContentLoaded', function () {
    // 初始化雷达图 canvas
    const canvas = document.getElementById('radar-chart');
    if (canvas) {
        const parent = canvas.parentElement;
        canvas.width = Math.min(parent.clientWidth - 20, 280);
        canvas.height = canvas.width;
    }

    // 如果面板默认打开，加载数据
    const panel = document.getElementById('personality-panel');
    if (panel && panel.classList.contains('open')) {
        loadPersonalityData();
        loadSkillRegistry();
        loadEquippedSkills();
        loadTemplates();
    }
});

function showModal(title, content, buttons) {
    let m = document.getElementById('personality-modal');
    if (!m) {
        m = document.createElement('div');
        m.id = 'personality-modal';
        m.className = 'personality-modal';
        m.innerHTML = `<div class="modal-overlay" onclick="closeModal()" style="pointer-events:none;"></div>
            <div class="modal-content" style="z-index:10003; pointer-events:auto;">
                <div class="modal-header">
                    <span class="modal-title"></span>
                    <span class="modal-close" onclick="closeModal()">✕</span>
                </div>
                <div class="modal-body"></div>
                <div class="modal-footer"></div>
            </div>`;
        document.body.appendChild(m);
    }
    m.querySelector('.modal-title').textContent = title;
    m.querySelector('.modal-body').innerHTML = content;
    const footer = m.querySelector('.modal-footer');
    footer.innerHTML = '';
    if (buttons) {
        buttons.forEach(b => {
            const btn = document.createElement('button');
            btn.textContent = b.text;
            btn.className = b.class || '';
            btn.onclick = b.action || closeModal;
            footer.appendChild(btn);
        });
    }
    m.classList.add('active');
}

function showToast(msg, type = 'success') {
    const t = document.getElementById('personality-toast');
    if (!t) return;
    t.textContent = msg;
    t.className = 'personality-toast show ' + type;
    clearTimeout(t._timer);
    t._timer = setTimeout(() => { t.className = 'personality-toast'; }, 2500);
}

// ============================================================
// 数据加载
// ============================================================