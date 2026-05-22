/* ============================================================
   TennineClaw - Markdown 渲染工具
   ============================================================ */

/**
 * 使用 marked.js 渲染 Markdown
 */
function renderMarkdown(text) {
    if (typeof marked !== "undefined" && marked.parse) {
        return marked.parse(text, { breaks: true, gfm: true });
    }
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

/**
 * 渲染 Markdown 并高亮代码块
 */
function renderMarkdownWithHighlight(text) {
    if (typeof marked === "undefined" || !marked.parse) {
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    }
    const html = marked.parse(text, { breaks: true, gfm: true });
    const temp = document.createElement("div");
    temp.innerHTML = html;
    if (typeof hljs !== "undefined" && hljs.highlightElement) {
        temp.querySelectorAll("pre code").forEach(function(block) {
            hljs.highlightElement(block);
        });
    }
    return temp.innerHTML;
}
