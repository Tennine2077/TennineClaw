/* ============================================================
   TennineClaw - 思考过程（推理内容）管理
   ============================================================ */

// ===== Thinking fold state =====
var _thinkingExpanded = false;
var _thinkingContainers = [];
var _thinkingBuffers = {};

/**
 * 创建思考容器（流式消息用）
 */
function createThinkingContainer(assistantMsg) {
    var existing = document.getElementById('thinking-container-' + (assistantMsg.id || 'cur'));
    if (existing) return existing;
    
    var container = document.createElement('div');
    container.className = 'thinking-container';
    container.id = 'thinking-container-' + (assistantMsg.id || 'cur');
    
    var header = document.createElement('div');
    header.className = 'thinking-header';
    
    var label = document.createElement('span');
    label.className = 'thinking-label';
    label.textContent = '💭 思考中...';
    
    var toggleBtn = document.createElement('button');
    toggleBtn.className = 'thinking-toggle-btn';
    toggleBtn.textContent = '📜 打开详情';
    toggleBtn.onclick = function(e) {
        e.stopPropagation();
        toggleAllThinking(!_thinkingExpanded);
    };
    
    header.appendChild(label);
    header.appendChild(toggleBtn);
    container.appendChild(header);
    
    var body = document.createElement('div');
    body.className = 'thinking-body';
    body.style.display = 'none';
    container.appendChild(body);
    
    if (assistantMsg && assistantMsg.parentNode) {
        assistantMsg.parentNode.insertBefore(container, assistantMsg);
    }
    
    _thinkingContainers.push(container);
    return container;
}

/**
 * 更新思考内容（流式更新）
 */
function updateThinkingContent(assistantMsg, content) {
    var container = createThinkingContainer(assistantMsg);
    if (!container) return;
    
    var body = container.querySelector('.thinking-body');
    if (body) {
        body.textContent = content;
        body.scrollTop = body.scrollHeight;
    }
}

/**
 * 完成思考内容（流式结束）
 */
function finalizeThinkingContent(assistantMsg) {
    var container = document.getElementById('thinking-container-' + (assistantMsg.id || 'cur'));
    if (!container) {
        _thinkingContainers = _thinkingContainers.filter(function(c) {
            return c.id !== 'thinking-container-' + (assistantMsg.id || 'cur');
        });
        return;
    }
    
    var label = container.querySelector('.thinking-label');
    if (label) label.textContent = '💭 思考过程';
    
    var toggleBtn = container.querySelector('.thinking-toggle-btn');
    if (toggleBtn) toggleBtn.textContent = _thinkingExpanded ? '📜 关闭详情' : '📜 打开详情';
    
    delete _thinkingBuffers['cur'];
}

/**
 * 切换所有思考容器的展开/折叠状态
 */
function toggleAllThinking(expand) {
    _thinkingExpanded = expand;
    for (var i = 0; i < _thinkingContainers.length; i++) {
        var c = _thinkingContainers[i];
        if (!c || !c.parentNode) {
            _thinkingContainers.splice(i, 1);
            i--;
            continue;
        }
        var body = c.querySelector('.thinking-body');
        var btn = c.querySelector('.thinking-toggle-btn');
        if (body) body.style.display = expand ? 'block' : 'none';
        if (btn) btn.textContent = expand ? '📜 关闭详情' : '📜 打开详情';
    }
}

/**
 * 清空思考状态（新流式会话前调用）
 */
function resetThinkingState() {
    _thinkingContainers = [];
    _thinkingBuffers = {};
    _thinkingExpanded = false;
}
