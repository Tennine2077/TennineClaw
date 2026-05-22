/* ============================================================
   TennineClaw - 状态 & Token 显示
   ============================================================ */

/**
 * 更新在线状态指示器
 */
function updateStatusDot(online) {
    const dot = document.getElementById('statusDot');
    if (dot) {
        dot.className = 'status-dot ' + (online ? 'online' : 'offline');
    }
}

/**
 * 更新 Token 状态显示
 */
function updateTokenStatus(totalTokens, maxTokens) {
    const el = {
        totalTokens: document.getElementById('totalTokens'),
        maxTokens: document.getElementById('maxTokens'),
        tokenProgress: document.getElementById('tokenProgress'),
        tokenBar: document.getElementById('tokenBar')
    };
    
    if (el.totalTokens) el.totalTokens.textContent = totalTokens || 0;
    if (el.maxTokens) el.maxTokens.textContent = maxTokens || '—';
    
    if (el.tokenBar && totalTokens != null && maxTokens) {
        const pct = Math.min((totalTokens / maxTokens) * 100, 100);
        el.tokenBar.style.width = pct + '%';
        el.tokenBar.className = 'token-bar-fill' + (pct > 90 ? ' danger' : pct > 70 ? ' warning' : '');
    }
}
