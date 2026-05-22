/* ============================================================
   TennineClaw - DOM 工具函数
   ============================================================ */

/**
 * 显示 Toast 通知
 */
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    const container = document.getElementById('toastContainer');
    if (container) {
        container.appendChild(toast);
    } else {
        document.body.appendChild(toast);
    }
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease forwards';
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

/**
 * HTML 转义
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * 带超时的 fetch
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
 * 带超时的 fetch + JSON 解析
 */
async function fetchJsonWithTimeout(url, timeoutMs = 5000) {
    const response = await fetchWithTimeout(url, {}, timeoutMs);
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
    }
    return await response.json();
}

/**
 * 日期分组工具
 */
function getDateGroup(timestamp) {
    if (!timestamp) return '其他';
    const date = new Date(timestamp.replace(' ', 'T'));
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    const weekAgo = new Date(today);
    weekAgo.setDate(weekAgo.getDate() - 7);
    const monthStart = new Date(now.getFullYear(), now.getMonth(), 1);

    if (date >= today) return '今天';
    if (date >= yesterday) return '昨天';
    if (date >= weekAgo) return '最近 7 天';
    if (date >= monthStart) return '本月';
    return '更早';
}
