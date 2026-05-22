// ============================================================
// TennineClaw - 技能管理下拉面板 (与主题切换按钮同款样式)
// ============================================================

var skillMgrAllPersonas = [];
var skillMgrEditMap = {};

function openSkillManagerModal() {
    Promise.all([
        fetch('/api/skills/registry').then(function(r) { if (!r.ok) throw new Error('HTTP '+r.status); return r.json(); }),
        fetch('/api/personality/templates/all').then(function(r) { if (!r.ok) return {}; return r.json(); })
    ])
    .then(function(results) {
        var skillsData = results[0];
        var personasData = results[1] || {};
        currentSkillsState.skills = (skillsData && skillsData.success) ? (skillsData.data || []) : [];
        var tmpl = personasData.data || personasData.templates || {};
        skillMgrAllPersonas = Object.keys(tmpl);
        skillMgrEditMap = {};
        renderDropdown();
    })
    .catch(function(e) {
        console.error('openSkillManagerModal error:', e);
        showToast('加载技能管理数据失败', 'error');
    });
}

function renderDropdown() {
    closeSkillMenuDropdown();

    var btn = document.getElementById('skillMenuBtn');
    if (!btn) return;
    var rect = btn.getBoundingClientRect();

    // ── Overlay ──
    var overlay = document.createElement('div');
    overlay.className = 'skill-menu-overlay';
    overlay.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;z-index:999;background:transparent;';
    overlay.addEventListener('click', function() { closeSkillMenuDropdown(); });
    document.body.appendChild(overlay);

    // ── Dropdown ──
    var menu = document.createElement('div');
    menu.className = 'skill-menu';
    menu.style.cssText = 'position:fixed;top:' + (rect.bottom + 4) + 'px;right:' + (window.innerWidth - rect.right) + 'px;width:420px;max-height:480px;overflow-y:auto;';
    menu.id = 'skillMenuDropdown';

    // Header
    var header = document.createElement('div');
    header.className = 'skill-menu-header';
    header.innerHTML = '<span>⚙️ 技能管理</span><span style="cursor:pointer;color:var(--text-muted);font-size:14px;" onclick="closeSkillMenuDropdown()">✕</span>';
    menu.appendChild(header);

    // Body
    var body = document.createElement('div');
    body.style.cssText = 'padding:4px 0;';

    var skills = currentSkillsState.skills || [];

    if (skills.length === 0) {
        var empty = document.createElement('div');
        empty.className = 'skill-menu-empty';
        empty.textContent = '暂无可用技能';
        body.appendChild(empty);
    } else {
        // 分组：自定义技能（is_builtin=false）在上，默认技能在下
        var customSkills = skills.filter(function(s) { return !s.is_builtin; });
        var defaultSkills = skills.filter(function(s) { return s.is_builtin; });

        // 渲染自定义技能
        if (customSkills.length > 0) {
            body.appendChild(createSectionHeader('🛠️ 自定义技能'));
            customSkills.forEach(function(s) {
                body.appendChild(renderSkillMenuItem(s));
            });
        }

        // 渲染默认技能
        if (defaultSkills.length > 0) {
            body.appendChild(createSectionHeader('📦 默认技能'));
            defaultSkills.forEach(function(s) {
                body.appendChild(renderSkillMenuItem(s));
            });
        }
    }

    menu.appendChild(body);

    // Footer — 导入按钮 + 保存按钮
    var footer = document.createElement('div');
    footer.className = 'skill-menu-footer';
    footer.innerHTML =
        '<button class="skill-menu-save-btn" style="flex:0 0 auto;background:var(--bg-tertiary,rgba(128,128,128,0.15));color:var(--text-primary);padding:8px 10px;border:1px dashed var(--border-color,#444);" onclick="showGitHubImport()">📥 从 GitHub 导入</button>' +
        '<button class="skill-menu-save-btn" onclick="saveSkillPersonaMapping()">💾 保存</button>';
    menu.appendChild(footer);

    document.body.appendChild(menu);
}

function createSectionHeader(text) {
    var div = document.createElement('div');
    div.style.cssText = 'font-size:11px;font-weight:600;color:var(--text-secondary,#888);padding:6px 14px 4px;letter-spacing:0.3px;';
    div.textContent = text;
    return div;
}

