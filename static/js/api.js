/* ============================================================
   TennineClaw - API 调用封装
   ============================================================ */

const API = {
    // 基础路径
    BASE: '',

    /**
     * 通用请求方法
     */
    async _request(method, path, body = null) {
        const options = {
            method,
            headers: {
                'Content-Type': 'application/json',
            },
        };
        if (body) {
            options.body = JSON.stringify(body);
        }
        
        try {
            const response = await fetch(`${this.BASE}${path}`, options);
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
            }
            return await response.json();
        } catch (error) {
            if (error.name === 'TypeError' && error.message.includes('fetch')) {
                throw new Error('网络连接失败，请检查服务器是否运行');
            }
            throw error;
        }
    },

    /**
     * 发送聊天消息（非流式）
     */
    async sendMessage(message) {
        return this._request('POST', '/api/chat', { message });
    },

    /**
     * 发送聊天消息（流式，返回 EventSource）
     */
    sendMessageStream(message) {
        const url = `${this.BASE}/api/chat/stream`;
        return fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message }),
        });
    },

    /**
     * 切换到 Smart 模式
     */
    async switchToSmart() {
        return this._request('POST', '/api/mode/smart');
    },

    /**
     * 切换到 Plan 模式
     */
    async switchToPlan() {
        return this._request('POST', '/api/mode/plan');
    },

    /**
     * 获取完整状态
     */
    async getFullStatus() {
        return this._request('GET', '/api/status');
    },

    /**
     * 获取实时状态
     */
    async getRealtimeStatus() {
        return this._request('GET', '/api/status/realtime');
    },

    /**
     * 获取会话标题
     */
    async getSessionTitle() {
        return this._request('GET', '/api/session/title');
    },

    /**
     * 获取会话列表
     */
    async listSessions() {
        return this._request('GET', '/api/sessions/list');
    },

    /**
     * 保存会话
     */
    async saveSession(title = '') {
        return this._request('POST', '/api/session/save', { title });
    },

    /**
     * 加载会话
     */
    async loadSession(path) {
        return this._request('POST', '/api/session/load', { path });
    },

    /**
     * 删除会话
     */
    async deleteSession(path) {
        return this._request('POST', '/api/session/delete', { path });
    },

    /**
     * 设置 Python 环境
     */
    async setPythonEnv(path) {
        return this._request('POST', '/api/env/set', { path });
    },

    /**
     * 获取 Python 环境信息
     */
    async getPythonEnv() {
        return this._request('GET', '/api/env/info');
    },

    /**
     * 获取当前 Python 环境状态
     */
    async getCurrentEnv() {
        return this._request('GET', '/api/env/current');
    },

    /**
     * 列出所有 conda 环境
     */
    async listCondaEnvs() {
        return this._request('GET', '/api/env/conda/list');
    },

    /**
     * 切换 conda 环境
     */
    async switchCondaEnv(envName) {
        return this._request('POST', '/api/env/conda/switch', { env_name: envName });
    },

    /**
     * 创建 conda 环境
     */
    async createCondaEnv(envName, pythonVersion = '3.10') {
        return this._request('POST', '/api/env/conda/create', { env_name: envName, python_version: pythonVersion });
    },

    /**
     * 获取当前会话消息（加载会话后渲染用）
     */
    async getSessionMessages(sessionId) {
        let url = '/api/chat/messages';
        if (sessionId && sessionId !== 'default') {
            url += '?session_id=' + encodeURIComponent(sessionId);
        }
        return this._request('GET', url);
    },

    /**
     * 获取可用模型列表
     */
    async listModels() {
        return this._request('GET', '/api/models');
    },

    /**
     * 切换模型
     */
    async switchModel(modelCode) {
        return this._request('PUT', '/api/models/switch', { model_name: modelCode });
    },

    /**
     * 添加自定义模型（名称、Code、Base URL、API Key）
     */
    async addCustomModel(name, code, baseUrl = '', apiKey = '') {
        return this._request('POST', '/api/models/add', {
            name: name,
            code: code,
            base_url: baseUrl,
            api_key: apiKey,
        });
    },

    /**
     * 删除自定义模型
     */
    async deleteModel(code) {
        return this._request('DELETE', `/api/models/${encodeURIComponent(code)}`);
    },

    /**
     * 更新指定模型的 API 配置（base_url, api_key）
     */
    async updateModelConfig(code, config) {
        return this._request('PUT', `/api/models/${encodeURIComponent(code)}/config`, config);
    },

    /**
     * 获取环境配置（Python / Conda）
     */
    async getConfig() {
        return this._request('GET', '/api/config');
    },

    /**
     * 更新环境配置（Python / Conda）
     */
    async updateConfig(config) {
        return this._request('PUT', '/api/config', config);
    },

    /**
     * Plan 菜单操作
     */
    async planAction(action) {
        return this._request('POST', '/api/plan/action', { action });
    },

    /**
     * 检查 Plan 菜单是否就绪
     */
    async checkPlanReady() {
        return this._request('GET', '/api/plan/check');
    },

    /**
     * 手动压缩上下文
     */
    async compactContext() {
        // 添加请求超时控制（180秒超时）
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 180000);
        try {
            const response = await fetch(this.BASE + '/api/context/compact', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                signal: controller.signal
            });
            clearTimeout(timeoutId);
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
            }
            return await response.json();
        } catch (error) {
            clearTimeout(timeoutId);
            if (error.name === 'AbortError') {
                throw new Error('压缩请求超时，请重试');
            }
            if (error.name === 'TypeError' && error.message.includes('fetch')) {
                throw new Error('网络连接失败，请检查服务器是否运行');
            }
            throw error;
        }
    },

    /**
     * 获取帮助文本
     */
    async getHelp() {
        return this._request('GET', '/api/context/help');
    },

    /**
     * 获取状态文本
     */
    async getStatusText() {
        return this._request('GET', '/api/context/status');
    },

    // ============================================================
    // 多会话 + 打断
    // ============================================================

    /** 创建新会话 */
    async createSession() {
        return this._request('POST', '/api/session/new');
    },

    /** 获取当前活动会话 */
    async getActiveSession() {
        return this._request('GET', '/api/session/active');
    },

    /** 列出所有活跃会话（注册表中的） */
    async listAllSessions() {
        return this._request('GET', '/api/sessions');
    },

    /** 激活指定会话 */
    async activateSession(sessionId) {
        return this._request('POST', `/api/session/${encodeURIComponent(sessionId)}/activate`);
    },

    /** 打断指定会话 */
    async interruptChat(sessionId) {
        return this._request('POST', `/api/chat/${encodeURIComponent(sessionId)}/interrupt`);
    },

    /** 从注册表删除会话 */
    async deleteRegisteredSession(sessionId) {
        return this._request('DELETE', `/api/session/${encodeURIComponent(sessionId)}`);
    },
};
