# TennineClaw

> Intelligent Terminal Assistant · AI-Powered Code Analysis & Task Execution Platform

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)]()
[![Python](https://img.shields.io/badge/python-3.10+-green.svg)]()
[![License](https://img.shields.io/badge/license-MIT-yellow.svg)]()

[🇨🇳 **中文**](README.md) | [🌏 **English**](README.en.md)

TennineClaw is a feature-rich AI programming assistant web platform, supporting streaming conversations, command execution, file operations, Git integration, session management, context compression, and more.

---

## 📅 Release Timeline

| Date | Version | Description |
|------|---------|-------------|
| May 19, 2026 | v1.0.0 | First official release: Web UI (FastAPI + SSE Streaming), 19 tools, built-in Composer context compression, session management, Smart/Plan dual modes |

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🤖 **AI Chat** | Streaming responses, supporting DeepSeek and other models |
| 🔍 **Grep Search** | Recursive file content search with file filtering + context display |
| ⚡ **Command Execution** | Safety-checked system command execution with timeout control |
| 📁 **File Operations** | Read/Write/Delete/Replace/Compare with paginated viewing |
| 🐍 **Conda Management** | View/Switch/Create Python environments |
| 📋 **Plan Mode** | Structured task planning, modification, and step-by-step execution |
| 💬 **Session Management** | Auto file saving, support for grouping, searching, renaming |
| 🧩 **Context Compression** | Auto/Manual/Micro compression to prevent Token overflow |
| 📊 **Token Monitoring** | Real-time display of input/output Token counts and ratios |
| 🌓 **Theme Switching** | Dark/Light theme support |

---

## 🚀 Quick Start

### 1. Installation

```bash
git clone https://github.com/your-org/tennineclaw.git
cd TennineClaw
pip install -r requirements.txt
```

### 2. Launch

```
python -m src.web_api
```

### 3. API Configuration

1. Open your browser and visit **http://127.0.0.1:7860**
2. Click the **⚙️** button next to the model selector in the top-right corner
3. Enter your API Key and Base URL
4. Configuration is automatically persisted — no need to set it again on next launch

> API configuration is managed entirely through the Web UI. No need to edit `.env` files.

---

## 📐 Layout Overview

```
┌────────────────────────────────────────────────────────────────────────────┐
│ 🧠 TennineClaw               🌓 Theme Toggle  [Model ▼] [⚙️] │
├─────────────────┬──────────────────────────────────┬──────────────────────┤
│ Left Panel      │ Center Area                      │ Right Panel          │
│ 💬 New Chat     │                                   │ 🤖 Model Info       │
│ 📂 History      │  🧠 Chat Area                     │ 🧩 Composer Status  │
│ ─────────       │                                   │ 📊 Token Usage      │
│ 📁 Session A    │  🧑 User Message                  │ 📝 Details          │
│ 📁 Session B    │  🤖 AI Response...               │                      │
│ ─────────       │                                   │                      │
│ 📁 Session C    │                                   │                      │
│ 📁 ...          │                                   │                      │
├─────────────────┴──────────────────────────────────┴──────────────────────┤
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Tool List

### File Search

| Command | Function | Example |
|---------|----------|---------|
| `grep` | Recursive file content search | `grep("def __init__", glob="*.py", context=2)` |
| `replace` | Batch replace, preview by default | `replace("old", "new", dry_run=True)` |
| `find_files` | Search files by extension | `find_files("*.py", sort_by="size")` |
| `count_lines` | Count lines of code | `count_lines(pattern="*.py,*.js")` |
| `diff` | Compare file contents | `diff("a.py", "b.py")` |
| `show_file` | View file with line numbers | `show_file("main.py", start=50, count=30)` |

### Git

| Command | Function |
|---------|----------|
| `git_status` | View repo status, including branch, remote, ahead/behind |
| `git_log` | View commit history with branch/author filtering |
| `git_diff` | View unstaged changes |
| `git_commit_stats` | Count file changes and commits |

### System

| Command | Function |
|---------|----------|
| `run_cmd` | Execute system commands (with safety checks) |
| `read_file` / `write_file` | File read/write |
| `list_files` / `create_directory` | Directory management |
| `get_system_info` | System information query |
| `get_current_time` | Current time |

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────┐
│         Web UI (FastAPI + Static Files)                  │
│   static/index.html + style.css + app.js                │
├──────────────────────────────────────────────────────────┤
│           web_api.py (API Route Layer)                   │
├──────────────────────────────────────────────────────────┤
│      main.py / main_stream.py (Chat Processing)          │
├──────────────────────────────────────────────────────────┤
│   tools/                                                 │
│   ├── __init__.py    Tool Registration                   │
│   ├── cmd_exec.py    System Command Execution            │
│   ├── file_ops.py    File Read/Write                     │
│   ├── dir_ops.py     Directory Operations                │
│   ├── info_ops.py    System Information                  │
│   ├── search_ops.py  Grep / Replace / Count              │
│   └── git_ops.py     Git Operations                      │
├──────────────────────────────────────────────────────────┤
│   Support Layer                                          │
│   ├── context.py         Context Management & Compression│
│   ├── session_manager.py Session Save/Load/Register      │
│   ├── safety.py          Command Safety Detection        │
│   ├── prompts.py         System Prompt Templates         │
│   ├── prompt_optimizer.py Prompt Optimization            │
│   ├── token_utils.py     Token Usage Utilities           │
│   └── mode_manager.py    Mode Management                 │
└──────────────────────────────────────────────────────────┘
```

## 📁 Project Structure

```
TennineClaw/
├── __init__.py              # Package init + version
├── config.py                # Configuration (persistent + defaults)
├── main.py                  # Core chat logic
├── main_stream.py           # Streaming chat logic
├── web_api.py               # FastAPI Web interface (37 routes)
│
├── session_manager.py       # Session persistence + global registry
├── context.py               # Context compression (Micro/Auto/Manual)
├── mode_manager.py          # Smart / Plan mode management
├── prompt_optimizer.py      # User input prompt optimization
├── prompts.py               # System prompt templates
├── safety.py                # System command safety detection
├── token_utils.py           # Token usage & formatting
│
├── requirements.txt         # Python dependencies
├── run.bat / run.ps1        # Windows startup scripts
│
├── tools/                   # Function Calling toolset
│   ├── __init__.py          # Tool registration decorator
│   ├── cmd_exec.py          # System command execution
│   ├── file_ops.py          # File read/write
│   ├── dir_ops.py           # Directory operations
│   ├── info_ops.py          # System info query
│   ├── search_ops.py        # Grep / Replace / Line count
│   └── git_ops.py           # Git status / log / diff
│
└── static/                  # Frontend static resources
    ├── index.html           # Main page
    ├── js/api.js            # API call wrapper
    ├── js/app.js            # Frontend interaction logic
    └── css/style.css        # Styles (Dark/Light theme)
```

---

## ⚙️ Configuration

### Server Configuration

| Option | Description | Default |
|--------|-------------|---------|
| `GRADIO_PORT` | Web service port | `7860` |
| `GRADIO_HOST` | Listen address | `127.0.0.1` |

### API Configuration

API Key, Base URL, and model selection are all configured through the **top-right corner** model settings page in the Web UI. They are automatically persisted to `user_config.json` — no manual editing required.

### Command Reference

| Command | Description |
|---------|-------------|
| `/smart` | Switch to Smart mode |
| `/plan` | Switch to Plan mode |
| `/clear` | Clear chat history |
| `/compact` | Manually compress context |
| `/save [name]` | Save current session |
| `/load <filename>` | Load a historical session |
| `/status` | View current status |
| `/tools` | View available tools |
| `/title <new title>` | Change session title |
| `/help` | View help |

---

## 💡 Usage Examples

### Code Search

```
You: Help me find FastAPI route definitions
→ AI calls grep()
→ Returns all route definitions with corresponding file line numbers
```

### Git Status

```
You: Check current repository status
→ AI calls git_status()
→ Shows branch, staging area, untracked files
```

### Line Count

```
You: Count how many lines of code are in this project
→ AI calls count_lines()
→ Displays categorized code line statistics
```

### Batch Replace

```
You: Replace all print statements with logging.info
→ AI calls replace()
→ Preview first, confirm, then execute
```

---

## 🔒 Security

- Dangerous commands (`rm -rf`, `format`, `dd if=`, etc.) are automatically blocked
- API Key is configured through the Web UI and stored only in memory
- `user_config.json` and `sessions/` directory are added to `.gitignore`

---

## 📄 License

MIT License

---

## 📝 Changelog

### v1.0.0 (May 19, 2026)

**First official release**

- **Complete Web UI Rewrite**: Migrated from Gradio to **FastAPI + Static Frontend**, supporting 37+ RESTful routes
- **Streaming SSE Chat**: `/api/chat/stream` endpoint with real-time streaming + interrupt recovery
- **19 Practical Tools**:
  - File operations: search, replace, read, write, delete, compare
  - Git integration: status, commit history, diff, contribution stats
  - System operations: command execution (with safety checks), directory management, info query
  - Conda management: environment view, switch, create
- **Composer Context Compression**: Micro (auto-trim tool info), Auto (compress at 80% Token usage), Manual (`/compact` trigger)
- **Session Management**: File-level persistence, global registry, grouping/search/rename
- **Smart / Plan Dual Mode**: Plan mode includes explore → modify → execute → confirm → reset workflow
- **Token Monitoring**: Real-time input/output/total usage display, cumulative session stats
- **Status Management**: Status query during streaming (0.3s timeout), auto-recovery after interruption
- **Theme Support**: Dark/Light theme switching
- **Prompt Optimization**: Uses LLM to optimize raw user input, UI shows before/after comparison
- **Model API Wrapper**: Supports independent configuration for multiple models (base_url / api_key), persisted to `user_config.json`

---

**Made with 💙**
