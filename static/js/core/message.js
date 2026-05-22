/* ============================================================
   TennineClaw - 消息 & 流式渲染
   ============================================================ */

/**
 * 添加消息到 DOM
 */
function addMessage(content, role) {
    if (el && el.welcomeMessage && !el.welcomeMessage.classList.contains('hidden')) {
        el.welcomeMessage.classList.add('hidden');
        el.welcomeMessage.style.display = 'none';
    }

    const msgDiv = document.createElement('div');
    msgDiv.className = 'message ' + role;
    
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
    return msgDiv;
}

/**
 * 创建流式消息容器
 */
function createStreamingMessageContainer() {
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message assistant streaming';
    
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = '🧠';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    msgDiv.appendChild(avatar);
    msgDiv.appendChild(contentDiv);
    el.messagesContainer.appendChild(msgDiv);
    el.messagesContainer.scrollTop = el.messagesContainer.scrollHeight;
    
    return { msgDiv, contentDiv };
}

/**
 * 更新流式内容
 */
function updateStreamingContent(contentDiv, fullContent) {
    if (!contentDiv) return;
    contentDiv.innerHTML = renderMarkdownWithHighlight(fullContent);
    const container = document.getElementById('messagesContainer');
    if (container) container.scrollTop = container.scrollHeight;
}

/**
 * 完成流式内容
 */
function finalizeStreamingContent(contentDiv, fullContent) {
    if (!contentDiv) return;
    contentDiv.innerHTML = renderMarkdownWithHighlight(fullContent);
    contentDiv.closest('.message')?.classList.remove('streaming');
}

/**
 * 渲染历史消息列表
 */
async function renderMessages(messages) {
    _thinkingContainers = [];
    
    if (!messages || messages.length === 0) {
        if (el.welcomeMessage) {
            el.welcomeMessage.classList.remove('hidden');
            el.welcomeMessage.style.display = 'block';
        }
        return;
    }

    if (el.welcomeMessage && !el.welcomeMessage.classList.contains('hidden')) {
        el.welcomeMessage.classList.add('hidden');
        el.welcomeMessage.style.display = 'none';
    }

    for (const m of messages) {
        if (m.role === 'tool') continue;

        const msgDiv = document.createElement('div');
        msgDiv.className = 'message ' + m.role;

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

        // 渲染思考内容
        if (m.role !== 'user' && m.reasoning_content) {
            var thinkingContainer = document.createElement('div');
            thinkingContainer.className = 'thinking-container';
            
            var thinkingHeader = document.createElement('div');
            thinkingHeader.className = 'thinking-header';
            
            var thinkingLabel = document.createElement('span');
            thinkingLabel.className = 'thinking-label';
            thinkingLabel.textContent = '💭 思考过程';
            
            var thinkingBtn = document.createElement('button');
            thinkingBtn.className = 'thinking-toggle-btn';
            thinkingBtn.textContent = _thinkingExpanded ? '📜 关闭详情' : '📜 打开详情';
            thinkingBtn.onclick = function(e) {
                e.stopPropagation();
                toggleAllThinking(!_thinkingExpanded);
            };
            
            thinkingHeader.appendChild(thinkingLabel);
            thinkingHeader.appendChild(thinkingBtn);
            thinkingContainer.appendChild(thinkingHeader);
            
            var thinkingBody = document.createElement('div');
            thinkingBody.className = 'thinking-body';
            thinkingBody.textContent = m.reasoning_content;
            thinkingBody.style.display = _thinkingExpanded ? 'block' : 'none';
            thinkingContainer.appendChild(thinkingBody);
            
            _thinkingContainers.push(thinkingContainer);
            el.messagesContainer.insertBefore(thinkingContainer, msgDiv);
        }

        // 优化 Prompt 提示
        if (m.role === 'user' && m.optimized_prompt) {
            const optDiv = document.createElement('div');
            optDiv.className = 'optimized-prompt';
            optDiv.textContent = '✨ Prompt 已优化: ' + m.optimized_prompt;
            el.messagesContainer.appendChild(optDiv);
        }
    }

    el.messagesContainer.scrollTop = el.messagesContainer.scrollHeight;
}
