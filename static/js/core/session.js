/* ============================================================
   TennineClaw - 会话管理
   ============================================================ */

/**
 * 创建新会话（前端切换）
 */
async function newChat() {
    try {
        const data = await API.createSession();
        return data.session_id || 'default';
    } catch (e) {
        showToast('创建会话失败: ' + e.message, 'error');
        return null;
    }
}

/**
 * 格式化会话列表的日期
 */
function formatSessionDate(timestamp) {
    if (!timestamp) return '';
    const d = new Date(timestamp.replace(' ', 'T'));
    const now = new Date();
    const isToday = d.toDateString() === now.toDateString();
    return isToday
        ? d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
        : d.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' });
}
