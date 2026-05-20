# TennineClaw Project Documentation

> **Version**: 1.0.0
> **Language**: English | [🇨🇳 中文](DOCUMENTATION.md)
> **Description**: Intelligent Terminal Assistant — AI-Powered Code Analysis & Task Execution Web Platform
> **License**: MIT License
> **Project Path**: `D:\Code\tools\Claude_code_learn\TennineClaw`

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture Overview](#2-architecture-overview)
3. [Module & Function Details](#3-module--function-details)
   - [3.1 `__init__.py` — Version Info](#31-__init__py--version-info)
   - [3.2 `config.py` — Global Configuration](#32-configpy--global-configuration)
   - [3.3 `main.py` — Agent Session Core Logic](#33-mainpy--agent-session-core-logic)
   - [3.4 `main_stream.py` — Streaming Chat Processing](#34-main_streampy--streaming-chat-processing)
   - [3.5 `context.py` — Triple Context Manager (Composer)](#35-contextpy--triple-context-manager-composer)
   - [3.6 `mode_manager.py` — Mode Manager](#36-mode_managerpy--mode-manager)
   - [3.7 `prompts.py` — System Prompt Builder](#37-promptspy--system-prompt-builder)
   - [3.8 `prompt_optimizer.py` — Smart Prompt Optimization](#38-prompt_optimizerpy--smart-prompt-optimization)
   - [3.9 `safety.py` — Command Safety Detection](#39-safetypy--command-safety-detection)
   - [3.10 `session_manager.py` — Session Persistence Management](#310-session_managerpy--session-persistence-management)
   - [3.11 `token_utils.py` — Token Statistics Utilities](#311-token_utilspy--token-statistics-utilities)
   - [3.12 `web_api.py` — FastAPI Web Service Layer](#312-web_apipy--fastapi-web-service-layer)
   - [3.13 `tools/__init__.py` — Tool Registration & Dispatch](#313-tools__init__py--tool-registration--dispatch)
   - [3.14 `tools/cmd_exec.py` — Command Execution Tool](#314-toolscmd_execpy--command-execution-tool)
   - [3.15 `tools/file_ops.py` — File Operations Tool](#315-toolsfile_opspy--file-operations-tool)
   - [3.16 `tools/dir_ops.py` — Directory Operations Tool](#316-toolsdir_opspy--directory-operations-tool)
   - [3.17 `tools/info_ops.py` — Info Query Tool](#317-toolsinfo_opspy--info-query-tool)
   - [3.18 `tools/search_ops.py` — Search & Replace Tool](#318-toolssearch_opspy--search--replace-tool)
   - [3.19 `tools/git_ops.py` — Git Operations Tool](#319-toolsgit_opspy--git-operations-tool)
4. [Data Flow](#4-data-flow)

---

## 1. Project Overview

**TennineClaw** is an AI-powered intelligent terminal assistant web platform. Its core capabilities include:

- **Streaming Chat** — AI responds in paragraphs with real-time reasoning display
- **19 Practical Tools** — AI-autonomous code analysis, file operations, Git integration, etc.
- **Triple Context Compression (Composer)** — Intelligent management of conversation token consumption
- **Dual-Mode Architecture** — Smart (intelligent processing) and Plan (plan-driven) modes
- **Multi-Session Management** — Manage multiple chat sessions simultaneously, supports save/restore
- **Smart Prompt Optimization** — AI automatically optimizes user input for better responses
- **Conda Environment Management** — Create and switch Python virtual environments online
- **Custom Model Management** — Register and switch between multiple AI models
- **Web UI** — FastAPI-based RESTful API + static frontend pages

**Tech Stack**: Python 3.10+, FastAPI, OpenAI SDK, SSE Streaming, JavaScript/HTML/CSS, Conda

---

## 2. Architecture Overview

```
TennineClaw/
├── __init__.py              # Version declaration
├── config.py                # Global config (API Key, models, thresholds, etc.)
├── main.py                  # AgentSession class (sync chat + tool dispatch + mode/env/model mgmt)
├── main_stream.py           # AgentSessionStreamMixin (streaming chat mixin)
├── context.py               # Triple Composer (Micro/Auto/Manual compressors)
├── mode_manager.py          # ModeManager (Smart/Plan mode state machine)
├── prompts.py               # System Prompt builder
├── prompt_optimizer.py      # User Prompt smart optimization
├── safety.py                # Command safety detection
├── session_manager.py       # Session CRUD + SessionRegistry
├── token_utils.py           # Token usage stats utilities
├── web_api.py               # FastAPI service + routes + status cache
├── tools/                   # Tool package directory
│   ├── __init__.py          # Tool registry + dispatch_tool scheduler
│   ├── cmd_exec.py          # System command execution (run_cmd)
│   ├── file_ops.py          # File read/write/delete
│   ├── dir_ops.py           # Directory list/search/create
│   ├── info_ops.py          # System info/time
│   ├── search_ops.py        # Search/replace/count/diff
│   └── git_ops.py           # Git operations (status/log/diff/commit_stats)
└── static/                  # Frontend static files
    ├── index.html           # Main page
    ├── css/style.css        # Styles
    └── js/                  # JavaScript
        ├── api.js           # API request wrapper
        └── app.js           # UI logic
```

**Data Flow Overview**:

```
User Input → Web UI / CLI
     ↓
AgentSession.process_message_stream() / process_message()
     ↓
Prompt Optimization (prompt_optimizer.py) → System prompt injection
     ↓
→ Special commands (/clear, /save, etc.) → Direct return
→ Normal chat → OpenAI API (stream/non-stream)
     ↓
     ← Tool calls → Execute (tools/) → Append results to messages → Continue API call
     ← Text reply → Chunk output → Micro Composer cleanup → Auto save
```

---

## 3. Module & Function Details

### 3.1 `__init__.py` — Version Info

**Source**: Project root entry file
**Purpose**: Declares project version number, description, and license info

| Variable | Value | Description |
|----------|-------|-------------|
| `__version__` | `"1.0.0"` | Current version, referenced by API responses and frontend display |
| `__description__` | `"Intelligent Terminal Assistant"` | Project description |

### 3.2 `config.py` — Global Configuration

**Source**: Project root
**Purpose**: Manages global configuration with a priority chain: `user_config.json` > environment variables > default values. Supports persistent writes.

#### Key Functions

| Function | Description |
|----------|-------------|
| `get_config(key, env_key, default)` | Get config by priority chain |
| `_load_user_config()` | Load persistent config from `user_config.json` |
| `_save_user_config(config)` | Merge and write config to `user_config.json` |
| `get_model_api_overrides()` | Get per-model API override configs |
| `save_model_api_override(code, base_url, api_key)` | Save API override for a single model |

#### Key Configuration Items

| Key | Default | Description |
|-----|---------|-------------|
| `COMPOSER_ENABLED` | `True` | Master switch for context compression |
| `MICRO_COMPOSER_KEEP_ROUNDS` | 2 | Recent chat rounds to keep in Micro Composer |
| `HIGH_RISK_PATTERNS` | `["rm -rf", "del /s /q", ...]` | List of high-risk command patterns |

### 3.3 `main.py` — Agent Session Core Logic

**Source**: Core business module
**Purpose**: Defines the `AgentSession` class, managing complete conversation lifecycle including state management, tool dispatch, mode switching, model management, Python/Conda environment, and session save/restore.

#### AgentSession Class — Key Methods

| Method | Description |
|--------|-------------|
| `__init__(session_id, mode)` | Initialize session: API client, dual-track message storage, Token counting, Composer stats, title system, environment config |
| `reset()` | Reset session to initial state (clear all context & stats) |
| `switch_mode(mode)` | Switch between Smart/Plan mode, rebuild system prompt |
| `save(path)` | Save session to file via `session_manager.save_session()` |
| `load(path)` | Restore session from file via `session_manager.restore_session()` |
| `compact_context()` | Manually trigger Manual Composer compression |
| `get_available_models()` | Get list of available models |
| `switch_model(code)` | Switch current AI model |
| `add_custom_model(name, code, base_url, api_key)` | Add a custom model |

#### Context Compression Methods

| Method | Description |
|--------|-------------|
| `_run_micro_composer()` | Auto-clean old tool info after each round (keep last 2 rounds) |
| `_run_auto_composer_if_needed()` | Auto-trigger semantic compression when input tokens reach 80% threshold |

### 3.4 `main_stream.py` — Streaming Chat Processing

**Source**: Mixin class for `AgentSession`
**Purpose**: Provides streaming chat processing supporting SSE paragraph-by-paragraph push, reasoning summary extraction, and tool call chain handling.

#### Key Function

| Function | Description |
|----------|-------------|
| `_split_into_paragraphs(text, min_chars)` | Split text into chunks by natural paragraphs/sentences |
| `_get_reasoning_summary(reasoning_text, max_chars)` | Extract summary from complete reasoning content |

#### AgentSessionStreamMixin Class

| Method | Description |
|--------|-------------|
| `process_message_stream(user_input)` | Core streaming method, yields AI replies paragraph-by-paragraph as a generator |

**`process_message_stream` Flow**:
1. **Command parsing** — Same as `process_message`, but uses `yield`
2. **Mode injection** — Injects system prompt
3. **Prompt optimization** — Optimized input sent via `__OPT__` prefix
4. **Streaming loop**:
   - Calls `OpenAI chat.completions.create` (`stream=True`)
   - **Interrupt detection** — Checks `self._stream_interrupted` flag
   - Collects `content`, `reasoning_content`, `tool_calls`
   - On `tool_calls` → execute tool → stream tool info → continue loop
   - No `tool_calls` → yield `content` paragraph-by-paragraph → end
5. **Post-processing** — Micro Composer → Auto save → Status cache update
6. **Exception safety** — `try/finally` ensures `auto_save` even on disconnect

### 3.5 `context.py` — Triple Context Manager (Composer)

**Source**: Independent module
**Purpose**: Provides three levels of context compression strategies to manage conversation token consumption.

#### 1️⃣ Micro Composer — Per-Round Auto Cleanup

| Function | Description |
|----------|-------------|
| `micro_composer(msgs)` | Auto-clean old tool call info after each round. Keeps all user/assistant text, but only retains the last 2 rounds of tool call details. Pure deletion, no LLM call. |
| `_split_into_rounds(msgs)` | Split messages into "rounds" grouped by user messages |

#### 2️⃣ Auto Composer — Threshold-Triggered Semantic Compression

| Function | Description |
|----------|-------------|
| `auto_composer(msgs, client, system_prompt)` | Auto-triggered when input tokens reach threshold (80% of limit). Uses LLM to semantically compress old rounds into summaries. |
| `_compress_rounds(rounds, client, system_prompt)` | Core compression logic that calls LLM to generate summaries |

#### 3️⃣ Manual Composer — User-Initiated Full Compression

| Function | Description |
|----------|-------------|
| `manual_composer(msgs, client, system_prompt)` | Triggered by `/compact` command. Compresses ALL conversation context using LLM semantic summarization. |

**Compression Strategy Comparison**:

| Feature | Micro | Auto | Manual |
|---------|-------|------|--------|
| Trigger | Per-round auto | Token at 80% | `/compact` command |
| Method | Delete tool details | LLM summary of old rounds | LLM summary of all |
| Cost | Free | LLM call (old rounds) | LLM call (all) |
| Speed | Instant | Slow (LLM dependent) | Slow (LLM dependent) |

### 3.6 `mode_manager.py` — Mode Manager

**Source**: Independent module
**Purpose**: Manages Smart and Plan dual-mode state machine.

| Function/Class | Description |
|----------------|-------------|
| `MODE_SMART` | Smart mode constant |
| `MODE_PLAN` | Plan mode constant |
| `ModeManager` class | Manages mode state switching and instructions |
| `PlanMode` class | Plan mode workflow (explore → modify → execute → confirm → reset) |

### 3.7 `prompts.py` — System Prompt Builder

**Source**: Independent module
**Purpose**: Builds different system prompts based on mode, tools, and optional personality.

| Function | Description |
|----------|-------------|
| `build_system_prompt(mode, tools, personality)` | Build complete system prompt |
| `get_base_prompt()` | Get base system prompt |
| `get_tool_descriptions(tools)` | Generate tool descriptions for LLM function calling |
| `get_mode_prompt(mode)` | Get mode-specific prompt additions |
| `get_personality_prompt(personality)` | Get personality prompt if available |

### 3.8 `prompt_optimizer.py` — Smart Prompt Optimization

**Source**: Independent module
**Purpose**: AI-driven user input optimization for better response quality.

| Function | Description |
|----------|-------------|
| `optimize_prompt(user_input, context)` | Optimize user input using LLM |
| `get_optimization_result()` | Get optimization result with before/after comparison |
| `is_optimization_enabled()` | Check if optimization is enabled |

### 3.9 `safety.py` — Command Safety Detection

**Source**: Independent module
**Purpose**: Prevents execution of dangerous system commands.

| Function | Description |
|----------|-------------|
| `check_command(cmd)` | Check if a command is safe to execute |
| `is_dangerous(cmd)` | Check against dangerous command patterns |
| `sanitize_command(cmd)` | Sanitize and normalize command input |
| `get_dangerous_patterns()` | Get list of blocked command patterns |

### 3.10 `session_manager.py` — Session Persistence Management

**Source**: Independent module
**Purpose**: Provides session CRUD, persistence, global registry for multi-session management.

#### Core CRUD Functions

| Function | Description |
|----------|-------------|
| `save_session(session, path, save_dir)` | Serialize AgentSession to JSON file |
| `load_session(path)` | Load session data from JSON file |
| `restore_session(session, path)` | Restore session from JSON to AgentSession object |
| `list_sessions(save_dir)` | List all saved sessions with title, time, message count, mode |
| `delete_session(path)` | Delete session file from disk |
| `auto_save(session, session_save_path, save_dir)` | Auto-save session as independent file |

#### SessionRegistry Class — Multi-Session Registry

| Method | Description |
|--------|-------------|
| `create(session_id)` | Create and register new session (auto UUID if not specified) |
| `get(session_id)` | Get session instance (thread-safe) |
| `get_lock(session_id)` | Get session-specific thread lock |
| `get_or_create(session_id)` | Get or create session |
| `remove(session_id)` | Remove from registry (keeps file) |
| `set_active(session_id)` | Set current active session |
| `get_active()` | Get current active session ID |
| `load_from_path(filepath)` | Load session from file into registry |
| `all_sessions()` | Get all sessions as `Dict[str, AgentSession]` |

### 3.11 `token_utils.py` — Token Statistics Utilities

| Function | Description |
|----------|-------------|
| `count_tokens(text)` | Count tokens in text using model-specific tokenizer |
| `format_token_count(count)` | Format token count for display (e.g., "1,234") |
| `calculate_token_ratio(used, total)` | Calculate token usage percentage |

### 3.12 `web_api.py` — FastAPI Web Service Layer

**Source**: API layer module
**Purpose**: Provides RESTful API endpoints for frontend communication.

**37+ Routes covering**:
- Chat streaming (`/api/chat/stream`)
- Session management (CRUD)
- Model management (list, switch, custom models)
- Configuration (get/set)
- System status and tools listing
- Static file serving

### 3.13 `tools/__init__.py` — Tool Registration & Dispatch

**Source**: `tools/` package
**Purpose**: Provides decorator-based tool registration and dispatch system.

| Function | Description |
|----------|-------------|
| `register_tool(name, description)` | Decorator to register a function as a tool |
| `get_all_tools()` | Get all registered tools |
| `get_tool_schemas()` | Get tool schemas in OpenAI function-calling format |
| `execute_tool(name, params)` | Execute a tool by name with parameters |
| `dispatch_tool(tool_calls)` | Dispatch multiple tool calls |

### 3.14 `tools/cmd_exec.py` — Command Execution Tool

| Function | Description |
|----------|-------------|
| `tool_run_cmd(cmd)` | Execute system command with safety check and 30s timeout |
| `_check_dangerous(cmd)` | Internal dangerous command detection |

### 3.15 `tools/file_ops.py` — File Operations Tool

| Function | Description |
|----------|-------------|
| `tool_read_file(path)` | Read file content (UTF-8, handles encoding errors, 20K char truncation) |
| `tool_write_file(path, content)` | Write/overwrite file (auto-creates parent directories) |
| `tool_delete_file(path)` | Delete file or empty dir (with system path protection) |

### 3.16 `tools/dir_ops.py` — Directory Operations Tool

| Function | Description |
|----------|-------------|
| `tool_list_files(directory, show_hidden, pattern)` | List directory contents (max 200 items) |
| `tool_search_files(name, directory, max_results)` | Search files by name (skips hidden/build dirs) |
| `tool_create_directory(path)` | Create directory (like `mkdir -p`) |

### 3.17 `tools/info_ops.py` — Info Query Tool

| Function | Description |
|----------|-------------|
| `tool_get_system_info()` | Get OS, Python version, CPU cores, user, CWD, encoding |
| `tool_get_current_time()` | Get current date/time |

### 3.18 `tools/search_ops.py` — Search & Replace Tool

#### Helper Functions

| Function | Description |
|----------|-------------|
| `_should_ignore(path, name, extra_ignores)` | Check if path should be skipped |
| `_is_binary(path)` | Check if file is binary (looks for `\x00` in first 8KB) |

#### Search Tools

| Function | Description |
|----------|-------------|
| `tool_grep(pattern, directory, glob, context_lines, max_results)` | Recursive regex file search with context display |
| `tool_replace(pattern, replacement, glob, dry_run)` | Batch text replace with optional preview |
| `tool_count_lines(directory, pattern)` | Count lines of code grouped by file type |
| `tool_find_files(pattern, directory, sort_by)` | Find files by name pattern |
| `tool_diff(file1, file2)` | Compare two files |
| `tool_show_file(path, start_line, line_count)` | View file with line numbers and pagination |

### 3.19 `tools/git_ops.py` — Git Operations Tool

| Function | Description |
|----------|-------------|
| `tool_git_status(directory)` | View repo status (branch, remote, ahead/behind) |
| `tool_git_log(directory, count, branch, author)` | View commit history |
| `tool_git_diff(directory, staged, path)` | View file differences |
| `tool_git_commit_stats(directory, days, top_n)` | View commit statistics |

---

## 4. Data Flow

### Smart Mode Flow

```
User Input → Prompt Optimization → System Prompt Assembly
     ↓
OpenAI API Call (streaming)
     ↓
┌─ Text Response → Stream to Frontend → Micro Composer → Auto Save ─┐
│                                                                    │
└─ Tool Call → Execute Tool → Append Results → Continue API Call ───┘
```

### Plan Mode Flow

```
1️⃣ Explore: Analyze user request, identify tasks
2️⃣ Modify: Adjust task plan based on feedback
3️⃣ Execute: Implement each step sequentially
4️⃣ Confirm: Verify execution results
5️⃣ Reset: Clear plan state when done
```

---

**Made with 💙**
