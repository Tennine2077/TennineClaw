/*
  TennineClaw - Individual Block Display
  Each thinking / tool_call is its own collapsible block.
  Two separate collapse states: thinking vs tool_call.
  Final response below as a separate block.
  Inline onclick for reliable collapse.
  State persists via localStorage.
*/

(function(){
  'use strict';

  // ===== Global Thinking Collapse State =====
  window.stateThinkingCollapsed = false;
  try {
    if (localStorage.getItem('tennine_thinking_collapsed') === 'true') window.stateThinkingCollapsed = true;
  } catch(e) {}

  window.toggleThinkingCollapse = function() {
    window.stateThinkingCollapsed = !window.stateThinkingCollapsed;
    applyThinkingState();
    try { localStorage.setItem('tennine_thinking_collapsed', window.stateThinkingCollapsed ? 'true' : 'false'); } catch(e) {}
  };

  function applyThinkingState() {
    var show = !window.stateThinkingCollapsed;
    var contents = document.querySelectorAll('.indiv-block.thinking > .indiv-content');
    for (var i = 0; i < contents.length; i++) {
      contents[i].style.display = show ? 'block' : 'none';
    }
    var labels = document.querySelectorAll('.indiv-block.thinking .collapse-label');
    var icon = show ? '\u25bc' : '\u25b6';
    for (var i = 0; i < labels.length; i++) {
      labels[i].textContent = icon;
    }
  }

  // ===== Global ToolCall Collapse State =====
  window.stateToolCallCollapsed = false;
  try {
    if (localStorage.getItem('tennine_toolcall_collapsed') === 'true') window.stateToolCallCollapsed = true;
  } catch(e) {}

  window.toggleToolCallCollapse = function() {
    window.stateToolCallCollapsed = !window.stateToolCallCollapsed;
    applyToolCallState();
    try { localStorage.setItem('tennine_toolcall_collapsed', window.stateToolCallCollapsed ? 'true' : 'false'); } catch(e) {}
  };

  function applyToolCallState() {
    var show = !window.stateToolCallCollapsed;
    var contents = document.querySelectorAll('.indiv-block.toolcall > .indiv-content');
    for (var i = 0; i < contents.length; i++) {
      contents[i].style.display = show ? 'block' : 'none';
    }
    var labels = document.querySelectorAll('.indiv-block.toolcall .collapse-label');
    var icon = show ? '\u25bc' : '\u25b6';
    for (var i = 0; i < labels.length; i++) {
      labels[i].textContent = icon;
    }
  }

  // ===== Sync both states (called after DOM update) =====
  window.syncRoundCollapse = function() {
    try { applyThinkingState(); } catch(e) {}
    try { applyToolCallState(); } catch(e) {}
  };

  // ===== Simple escape =====
  function esc(t) {
    if (!t) return '';
    return t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  // ===== buildSegmentedHtml =====
  // Returns {html: string, thinkCount: number, toolCount: number}
  // Each thinking / tool_call block is an independent collapsible box.
  // Response text rendered below.
  // startThink, startTool: offset counters for session-wide sequential numbering.
  window.buildSegmentedHtml = function(orderedBlocks, responseHtml, isStreaming, startThink, startTool) {
    if (!orderedBlocks) orderedBlocks = [];
    var tIcon = window.stateThinkingCollapsed ? '\u25b6' : '\u25bc';
    var tDisp = window.stateThinkingCollapsed ? 'none' : 'block';
    var tcIcon = window.stateToolCallCollapsed ? '\u25b6' : '\u25bc';
    var tcDisp = window.stateToolCallCollapsed ? 'none' : 'block';

    var thinkCount = startThink || 0;
    var toolCount = startTool || 0;
    var parts = [];

    for (var i = 0; i < orderedBlocks.length; i++) {
      var block = orderedBlocks[i];
      if (!block.content || !block.content.trim()) continue;

      if (block.type === 'thinking') {
        thinkCount++;
        parts.push('<div class="indiv-block thinking">');
        parts.push('<div class="indiv-header" onclick="window.toggleThinkingCollapse()"><span class="collapse-label">' + tIcon + '</span> \uD83E\uDDE0 \u7b2c' + thinkCount + '\u6b21\u63a8\u7406\u8fc7\u7a0b</div>');
        parts.push('<div class="indiv-content" style="display:' + tDisp + '"><pre>' + esc(block.content) + '</pre></div>');
        parts.push('</div>');
      } else if (block.type === 'tool_call') {
        toolCount++;
        parts.push('<div class="indiv-block toolcall">');
        parts.push('<div class="indiv-header" onclick="window.toggleToolCallCollapse()"><span class="collapse-label">' + tcIcon + '</span> \uD83D\uDD27 \u7b2c' + toolCount + '\u6b21\u5de5\u5177\u8c03\u7528</div>');
        parts.push('<div class="indiv-content" style="display:' + tcDisp + '"><pre>' + esc(block.content) + '</pre></div>');
        parts.push('</div>');
      }
    }

    if (responseHtml && responseHtml.trim()) {
      parts.push('<div class="response-block">' + responseHtml + '</div>');
    }

    var html = parts.join('\n');
    if (isStreaming) html += '<span class="streaming-cursor">\u258a</span>';
    return {html: html, thinkCount: thinkCount, toolCount: toolCount};
  };

  // ===== roundsToBlocks: rounds from backend -> orderedBlocks =====
  window.roundsToBlocks = function(rounds) {
    var blocks = [];
    var lastResponse = '';
    for (var ri = 0; ri < rounds.length; ri++) {
      var r = rounds[ri];
      if (r.thinking && r.thinking.trim()) {
        blocks.push({type: 'thinking', content: r.thinking});
      }
      var tcs = r.tool_calls || [];
      for (var ti = 0; ti < tcs.length; ti++) {
        var tc = tcs[ti];
        var tcContent = '\uD83D\uDD27 ' + tc.name + '\n';
        if (tc.arguments) tcContent += '\u53c2\u6570: ' + tc.arguments + '\n';
        if (tc.result) tcContent += '\u8fd4\u56de\u7ed3\u679c: ' + tc.result;
        blocks.push({type: 'tool_call', content: tcContent});
      }
      if (r.response && r.response.trim()) {
        lastResponse = r.response;
      }
    }
    return {orderedBlocks: blocks, responseText: lastResponse};
  };

  // ===== Apply initial state =====
  applyThinkingState();
  applyToolCallState();
  console.log('[Patch] Individual block display ready');
})();