function renderSkillMenuItem(s) {
    var item = document.createElement('div');
    item.className = 'skill-menu-item';
    item.dataset.skillId = s.id;

    var usedBy = s.used_by_personas || [];
    var equippedIds = currentSkillsState.equippedIds || [];
    var isOn = equippedIds.indexOf(s.id) >= 0;

    // 使用状态：已装备时绿色圆点，否则灰色
    var statusDot = isOn
        ? '<span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:#22c55e;flex-shrink:0;"></span>'
        : '<span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:#666;flex-shrink:0;"></span>';

    item.innerHTML =
        '<div style="display:flex;align-items:center;gap:6px;flex:1;min-width:0;">' +
            statusDot +
            '<span class="skill-icon">' + (s.icon || '⚡') + '</span>' +
            '<span class="skill-name">' + (s.name || s.id) + '</span>' +
        '</div>' +
        '<div style="display:flex;align-items:center;gap:6px;flex-shrink:0;">' +
            '<span style="font-size:10px;color:var(--text-muted);">' + usedBy.length + '个角色</span>' +
            '<span class="skill-arrow">▶</span>' +
        '</div>';

    // ── hover: 弹出角色勾选浮层 ──
    item.addEventListener('mouseenter', function() {
        removeAllSubmenuPortals();
        showSubmenuPortal(s, item);
    });

    return item;
}

// ── 显示三级菜单（角色勾选浮层）──
function showSubmenuPortal(s, item) {
    document.querySelectorAll('.skill-menu-item.active').forEach(function(el) { el.classList.remove('active'); });
    item.classList.add('active');

    var portal = document.createElement('div');
    portal.id = 'submenu_portal_' + s.id;

    var itemRect = item.getBoundingClientRect();
    var portalLeft = itemRect.left - 248;
    if (portalLeft < 8) portalLeft = itemRect.right + 8;

    portal.style.cssText = 'position:fixed;left:' + portalLeft + 'px;top:' + (itemRect.top - 4) + 'px;' +
        'width:240px;max-height:320px;overflow-y:auto;z-index:10000;display:block;margin:0;padding:4px 0;' +
        'background:var(--bg-secondary,#1a1b26);border:1px solid var(--border-color,#2d2e42);border-radius:8px;' +
        'box-shadow:0 8px 24px rgba(0,0,0,0.5);color:var(--text-primary,#e0e0e0);';

    // 填充内容
    var editKey = s.id;
    var editedList = skillMgrEditMap[editKey];
    if (editedList === undefined) {
        editedList = (s.used_by_personas || []).slice();
        skillMgrEditMap[editKey] = editedList;
    }

    if (skillMgrAllPersonas.length === 0) {
        portal.innerHTML = '<div style="padding:12px;text-align:center;font-size:11px;color:var(--text-muted);">无可用角色</div>';
    } else {
        var subHtml = '<div style="font-size:11px;font-weight:600;color:var(--text-secondary);padding:6px 12px 4px;border-bottom:1px solid var(--border-light, rgba(128,128,128,0.15));">' + (s.name || s.id) + ' 的使用角色</div>';
        for (var pi = 0; pi < skillMgrAllPersonas.length; pi++) {
            var pname = skillMgrAllPersonas[pi];
            var checked = editedList.indexOf(pname) >= 0;
            subHtml += '<label class="skill-submenu-item">' +
                '<span class="check-icon">' + (checked ? '✅' : '⬜') + '</span>' +
                '<span style="font-size:12px;color:var(--text-primary);">' + pname + '</span>' +
                '<input type="checkbox" ' + (checked ? 'checked' : '') +
                ' onchange="toggleSkillPersona(\'' + s.id + '\',\'' + pname + '\')" style="display:none;">' +
                '</label>';
        }
        portal.innerHTML = subHtml;
    }

    // portal 不自动关闭，只在悬停其他技能或关闭下拉时消失
    document.body.appendChild(portal);
}

// ── GitHub 导入弹窗 ──
function showGitHubImport() {
    var html = '<div style="display:flex;flex-direction:column;gap:10px;">' +
        '<label style="font-size:12px;color:var(--text-secondary);">GitHub 仓库链接</label>' +
        '<input id="githubImportUrl" style="padding:8px 10px;border-radius:6px;border:1px solid var(--border-color);background:var(--bg-input);color:var(--text-primary);font-size:13px;"' +
        ' placeholder="例如: https://github.com/user/repo 或 user/repo">' +
        '<div style="font-size:10px;color:var(--text-muted);line-height:1.4;">' +
        '支持格式：<br>' +
        '• https://github.com/用户名/仓库名<br>' +
        '• 用户名/仓库名<br>' +
        '从仓库中读取 skill.json / description.md / guide.md 自动注册为自定义技能' +
        '</div></div>';

    showModal('📥 从 GitHub 导入技能', html, [
        { text: '取消', class: 'modal-btn-cancel', action: closeModal },
        { text: '导入', class: 'modal-btn-primary', action: function() {
            var url = document.getElementById('githubImportUrl')?.value?.trim();
            if (!url) { showToast('请输入 GitHub 链接', 'error'); return; }
            doGitHubImport(url);
        }}
    ]);
    setTimeout(function() {
        var inp = document.getElementById('githubImportUrl');
        if (inp) inp.focus();
    }, 100);
}

