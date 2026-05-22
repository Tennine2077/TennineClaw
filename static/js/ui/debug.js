/* ============================================================
   TennineClaw - 调试面板
   ============================================================ */

var _debugMode = false;
var _debugLog = [];

/**
 * 切换调试模式
 */
function toggleDebugMode() {
    _debugMode = !_debugMode;
    const panel = document.getElementById('debugPanel');
    if (panel) panel.style.display = _debugMode ? 'block' : 'none';
    renderDebugPanel();
}

/**
 * 记录调试日志
 */
function debugLog(msg) {
    if (!_debugMode) return;
    _debugLog.push(new Date().toLocaleTimeString() + ' ' + msg);
    if (_debugLog.length > 200) _debugLog.splice(0, _debugLog.length - 200);
    renderDebugPanel();
}

/**
 * 渲染调试面板
 */
function renderDebugPanel() {
    const dp = document.getElementById('debugPanel');
    if (!dp || !_debugMode) return;
    let html = '<div style="padding:8px;font-size:12px;color:#0f0;font-family:monospace;">';
    for (var i = 0; i < _debugLog.length; i++) {
        html += '<div style="padding:1px 0;border-bottom:1px solid rgba(255,255,255,0.05);word-break:break-all;">'
            + escapeHtml(_debugLog[i]) + '</div>';
    }
    html += '</div>';
    dp.innerHTML = html;
    dp.scrollTop = dp.scrollHeight;
}
