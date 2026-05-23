# TennineClaw

> Intelligent Terminal Assistant · AI-Powered Code Analysis & Task Execution Platform

[![Version](https://img.shields.io/badge/version-1.1.2-blue.svg)]()
[![Python](https://img.shields.io/badge/python-3.10+-green.svg)]()
[![License](https://img.shields.io/badge/license-MIT-yellow.svg)]()

[🇨🇳 **中文**](README.md) | [🌏 **English**](README.en.md)

TennineClaw is a feature-rich AI programming assistant web platform, supporting streaming conversations, command execution, file operations, Git integration, session management, context compression, branch sessions, smart prompt optimization, and more.

---

## 📅 Release Timeline

| Date | Version | Description |
|------|---------|-------------|
| May 23, 2026 | **v1.1.2** | 🌿 **Branch Sessions**: Create independent branch conversations from any AI reply (full context inheritance), Smart Prompt Optimization (context-aware input optimization), auto-save stability enhancements (fixed Windows filename illegal character issue) |
| May 23, 2026 | **v1.1.1** | 🎨 **UI Overhaul**: Refactored skill management modal (standalone popup, real-time toggle, add/delete custom skills), optimized role management UI (role switching, soul.md display), independent collapsible sections for reasoning process & tool calls |
| May 22, 2026 | v1.1.0 | Custom role system (personas/ dynamic scanning), skill management modal (add/delete/toggle), personality template dynamic loading, soul.md soul definition, role switching & skill sync bug fixes |
| May 19, 2026 | v1.0.0 | First official release: Web UI (FastAPI + SSE Streaming), 19 tools, built-in Composer context compression, session management, Smart/Plan dual modes |

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🤖 **AI Chat** | Streaming responses, supporting DeepSeek and other models; separate sections for reasoning & replies |
| 🔍 **Grep Search** | Recursive file content search with file filtering + context display |
| ⚡ **Command Execution** | Safety-checked system command execution with timeout control |
| 📁 **File Operations** | Read/Write/Delete/Replace/Compare with paginated viewing |
| 🐍 **Conda Management** | View/Switch/Create Python environments |
| 📋 **Plan Mode** | Structured task planning, modification, and step-by-step execution |
| 💬 **Session Management** | Auto file saving, supports grouping, search, rename |
| 🌿 **Branch Sessions** | Create independent branches from any AI reply, full context inheritance, supports recursive multi-level branching |
| 🧩 **Context Compression** | Auto/Manual/Micro (Micro Composer) compression to prevent token overflow |
| 🤖 **Smart Prompt Optimization** | Context-aware optimization using full conversation history |
| 📊 **Token Monitoring** | Real-time input/output token count and ratio display |
| 🎭 **Custom Roles** | Dynamic role loading from personas/ directory, complete personality definition (OCEAN, language style, behavior preferences) + soul.md |
| 🛠️ **Skill Management** | Independent popup management, real-time toggle, add (name+description+guide), delete custom skills |
| 💭 **Reasoning Display** | Individual collapsible blocks for each reasoning step, global collapse/expand |
| 🔧 **Tool Call Display** | Individual collapsible blocks for each tool call, clear parameter/result sections |
| 🌓 **Theme Toggle** | Dark/Light theme |

---

## 🚀 Quick Start

### 1. Installation

```bash
git clone https://github.com/your-org/tennineclaw.git
cd TennineClaw
pip install -r requirements.txt
```

### 2. Run

```
python -m src.web_api
```

### 3. Configure API

1. Open browser at **http://127.0.0.1:7860**
2. Click the **⚙️** button next to the model selector
3. Enter your API Key and Base URL
4. The configuration will persist automatically

> All API configuration is managed through the Web UI — no need to edit `.env` files.

---

## 📐 Layout

```
┌────────────────────────────────────────────────────────────────────────────┐
│ 🧠 TennineClaw                            v1.1.2      Model Select ⚙️ 🌓 │
├────────────────────────────────────────────────────────────────────────────┤
│ ┌─────────────┐  ┌──────────────────────────────────────────────────────┐ │
│ │ 📂 Sessions   │  │  💬 Chat Area                                      │ │
│ │              │  │                                                     │ │
│ │  📅 Today    │  │  🧑 User Message                                   │ │
│ │  ├ Branch 🌿 │  │  🤖 AI Reply                    [🌿 Create Branch] │ │
│ │  ├ Analysis  │  │    ├ 💭 Reasoning (collapsible)                     │ │
│ │  ├ ...       │  │    ├ 🔧 Tool Call (collapsible)                     │ │
│ │  📅 Yesterday│  │    └ 📝 Final Reply                                │ │
│ │  └ ...       │  │                                                     │ │
│ │              │  │  🧑 User Message (optimized✨)                       │ │
│ │  🌿 Branch   │  │  🤖 AI Reply                    [🌿 Create Branch] │ │
│ │     Tag      │  │                                                     │ │
│ └─────────────┘  │  ┌────────────────────────────────────────────────┐   │
│                  │  │ 💬 Input message...              [Send] [Stop] │   │
│                  │  └────────────────────────────────────────────────┘   │
│                  └──────────────────────────────────────────────────────┘ │
├────────────────────────────────────────────────────────────────────────────┤
│ 📊 Token: 1,234 / 8,000 (15.4%)  📦 Msgs: 6  ⚡ Tools: 3 🧩 Composer   │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔌 API Reference

### Session Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/session/new` | POST | Create new session |
| `/api/session/load` | POST | Load session from file |
| `/api/session/save` | POST | Save current session |
| `/api/session/branch` | POST | **Create branch from message** (v1.1.2 new) |
| `/api/session/title` | GET | Get session title |
| `/api/sessions/list` | GET | List all saved sessions |

#### POST /api/session/branch

**Function**: Create a branch session from a specific AI reply, inheriting all context up to that message.

**Request**:
```json
{
  "session_id": "source_session_id",
  "message_index": 3
}
```

**Response**:
```json
{
  "session_id": "new_branch_session_id",
  "save_path": "sessions/[Branch]xxx.json",
  "parent_session_id": "source_session_id",
  "trigger_message_index": 3,
  "trigger_message_preview": "AI reply preview",
  "message_count": 4
}
```

**Branch data model**: Branch session JSON files include the following metadata:
- `parent_session_id`: Source session ID
- `trigger_message_index`: Index of the message that triggered the branch
- `trigger_message_preview`: Preview text of the trigger message

### Chat

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat/stream` | POST | Streaming chat (SSE) |
| `/api/chat/messages` | GET | Get session messages |

### Status

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/status` | GET | Get session status summary |
| `/api/status/realtime` | GET | Get real-time token status |

### Personality & Skills

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/personality/template` | POST | Apply personality template |
| `/api/personality/templates/all` | GET | List all personality templates |
| `/api/personality/equipped-skills` | GET | Get equipped skills |
| `/api/skills/registry` | GET | Get skill registry |

### Other

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/env/current` | GET | Get current environment info |
| `/api/models` | GET | Get available models |
| `/api/plan/check` | GET | Check current plan status |

---

## 🗂️ Project Structure

```
TennineClaw/
├── src/
│   ├── web_api.py            # FastAPI Web service (all API endpoints)
│   ├── main.py               # AgentSession core class
│   ├── main_stream.py        # Streaming message processing (SSE)
│   ├── session_manager.py    # Session persistence (save/load/auto-save)
│   ├── prompt_optimizer.py   # Prompt optimizer (context-aware)
│   ├── prompts.py            # System prompt builder
│   ├── context.py            # Composer (Micro/Auto/Manual)
│   ├── config.py             # Global configuration
│   ├── mode_manager.py       # Smart/Plan mode management
│   ├── tools.py              # Tool definitions & registration
│   ├── token_utils.py        # Token counting utilities
│   ├── skill_engine.py       # Skill engine
│   └── personality_engine.py # Personality engine
├── static/
│   ├── index.html            # Frontend entry
│   ├── js/
│   │   ├── app.js            # Main app logic (sessions, messages, branches)
│   │   └── api.js            # API client wrapper
│   └── css/
│       └── style.css         # Stylesheet
├── sessions/                 # Session file storage
├── personas/                 # Role definitions
├── requirements.txt
├── run.bat
└── README.md
```

---

## 🧑‍💻 Development

### Requirements

- **Python** 3.10+
- **pip** (Python package manager)

### Local Development

```bash
# Clone
git clone https://github.com/your-org/tennineclaw.git
cd TennineClaw

# Install dependencies
pip install -r requirements.txt

# Start dev server (hot reload)
python -m src.web_api

# Open
open http://127.0.0.1:7861
```

---

## 🧠 How It Works

### AI Conversation Flow

```
User Input
  ↓
Prompt Optimizer (optional)
  ↓  Context-aware: uses full self.msgs for optimization
  ↓
Micro Composer (automatic)
  ↓  Compresses long context, keeps recent N rounds
  ↓
Build System Prompt + Tool Definitions
  ↓
Call AI Model (streaming)
  ↓
Tool Calls ↔ Tool Execution
  ↓
Stream Output Response
  ↓
Auto-save to Session File
```

### Branch Session Mechanism (v1.1.2 new)

```
Source Session:
  👤: First question
  🤖: First reply    ──→ 🌿 Create branch
  👤: Second question
  🤖: Second reply

Branch Session (independent):
  👤: First question (inherited)
  🤖: First reply (inherited)
  👤: Continue in branch (independent)
  🤖: Branch reply
```

- Branches are saved as independent JSON files
- Branch metadata: `parent_session_id`, `trigger_message_index`
- Supports recursive multi-level branching
- Original session is never affected

---

## 🗺️ Roadmap

- [x] Basic AI Chat (SSE Streaming)
- [x] Tool Calls (19 built-in tools)
- [x] Smart / Plan dual modes
- [x] Session persistence & management
- [x] Context compression (Micro/Auto/Manual Composer)
- [x] Real-time token monitoring
- [x] Custom role system (personas dynamic scanning)
- [x] Skill management modal
- [x] Independent reasoning display
- [x] Independent tool call display
- [x] Branch sessions (create independent sessions from any AI reply)
- [x] Smart Prompt Optimization (context-aware)
- [ ] Multi-user collaboration
- [ ] Plugin system
- [ ] Session export (Markdown / PDF)
- [ ] More model support (Claude, Gemini, etc.)
- [ ] Knowledge base RAG integration

---

## 📄 License

MIT License

---

> **TennineClaw** — Developed & Maintained by **Tennine**
