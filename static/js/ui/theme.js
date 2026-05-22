/* ============================================================
   TennineClaw - 主题 & UI 交互
   ============================================================ */

/**
 * 设置 highlight.js 主题
 */
function setHighlightTheme(theme) {
    const link = document.getElementById('hljsTheme');
    if (link) {
        link.href = `https://cdn.jsdelivr.net/gh/highlightjs/cdn-release/build/styles/${theme}.min.css`;
    }
}

/**
 * 切换明暗主题
 */
function toggleTheme() {
    const html = document.documentElement;
    const current = html.getAttribute('data-theme');
    const theme = current === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
    setHighlightTheme(theme === 'dark' ? 'github-dark' : 'github-light');
    const btn = document.getElementById('themeToggle');
    if (btn) btn.textContent = theme === 'dark' ? '🌙' : '☀️';
}

/**
 * 加载已保存的主题
 */
function loadTheme() {
    const saved = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', saved);
    setHighlightTheme(saved === 'dark' ? 'github-dark' : 'github-light');
    const btn = document.getElementById('themeToggle');
    if (btn) btn.textContent = saved === 'dark' ? '🌙' : '☀️';
}

/**
 * 切换侧边栏
 */
function toggleSidebar() {
    const sidebar = document.getElementById('leftSidebar');
    const toggle = document.getElementById('sidebarToggle');
    if (sidebar) {
        sidebar.classList.toggle('collapsed');
        if (toggle) toggle.textContent = sidebar.classList.contains('collapsed') ? '☰' : '☰';
    }
}

/**
 * 切换可折叠面板
 */
function toggleCollapsible(header, body) {
    if (!header || !body) return;
    const isOpen = body.style.display !== 'none';
    body.style.display = isOpen ? 'none' : 'block';
    header.classList.toggle('collapsed', isOpen);
}

/**
 * 自动调整 textarea 高度
 */
function autoResizeTextarea() {
    const textarea = document.getElementById('chatInput');
    if (!textarea) return;
    const adjust = () => {
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
    };
    textarea.addEventListener('input', adjust);
    // 初始调整
    setTimeout(adjust, 100);
}
