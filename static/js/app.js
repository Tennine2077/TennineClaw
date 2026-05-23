
// ============================================================
// 角色池 (左侧浮动角色选择)
// ============================================================

/**
 * 创建并显示左侧浮动角色池
 * 替代原有的 modal 式角色选择
 * 点击角色悬停显示 soul.md 预览
 */
async function toggleRoleSubmenu() {
    // 如果已存在角色池，关闭它
    var existing = document.querySelector('.role-pool-overlay');
    if (existing) { existing.remove(); return; }

    try {
        var r = await fetch('/api/personality/templates/all');
        var data = await r.json();
        var templates = data.data || data.templates || {};
        var names = Object.keys(templates);
        if (names.length === 0) { showToast('没有可用的角色卡', 'error'); return; }

        // 创建覆盖层 + 角色池
        var overlay = document.createElement('div');
        overlay.className = 'role-pool-overlay';
        overlay.onclick = function(e) { if (e.target === overlay) overlay.remove(); };

        var pool = document.createElement('div');
        pool.className = 'role-pool';
        pool.onclick = function(e) { e.stopPropagation(); }; // 防止点击池内冒泡到 overlay

        // 头部
        var header = document.createElement('div');
        header.className = 'role-pool-header';
        header.innerHTML = '<span>🎭 选择角色卡</span><span class="role-pool-close" onclick="this.closest(\'.role-pool-overlay\').remove()">✕</span>';
        pool.appendChild(header);

        // 主体
        var body = document.createElement('div');
        body.className = 'role-pool-body';
        body.style.position = 'relative';

        names.forEach(function(name) {
            var t = templates[name];
            var isBuiltin = t.is_builtin === true;

            var item = document.createElement('div');
            item.className = 'role-pool-item';
            item.dataset.roleName = name;

            // 悬停显示 soul.md 预览
            var previewTimer = null;
            item.addEventListener('mouseenter', function(e) {
                clearTimeout(previewTimer);
                clearTimeout(window._previewHideTimer);
                previewTimer = setTimeout(function() {
                    showRolePreview(name, e.target);
                }, 400); // 400ms 延迟避免频繁请求
            });
            item.addEventListener('mouseleave', function() {
                clearTimeout(previewTimer);
                // 延迟 500ms 隐藏预览，给用户移到预览区域的时间
                window._previewHideTimer = setTimeout(function() {
                    hidePreview();
                }, 500);
            });

            // 点击应用角色
            item.addEventListener('click', function() {
                overlay.remove();
                applyRole(name);
            });

            item.innerHTML =
                '<span class="role-pool-item-icon">' + (t.icon || '🧑') + '</span>' +
                '<div class="role-pool-item-info">' +
                    '<div class="role-pool-item-name">' + name + '</div>' +
                    '<div class="role-pool-item-desc">' + (t.description || '') + '</div>' +
                '</div>' +
                (isBuiltin ? '<span class="role-pool-item-badge">内置</span>' : '');

            // 自定义角色添加删除按钮
            if (!isBuiltin) {
                var delBtn = document.createElement('span');
                delBtn.style.cssText = 'cursor:pointer; font-size:10px; padding:2px 6px; border-radius:4px; background:rgba(239,68,68,0.12); color:#ef4444; flex-shrink:0;';
                delBtn.textContent = '✖';
                delBtn.addEventListener('click', function(e) {
                    e.stopPropagation();
                    deleteRoleTemplate(name);
                });
                item.appendChild(delBtn);
            }

            body.appendChild(item);
        });

        // 添加自定义角色按钮
        var addBtn = document.createElement('div');
        addBtn.className = 'role-pool-add';
        addBtn.textContent = '+ 添加自定义角色';
        addBtn.addEventListener('click', function() {
            overlay.remove();
            showAddRoleForm();
        });
        body.appendChild(addBtn);

        pool.appendChild(body);
        overlay.appendChild(pool);
        document.body.appendChild(overlay);
    } catch(e) {
        console.error('toggleRoleSubmenu error:', e);
        showToast('加载角色列表失败', 'error');
    }
}

/**
 * 获取并显示角色 soul.md 浮动预览
 */
var _previewDiv = null;

function showRolePreview(roleName, targetEl) {
    // 创建预览浮层（首次）
    if (!_previewDiv) {
        _previewDiv = document.createElement('div');
        _previewDiv.className = 'floating-preview';
        document.body.appendChild(_previewDiv);
    }

    // 计算位置：显示在 targetEl 右侧
    var rect = targetEl.getBoundingClientRect();
    var left = rect.right + 12;
    var top = Math.max(4, rect.top - 10);
    // 避免超出右侧屏幕
    if (left + 320 > window.innerWidth) {
        left = rect.left - 332; // 改为左侧显示
    }
    // 避免超出底部
    if (top + 320 > window.innerHeight) {
        top = window.innerHeight - 330;
    }
    _previewDiv.style.left = left + 'px';
    _previewDiv.style.top = top + 'px';
    _previewDiv.innerHTML = '<div class="preview-loading">⏳ 加载中...</div>';
    _previewDiv.classList.add('visible');

    // 鼠标移到预览浮层内时，取消隐藏延时
    _previewDiv.onmouseenter = function() {
        clearTimeout(window._previewHideTimer);
    };
    _previewDiv.onmouseleave = function() {
        window._previewHideTimer = setTimeout(function() {
            hidePreview();
        }, 500);
    };

    // 异步获取 soul.md
    fetch('/api/personality/templates/' + encodeURIComponent(roleName) + '/soul')
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.success && data.content) {
                // 简化 Markdown 渲染：转义后支持简单换行
                var content = data.content
                    .replace(/&/g, '&amp;')
                    .replace(/</g, '&lt;')
                    .replace(/>/g, '&gt;')
                    .replace(/\n\n/g, '</p><p>')
                    .replace(/\n/g, '<br>')
                    .replace(/^# (.*$)/gm, '<h1>$1</h1>')
                    .replace(/^## (.*$)/gm, '<h2>$1</h2>')
                    .replace(/^### (.*$)/gm, '<h3>$1</h3>')
                    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
                _previewDiv.innerHTML = '<div style="font-size:11px; font-weight:600; color:var(--accent-primary); margin-bottom:4px;">📄 ' + roleName + ' · soul.md</div>' +
                    '<p>' + content + '</p>';
            } else {
                _previewDiv.innerHTML = '<div class="preview-error">该角色没有 soul.md 文件</div>';
            }
        })
        .catch(function() {
            _previewDiv.innerHTML = '<div class="preview-error">加载失败</div>';
        });
}

function hidePreview() {
    clearTimeout(window._previewHideTimer);
    if (_previewDiv) {
        _previewDiv.classList.remove('visible');
    }
}

// ============================================================
// 技能栏 - 水平 Flex-Wrap 排列
// ============================================================

/**
 * 重写 renderSkillsCompact: 改为水平 flex-wrap 排版
 * 每个技能一个小芯片，悬停显示技能详情预览
 */
function renderSkillsCompact() {
    const container = document.getElementById('skillsCompactList');
    const manageBtn = document.getElementById('manageSkillsBtn');
    if (!container) return;

    const skills = currentSkillsState.skills || [];
    const equippedIds = currentSkillsState.equippedIds || [];

    // 已启用的技能
    var equippedSkills = skills.filter(function(s) { return equippedIds.indexOf(s.id) >= 0; });
    var totalCount = skills.length;
    var equippedCount = equippedSkills.length;

    // 紧凑徽标：仅显示已装备技能数量，点击展开详情
    var html = '<div class="skills-compact-toggle" onclick="toggleSkillsExpand()">';
    html += '<span style="font-size:13px;">🛠️</span>';
    html += '<span style="font-size:13px; font-weight:600; color:var(--text-primary); margin-left:4px;">' + equippedCount + '</span>';
    html += '<span style="font-size:10px; color:var(--text-muted); margin-left:2px;">个技能</span>';
    html += '<span id="skillsExpandIcon" style="margin-left:auto; font-size:10px; color:var(--text-muted);">▶</span>';
    html += '</div>';

    // 展开详情面板（初始隐藏）
    html += '<div id="skillsExpandPanel" class="skills-expand-panel" style="display:none; margin-top:4px;">';

    equippedSkills.forEach(function(s) {
        var sq = "'";
        var escapedName = (s.name || s.id).replace(/'/g, '\'');
        var escapedDesc = (s.short_description || '').replace(/'/g, '\'');
        html += '<div class="skills-expand-item" data-skill-name="' + escapedName + '" data-skill-desc="' + escapedDesc + '" data-skill-id="' + s.id + '">';
        html += '<div class="skills-expand-item-top">';
        html += '<span style="font-size:14px; flex-shrink:0;">' + (s.icon || '⚡') + '</span>';
        html += '<span style="flex:1; font-size:12px; font-weight:500; color:var(--text-primary); margin-left:4px;">' + (s.name || s.id) + '</span>';
        html += '<span style="font-size:11px; padding:1px 6px; border-radius:8px; flex-shrink:0; background:rgba(34,197,94,0.2); color:#22c55e;">✓ 已启用</span>';
        html += '</div>';
        if (s.short_description) {
            html += '<div class="skills-expand-item-desc">' + s.short_description + '</div>';
        }
        html += '</div>';
    });

    html += '</div>';

    container.innerHTML = html;
    if (manageBtn) manageBtn.style.display = 'block';

    // 绑定技能悬停预览：鼠标移到技能项上时，在左侧显示 description
    var panel = document.getElementById('skillsExpandPanel');
    if (panel) {
        var skillPreviewTimer = null;
        panel.addEventListener('mouseover', function(e) {
            var item = e.target.closest('.skills-expand-item');
            if (!item) return;

            clearTimeout(skillPreviewTimer);
            clearTimeout(window._previewHideTimer);
            skillPreviewTimer = setTimeout(function() {
                var name = item.dataset.skillName || '未知技能';
                var desc = item.dataset.skillDesc || '暂无描述';
                // 异步获取完整 description.md（后端读取 description.md 文件）
                var skId = item.dataset.skillId ? [null, item.dataset.skillId] : null;
                if (skId && skId[1]) {
                    fetch('/api/skills/registry/' + encodeURIComponent(skId[1]) + '/detail')
                        .then(function(r) { return r.json(); })
                        .then(function(data) {
                            if (data.success && data.description) {
                                _previewDiv.innerHTML = '<div style="font-size:11px; font-weight:600; color:var(--accent-primary); margin-bottom:4px;">⚡ ' + name + '</div>' +
                                    '<div style="font-size:11px; color:var(--text-secondary); line-height:1.5;">' + data.description.replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br>') + '</div>';
                            }
                        })
                        .catch(function() {});
                }

                if (!_previewDiv) {
                    _previewDiv = document.createElement('div');
                    _previewDiv.className = 'floating-preview';
                    document.body.appendChild(_previewDiv);
                }

                // 定位：显示在技能项左侧
                var rect = item.getBoundingClientRect();
                var left = rect.left - 332;
                var top = Math.max(4, rect.top - 10);
                if (left < 4) {
                    // 左侧不够，改到右侧
                    left = rect.right + 12;
                }
                if (top + 320 > window.innerHeight) {
                    top = window.innerHeight - 330;
                }
                _previewDiv.style.left = left + 'px';
                _previewDiv.style.top = top + 'px';
                _previewDiv.innerHTML = '<div style="font-size:11px; font-weight:600; color:var(--accent-primary); margin-bottom:4px;">⚡ ' + name + '</div>' +
                    '<div style="font-size:11px; color:var(--text-secondary); line-height:1.5;">' + desc + '</div>';
                _previewDiv.classList.add('visible');

                _previewDiv.onmouseenter = function() {
                    clearTimeout(window._previewHideTimer);
                };
                _previewDiv.onmouseleave = function() {
                    window._previewHideTimer = setTimeout(function() {
                        hidePreview();
                    }, 500);
                };
            }, 400);
        });

        panel.addEventListener('mouseout', function(e) {
            var item = e.target.closest('.skills-expand-item');
            if (!item) return;

            clearTimeout(skillPreviewTimer);
            window._previewHideTimer = setTimeout(function() {
                hidePreview();
            }, 500);
        });
    }
}

/**
 * Toggle skills expand panel open/close
 */
window.toggleSkillsExpand = function() {
    var panel = document.getElementById('skillsExpandPanel');
    var icon = document.getElementById('skillsExpandIcon');
    if (!panel || !icon) return;
    var isOpen = panel.style.display !== 'none';
    panel.style.display = isOpen ? 'none' : 'block';
    icon.textContent = isOpen ? '▶' : '▼';
}

/**
 * 显示技能浮动预览
 */
function showSkillPreview(chip) {
    var skillName = chip.dataset.skillName || '未知技能';
    var desc = chip.dataset.skillDesc || '';
    var guide = chip.dataset.skillGuide || '';

    if (!_previewDiv) {
        _previewDiv = document.createElement('div');
        _previewDiv.className = 'floating-preview';
        document.body.appendChild(_previewDiv);
    }

    // 计算位置
    var rect = chip.getBoundingClientRect();
    var left = rect.left;
    var top = rect.bottom + 8;
    // 如果底部不够，改到上方
    if (top + 320 > window.innerHeight) {
        top = rect.top - 330;
    }
    // 如果右侧不够，向左偏移
    if (left + 320 > window.innerWidth) {
        left = window.innerWidth - 330;
    }
    if (left < 4) left = 4;

    _previewDiv.style.left = left + 'px';
    _previewDiv.style.top = top + 'px';

    var content = '<div style="font-size:11px; font-weight:600; color:var(--accent-primary); margin-bottom:4px;">⚡ ' + skillName + '</div>';
    if (desc) {
        content += '<div style="font-size:11px; color:var(--text-secondary); margin-bottom:4px;">' + desc + '</div>';
    }
    if (guide) {
        content += '<hr style="border:none; border-top:1px solid var(--border-color); margin:4px 0;">';
        content += '<div style="font-size:10px; color:var(--text-muted); max-height:200px; overflow-y:auto;">' +
            guide.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br>') +
            '</div>';
    }
    content += '</div>';

    _previewDiv.innerHTML = content;
    _previewDiv.classList.add('visible');

    _previewDiv.onmouseenter = function() {
        clearTimeout(window._previewHideTimer);
    };
    _previewDiv.onmouseleave = function() {
        window._previewHideTimer = setTimeout(function() {
            hidePreview();
        }, 500);
    };
}

