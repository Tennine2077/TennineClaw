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
        activeSessionId: 'default',  // 始终使用默认会话
        sessionInputs: {},      // 保存每个 session 的输入框文字 { sessionId: text }
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

    function addMessage(content, role) {
        if (el.welcomeMessage && !el.welcomeMessage.classList.contains('hidden')) {
            el.welcomeMessage.classList.add('hidden');
            el.welcomeMessage.style.display = 'none';
        }

        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${role}`;
        
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
    function finalizeStreamingContent(contentDiv, fullContent) {
        // 流式完成后，使用带代码高亮的渲染
        contentDiv.innerHTML = renderMarkdownWithHighlight(fullContent);
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
        
        addMessage(text, 'user');
        const { msgDiv: assistantMsg, contentDiv } = createStreamingMessageContainer();
        let fullContent = '';
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
                            fullContent += data.content;
                            updateStreamingContent(contentDiv, fullContent);
                        } else if (data.type === 'optimized_prompt') {
                            // 在用户消息和 AI 回复之间插入优化提示
                            const optDiv = document.createElement('div');
                            optDiv.className = 'optimized-prompt';
                            optDiv.textContent = '✨ Prompt 已优化: ' + data.content;
                            el.messagesContainer.insertBefore(optDiv, assistantMsg);
                        } else if (data.type === 'tool_call') {
                            fullContent += data.content;
                            updateStreamingContent(contentDiv, fullContent);
                        } else if (data.type === 'reasoning') {
                            fullContent += data.content;
                            updateStreamingContent(contentDiv, fullContent);
                        } else if (data.type === 'interrupted') {
                            fullContent += data.content;
                            updateStreamingContent(contentDiv, fullContent);
                        } else if (data.type === 'interrupted_done') {
                            finalizeStreamingContent(contentDiv, fullContent);
                            doneReceived = true;
                            await updateTokenStatus(data.total_tokens, data.max_tokens);
                            await updateFullStatus();
                            await updateSessionTitle();
                            await renderSessionList();
                        } else if (data.type === 'done') {
                            finalizeStreamingContent(contentDiv, fullContent);
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
            
            if (!doneReceived && fullContent) {
                finalizeStreamingContent(contentDiv, fullContent);
                await updateFullStatus();
                await updateSessionTitle();
                await checkPlanMenu();
                await renderSessionList();
            }
            
        } catch (error) {
            if (error.name === 'AbortError') {
                if (fullContent) {
                    finalizeStreamingContent(contentDiv, fullContent + '\n\n> ⏹️ 已中断');
                } else {
                    contentDiv.innerHTML = '⏹️ 已取消';
                }
                await renderSessionList();
            } else {
                if (fullContent) {
                    finalizeStreamingContent(contentDiv, fullContent + `\n\n> ❌ ${error.message}`);
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
            await renderSessionList();
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
            
            // 清空消息区域
            el.messagesContainer.querySelectorAll('.message').forEach(msg => msg.remove());
            el.messagesContainer.querySelectorAll('.optimized-prompt').forEach(opt => opt.remove());
            
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
                addMessage(data.message, 'assistant');
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

        for (const m of messages) {
            if (m.role === 'tool') continue; // 不显示工具调用结果

            const msgDiv = document.createElement('div');
            msgDiv.className = `message ${m.role}`;

            const avatar = document.createElement('div');
            avatar.className = 'message-avatar';
            avatar.textContent = m.role === 'user' ? '👤' : '🧠';

            const contentDiv = document.createElement('div');
            contentDiv.className = 'message-content';

            if (m.role === 'user') {
                contentDiv.textContent = m.content;
            } else {
                contentDiv.innerHTML = renderMarkdownWithHighlight(m.content);
            }

            msgDiv.appendChild(avatar);
            msgDiv.appendChild(contentDiv);
            el.messagesContainer.appendChild(msgDiv);

            // 用户消息如果有优化 Prompt，在下方插入黄色提示框
            if (m.role === 'user' && m.optimized_prompt) {
                const optDiv = document.createElement('div');
                optDiv.className = 'optimized-prompt';
                optDiv.textContent = '✨ Prompt 已优化: ' + m.optimized_prompt;
                el.messagesContainer.appendChild(optDiv);
            }
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
        
        // 清除当前 DOM
        el.messagesContainer.querySelectorAll('.message').forEach(msg => msg.remove());
        el.messagesContainer.querySelectorAll('.optimized-prompt').forEach(opt => opt.remove());
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

            // 2. 清除当前显示的消息
            el.messagesContainer.querySelectorAll('.message').forEach(msg => msg.remove());
            el.messagesContainer.querySelectorAll('.optimized-prompt').forEach(opt => opt.remove());

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
    async function renderSessionList() {
        if (state.isStreaming) return;
        
        try {
            const data = await fetchJsonWithTimeout('/api/sessions/list', 5000);
            state.sessions = data.saved_files || [];
            
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
                        
                        item.innerHTML = `
                            <div class="session-item-title" title="${escapeHtml(title)}">${escapeHtml(displayTitle)}</div>
                            <div class="session-item-meta">
                                <span>${s.timestamp || ''}</span>
                                <span>${msgCount} 条</span>
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
        overlay.onclick = (e) => { if (e.target === overlay) closeModal(); };
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
        localStorage.setItem('theme', newTheme);
        setHighlightTheme(newTheme);
    }

    function loadTheme() {
        const savedTheme = localStorage.getItem('theme') || 'dark';
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

});