function doGitHubImport(githubUrl) {
    showToast('⏳ 正在从 GitHub 导入技能...', 'info');
    fetch('/api/skills/import-from-github', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ github_url: githubUrl })
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (data.success) {
            showToast(data.message || '✅ 技能导入成功', 'success');
            closeModal();
            // 刷新技能列表
            return fetch('/api/skills/registry').then(function(r) { return r.json(); });
        } else {
            showToast('❌ ' + (data.detail || data.message || '导入失败'), 'error');
        }
    })
    .then(function(rd) {
        if (rd && rd.success && rd.data) {
            currentSkillsState.skills = rd.data;
            // 同时刷新 equipped skills
            return fetch('/api/personality/equipped-skills').then(function(r) { if (!r.ok) return {}; return r.json(); });
        }
    })
    .then(function(eqData) {
        if (eqData) {
            currentSkillsState.equippedIds = eqData.equipped_ids || [];
        }
        // 重新渲染
        renderDropdown();
        if (typeof renderSkillsCompact === 'function') {
            renderSkillsCompact();
        }
    })
    .catch(function(e) {
        console.error('GitHub import error:', e);
        showToast('❌ 导入失败: ' + (e.message || '网络错误'), 'error');
    });
}

// ── 移除所有三级菜单 ──
function removeAllSubmenuPortals() {
    var portals = document.querySelectorAll('[id^="submenu_portal_"]');
    for (var i = 0; i < portals.length; i++) {
        portals[i].remove();
    }
}

function toggleSkillPersona(skillId, personaName) {
    var list = skillMgrEditMap[skillId];
    if (!list) {
        var skills = currentSkillsState.skills || [];
        for (var i = 0; i < skills.length; i++) {
            if (skills[i].id === skillId) {
                list = (skills[i].used_by_personas || []).slice();
                skillMgrEditMap[skillId] = list;
                break;
            }
        }
    }
    if (!list) return;
    var idx = list.indexOf(personaName);
    if (idx >= 0) { list.splice(idx, 1); } else { list.push(personaName); }
}

// 全局监听 checkbox 变化
document.addEventListener('change', function(e) {
    if (e.target && e.target.type === 'checkbox' && e.target.closest('[id^="submenu_portal_"]')) {
        var label = e.target.closest('.skill-submenu-item');
        if (label) {
            var icon = label.querySelector('.check-icon');
            if (icon) icon.textContent = e.target.checked ? '✅' : '⬜';
        }
    }
});

function saveSkillPersonaMapping() {
    var keys = Object.keys(skillMgrEditMap);
    if (keys.length === 0) { showToast('没有需要保存的更改'); return; }

    var promises = [];
    for (var ki = 0; ki < keys.length; ki++) {
        var skId = keys[ki];
        var personaList = skillMgrEditMap[skId];
        var p = fetch('/api/skills/' + encodeURIComponent(skId) + '/personas', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ persona_names: personaList })
        }).then(function(r) { return r.json(); });
        promises.push(p);
    }

    Promise.all(promises)
    .then(function() {
        // 同步：以技能端为准重建所有人格的 equipped_skill_ids
        return fetch('/api/skills/sync-personas', { method: 'POST' });
    })
    .then(function() {
        showToast('✅ 技能-角色关联已保存');
        // 不关闭 dropdown —— 刷新数据后重新渲染
        return Promise.all([
            fetch('/api/skills/registry').then(function(r) { return r.json(); }),
            fetch('/api/personality/equipped-skills').then(function(r) { if (!r.ok) return {}; return r.json(); })
        ]);
    })
    .then(function(results) {
        var rd = results[0];
        var eqData = results[1] || {};

        if (rd && rd.success && rd.data) {
            currentSkillsState.skills = rd.data;
            skillMgrEditMap = {};
        }

        currentSkillsState.equippedIds = eqData.equipped_ids || [];
        // 重新渲染 dropdown（更新绿点状态）+ 侧边栏
        renderDropdown();
        if (typeof renderSkillsCompact === 'function') {
            renderSkillsCompact();
        }
    })
    .catch(function(e) {
        console.error('saveSkillPersonaMapping error:', e);
        showToast('❌ 保存失败', 'error');
    });
}

function closeSkillMenuDropdown() {
    removeAllSubmenuPortals();
    var menu = document.getElementById('skillMenuDropdown');
    if (menu) menu.remove();
    var overlays = document.querySelectorAll('.skill-menu-overlay');
    for (var i = 0; i < overlays.length; i++) overlays[i].remove();
}

// ── 初始化：为右上角技能管理按钮绑定点击事件 ──
document.addEventListener('DOMContentLoaded', function() {
    var btn = document.getElementById('skillMenuBtn');
    if (btn) {
        btn.addEventListener('click', function() {
            openSkillManagerModal();
        });
    }
});