/* ============================================================
   TennineClaw - 前端交互逻辑（ChatGPT 风格会话管理）
   ============================================================ */

document.addEventListener('DOMContentLoaded', () => {
    'use strict';

    // ============================================================
    // DOM 引用
    // ============================================================
    const $ = (id) => document.getElementById(id);
    const $$ = (sel) => document.querySelectorAll(sel);

    const el = {
        messagesContainer: $('messagesContainer'),
        welcomeMessage: $('welcomeMessage'),
        chatInput: $('chatInput'),
        sendBtn: $('sendBtn'),
        sessionTitle: $('sessionTitle'),
        smartBtn: $('smartBtn'),
        planBtn: $('planBtn'),

        themeToggle: $('themeToggle'),
        skillMenuBtn: $('skillMenuBtn'),

        // 左侧会话栏
        leftSidebar: $('leftSidebar'),
        sidebarToggle: $('sidebarToggle'),
        newChatBtn: $('newChatBtn'),
        sessionSearch: $('sessionSearch'),
        sessionList: $('sessionList'),

        // Plan 菜单
        planMenuPanel: $('planMenuPanel'),
        planExploreBtn: $('planExploreBtn'),
        planModifyBtn: $('planModifyBtn'),
        planExecuteBtn: $('planExecuteBtn'),
        planActionRow: $('planActionRow'),
        planResetBtn: $('planResetBtn'),
        planConfirmBtn: $('planConfirmBtn'),
        planStatus: $('planStatus'),

        // Composer
        microCount: $('microCount'),
        autoCount: $('autoCount'),
        manualCount: $('manualCount'),
        composerNotification: $('composerNotification'),

        // 快捷操作
        compactBtn: $('compactBtn'),
        statusBtn: $('statusBtn'),
        helpBtn: $('helpBtn'),

        // 环境
        envCurrentInfo: $('envCurrentInfo'),
        envCurrentName: $('envCurrentName'),
        envCurrentPath: $('envCurrentPath'),
        envCondaList: $('envCondaList'),
        envCreateInput: $('envCreateInput'),
        envCreateBtn: $('envCreateBtn'),

        // 模型切换
        modelSelect: $('modelSelect'),
        modelAddBtn: $('modelAddBtn'),
        modelDelBtn: $('modelDelBtn'),
        modelCfgBtn: $('modelCfgBtn'),

        // 可折叠面板
        envPanelToggle: $('envPanelToggle'),
        envPanelBody: $('envPanelBody'),

        // 打断
        interruptBtn: $('interruptBtn'),

        // Toast
        toastContainer: $('toastContainer'),
    };

    // ============================================================
    // 状态
    // ============================================================
    const state = {
        isLoading: false,
        isStreaming: false,
        planSelected: null,
        statusInterval: null,
        planCheckInterval: null,
        sessionListInterval: null,
        currentMode: '🧠 智能处理模式',
        abortController: null,
        sessions: [],           // 已保存的会话文件列表
        activeSessions: [],     // 活跃 registry session 列表
        currentActivePath: null, // 当前高亮的会话路径
        activeSessionId: 'default',  // 初始为默认会话，切换后更新
        sessionInputs: {},      // 保存每个 session 的输入框文字 { sessionId: text }
        _msgCounter: 0,         // 消息索引计数器（用于分支会话）
    };

    // ============================================================
    // Toast 通知
    // ============================================================
    function showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        el.toastContainer.appendChild(toast);
        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease forwards';
            setTimeout(() => toast.remove(), 300);
        }, 3500);
    }

    // ============================================================
    // 消息渲染
    // ============================================================
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function renderMarkdown(text) {
        // 使用 marked.js 解析 Markdown（支持 GFM）
        if (typeof marked !== "undefined" && marked.parse) {
            return marked.parse(text, { breaks: true, gfm: true });
        }
        // fallback: 如果 marked 未加载，返回纯文本
        var div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * 娓叉煋 Markdown 骞堕珮浜唬鐮佸潡锛堢敤浜庨潪娴佸紡鍦烘櫙锛?
     */
    function renderMarkdownWithHighlight(text) {
        if (typeof marked === "undefined" || !marked.parse) {
            var div = document.createElement("div");
            div.textContent = text;
            return div.innerHTML;
        }
        var html = marked.parse(text, { breaks: true, gfm: true });
        var temp = document.createElement("div");
        temp.innerHTML = html;
        if (typeof hljs !== "undefined" && hljs.highlightElement) {
            temp.querySelectorAll("pre code").forEach(function(block) {
                hljs.highlightElement(block);
            });
        }
        return temp.innerHTML;
    }



// ============================================================
// 分支会话功能
// ============================================================

/**
 * 在 AI 消息上添加分支按钮
 */
function addBranchButton(msgDiv, messageIndex) {
    // 避免重复添加
    if (msgDiv.querySelector('.branch-btn')) return;
    
    const btn = document.createElement('button');
    btn.className = 'branch-btn';
    btn.title = '从此处创建分支会话';
    btn.innerHTML = '🌿';
    btn.dataset.messageIndex = messageIndex;
    
    btn.addEventListener('click', function(e) {
        e.stopPropagation();
        handleBranchClick(parseInt(this.dataset.messageIndex));
    });
    
    msgDiv.appendChild(btn);
    msgDiv.classList.add('has-branch-btn');
}

/**
 * 处理分支会话创建
 */
async function handleBranchClick(messageIndex) {
    if (messageIndex === undefined || messageIndex < 0) {
        showToast('无效的消息索引', 'error');
        return;
    }
    
    const sessionId = state.activeSessionId;
    if (!sessionId) {
        showToast('未找到当前会话', 'error');
        return;
    }
    
    // 如果是 default 会话且没有保存路径，先保存
    try {
        await API.saveSession();
    } catch (e) {
        // ignore
    }
    
    try {
        showToast('正在创建分支会话...', 'info');
        
        const data = await API.createBranch(sessionId, messageIndex);
        
        if (data.status === 'success') {
            showToast('✅ 分支会话已创建，正在跳转...', 'success');
            
            // 保存当前会话输入
            _switchSaveInput();
            
            // 停止流式
            if (state.isStreaming) {
                state.isStreaming = false;
                el.interruptBtn.style.display = 'none';
                el.sendBtn.style.display = 'flex';
                el.sendBtn.disabled = false;
            }
            
            // 切换到新会话 - 最简方案：直接切换 + 显式保存
            state.activeSessionId = data.session_id;
            state._msgCounter = 0;
            state.currentActivePath = data.save_path || null;
            
            // 清除当前消息
            el.messagesContainer.querySelectorAll('.message').forEach(msg => msg.remove());
            el.messagesContainer.querySelectorAll('.optimized-prompt').forEach(opt => opt.remove());
            
            // 从后端获取会话消息
            const msgData = await API.getSessionMessages(state.activeSessionId);
            const messages = msgData.messages || [];
            await renderMessages(messages);
            
            // 恢复输入
            el.chatInput.value = state.sessionInputs[state.activeSessionId] || '';
            
            // 强制保存到磁盘（明确指定 session_id，确保保存到正确文件）
            try {
                const saveResult = await API.saveSession('', state.activeSessionId);
                console.log('[分支] 保存结果:', saveResult, 'session:', state.activeSessionId);
            } catch (e) {
                console.warn('[分支] 保存失败:', e);
            }
            
            // 直接刷新会话列表（强制刷新，不检查 isStreaming）
            await renderSessionList(true);
            
            showToast('🌿 已切换到分支会话', 'success');
        } else {
            showToast('创建分支会话失败: ' + (data.detail || '未知错误'), 'error');
        }
    } catch (e) {
        showToast('创建分支会话失败: ' + e.message, 'error');
    }
}

    function addMessage(content, role, messageIndex) {
        if (el.welcomeMessage && !el.welcomeMessage.classList.contains('hidden')) {
            el.welcomeMessage.classList.add('hidden');
            el.welcomeMessage.style.display = 'none';
        }

        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${role}`;
        if (messageIndex !== undefined) {
            msgDiv.dataset.messageIndex = messageIndex;
        }
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.textContent = role === 'user' ? '👤' : '🧠';
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        if (role === 'user') {
            contentDiv.textContent = content;
        } else {
            contentDiv.innerHTML = renderMarkdown(content);
        }
        
        msgDiv.appendChild(avatar);
        msgDiv.appendChild(contentDiv);
        
        // 为 AI 消息添加分支按钮
        if (role === 'assistant' && messageIndex !== undefined) {
            addBranchButton(msgDiv, messageIndex);
        }
        
        el.messagesContainer.appendChild(msgDiv);
        
        el.messagesContainer.scrollTop = el.messagesContainer.scrollHeight;
        
        return { msgDiv, contentDiv };
    }

    // ============================================================
    // 流式消息渲染
    // ============================================================

    /**
     * Create streaming message container with blinking cursor
     * @returns {{ msgDiv: HTMLElement, contentDiv: HTMLElement }}
     */
    function createStreamingMessageContainer() {
        if (el.welcomeMessage && !el.welcomeMessage.classList.contains('hidden')) {
            el.welcomeMessage.classList.add('hidden');
            el.welcomeMessage.style.display = 'none';
        }

        const msgDiv = document.createElement('div');
        msgDiv.className = 'message assistant streaming';
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.textContent = '🧠';
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        contentDiv.innerHTML = '<span class="streaming-cursor">▊</span>';
        
        msgDiv.appendChild(avatar);
        msgDiv.appendChild(contentDiv);
        el.messagesContainer.appendChild(msgDiv);
        
        el.messagesContainer.scrollTop = el.messagesContainer.scrollHeight;
        
        return { msgDiv, contentDiv };
    }

    /**
     * Update streaming message content, auto-scroll to bottom
     * @param {HTMLElement} contentDiv - Message content container
     * @param {string} fullContent - Accumulated full content
     */
    function updateStreamingContent(contentDiv, fullContent) {
        const rendered = renderMarkdown(fullContent);
        contentDiv.innerHTML = rendered + '<span class="streaming-cursor">▊</span>';
        
        const container = el.messagesContainer;
        const isNearBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 100;
        if (isNearBottom) {
            container.scrollTop = container.scrollHeight;
        }
    }

    /**
     * Finalize streaming message rendering, remove blinking cursor
     * @param {HTMLElement} contentDiv - Message content container
     * @param {string} fullContent - Final complete content
     */
    function finalizeStreamingContent(contentDiv, fullContent, orderedBlocks, wasInterrupted) {
        var renderedHtml = fullContent ? renderMarkdownWithHighlight(fullContent) : '';
        if (wasInterrupted) renderedHtml += '\n\n> ⏹️ 已中断';

        if (typeof window.buildSegmentedHtml === 'function') {
            var result = window.buildSegmentedHtml(orderedBlocks || [], renderedHtml, false);
            contentDiv.innerHTML = result.html;
        } else {
            contentDiv.innerHTML = renderedHtml;
        }

        setTimeout(function() {
            if (typeof window.syncRoundCollapse === 'function') {
                window.syncRoundCollapse();
            }
        }, 50);
        el.messagesContainer.scrollTop = el.messagesContainer.scrollHeight;
    }

    // ============================================================
    // 带超时的 fetch 工具函数
    // ============================================================

    /**
     * 带超时的 fetch 封装
     * @param {string} url - 请求 URL
     * @param {object} [options={}] - fetch 选项
     * @param {number} [timeoutMs=5000] - 超时毫秒数
     * @returns {Promise<Response>}
     */
    /**
     * Fetch wrapper with timeout support
     * @param {string} url - Request URL
     * @param {object} [options={}] - Fetch options
     * @param {number} [timeoutMs=5000] - Timeout in milliseconds
     * @returns {Promise<Response>}
     */
    async function fetchWithTimeout(url, options = {}, timeoutMs = 5000) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
        
        try {
            const response = await fetch(url, {
                ...options,
                signal: options.signal || controller.signal,
            });
            return response;
        } finally {
            clearTimeout(timeoutId);
        }
    }

    /**
     * Fetch with timeout + JSON parsing
     * @param {string} url - Request URL
     * @param {number} [timeoutMs=5000] - Timeout in milliseconds
     * @returns {Promise<object>}
     */
    async function fetchJsonWithTimeout(url, timeoutMs = 5000) {
        const response = await fetchWithTimeout(url, {}, timeoutMs);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        return await response.json();
    }

    // ============================================================
    // 状态更新
    // ============================================================
    /**
     * Poll for realtime status updates (mode, notifications)
     */
    async function updateStatus() {
        if (state.isStreaming) return;
        
        try {
            const data = await fetchJsonWithTimeout('/api/status/realtime', 5000);
            const modeName = data.mode || '🧠 智能处理模式';
            state.currentMode = modeName;
            
            // 更新 Composer 计数
            if (data.micro_count != null) {
                el.microCount.textContent = data.micro_count;
                el.autoCount.textContent = data.auto_count;
                el.manualCount.textContent = data.manual_count;
            }
            if (data.notification) {
                el.composerNotification.textContent = `🔔 ${data.notification}`;
                el.composerNotification.style.display = 'block';
            }
        } catch (error) {
            if (error.name === 'AbortError') {
                console.warn('状态轮询超时（5s），跳过本轮');
            } else {
                console.error('状态更新失败:', error);
            }
        }
    }

    /**
     * Update token usage panel display
     * @param {number} inputTokens - Input token count
     * @param {number} outputTokens - Output token count
     * @param {number} totalTokens - Total token count
     * @param {number} maxTokens - Maximum token limit
     */
    function updateTokenStatus(totalTokens, maxTokens) {
        const elTokenTotal = document.getElementById('tokenTotal');
        if (!elTokenTotal) return;
        const total = totalTokens || 0;
        const max = maxTokens || 128000;
        document.getElementById('tokenTotal').textContent = total.toLocaleString();
        const pct = max > 0 ? Math.min((total / max) * 100, 100) : 0;
        document.getElementById('tokenBarFill').style.width = pct.toFixed(1) + '%';
        document.getElementById('tokenBarText').textContent = pct.toFixed(1) + '%';
    }

    /**
     * Poll for full status including token usage, mode, etc.
     */
    async function updateFullStatus() {
        try {
            const data = await fetchJsonWithTimeout('/api/status', 5000);
            
            // Token 用量面板始终更新（不受 isStreaming 限制）
            const elTokenTotal = document.getElementById('tokenTotal');
            if (elTokenTotal && data.total_tokens != null) {
                const total = data.total_tokens || 0;
                document.getElementById('tokenTotal').textContent = total.toLocaleString();
                const pct = data.usage_percent || 0;
                document.getElementById('tokenBarFill').style.width = pct + '%';
                document.getElementById('tokenBarText').textContent = pct + '%';
            }
            
            // 更新 Composer 计数（不受 isStreaming 限制）
            if (data.micro_count != null) {
                el.microCount.textContent = data.micro_count;
                el.autoCount.textContent = data.auto_count;
                el.manualCount.textContent = data.manual_count;
            }
            // 更新通知
            if (data.notification) {
                el.composerNotification.textContent = "🔔 " + data.notification;
                el.composerNotification.style.display = "block";
            } else if (data.notification === "") {
                el.composerNotification.style.display = "none";
            }

            if (state.isStreaming) return;
            
        } catch (error) {
            if (error.name === 'AbortError') {
                console.warn('完整状态获取超时（5s），跳过本轮');
            } else {
                console.error('完整状态获取失败:', error);
            }
        }
    }

    /**
     * 获取并更新会话标题
     */
    async function updateSessionTitle() {
        try {
            const data = await fetchJsonWithTimeout('/api/session/title', 5000);
            const titleText = data.title.replace(/<[^>]*>/g, '');
            el.sessionTitle.textContent = titleText;
        } catch (error) {
            if (error.name !== 'AbortError') {
                console.error('获取会话标题失败:', error);
            }
        }
    }

    // ============================================================
    // 模式切换
    // ============================================================
    /**
     * Switch between smart and plan mode
     * @param {string} mode - Mode name ('smart' | 'plan')
     */
    async function switchMode(mode) {
        try {
            let result;
            if (mode === 'smart') {
                result = await API.switchToSmart();
                el.smartBtn.className = 'btn btn-primary btn-smart';
                el.planBtn.className = 'btn btn-secondary btn-plan';
            } else {
                result = await API.switchToPlan();
                el.smartBtn.className = 'btn btn-secondary btn-smart';
                el.planBtn.className = 'btn btn-primary btn-plan';
            }
            showToast(result.message, 'success');
            await updateFullStatus();
            await checkPlanMenu();
        } catch (error) {
            showToast(`模式切换失败: ${error.message}`, 'error');
        }
    }

    // ============================================================
    // Plan 菜单
    // ============================================================
    /**
     * Check if Plan menu is ready and update UI
     */
    async function checkPlanMenu() {
        if (state.isStreaming) return;
        
        try {
            const data = await fetchJsonWithTimeout('/api/plan/check', 5000);
            if (data.ready) {
                el.planMenuPanel.style.display = 'block';
            } else {
                el.planMenuPanel.style.display = 'none';
                el.planActionRow.style.display = 'none';
                el.planStatus.textContent = '';
                state.planSelected = null;
                resetPlanButtons();
            }
        } catch (error) {
            if (error.name === 'AbortError') {
                console.warn('Plan 检查超时（5s），跳过本轮');
            } else {
                console.error('检查 Plan 菜单失败:', error);
            }
        }
    }

    /**
     * Reset all plan button styles to unselected state
     */
    function resetPlanButtons() {
        [el.planExploreBtn, el.planModifyBtn, el.planExecuteBtn].forEach(btn => {
            btn.className = 'btn plan-btn';
        });
    }

    /**
     * 高亮选中的 Plan 按钮
     * @param {HTMLElement} selectedBtn - 选中的按钮元素
     */
    function highlightPlanButton(selectedBtn) {
        resetPlanButtons();
        selectedBtn.className = 'btn plan-btn active';
    }

    /**
     * Handle Plan menu operations (explore/modify/execute/reset/confirm)
     * @param {string} action - Action type
     */
    async function handlePlanAction(action) {
        try {
            const data = await API.planAction(action);
            
            if (action === 'explore') {
                state.planSelected = 0;
                highlightPlanButton(el.planExploreBtn);
                el.planActionRow.style.display = 'flex';
                el.planStatus.textContent = data.message;
            } else if (action === 'modify') {
                state.planSelected = 1;
                highlightPlanButton(el.planModifyBtn);
                el.planActionRow.style.display = 'flex';
                el.planStatus.textContent = data.message;
            } else if (action === 'execute') {
                state.planSelected = 2;
                highlightPlanButton(el.planExecuteBtn);
                el.planActionRow.style.display = 'flex';
                el.planStatus.textContent = data.message;
            } else if (action === 'reset') {
                state.planSelected = null;
                el.planActionRow.style.display = 'none';
                el.planStatus.textContent = data.message;
                resetPlanButtons();
            } else if (action === 'confirm') {
                el.planActionRow.style.display = 'none';
                el.planMenuPanel.style.display = 'none';
                el.planStatus.textContent = '';
                resetPlanButtons();
                state.planSelected = null;
                if (data.message) {
                    showToast(data.message, 'success');
                    await updateFullStatus();
                }
            }
        } catch (error) {
            showToast(`Plan 操作失败: ${error.message}`, 'error');
        }
    }

    // ============================================================
    // 发送消息 — 流式渲染版
    // ============================================================
    // ===== Streaming display update helper (real-time) =====
    var _streamRenderTimer = null;
    function updateStreamingDisplay(contentDiv, orderedBlocks, responseContent, immediate) {
        if (!immediate) {
            if (_streamRenderTimer) return;
            _streamRenderTimer = setTimeout(function() {
                _streamRenderTimer = null;
                _doStreamRender(contentDiv, orderedBlocks, responseContent);
            }, 80);
            return;
        }
        clearTimeout(_streamRenderTimer);
        _streamRenderTimer = null;
        _doStreamRender(contentDiv, orderedBlocks, responseContent);
    }
    function _doStreamRender(contentDiv, orderedBlocks, responseContent) {
        if (contentDiv._streamDestroyed) return;
        var renderedHtml = responseContent ? renderMarkdownWithHighlight(responseContent) : "";
        if (typeof window.buildSegmentedHtml === "function") {
            var result = window.buildSegmentedHtml(orderedBlocks || [], renderedHtml, true);
            contentDiv.innerHTML = result.html;
        } else {
            contentDiv.innerHTML = renderedHtml + '<span class="streaming-cursor">\u258a</span>';
        }
        el.messagesContainer.scrollTop = el.messagesContainer.scrollHeight;
    }

    async function sendMessage() {
        const text = el.chatInput.value.trim();
        if (!text || state.isLoading) return;

        el.chatInput.value = '';
        el.chatInput.style.height = 'auto';
        
        state.isLoading = true;
        el.sendBtn.disabled = true;
        state.isStreaming = true;
        _stopPartialPoll();  // 停止旧 partial 轮询，SSE stream 会接管
        const _thisAbortCtrl = state.abortController = new AbortController();
        const _thisSessionId = state.activeSessionId;
        
        // 显示打断按钮
        el.interruptBtn.style.display = 'flex';
        el.sendBtn.style.display = 'none';
        
        addMessage(text, 'user', state._msgCounter++);
        const { msgDiv: assistantMsg, contentDiv } = createStreamingMessageContainer();
        let orderedBlocks = [];          // [{type:'thinking'|'tool_call', content:string}]
        let responseContent = '';        // 回复文本
        let doneReceived = false;
        
        try {
            const response = await fetch('/api/chat/stream', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text, session_id: state.activeSessionId }),
                signal: _thisAbortCtrl.signal,
            });
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
            }
            
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                
                buffer += decoder.decode(value, { stream: true });
                
                const events = buffer.split('\n\n');
                buffer = events.pop() || '';
                
                for (const event of events) {
                    if (!event.trim()) continue;
                    
                    const dataLine = event.trim();
                    if (!dataLine.startsWith('data: ')) continue;
                    
                    const jsonStr = dataLine.substring(6);
                    try {
                        const data = JSON.parse(jsonStr);
                        
                        if (data.type === 'chunk') {
                            responseContent += data.content;
                            updateStreamingDisplay(contentDiv, orderedBlocks, responseContent, false);
                        } else if (data.type === 'optimized_prompt') {
                            // 在用户消息和 AI 回复之间插入优化提示
                            const optDiv = document.createElement('div');
                            optDiv.className = 'optimized-prompt';
                            optDiv.textContent = '✨ Prompt 已优化: ' + data.content;
                            el.messagesContainer.insertBefore(optDiv, assistantMsg);
                        } else if (data.type === 'tool_call') {
                            orderedBlocks.push({type:'tool_call', content: data.content});
                            updateStreamingDisplay(contentDiv, orderedBlocks, responseContent, true);
                        } else if (data.type === 'reasoning') {
                            orderedBlocks.push({type:'thinking', content: data.content});
                            updateStreamingDisplay(contentDiv, orderedBlocks, responseContent, true);
                        } else if (data.type === 'interrupted') {
                            responseContent += data.content;
                        } else if (data.type === 'interrupted_done') {
                            clearTimeout(_streamRenderTimer);
                            contentDiv._streamDestroyed = true;
                            finalizeStreamingContent(contentDiv, responseContent, orderedBlocks, true);
                            assistantMsg.dataset.messageIndex = state._msgCounter;
                            addBranchButton(assistantMsg, state._msgCounter++);
                            doneReceived = true;
                            await updateTokenStatus(data.total_tokens, data.max_tokens);
                            await updateFullStatus();
                            await updateSessionTitle();
                            await renderSessionList();
                        } else if (data.type === 'done') {
                            clearTimeout(_streamRenderTimer);
                            contentDiv._streamDestroyed = true;
                            finalizeStreamingContent(contentDiv, responseContent, orderedBlocks, false);
                            assistantMsg.dataset.messageIndex = state._msgCounter;
                            addBranchButton(assistantMsg, state._msgCounter++);
                            doneReceived = true;
                            await updateTokenStatus(data.total_tokens, data.max_tokens);
                            await updateFullStatus();
                            await updateSessionTitle();
                            await checkPlanMenu();
                            await renderSessionList();
                        } else if (data.type === 'error') {
                            throw new Error('__SSE_ERROR__' + (data.content || '服务器返回错误'));
                        }
                    } catch (e) {
                        if (e.message && (e.message.startsWith('__SSE_ERROR__') || e.message.startsWith('服务器返回错误'))) throw e;
                        console.warn('SSE 数据解析警告:', e.message, jsonStr.substring(0, 100));
                    }
                }
            }

            if (!doneReceived && (responseContent || orderedBlocks.length > 0)) {
                clearTimeout(_streamRenderTimer);
                contentDiv._streamDestroyed = true;
                finalizeStreamingContent(contentDiv, responseContent, orderedBlocks, false);
                await updateFullStatus();
                await updateSessionTitle();
                await checkPlanMenu();
                await renderSessionList();
            }
        } catch (error) {
            if (error.name === 'AbortError') {
                if (responseContent || orderedBlocks.length > 0) {
                    clearTimeout(_streamRenderTimer);
                    contentDiv._streamDestroyed = true;
                    finalizeStreamingContent(contentDiv, responseContent, orderedBlocks, true);
                } else {
                    contentDiv.innerHTML = '⏹️ 已取消';
                }
                await renderSessionList();
            } else {
                if (responseContent || orderedBlocks.length > 0) {
                    clearTimeout(_streamRenderTimer);
                    contentDiv._streamDestroyed = true;
                    finalizeStreamingContent(contentDiv, responseContent, orderedBlocks, false);
                } else {
                    contentDiv.innerHTML = `❌ 请求失败: ${escapeHtml(error.message.replace('__SSE_ERROR__', ''))}`;
                }
                showToast(`发送消息失败: ${error.message}`, 'error');
                await renderSessionList();
            }
        } finally {
            // 隐藏打断按钮，恢复发送按钮
            el.interruptBtn.style.display = 'none';
            el.sendBtn.style.display = 'flex';
            
            // 只清空本 sendMessage 启动的 AbortController（防 race）
            if (state.abortController === _thisAbortCtrl) {
                state.abortController = null;
            }
            // 只有当前视图仍是本 session 才清除 isStreaming
            if (state.activeSessionId === _thisSessionId) {
                state.isStreaming = false;
            }
            state.isLoading = false;
            el.sendBtn.disabled = false;
            el.chatInput.focus();
            
            // 刷新会话列表（放在 isStreaming=false 之后）
            await renderSessionList(true);
        }
    }

    // ============================================================
    // 新开会话（不中断当前会话）
    // ============================================================

    async function newChat() {
        // 保存当前 session 的输入框文字
        _switchSaveInput();
        // 停止 partial 轮询
        _stopPartialPoll();
        
        // 不中断后台流——让旧 session 的 AI 继续跑完再 auto_save
        // 只切换前端视图到新会话
        if (state.isStreaming) {
            // 不 abort 旧 SSE 连接，仅切换 UI 状态
            state.isStreaming = false;
            el.interruptBtn.style.display = 'none';
            el.sendBtn.style.display = 'flex';
            el.sendBtn.disabled = false;
        }
        
        // 隐藏欢迎消息（如果正在显示）
        if (el.welcomeMessage) {
            el.welcomeMessage.classList.add('hidden');
            el.welcomeMessage.style.display = 'none';
        }
        
        try {
            // 保存当前会话（确保 default 会话被持久化到文件）
            const hasMessages = el.messagesContainer.querySelectorAll('.message').length > 0;
            if (hasMessages && !state.isStreaming) {
                try {
                    await API.saveSession();
                } catch (e) {
                    console.warn('保存当前会话失败:', e);
                }
            }
            
            // 在后端创建新会话
            const data = await API.createSession();
            const newSid = data.session_id || 'default';
            
            // 保存当前 dialog 的输入到新 session 的 key 下（用于恢复）
            const oldSid = state.activeSessionId;
            if (oldSid && oldSid !== newSid) {
                state.sessionInputs[newSid] = state.sessionInputs[oldSid] || '';
            }
            
            state.activeSessionId = newSid;
            state._msgCounter = 0;
            
            // 立即刷新 composer 状态（新会话从 0 开始）
            el.microCount.textContent = '0';
            el.autoCount.textContent = '0';
            el.manualCount.textContent = '0';
            el.composerNotification.style.display = 'none';
            
            // 清空消息区域
            el.messagesContainer.querySelectorAll('.message').forEach(msg => msg.remove());
            el.messagesContainer.querySelectorAll('.optimized-prompt').forEach(opt => opt.remove());
            // Reset role display - user will select manually
            if (typeof updateRoleDisplay === 'function') { updateRoleDisplay(null); }
            
            // 清空输入框（新会话）
            el.chatInput.value = '';
            
            // 更新标题
            if (el.sessionTitle) {
                el.sessionTitle.textContent = '新会话';
            }
            
            await renderSessionList();
            await updateFullStatus();
            showToast('✏️ 已开启新会话', 'success');
        } catch (e) {
            showToast('创建会话失败: ' + e.message, 'error');
        }
    }

    // ============================================================
    // 打断
    // ============================================================

    /**
     * Interrupt the current AI response
     */
    async function interruptChat() {
        try {
            await API.interruptChat(state.activeSessionId);
            showToast('⏹️ 正在中断...', 'info');
        } catch (e) {
            console.warn('中断失败:', e);
        }
    }

    // ============================================================

    async function compactContext() {
        if (state.isStreaming) {
            showToast('\u23f3 AI \u54cd\u5e94\u4e2d\uff0c\u8bf7\u7a0d\u540e\u518d\u8bd5', 'warning');
            return;
        }
        const btn = el.compactBtn;
        const originalText = btn.textContent || '\ud83d\udedc\ufe0f \u624b\u52a8\u538b\u7f29';
        btn.disabled = true;
        btn.textContent = '\u23f3 \u538b\u7f29\u4e2d...';
        btn.classList.add('loading');
        try {
            const data = await API.compactContext();
            const msg = data.message || '';
            const hasToken = msg.indexOf('Token') >= 0 || msg.indexOf('token') >= 0;
            showToast(hasToken ? msg : '\ud83d\udedc\ufe0f ' + msg, 'success');
            // 立即更新 composer 计数（manual +1）
            if (data.micro_count != null) {
                el.microCount.textContent = data.micro_count;
                el.autoCount.textContent = data.auto_count;
                el.manualCount.textContent = data.manual_count;
            }
            if (data.notification) {
                el.composerNotification.textContent = "🔔 " + data.notification;
                el.composerNotification.style.display = "block";
            }
            await updateFullStatus();
        } catch (error) {
            showToast('\u538b\u7f29\u5931\u8d25: ' + error.message, 'error');
        } finally {
            btn.disabled = false;
            btn.textContent = originalText;
            btn.classList.remove('loading');
        }
    }

    /**
     * Display current status as an assistant message
     */
    async function showStatus() {
        if (state.isStreaming) return;
        try {
            const data = await API.getStatusText();
            if (data.message) {
                addMessage(data.message, 'assistant', state._msgCounter++);
            }
        } catch (error) {
            showToast(`获取状态失败: ${error.message}`, 'error');
        }
    }

    /**
     * Display help text as an assistant message
     */
    async function showHelp() {
        if (state.isStreaming) return;
        try {
            const data = await API.getHelp();
            if (data.message) {
                addMessage(data.message, 'assistant');
            }
        } catch (error) {
            showToast(`获取帮助失败: ${error.message}`, 'error');
        }
    }

    // ============================================================
    // 左侧会话列表（ChatGPT 风格）
    // ============================================================

    /**
     * 将 ISO 时间戳转为友好的日期分组
     */
    function getDateGroup(timestamp) {
        if (!timestamp || timestamp === '未知') return '其他';
        const now = new Date();
        const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        const yesterday = new Date(today);
        yesterday.setDate(yesterday.getDate() - 1);
        
        // 解析时间戳 "2025年5月20日 16:30:00"
        const parts = timestamp.split(' ');
        const datePart = parts[0];
        if (!datePart) return '其他';
        
        const sessionDate = new Date(datePart);
        if (isNaN(sessionDate.getTime())) return '其他';
        
        const sessionDay = new Date(sessionDate.getFullYear(), sessionDate.getMonth(), sessionDate.getDate());
        
        const diffDays = Math.floor((today - sessionDay) / (1000 * 60 * 60 * 24));
        
        if (diffDays === 0) return '今天';
        if (diffDays === 1) return '昨天';
        if (diffDays <= 7) return '最近 7 天';
        if (diffDays <= 30) return '本月';
        return '更早';
    }

    /**
     * 加载并加载会话
     */
    /**
     * 加载并渲染会话消息
     */
    async function renderMessages(messages) {
        if (!messages || messages.length === 0) {
            if (el.welcomeMessage) {
                el.welcomeMessage.classList.remove('hidden');
                el.welcomeMessage.style.display = 'block';
            }
            return;
        }

        // 隐藏欢迎消息
        if (el.welcomeMessage && !el.welcomeMessage.classList.contains('hidden')) {
            el.welcomeMessage.classList.add('hidden');
            el.welcomeMessage.style.display = 'none';
        }

        var _thinkCount = 0, _toolCount = 0;

        let msgCounter = 0;

        for (const m of messages) {
            if (m.role === 'tool') continue; // 不显示工具调用结果

            const msgDiv = document.createElement('div');
            msgDiv.className = `message ${m.role}`;
            msgDiv.dataset.messageIndex = msgCounter;

            const avatar = document.createElement('div');
            avatar.className = 'message-avatar';
            avatar.textContent = m.role === 'user' ? '👤' : '🧠';

            const contentDiv = document.createElement('div');
            contentDiv.className = 'message-content';

            if (m.role === 'user') {
                contentDiv.textContent = m.content;
            } else {
                // ---- assistant: 使用 rounds 数据重建时序 ----
                var blocks = [];
                var responseText = m.content;

                // 尝试匹配 round 数据
                if (m.rounds && m.rounds.length > 0) {
                    var result = (typeof window.roundsToBlocks === 'function')
                        ? window.roundsToBlocks(m.rounds)
                        : null;
                    if (result && result.orderedBlocks && result.orderedBlocks.length > 0) {
                        blocks = result.orderedBlocks;
                        responseText = result.responseText || ''; // 有 rounds 则只取 rounds 中的数据，不退回 m.content
                    }
                }

                if (blocks.length > 0 && typeof window.buildSegmentedHtml === 'function') {
                    var renderedHtml = responseText ? renderMarkdownWithHighlight(responseText) : '';
                    var segResult = window.buildSegmentedHtml(blocks, renderedHtml, false, _thinkCount, _toolCount);
                    contentDiv.innerHTML = segResult.html;
                    _thinkCount = segResult.thinkCount;
                    _toolCount = segResult.toolCount;
                } else {
                    contentDiv.innerHTML = renderMarkdownWithHighlight(m.content);
                }
            }

            msgDiv.appendChild(avatar);
            msgDiv.appendChild(contentDiv);
            // 为 AI 消息添加分支按钮（仅在 renderMessages 中有索引时）
            if (m.role === 'assistant' && typeof msgCounter !== 'undefined') {
                addBranchButton(msgDiv, msgCounter);
            }
            el.messagesContainer.appendChild(msgDiv);

            // 用户消息如果有优化 Prompt，在下方插入黄色提示框
            if (m.role === 'user' && m.optimized_prompt) {
                const optDiv = document.createElement('div');
                optDiv.className = 'optimized-prompt';
                optDiv.textContent = '✨ Prompt 已优化: ' + m.optimized_prompt;
                el.messagesContainer.appendChild(optDiv);
            }
            msgCounter++;
        }

        el.messagesContainer.scrollTop = el.messagesContainer.scrollHeight;
    }

    // ============================================================
    // 跨会话状态管理
    // ============================================================

    let _partialPollTimer = null;  // partial content 轮询定时器

    /**
     * 保存当前 session 的输入框文字
     */
    function _switchSaveInput() {
        state.sessionInputs[state.activeSessionId] = el.chatInput.value;
    }

    /**
     * 停止 partial content 轮询
     */
    function _stopPartialPoll() {
        if (_partialPollTimer) {
            clearInterval(_partialPollTimer);
            _partialPollTimer = null;
        }
    }

    /**
     * 切换到活跃 session（不创建新 session，直接从 registry 读状态）
     */
    async function switchToActiveSession(sessionId) {
        if (!sessionId || sessionId === state.activeSessionId) return;
        
        // 停止旧 session 的轮询
        _stopPartialPoll();
        
        // 保存当前 session 的输入和状态
        _switchSaveInput();
        
        state.activeSessionId = sessionId;
            state._msgCounter = 0;
        
        // 清除当前 DOM
        el.messagesContainer.querySelectorAll('.message').forEach(msg => msg.remove());
        el.messagesContainer.querySelectorAll('.optimized-prompt').forEach(opt => opt.remove());
            // Reset role display - user will select manually
            if (typeof updateRoleDisplay === 'function') { updateRoleDisplay(null); }
        el.chatInput.value = '';
        
        try {
            // 从 registry 获取消息
            const msgData = await API.getSessionMessages(sessionId);
            const messages = msgData.messages || [];
            
            // 恢复输入框
            if (state.sessionInputs[sessionId]) {
                el.chatInput.value = state.sessionInputs[sessionId];
            }
            
            // 更新按钮状态
            if (msgData.is_streaming) {
                state.isStreaming = true;
                el.interruptBtn.style.display = 'flex';
                el.sendBtn.style.display = 'none';
                el.sendBtn.disabled = true;
            } else {
                state.isStreaming = false;
                el.interruptBtn.style.display = 'none';
                el.sendBtn.style.display = 'flex';
                el.sendBtn.disabled = false;
            }
            
            // partial content 记录和轮询
            let _partialDiv = null;
            let _partialContentDiv = null;
            
            // 渲染已完成消息
            if (messages.length > 0) {
                await renderMessages(messages);
                
                // 处理 partial content（正在流的消息）
                if (msgData.is_streaming && msgData.partial_content) {
                    const { msgDiv, contentDiv } = createStreamingMessageContainer();
                    contentDiv.textContent = msgData.partial_content;
                    el.messagesContainer.appendChild(msgDiv);
                    _partialDiv = msgDiv;
                    _partialContentDiv = contentDiv;
                }
            } else if (el.welcomeMessage) {
                el.welcomeMessage.classList.remove('hidden');
                el.welcomeMessage.style.display = '';
            }
            
            // 更新 UI
            if (msgData.title) {
                el.sessionTitle.textContent = msgData.title;
            }
            state.currentActivePath = null;
            state.currentMode = msgData.mode || state.currentMode;
            // 切换 session 后立即刷新 composer 状态
            await updateFullStatus();
            await updateSessionTitle();
            await checkPlanMenu();
            await renderSessionList();
            
            // 如果正在流，启动轮询
            if (msgData.is_streaming) {
                _partialPollTimer = setInterval(async () => {
                    try {
                        const pollData = await API.getSessionMessages(sessionId);
                        if (pollData.is_streaming && pollData.partial_content && _partialContentDiv) {
                            // 更新 partial 文本
                            _partialContentDiv.textContent = pollData.partial_content;
                            el.messagesContainer.scrollTop = el.messagesContainer.scrollHeight;
                        } else if (!pollData.is_streaming) {
                            // 流已结束，停止轮询，完整重新渲染
                            _stopPartialPoll();
                            // 重新获取完成消息
                            const finalMsgs = pollData.messages || [];
                            // 只替换 streaming 容器后的内容
                            if (_partialDiv) {
                                _partialDiv.remove();
                                _partialDiv = null;
                                _partialContentDiv = null;
                            }
                            // 清除旧消息并完整渲染
                            el.messagesContainer.querySelectorAll('.message').forEach(msg => msg.remove());
                            el.messagesContainer.querySelectorAll('.optimized-prompt').forEach(opt => opt.remove());
            // Reset role display - user will select manually
            if (typeof updateRoleDisplay === 'function') { updateRoleDisplay(null); }
                            if (finalMsgs.length > 0) {
                                await renderMessages(finalMsgs);
                                el.messagesContainer.scrollTop = el.messagesContainer.scrollHeight;
                            }
                            // 按钮切回非流式
                            state.isStreaming = false;
                            el.interruptBtn.style.display = 'none';
                            el.sendBtn.style.display = 'flex';
                            el.sendBtn.disabled = false;
                            // 刷新侧栏
                            await renderSessionList();
                        }
                    } catch (e) {
                        // 静默失败（切换 session 时定时器会停止）
                    }
                }, 2000);
            }
            
        } catch (error) {
            showToast(`切换会话失败: ${error.message}`, 'error');
        }
    }

    /**
     * Load a saved session by file path
     * @param {string} path - Session file path
     */
    async function loadSessionByPath(path) {
        if (!path) {
            showToast('请先选择一个会话', 'warning');
            return;
        }
        
        // 保存当前 session 的输入框文字
        _switchSaveInput();
        // 停止 partial 轮询
        _stopPartialPoll();
        
        if (state.isStreaming) {
            // 不中断后台流——让旧 session 的 AI 继续跑完再 auto_save
            // 只切换前端视图
            state.isStreaming = false;
            el.interruptBtn.style.display = 'none';
            el.sendBtn.style.display = 'flex';
            el.sendBtn.disabled = false;
        }
        try {
            // 加载会话
            const loadData = await API.loadSession(path);
            showToast(loadData.message, 'success');

            if (loadData.already_active) {
                // 已有活跃 session 跟踪此文件，走 switch 路径（保留输入/状态）
                await switchToActiveSession(loadData.session_id);
                state.currentActivePath = path;
                return;
            }

            // 新 session
            state.activeSessionId = loadData.session_id || 'default';
            state._msgCounter = 0;

            // 2. 清除当前显示的消息
            el.messagesContainer.querySelectorAll('.message').forEach(msg => msg.remove());
            el.messagesContainer.querySelectorAll('.optimized-prompt').forEach(opt => opt.remove());
            // Reset role display - user will select manually
            if (typeof updateRoleDisplay === 'function') { updateRoleDisplay(null); }

            // 3. 获取会话消息并渲染
            const msgData = await API.getSessionMessages(state.activeSessionId);
            const messages = msgData.messages || [];
            await renderMessages(messages);

            // 恢复已保存的输入文字
            el.chatInput.value = state.sessionInputs[state.activeSessionId] || '';

            // 4. 更新 UI
            state.currentActivePath = path;
            await renderSessionList();
            await updateFullStatus();
            await updateSessionTitle();
            await checkPlanMenu();
        } catch (error) {
            showToast(`加载失败: ${error.message}`, 'error');
        }
    }

    /**
     * 加载服务器上已有的会话消息（用于多标签页同步）
     */
    async function loadExistingMessages() {
        try {
            const msgData = await API.getSessionMessages(state.activeSessionId);
            const messages = msgData.messages || [];
            if (messages.length > 0) {
                // 已有消息，渲染它们（覆盖欢迎页面）
                await renderMessages(messages);
                if (msgData.title) {
                    el.sessionTitle.textContent = msgData.title;
                }
                // 更新状态
                state.currentActivePath = null;
                await updateFullStatus();
                await updateSessionTitle();
                await checkPlanMenu();
            }
        } catch (error) {
            // 静默失败（首次加载或没有会话时是正常的）
            console.debug('加载已有消息失败（首次加载可忽略）:', error.message);
        }
    }

    /**
     * Delete a saved session by file path
     * @param {string} path - Session file path
     */
    async function deleteSessionByPath(path) {
        if (!path) return;
        if (!confirm('确定要删除这个会话吗？')) return;
        try {
            const data = await API.deleteSession(path);
            showToast(data.message, 'success');
            if (state.currentActivePath === path) {
                state.currentActivePath = null;
            }
            await renderSessionList();
        } catch (error) {
            showToast(`删除失败: ${error.message}`, 'error');
        }
    }

    /**
     * 渲染左侧会话列表（活跃会话 + 已保存文件）
     */
    async function renderSessionList(forceRefresh) {
        if (state.isStreaming && !forceRefresh) return;
        
        try {
            const data = await fetchJsonWithTimeout('/api/sessions/list', 5000);
            // 合并已保存文件 + 活跃会话（注册表中的会话可能未保存到磁盘）
            state.sessions = data.saved_files || [];
            
            // 按修改时间排序（最新在最前）
            state.sessions.sort(function(a, b) {
                var ta = a.timestamp || '';
                var tb = b.timestamp || '';
                return new Date(tb.replace(' ', 'T')).getTime() - new Date(ta.replace(' ', 'T')).getTime();
            });
            
            const searchText = (el.sessionSearch.value || '').toLowerCase().trim();
            
            // 过滤已保存文件
            let filteredSaved = state.sessions;
            if (searchText) {
                filteredSaved = filteredSaved.filter(s => {
                    const title = (s.title || '').toLowerCase();
                    const filename = (s.filename || '').toLowerCase();
                    return title.includes(searchText) || filename.includes(searchText);
                });
            }
            
            el.sessionList.innerHTML = '';
            
            // ---- 已保存文件区 ----
            if (filteredSaved.length === 0) {
                const empty = document.createElement('div');
                empty.className = 'session-list-empty';
                empty.textContent = searchText ? '没有匹配的会话' : '暂无保存的会话\n开始对话后会自动保存';
                el.sessionList.appendChild(empty);
                return;
            }
                // 按日期分组
                const groups = {};
                filteredSaved.forEach(s => {
                    const group = getDateGroup(s.timestamp);
                    if (!groups[group]) groups[group] = [];
                    groups[group].push(s);
                });
                
                const groupOrder = ['今天', '昨天', '最近 7 天', '本月', '更早', '其他'];
                
                for (const groupName of groupOrder) {
                    const items = groups[groupName];
                    if (!items || items.length === 0) continue;
                    
                    const header = document.createElement('div');
                    header.className = 'session-date-header';
                    header.textContent = groupName;
                    el.sessionList.appendChild(header);
                    
                    items.forEach(s => {
                        const item = document.createElement('div');
                        item.className = 'session-item';
                        if (s.path === state.currentActivePath) {
                            item.classList.add('active');
                        }

                        
                        const title = s.title || '（无标题）';
                        const displayTitle = title.length > 30 ? title.substring(0, 27) + '...' : title;
                        const mode = s.mode || '';
                        const msgCount = s.messages || 0;
                        
                        // 判断是否为分支会话
                        const isBranch = s.parent_session_id && s.parent_session_id !== '';
                        const branchLabel = isBranch ? '<span class="session-item-branch-label" title="从 ' + escapeHtml(s.parent_session_id || '') + ' 分支">🌿 分支</span>' : '';
                        // 分支会话文件名加 "分支" 前缀
                        const displayFilename = isBranch ? '分支 - ' + (s.filename || '') : (s.filename || '');
                        
                        item.innerHTML = `
                            <div class="session-item-title" title="${escapeHtml(title)}">${escapeHtml(displayTitle)} ${branchLabel}</div>
                            <div class="session-item-meta">
                                <span>${s.timestamp || ''}</span>
                                <span>${msgCount} 条</span>
                                ${isBranch ? `<span class="session-item-file">${escapeHtml(displayFilename)}</span>` : ''}
                                ${mode ? `<span class="session-item-mode">${mode}</span>` : ''}
                            </div>
                            <button class="session-item-delete" title="删除会话">🗑️</button>
                        `;
                        
                        item.addEventListener('click', (e) => {
                            if (e.target.closest('.session-item-delete')) return;
                            _switchSaveInput();
                            loadSessionByPath(s.path);
                        });
                        
                        const delBtn = item.querySelector('.session-item-delete');
                        delBtn.addEventListener('click', (e) => {
                            e.stopPropagation();
                            deleteSessionByPath(s.path);
                        });
                        
                        el.sessionList.appendChild(item);
                    });
                }
        } catch (error) {
            if (error.name !== 'AbortError') {
                console.error('渲染会话列表失败:', error);
            }
        }
    }

    // ============================================================
    // Conda 环境管理
    // ============================================================

    async function renderCondaEnvs() {
        try {
            const data = await API.listCondaEnvs();
            const currentEnv = data.current || '';
            el.envCondaList.innerHTML = '';

            if (!data.success) {
                el.envCondaList.innerHTML = `<div class="env-error">❌ ${data.error}</div>`;
                return;
            }

            const envs = data.envs || [];
            if (envs.length === 0) {
                el.envCondaList.innerHTML = '<div class="env-empty">没有找到 conda 环境</div>';
                return;
            }

            envs.forEach(envName => {
                const item = document.createElement('div');
                item.className = 'env-conda-item';
                if (envName === currentEnv) {
                    item.classList.add('active');
                }

                const isActive = envName === currentEnv;
                item.innerHTML = `
                    <span class="env-conda-icon">${isActive ? '🟢' : '🔵'}</span>
                    <span class="env-conda-name">${escapeHtml(envName)}</span>
                    <span class="env-conda-check">✓</span>
                `;

                if (!isActive) {
                    item.addEventListener('click', async () => {
                        try {
                            const result = await API.switchCondaEnv(envName);
                            showToast(result.message, 'success');
                            await refreshEnvPanel();
                        } catch (error) {
                            showToast(`切换失败: ${error.message}`, 'error');
                        }
                    });
                }

                el.envCondaList.appendChild(item);
            });
        } catch (error) {
            el.envCondaList.innerHTML = `<div class="env-error">❌ ${error.message}</div>`;
        }
    }

    async function refreshEnvPanel() {
        try {
            const env = await API.getCurrentEnv();
            el.envCurrentName.textContent = env.conda_env || 'base';
            el.envCurrentPath.textContent = env.python_path || '未知';
        } catch (error) {
            el.envCurrentName.textContent = '获取失败';
            el.envCurrentPath.textContent = error.message;
        }
        await renderCondaEnvs();
    }

    async function createCondaEnv() {
        const name = el.envCreateInput.value.trim();
        if (!name) {
            showToast('请输入环境名称', 'warning');
            return;
        }
        el.envCreateBtn.disabled = true;
        el.envCreateBtn.textContent = '⏳ 创建中...';
        try {
            const result = await API.createCondaEnv(name);
            showToast(result.message, 'success');
            el.envCreateInput.value = '';
            await refreshEnvPanel();
        } catch (error) {
            showToast(`创建失败: ${error.message}`, 'error');
        } finally {
            el.envCreateBtn.disabled = false;
            el.envCreateBtn.textContent = '➕ 创建';
        }
    }

    // ============================================================
    // 模型切换
    // ============================================================

    async function refreshModelList() {
        try {
            const data = await API.listModels();
            const models = data.models || [];
            const current = data.current || '';

            el.modelSelect.innerHTML = '';
            models.forEach(m => {
                const opt = document.createElement('option');
                opt.value = m.code;
                opt.textContent = m.name;
                // 标记是否为自定义模型（在 data 属性中记录）
                opt.dataset.isCustom = m.is_custom ? 'true' : 'false';
                el.modelSelect.appendChild(opt);
            });
            // 设置选中值（不触发 change 事件，避免意外调用 switchModel）
            if (current) el.modelSelect.value = current;

            // 更新删除按钮可见性
            updateModelDelBtn();
        } catch (error) {
            console.error('获取模型列表失败:', error);
        }
    }

    function updateModelDelBtn() {
        if (!el.modelDelBtn) return;
        const selectedOpt = el.modelSelect.options[el.modelSelect.selectedIndex];
        if (selectedOpt && selectedOpt.dataset.isCustom === 'true') {
            el.modelDelBtn.style.display = 'inline-flex';
        } else {
            el.modelDelBtn.style.display = 'none';
        }
    }

    async function switchModel() {
        const modelCode = el.modelSelect.value;
        if (!modelCode) return;
        try {
            const data = await API.switchModel(modelCode);
            showToast(data.message, 'success');
            await refreshModelList();
        } catch (error) {
            showToast(`切换模型失败: ${error.message}`, 'error');
            await refreshModelList();
        }
    }

    /**
     * Delete the currently selected custom model
     */
    async function deleteCustomModel() {
        const modelCode = el.modelSelect.value;
        if (!modelCode) return;
        const modelName = el.modelSelect.options[el.modelSelect.selectedIndex].text;
        if (!confirm(`确定要删除自定义模型「${modelName}」吗？`)) return;
        try {
            const data = await API.deleteModel(modelCode);
            showToast(data.message, 'success');
            await refreshModelList();
        } catch (error) {
            showToast(`删除失败: ${error.message}`, 'error');
            await refreshModelList();
        }
    }

    /**
     * Open modal dialog to add a custom model
     */
    async function addCustomModel() {
        // 弹出添加模型对话框（名称、Code、Base URL、API Key）
        const overlay = document.createElement('div');
        overlay.className = 'modal-overlay';
        overlay.innerHTML = `
            <div class="modal-dialog">
                <div class="modal-header">
                    <span>➕ 添加自定义模型</span>
                    <span class="modal-close">&times;</span>
                </div>
                <div class="modal-body">
                    <div class="config-field">
                        <label>模型名称</label>
                        <input class="config-input" id="addModelName" placeholder="例如: My Custom Model">
                    </div>
                    <div class="config-field">
                        <label>模型 Code</label>
                        <input class="config-input" id="addModelCode" placeholder="例如: my-custom-model">
                    </div>
                    <div class="config-field">
                        <label>Base URL（可选）</label>
                        <input class="config-input" id="addModelBaseUrl" placeholder="留空则使用全局配置">
                    </div>
                    <div class="config-field">
                        <label>API Key（可选）</label>
                        <input class="config-input" id="addModelApiKey" type="password" placeholder="留空则使用全局配置">
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary modal-cancel-btn">取消</button>
                    <button class="btn btn-primary modal-confirm-btn">确认添加</button>
                </div>
            </div>
        `;
        document.body.appendChild(overlay);

        // 事件绑定
        const closeModal = () => overlay.remove();
        overlay.querySelector('.modal-close').onclick = closeModal;
        overlay.querySelector('.modal-cancel-btn').onclick = closeModal;
        overlay.onclick = (e) => { if (e.target === overlay) { var ov = document.querySelector('.role-pool-overlay'); if (ov) ov.remove(); } };
        overlay.querySelector('.modal-confirm-btn').onclick = async () => {
            const name = overlay.querySelector('#addModelName').value.trim();
            const code = overlay.querySelector('#addModelCode').value.trim();
            const baseUrl = overlay.querySelector('#addModelBaseUrl').value.trim();
            const apiKey = overlay.querySelector('#addModelApiKey').value.trim();
            if (!name || !code) {
                showToast('模型名称和 Code 不能为空', 'warning');
                return;
            }
            try {
                const data = await API.addCustomModel(name, code, baseUrl, apiKey);
                showToast(data.message, 'success');
                closeModal();
                await refreshModelList();
            } catch (error) {
                showToast(`添加失败: ${error.message}`, 'error');
            }
        };
        // 聚焦到名称输入框
        setTimeout(() => overlay.querySelector('#addModelName').focus(), 100);
    }

    // ============================================================
    // 配置面板
    // ============================================================

    // ============================================================
    // 模型 API 配置弹窗
    // ============================================================
    /**
     * Open modal dialog to configure model API settings
     */
    async function openModelConfigDialog() {
        const modelCode = el.modelSelect.value;
        if (!modelCode) return;
        const modelName = el.modelSelect.options[el.modelSelect.selectedIndex].text;

        // 获取当前模型的 API 配置
        let currentBaseUrl = '', currentApiKey = '';
        try {
            const modelData = await API.listModels();
            const models = modelData.models || [];
            const m = models.find(x => x.code === modelCode);
            if (m) {
                currentBaseUrl = m.base_url || '';
                currentApiKey = m.api_key || '';
            }
        } catch (e) {
            // ignore
        }

        const overlay = document.createElement('div');
        overlay.className = 'modal-overlay';
        overlay.innerHTML = `
            <div class="modal-dialog">
                <div class="modal-header">
                    <span>⚙️ 模型 API 配置 — ${escapeHtml(modelName)}</span>
                    <span class="modal-close">&times;</span>
                </div>
                <div class="modal-body">
                    <div class="config-field">
                        <label>模型 Code</label>
                        <input class="config-input" id="mcfgModelCode" value="${escapeHtml(modelCode)}" readonly style="opacity:0.7">
                    </div>
                    <div class="config-field">
                        <label>Base URL</label>
                        <input class="config-input" id="mcfgBaseUrl" placeholder="留空则使用默认地址" value="${escapeHtml(currentBaseUrl)}">
                    </div>
                    <div class="config-field">
                        <label>API Key</label>
                        <input class="config-input" id="mcfgApiKey" type="password" placeholder="留空则使用默认 Key" value="${escapeHtml(currentApiKey)}">
                    </div>
                    <div class="config-tip">💡 留空表示使用默认配置。保存后立即生效。</div>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary modal-cancel-btn">取消</button>
                    <button class="btn btn-primary modal-confirm-btn">💾 保存</button>
                </div>
            </div>
        `;
        document.body.appendChild(overlay);

        const closeModal = () => overlay.remove();
        overlay.querySelector('.modal-close').onclick = closeModal;
        overlay.querySelector('.modal-cancel-btn').onclick = closeModal;
        overlay.onclick = (e) => { if (e.target === overlay) closeModal(); };
        overlay.querySelector('.modal-confirm-btn').onclick = async () => {
            const baseUrl = overlay.querySelector('#mcfgBaseUrl').value.trim();
            const apiKey = overlay.querySelector('#mcfgApiKey').value.trim();
            const btn = overlay.querySelector('.modal-confirm-btn');
            btn.disabled = true;
            btn.textContent = '⏳ 保存中...';
            try {
                const data = await API.updateModelConfig(modelCode, {
                    api_base_url: baseUrl,
                    api_key: apiKey,
                });
                showToast(data.message, 'success');
                closeModal();
            } catch (error) {
                showToast(`保存失败: ${error.message}`, 'error');
                btn.disabled = false;
                btn.textContent = '💾 保存';
            }
        };
        setTimeout(() => overlay.querySelector('#mcfgBaseUrl').focus(), 100);
    }

    // ============================================================
    // 主题切换
    // ============================================================
    /**
     * 切换 highlight.js 主题（跟随系统主题）
     */
    function setHighlightTheme(theme) {
        var link = document.getElementById('hljsTheme');
        if (!link) return;
        if (theme === 'light') {
            link.href = 'https://cdn.jsdelivr.net/gh/highlightjs/cdn-release/build/styles/github.min.css';
        } else {
            link.href = 'https://cdn.jsdelivr.net/gh/highlightjs/cdn-release/build/styles/github-dark.min.css';
        }
    }

    function toggleTheme() {
        const html = document.documentElement;
        const currentTheme = html.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        html.setAttribute('data-theme', newTheme);
        el.themeToggle.textContent = newTheme === 'dark' ? '🌙' : '☀️';
        try { localStorage.setItem('theme', newTheme); } catch(e) {};
        setHighlightTheme(newTheme);
    }

    function loadTheme() {
        const savedTheme = (function(){try{return localStorage.getItem('theme')}catch(e){return null}})() || 'dark';
        document.documentElement.setAttribute('data-theme', savedTheme);
        el.themeToggle.textContent = savedTheme === 'dark' ? '🌙' : '☀️';
        setHighlightTheme(savedTheme);
    }

    // ============================================================
    // 侧边栏折叠
    // ============================================================
    function toggleSidebar() {
        el.leftSidebar.classList.toggle('collapsed');
    }

    // ============================================================
    // 可折叠面板
    // ============================================================
    function toggleCollapsible(header, body) {
        header.addEventListener('click', () => {
            body.classList.toggle('hidden');
            header.classList.toggle('collapsed');
        });
    }

    // ============================================================
    // 输入框自动伸缩
    // ============================================================
    function autoResizeTextarea() {
        el.chatInput.style.height = 'auto';
        el.chatInput.style.height = Math.min(el.chatInput.scrollHeight, 150) + 'px';
    }

    // ============================================================
    // 事件绑定
    // ============================================================
    
    // 发送消息
    el.sendBtn.addEventListener('click', sendMessage);
    el.chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    el.chatInput.addEventListener('input', autoResizeTextarea);

    // 模式切换
    el.smartBtn.addEventListener('click', () => switchMode('smart'));
    el.planBtn.addEventListener('click', () => switchMode('plan'));

    // 新开会话（创建新后台会话，不中断当前）
    el.newChatBtn.addEventListener('click', newChat);

    // 会话搜索
    el.sessionSearch.addEventListener('input', () => {
        renderSessionList();
    });

    // 侧边栏折叠
    el.sidebarToggle.addEventListener('click', toggleSidebar);

    // 快捷操作
    el.compactBtn.addEventListener('click', compactContext);
    el.statusBtn.addEventListener('click', showStatus);
    el.helpBtn.addEventListener('click', showHelp);

    // 主题切换
    el.themeToggle.addEventListener('click', toggleTheme);

    // 技能管理
    el.skillMenuBtn.addEventListener('click', openSkillManagerModal);

    // Plan 菜单
    el.planExploreBtn.addEventListener('click', () => handlePlanAction('explore'));
    el.planModifyBtn.addEventListener('click', () => handlePlanAction('modify'));
    el.planExecuteBtn.addEventListener('click', () => handlePlanAction('execute'));
    el.planResetBtn.addEventListener('click', () => handlePlanAction('reset'));
    el.planConfirmBtn.addEventListener('click', () => handlePlanAction('confirm'));

    // Conda 环境
    el.envCreateBtn.addEventListener('click', createCondaEnv);
    el.envCreateInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') createCondaEnv();
    });

    // 模型切换
    el.modelSelect.addEventListener('change', switchModel);
    el.modelAddBtn.addEventListener('click', addCustomModel);
    el.modelDelBtn.addEventListener('click', deleteCustomModel);
    el.modelCfgBtn.addEventListener('click', openModelConfigDialog);

    // 打断按钮
    el.interruptBtn.addEventListener('click', interruptChat);

    // 可折叠面板
    toggleCollapsible(el.envPanelToggle, el.envPanelBody);

    // ============================================================
    // 智能定时刷新
    // ============================================================
    
    function startSmartPolling() {
        if (state.statusInterval) clearInterval(state.statusInterval);
        if (state.planCheckInterval) clearInterval(state.planCheckInterval);
        if (state.sessionListInterval) clearInterval(state.sessionListInterval);
        
        state.statusInterval = setInterval(updateStatus, 3000);
        state.planCheckInterval = setInterval(checkPlanMenu, 5000);
        state.sessionListInterval = setInterval(renderSessionList, 15000);
    }

    // ============================================================
    // 初始化
    // ============================================================
    loadTheme();
    startSmartPolling();
    updateFullStatus();
    renderSessionList();
    checkPlanMenu();
    refreshEnvPanel();
    refreshModelList();
    loadExistingMessages();  // 加载已有会话消息（多标签页同步）
    autoResizeTextarea();
    el.chatInput.focus();
    
    // 初始化默认角色 & 技能
    selectRoleForNewSession();
    setTimeout(function() {
        loadSkillsForRole('Tennine');
    }, 500);

});

// ============================================================




async function selectRoleForNewSession() {
    try {
        const r = await fetch('/api/personality/templates/all');
        const data = await r.json();
        const templates = data.data || data.templates || {};
        const names = Object.keys(templates);

        if (names.length === 0) {
            updateRoleDisplay({
                roleId: 'default',
                roleName: '默认助手',
                roleIcon: '🧑',
                roleDesc: '默认角色'
            });
            return;
        }

        let selected = null;
        if (templates['Tennine']) {
            selected = templates['Tennine'];
        } else if (templates['default']) {
            selected = templates['default'];
        } else {
            selected = templates[names[0]];
        }
        
        if (selected) {
            var roleName = selected.name || names[0];
            updateRoleDisplay({
                roleId: selected.id || names[0],
                roleName: roleName,
                roleIcon: selected.icon || '🧑',
                roleDesc: selected.description || ''
            });
            applyRole(roleName);
        }
    } catch (e) {
        console.error('selectRoleForNewSession error:', e);
        updateRoleDisplay({
            roleId: 'default',
            roleName: '默认助手',
            roleIcon: '🧑',
            roleDesc: '默认角色'
        });
    }
}


async function showRoleSelector() {
    try {
        const r = await fetch('/api/personality/templates/all');
        const data = await r.json();
        const templates = data.data || data.templates || {};
        const names = Object.keys(templates);
        
        if (names.length === 0) {
            showToast('没有可用的角色卡', 'error');
            return;
        }
        
        // Build role selection HTML
        var q1 = "'";
        let html = '<div style="display:flex; flex-direction:column; gap:6px; max-height:400px; overflow-y:auto;">';
        names.forEach(function(name) {
            const t = templates[name];
            const isBuiltin = t.is_builtin === true;
            html += '<div style="display:flex; align-items:center; gap:6px; padding:7px 8px; border-radius:6px; margin:2px 0; cursor:pointer; border:1px solid var(--border-color);" onclick="applyRole(' + q1 + name + q1 + ')">';
            html += '<span style="font-size:20px;">' + (t.icon || '🧑') + '</span>';
            html += '<div style="flex:1; min-width:0;">';
            html += '<div style="font-size:13px; font-weight:600; color:var(--text-primary);">' + name + '</div>';
            html += '<div style="font-size:10px; color:var(--text-muted); white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">' + (t.description || '') + '</div>';
            html += '</div>';
            if (isBuiltin) {
                html += '<span style="font-size:9px; padding:2px 6px; border-radius:4px; background:rgba(99,102,241,0.12); color:#818cf8;">内置</span>';
            } else {
                html += '<span style="cursor:pointer; font-size:10px; padding:2px 6px; border-radius:4px; background:rgba(239,68,68,0.12); color:#ef4444;" onclick="event.stopPropagation();deleteRoleTemplate(' + q1 + name + q1 + ')">✖ 删除</span>';
            }
            html += '</div>';
        });
        html += '</div>';
        html += '<div style="cursor:pointer; width:100%; margin-top:8px; padding:5px; border:1px dashed var(--border-color); border-radius:5px; background:transparent; color:var(--accent-primary); font-size:11px; text-align:center;" onclick="showAddRoleForm()">+ 添加自定义角色</div>';
        
        showModal('🎭 选择角色卡', html, [
            { text: '关闭', class: 'modal-btn-cancel', action: closeModal }
        ]);
    } catch (e) {
        console.error('showRoleSelector error:', e);
        showToast('加载角色列表失败', 'error');
    }
}



var currentRoleState = currentRoleState || {
    roleId: 'default',
    roleName: '默认助手',
    roleIcon: '🧑',
    roleDesc: '专业、高效、友好的智能终端助手',
};

function updateRoleDisplay(role) {
    if (!role) role = currentRoleState;
    else currentRoleState = role;

    const card = document.getElementById('roleCard');
    const empty = document.getElementById('roleEmpty');
    const icon = document.getElementById('roleIcon');
    const name = document.getElementById('roleName');
    if (!card || !empty) return;

    if (role && role.roleId) {
        card.style.display = 'flex';
        empty.style.display = 'none';
        if (icon) icon.textContent = role.roleIcon || '🧑';
        if (name) name.textContent = role.roleName || '未知角色';
    } else {
        card.style.display = 'none';
        empty.style.display = 'block';
    }
}


async function loadTemplateCache() {
    try {
        var r = await fetch('/api/personality/templates/all');
        var data = await r.json();
        __templateCache = data.data || data.templates || {};
    } catch(e) {
        console.error('loadTemplateCache error:', e);
    }
}



function showAddRoleForm() {
    closeModal();
    const html = '<div style="display:flex; flex-direction:column; gap:8px;">' +
        '<label style="font-size:12px; color:var(--text-secondary);">角色名称</label>' +
        '<input id="newRoleName" style="padding:7px 10px; border-radius:6px; border:1px solid var(--border-color); background:var(--bg-input); color:var(--text-primary); font-size:13px;" placeholder="请输入角色名称">' +
        '<label style="font-size:12px; color:var(--text-secondary); margin-top:2px;">角色描述</label>' +
        '<input id="newRoleDesc" style="padding:7px 10px; border-radius:6px; border:1px solid var(--border-color); background:var(--bg-input); color:var(--text-primary); font-size:13px;" placeholder="简短描述该角色">' +
        '<label style="font-size:12px; color:var(--text-secondary); margin-top:2px;">图标（可选）</label>' +
        '<input id="newRoleIcon" style="padding:7px 10px; border-radius:6px; border:1px solid var(--border-color); background:var(--bg-input); color:var(--text-primary); font-size:13px;" placeholder="默认 🧑" value="🧑">' +
        '<label style="font-size:12px; color:var(--text-secondary); margin-top:4px;">角色灵魂 (soul.md) <span style="color:var(--text-muted); font-size:10px;">定义角色的核心特质、性格、做事风格</span></label>' +
        '<textarea id="newRoleSoul" style="padding:7px 10px; border-radius:6px; border:1px solid var(--border-color); background:var(--bg-input); color:var(--text-primary); font-size:12px; min-height:120px; resize:vertical; font-family:inherit;" placeholder="# 角色名：\n\n## 🌟 核心身份\n\n## 🎯 做事风格\n\n## 💭 核心信念\n\n## 🧠 性格特征"></textarea>' +
        '</div>';
    showModal('➕ 添加自定义角色', html, [
        { text: '取消', class: 'modal-btn-cancel', action: closeModal },
        { text: '创建角色', class: 'modal-btn-primary', action: createNewRole }
    ]);
    setTimeout(function() {
        const inp = document.getElementById('newRoleName');
        if (inp) inp.focus();
    }, 100);
}

async function createNewRole() {
    const name = document.getElementById('newRoleName')?.value?.trim();
    if (!name) { showToast('角色名称不能为空', 'error'); return; }
    const desc = document.getElementById('newRoleDesc')?.value?.trim() || '';
    const icon = document.getElementById('newRoleIcon')?.value?.trim() || '🧑';
    const soulMd = document.getElementById('newRoleSoul')?.value?.trim() || '';
    try {
        const r = await fetch('/api/personality/templates/custom', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: name, description: desc, icon: icon, soul_md: soulMd })
        });
        const data = await r.json();
        if (data.success) {
            showToast('✅ 角色「' + name + '」创建成功');
            closeModal();
            showRoleSelector();
        } else {
            showToast('❌ 创建失败: ' + (data.detail || data.message || '未知错误'), 'error');
        }
    } catch(e) {
        console.error('createNewRole error:', e);
        showToast('创建角色失败', 'error');
    }
}

async function deleteRoleTemplate(name) {
    if (name === 'Tennine') {
        showToast('❌ Tennine 是默认角色，不可删除', 'error');
        return;
    }
    if (!confirm('确定要删除角色「' + name + '」吗？')) return;
    try {
        const r = await fetch('/api/personality/templates/custom/' + encodeURIComponent(name), {
            method: 'DELETE'
        });
        const data = await r.json();
        if (data.success) {
            showToast('✅ 角色「' + name + '」已删除');
            closeModal();
            showRoleSelector();
        } else {
            showToast('❌ 删除失败: ' + (data.detail || data.message || '未知错误'), 'error');
        }
    } catch(e) {
        console.error('deleteRoleTemplate error:', e);
        showToast('删除角色失败', 'error');
    }
}

// Global template cache to avoid re-fetching
var __templateCache = {};

// Global template cache
var __templateCache = {};

async function closeRoleSubmenu() { var ov = document.querySelector('.role-pool-overlay'); if (ov) ov.remove(); }

async function applyRole(roleName) {
    console.log('[applyRole] Starting for:', roleName);
    closeRoleSubmenu();
    try {
        // Check cache
        var tmpl = __templateCache[roleName];
        console.log('[applyRole] Cache hit:', !!tmpl);
        
        if (!tmpl) {
            console.log('[applyRole] Fetching templates...');
            var r = await fetch('/api/personality/templates/all');
            var data = await r.json();
            var templates = data.data || data.templates || {};
            __templateCache = templates;
            tmpl = templates[roleName];
            console.log('[applyRole] After fetch, found:', !!tmpl, 'keys:', Object.keys(templates).slice(0,5));
        }
        
        if (!tmpl) {
            console.error('[applyRole] Template not found:', roleName);
            showToast('角色卡不存在: ' + roleName, 'error');
            return;
        }
        
        // POST to apply
        console.log('[applyRole] POSTing to /api/personality/template');
        var applyR = await fetch('/api/personality/template', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: roleName })
        });
        console.log('[applyRole] Response status:', applyR.status);
        var applyData = await applyR.json();
        console.log('[applyRole] Response data:', JSON.stringify(applyData));
        
        if (applyData.success) {
            console.log('[applyRole] Success! Updating display');
            updateRoleDisplay({
                roleId: roleName,
                roleName: roleName,
                roleIcon: tmpl.icon || '🧑',
                roleDesc: tmpl.description || ''
            });
            showToast('✅ 已切换到角色卡: ' + roleName);
            
            if (typeof loadSkillsForRole === 'function') {
                loadSkillsForRole(roleName);
            }
        } else {
            var errMsg = applyData.detail || applyData.message || '未知错误';
            console.error('[applyRole] Backend error:', errMsg);
            if (errMsg.includes('忙') || applyR.status === 423) {
                showToast('⏳ 服务器处理中，请稍后再试', 'warning');
            } else {
                showToast('❌ ' + errMsg, 'error');
            }
        }
    } catch (e) {
        console.error('[applyRole] Exception:', e);
        showToast('应用角色卡失败: ' + e.message, 'error');
    }
}








// ============================================================
// Skills Management (Right Sidebar)
// ============================================================

let currentSkillsState = {
    skills: [],
    equippedIds: [],
};

async function loadSkillsForRole(roleName) {
    try {
        // Load skills from API
        const r = await fetch('/api/skills/registry');
        const data = await r.json();
        const skillsList = data.data || [];
        
        // Load equipped skills
        const e = await fetch('/api/personality/equipped-skills');
        const eqData = await e.json();
        const equippedIds = eqData.equipped_ids || [];
        
        currentSkillsState.skills = skillsList;
        currentSkillsState.equippedIds = equippedIds;
        
        // Auto-activate built-in default skills
        skillsList.forEach(function(sk) {
            if (sk.is_builtin && currentSkillsState.equippedIds.indexOf(sk.id) < 0) {
                currentSkillsState.equippedIds.push(sk.id);
                // Async API call to activate
                fetch('/api/skills/' + sk.id + '/activate', { method: 'POST' }).catch(function(){});
                fetch('/api/personality/equip-skill/' + sk.id, { method: 'POST' }).catch(function(){});
            }
        });
        
        renderSkillsCompact();
    } catch (e) {
        console.error('loadSkillsForRole error:', e);
    }
}




function autoEquipDefaultSkills() {
    // Auto-activate all built-in skills that are not yet equipped
    var skills = currentSkillsState.skills || [];
    var equipped = currentSkillsState.equippedIds || [];
    var changed = false;
    
    skills.forEach(function(s) {
        if (s.is_builtin && equipped.indexOf(s.id) < 0) {
            // Activate this built-in skill
            fetch('/api/skills/' + s.id + '/activate', { method: 'POST' })
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    if (data.success) {
                        return fetch('/api/personality/equip-skill/' + s.id, { method: 'POST' });
                    }
                })
                .then(function(r) { if(r) return r.json(); })
                .then(function(data) {
                    if (data && data.success) {
                        if (currentSkillsState.equippedIds.indexOf(s.id) < 0) {
                            currentSkillsState.equippedIds.push(s.id);
                        }
                    }
                })
                .catch(function(e) {
                    console.error('autoEquipDefaultSkills error for', s.id, e);
                });
            changed = true;
        }
    });
}

function openSkillManagerModal() {
    // Load skills data from APIs
    Promise.all([
        fetch('/api/skills/registry').then(function(r) { return r.json(); }),
        fetch('/api/personality/equipped-skills').then(function(r) { return r.json(); })
    ])
    .then(function(results) {
        var skillsData = results[0];
        var eqData = results[1];
        currentSkillsState.skills = skillsData.data || [];
        currentSkillsState.equippedIds = eqData.equipped_ids || [];
        renderSkillManagerModal();
    })
    .catch(function(e) {
        console.error('openSkillManagerModal error:', e);
        showToast('加载技能列表失败', 'error');
    });
}

function renderSkillManagerModal() {
    var skills = currentSkillsState.skills || [];
    var equippedIds = currentSkillsState.equippedIds || [];
    var sq = "'";
    
    var html = '';
    
    // Section 1: Currently equipped skills badges
    var equippedSkills = skills.filter(function(s) { return equippedIds.indexOf(s.id) >= 0; });
    if (equippedSkills.length > 0) {
        html += '<div style="margin-bottom:6px; font-size:11px; color:var(--text-secondary); font-weight:600;">✅ 当前已启用 (' + equippedSkills.length + ')</div>';
        html += '<div style="display:flex; flex-wrap:wrap; gap:4px; margin-bottom:10px;">';
        equippedSkills.forEach(function(s) {
            html += '<span style="display:inline-flex; align-items:center; gap:3px; padding:2px 8px; border-radius:10px; background:rgba(34,197,94,0.15); color:#22c55e; font-size:11px;">' + (s.icon || '⚡') + ' ' + (s.name || s.id) + '</span>';
        });
        html += '</div>';
    } else {
        html += '<div style="margin-bottom:10px; font-size:11px; color:var(--text-muted);">❌ 当前未启用任何技能</div>';
    }
    
    // Section 2: All skills list
    html += '<div style="font-size:11px; color:var(--text-secondary); font-weight:600; margin-bottom:4px; border-top:1px solid var(--border-color); padding-top:8px;">📋 全部技能</div>';
    html += '<div style="max-height:280px; overflow-y:auto;">';
    
    if (skills.length === 0) {
        html += '<div style="text-align:center; padding:12px; color:var(--text-muted); font-size:11px;">暂无可用技能</div>';
    } else {
        skills.forEach(function(s) {
            var isOn = equippedIds.indexOf(s.id) >= 0;
            var isBuiltin = s.is_builtin === true;
            html += '<div style="display:flex; align-items:center; gap:6px; padding:4px 6px; border-radius:4px; margin:1px 0; border:1px solid transparent;">';
            html += '<div style="cursor:pointer; display:flex; align-items:center; gap:6px; flex:1; min-width:0;" onclick="toggleSkillInModal(' + sq + s.id + sq + ')">';
            html += '<span>' + (s.icon || '⚡') + '</span>';
            html += '<span style="flex:1; font-size:12px; color:var(--text-primary); white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">' + (s.name || s.id) + '</span>';
            html += '<span style="font-size:10px; padding:2px 8px; border-radius:10px; flex-shrink:0; background:' + (isOn ? 'rgba(34,197,94,0.2)' : 'rgba(100,100,100,0.15)') + '; color:' + (isOn ? '#22c55e' : '#888') + ';">' + (isOn ? '✅ 已启用' : '❌ 禁用') + '</span>';
            html += '</div>';
            if (!isBuiltin) {
                html += '<div style="cursor:pointer; flex-shrink:0; padding:2px 6px; border-radius:3px; background:rgba(239,68,68,0.12); color:#ef4444; font-size:10px;" onclick="deleteCustomSkillFromModal(' + sq + s.id + sq + ',' + sq + (s.name || s.id) + sq + ')">✖</div>';
            } else {
                html += '<span style="flex-shrink:0; font-size:9px; color:var(--text-muted);">默认</span>';
            }
            html += '</div>';
        });
    }
    html += '</div>';
    
    html += '<div style="cursor:pointer; width:100%; margin-top:8px; padding:5px; border:1px dashed var(--border-color); border-radius:5px; background:transparent; color:var(--accent-primary); font-size:11px; text-align:center;" onclick="showAddSkillFormInModal()">+ 创建自定义技能</div>';
    
    showModal('⚙️ 技能管理', html, [
        { text: '关闭', class: 'modal-btn-cancel', action: closeModal }
    ]);
}

function toggleSkillInModal(skillId) {
    var isCurrentlyEquipped = currentSkillsState.equippedIds.indexOf(skillId) >= 0;
    
    fetch('/api/skills/' + skillId + '/activate', { method: 'POST' })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (!data.success) {
                showToast('技能切换失败', 'error');
                return;
            }
            var method = isCurrentlyEquipped ? 'DELETE' : 'POST';
            return fetch('/api/personality/equip-skill/' + skillId, { method: method });
        })
        .then(function(r) { if(r) return r.json(); })
        .then(function(data) {
            if (data && !data.success) {
                showToast('技能同步失败', 'error');
                return;
            }
            var idx = currentSkillsState.equippedIds.indexOf(skillId);
            if (idx >= 0) {
                currentSkillsState.equippedIds.splice(idx, 1);
            } else {
                currentSkillsState.equippedIds.push(skillId);
            }
            renderSkillManagerModal();
        })
        .catch(function(e) {
            console.error('toggleSkillInModal error:', e);
        });
}

function showAddSkillFormInModal() {
    closeModal();
    var html = '<div style="display:flex; flex-direction:column; gap:8px;">' +
        '<label style="font-size:12px; color:var(--text-secondary);">技能名称 <span style="color:#ef4444;">*</span></label>' +
        '<input id="newSkillName" style="padding:7px 10px; border-radius:6px; border:1px solid var(--border-color); background:var(--bg-input); color:var(--text-primary); font-size:13px;" placeholder="请输入技能名称">' +
        '<label style="font-size:12px; color:var(--text-secondary); margin-top:2px;">技能描述 <span style="color:#ef4444;">*</span></label>' +
        '<textarea id="newSkillDesc" style="padding:7px 10px; border-radius:6px; border:1px solid var(--border-color); background:var(--bg-input); color:var(--text-primary); font-size:12px; min-height:50px; resize:vertical;" placeholder="描述该技能的功能和用途"></textarea>' +
        '<label style="font-size:12px; color:var(--text-secondary); margin-top:2px;">技能 Guide <span style="color:#ef4444;">*</span></label>' +
        '<textarea id="newSkillGuide" style="padding:7px 10px; border-radius:6px; border:1px solid var(--border-color); background:var(--bg-input); color:var(--text-primary); font-size:12px; min-height:80px; resize:vertical; font-family:inherit;" placeholder="编写该技能的指南/使用说明，定义技能的行为逻辑和注意事项"></textarea>' +
        '<label style="font-size:12px; color:var(--text-secondary); margin-top:2px;">图标（可选）</label>' +
        '<input id="newSkillIcon" style="padding:7px 10px; border-radius:6px; border:1px solid var(--border-color); background:var(--bg-input); color:var(--text-primary); font-size:13px;" placeholder="默认 ⚡" value="⚡">' +
        '</div>';
    showModal('➕ 创建自定义技能', html, [
        { text: '取消', class: 'modal-btn-cancel', action: function() { closeModal(); openSkillManagerModal(); } },
        { text: '创建技能', class: 'modal-btn-primary', action: createNewSkillFromModal }
    ]);
    setTimeout(function() {
        var inp = document.getElementById('newSkillName');
        if (inp) inp.focus();
    }, 100);
}

async function createNewSkillFromModal() {
    var name = document.getElementById('newSkillName')?.value?.trim();
    if (!name) { showToast('技能名称不能为空', 'error'); return; }
    var desc = document.getElementById('newSkillDesc')?.value?.trim();
    if (!desc) { showToast('技能描述不能为空', 'error'); return; }
    var guide = document.getElementById('newSkillGuide')?.value?.trim();
    if (!guide) { showToast('技能 Guide 不能为空', 'error'); return; }
    var icon = document.getElementById('newSkillIcon')?.value?.trim() || '⚡';
    try {
        var r = await fetch('/api/skills/registry', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                name: name, 
                short_description: desc, 
                icon: icon,
                guide: guide,
                detail_content: guide
            })
        });
        var data = await r.json();
        if (data.success) {
            showToast('✅ 技能「' + name + '」创建成功');
            closeModal();
            openSkillManagerModal();
        } else {
            showToast('❌ 创建失败: ' + (data.detail || data.message || '未知错误'), 'error');
        }
    } catch(e) {
        console.error('createNewSkill error:', e);
        showToast('创建技能失败', 'error');
    }
}

async function deleteCustomSkillFromModal(skillId, skillName) {
    if (!confirm('确定要删除技能「' + skillName + '」吗？')) return;
    try {
        var r = await fetch('/api/skills/registry/' + encodeURIComponent(skillId), {
            method: 'DELETE'
        });
        var data = await r.json();
        if (data.success) {
            showToast('✅ 技能「' + skillName + '」已删除');
            var rr = await fetch('/api/skills/registry');
            var rd = await rr.json();
            currentSkillsState.skills = rd.data || [];
            closeModal();
            openSkillManagerModal();
        } else {
            showToast('❌ 删除失败: ' + (data.detail || data.message || '未知错误'), 'error');
        }
    } catch(e) {
        console.error('deleteCustomSkill error:', e);
        showToast('删除技能失败', 'error');
    }
}



function toggleSkill(skillId) {
    // Check if currently equipped (local state)
    const isCurrentlyEquipped = currentSkillsState.equippedIds.indexOf(skillId) >= 0;
    
    // Step 1: Toggle in skill engine
    fetch('/api/skills/' + skillId + '/activate', { method: 'POST' })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (!data.success) {
                console.warn('Skill engine toggle failed:', data);
                throw new Error('Skill engine toggle failed');
            }
            // Step 2: Sync with personality engine (equip/unequip)
            const method = isCurrentlyEquipped ? 'DELETE' : 'POST';
            return fetch('/api/personality/equip-skill/' + skillId, { method: method });
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (!data.success) {
                console.warn('Personality engine sync failed:', data);
                throw new Error('Personality engine sync failed');
            }
            // Step 3: Update local state
            const idx = currentSkillsState.equippedIds.indexOf(skillId);
            if (idx >= 0) {
                currentSkillsState.equippedIds.splice(idx, 1);
            } else {
                currentSkillsState.equippedIds.push(skillId);
            }
            // Step 4: Re-render UI
            renderSkillsCompact();
            renderSkillManager();
            // 如果技能管理下拉面板已打开，同步刷新其状态
            if (document.getElementById('skillMenuDropdown') && typeof renderDropdown === 'function') {
                renderDropdown();
            }
        })
        .catch(function(e) {
            console.error('toggleSkill error:', e);
            showToast('❌ 技能切换失败: ' + (e.message || '网络错误'), 'error');
            // 回滚本地状态：重新拉取真实 equipped 状态
            fetch('/api/personality/equipped-skills')
                .then(function(r) { return r.json(); })
                .then(function(eqData) {
                    currentSkillsState.equippedIds = eqData.equipped_ids || [];
                    renderSkillsCompact();
                    if (document.getElementById('skillMenuDropdown') && typeof renderDropdown === 'function') {
                        renderDropdown();
                    }
                })
                .catch(function() {});
        });
}

function toggleSkillManager() {
    const manager = document.getElementById('skillManager');
    const btn = document.getElementById('manageSkillsBtn');
    if (!manager || !btn) return;
    
    const isOpen = manager.style.display !== 'none';
    manager.style.display = isOpen ? 'none' : 'block';
    btn.textContent = isOpen ? '\u2699\ufe0f \u7ba1\u7406\u6280\u80fd' : '\u2716 \u6536\u8d77';
    
    if (!isOpen) {
        renderSkillManager();
    }
}

function renderSkillManager() {
    const container = document.getElementById('skillManagerList');
    if (!container) return;
    
    const skills = currentSkillsState.skills || [];
    const equippedIds = currentSkillsState.equippedIds || [];
    
    if (skills.length === 0) {
        container.innerHTML = '<div style="text-align:center; padding:8px; color:var(--text-muted); font-size:11px;">暂无可用技能</div>' +
            '<button onclick="showAddSkillForm()" style="width:100%; margin-top:6px; padding:5px; border:1px dashed var(--border-color); border-radius:5px; background:transparent; color:var(--accent-primary); cursor:pointer; font-size:11px;">+ 添加自定义技能</button>';
        return;
    }
    
    let html = '<div style="margin-bottom:6px; font-size:10px; color:var(--text-muted);">点击技能切换启用/禁用</div>';
    skills.forEach(function(s) {
        const isOn = equippedIds.includes(s.id);
        const isBuiltin = s.is_builtin === true;
        html += '<div style="display:flex; align-items:center; gap:6px; padding:4px 6px; border-radius:4px; margin:2px 0;">';
        html += '<div onclick="toggleSkill(\'' + s.id + '\')" style="display:flex; align-items:center; gap:6px; flex:1; cursor:pointer; min-width:0;">';
        html += '<span>' + (s.icon || '⚡') + '</span>';
        html += '<span style="flex:1; font-size:12px; color:var(--text-primary); white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">' + (s.name || s.id) + '</span>';
        html += '<span style="font-size:11px; padding:2px 8px; border-radius:10px; flex-shrink:0; background:' + (isOn ? 'rgba(34,197,94,0.2)' : 'rgba(100,100,100,0.15)') + '; color:' + (isOn ? '#22c55e' : '#888') + ';">' + (isOn ? '✔️ 已启用' : '❌ 禁用') + '</span>';
        html += '</div>';
        if (!isBuiltin) {
            html += '<button onclick="event.stopPropagation();deleteCustomSkill(\'' + s.id + '\',\'' + (s.name || s.id) + '\')" style="flex-shrink:0; padding:2px 6px; border:none; border-radius:3px; background:rgba(239,68,68,0.12); color:#ef4444; cursor:pointer; font-size:10px;" title="删除技能">✖</button>';
        }
        html += '</div>';
    });
    html += '<button onclick="showAddSkillForm()" style="width:100%; margin-top:6px; padding:5px; border:1px dashed var(--border-color); border-radius:5px; background:transparent; color:var(--accent-primary); cursor:pointer; font-size:11px;">+ 添加自定义技能</button>';
    
    container.innerHTML = html;
}

function showAddSkillForm() {
    // Reuse the personality modal or create a simple prompt
    const html = '<div style="display:flex; flex-direction:column; gap:10px;">' +
        '<label style="font-size:12px; color:var(--text-secondary);">技能名称</label>' +
        '<input id="newSkillName" style="padding:8px 10px; border-radius:6px; border:1px solid var(--border-color); background:var(--bg-input); color:var(--text-primary); font-size:13px;" placeholder="请输入技能名称">' +
        '<label style="font-size:12px; color:var(--text-secondary); margin-top:4px;">简短描述</label>' +
        '<textarea id="newSkillDesc" style="padding:8px 10px; border-radius:6px; border:1px solid var(--border-color); background:var(--bg-input); color:var(--text-primary); font-size:13px; min-height:60px; resize:vertical;" placeholder="描述该技能的功能"></textarea>' +
        '<label style="font-size:12px; color:var(--text-secondary); margin-top:4px;">图标（可选）</label>' +
        '<input id="newSkillIcon" style="padding:8px 10px; border-radius:6px; border:1px solid var(--border-color); background:var(--bg-input); color:var(--text-primary); font-size:13px;" placeholder="默认 ⚡" value="⚡">' +
        '</div>';
    showModal('➕ 添加自定义技能', html, [
        { text: '取消', class: 'modal-btn-cancel', action: closeModal },
        { text: '创建技能', class: 'modal-btn-primary', action: createNewSkill }
    ]);
    setTimeout(function() {
        const inp = document.getElementById('newSkillName');
        if (inp) inp.focus();
    }, 100);
}

async function createNewSkill() {
    const name = document.getElementById('newSkillName')?.value?.trim();
    if (!name) { showToast('技能名称不能为空', 'error'); return; }
    const desc = document.getElementById('newSkillDesc')?.value?.trim();
    if (!desc) { showToast('简短描述不能为空', 'error'); return; }
    const icon = document.getElementById('newSkillIcon')?.value?.trim() || '⚡';
    try {
        const r = await fetch('/api/skills/registry', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: name, short_description: desc, icon: icon })
        });
        const data = await r.json();
        if (data.success) {
            showToast('✅ 技能「' + name + '」创建成功');
            closeModal();
            // Refresh skill list
            const rr = await fetch('/api/skills/registry');
            const rd = await rr.json();
            currentSkillsState.skills = rd.data || [];
            renderSkillsCompact();
            renderSkillManager();
        } else {
            showToast('❌ 创建失败: ' + (data.detail || data.message || '未知错误'), 'error');
        }
    } catch(e) {
        console.error('createNewSkill error:', e);
        showToast('创建技能失败', 'error');
    }
}

async function deleteCustomSkill(skillId, skillName) {
    if (!confirm('确定要删除技能「' + skillName + '」吗？')) return;
    try {
        const r = await fetch('/api/skills/registry/' + encodeURIComponent(skillId), {
            method: 'DELETE'
        });
        const data = await r.json();
        if (data.success) {
            showToast('✅ 技能「' + skillName + '」已删除');
            // Refresh skill list
            const rr = await fetch('/api/skills/registry');
            const rd = await rr.json();
            currentSkillsState.skills = rd.data || [];
            renderSkillsCompact();
            renderSkillManager();
        } else {
            showToast('❌ 删除失败: ' + (data.detail || data.message || '未知错误'), 'error');
        }
    } catch(e) {
        console.error('deleteCustomSkill error:', e);
        showToast('删除技能失败', 'error');
    }
}
