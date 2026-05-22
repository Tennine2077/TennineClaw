# TennineClaw

> Intelligent Terminal Assistant · AI-Powered Code Analysis & Task Execution Platform

[![Version](https://img.shields.io/badge/version-1.1.1-blue.svg)]()
[![Python](https://img.shields.io/badge/python-3.10+-green.svg)]()
[![License](https://img.shields.io/badge/license-MIT-yellow.svg)]()

[🇨🇳 **中文**](README.md) | [🌏 **English**](README.en.md)

TennineClaw is a feature-rich AI programming assistant web platform, supporting streaming conversations, command execution, file operations, Git integration, session management, context compression, and more.

---

## 📅 Release Timeline

| Date | Version | Description |
|------|---------|-------------|
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
| 💬 **Session Management** | Auto file saving, support for grouping, searching, renaming |
| 🧩 **Context Compression** | Auto/Manual/Micro compression to prevent Token overflow |
| 📊 **Token Monitoring** | Real-time display of input/output Token counts and ratios |
| 🎭 **Custom Roles** | Dynamic role loading from personas/ directory, complete personality definition (OCEAN five-factor model, language style, behavior preferences) + soul.md soul definition; optimized role switching UI |
| 🛠️ **Skill Management** | Standalone popup modal with real-time toggle, add custom skill (name+description+guide), delete custom skills, fully refactored UI |
| 🧩 **Dynamic Template Discovery** | Built-in templates exported to Personas directory; all roles auto-discovered from filesystem, no hardcoding needed |
| 💭 **Reasoning Display** | Each reasoning step in its own collapsible block with global collapse/expand, state persisted via localStorage |
| 🔧 **Tool Call Display** | Each tool invocation as a separate collapsible section with clearly separated parameters and results, global collapse/expand support |
| 🌓 **Theme Toggle** | Dark/Light theme |

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

### 3. Configure API

1. Open browser and navigate to **http://127.0.0.1:7860**
2. Click the **⚙️** button next to the model selector in the top-right corner
3. Enter your API Key and Base URL
4. Configuration is automatically persisted — no need to re-enter on restart

> API configuration is managed entirely through the Web UI. No need to edit `.env` files.

---

## 📐 Layout Overview

```
┌────────────────────────────────────────────────────────────────────────────┐
│ 🧠 TennineClaw               🌓 Theme Toggle   [Model ▼] [⚙️] │
├─────────────────┬──────────────────────────────────┬──────────────────────┤
│ Left Panel      │ Center Area                       │ Right Panel          │
│ 💬 New Chat     │                                   │ 🤖 Model Info        
│ 📋 Session List │   🤖 AI Chat Area                 │ 🧩 Loaded Skills     
│ 🔍 Search       │   ┌──────────────────────┐       │ 🎭 Current Role      
│                 │   │ 💭 Reasoning (fold)   │       │ 📊 Token Stats       
│                 │   ├──────────────────────┤       │                      │
│                 │   │ 🔧 Tool Call (fold)   │       │                      │
│                 │   ├──────────────────────┤       │                      │
│                 │   │ 💬 AI Response        │       │                      │
│                 │   └──────────────────────┘       │                      │
│                 │                                   │                      │
│                 │   [📝 Type a message...] [Send]   │                      │
├─────────────────┴──────────────────────────────────┴──────────────────────┤
│ 🔌 Shortcuts: Ctrl+Enter Send · Ctrl+Shift+Enter Newline · ↑↓ History    │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 🧩 Skill System

The skill system is the core extensibility mechanism of TennineClaw, supporting flexible combination and dynamic loading of skills.

### Built-in Skills

| Skill | Description |
|-------|-------------|
| 🔍 **File Search Master** | Proficient in file search and content retrieval |
| 🧠 **Context Manager** | Context management and compression for efficient conversations |
| 💻 **Shell Commander** | System command execution and command-line operations |
| 📊 **Intelligence Analyst** | System information collection and analysis |
| 📝 **Code Modifier** | File reading/writing and code editing |

### Custom Skills

Define custom skills in the `skills_custom/` directory via `skill.json`. The system automatically discovers and loads them.

---

## 🎭 Persona System

The persona system gives the AI assistant personality traits, including character, language style, and behavior preferences.

### Built-in Personas

| Persona | Description |
|---------|-------------|
| 🧑‍💻 **Tennine** | Default persona — a quirky AI assistant sprite, reliable yet playful |
| 🧑‍🔧 **Strict Engineer** | Professional, precise, specification-focused programming assistant |
| 🎨 **Creative Geek** | Imaginative, innovation-oriented tech partner |
| 😺 **Miao Xiaotang** | Cute-style AI assistant with an adorable communication style |
| ⚡ **Efficient Assistant** | Concise, direct, efficiency-focused task executor |

### Creating Custom Personas

1. Create a new folder under `personas/` (e.g., `personas/MyPersona/`)
2. Create `personality.json` to define personality parameters
3. (Optional) Create `soul.md` to write the persona's soul definition and core settings
4. Refresh the page — the persona will automatically appear in the list

---

## 💻 Technical Architecture

```
TennineClaw/
├── src/                    # Core backend code
│   ├── main.py             # Agent session main logic
│   ├── main_stream.py      # Streaming conversation module (SSE)
│   ├── web_api.py          # FastAPI web service
│   ├── config.py           # Global configuration
│   ├── context.py          # Triple context composer (Micro/Auto/Manual)
│   ├── session_manager.py  # Session management (save/load/list)
│   ├── skill_engine.py     # Skill engine (load/match/execute)
│   ├── skill_loader.py     # Skill loader
│   ├── skill_models.py     # Skill data models
│   ├── personality_engine.py  # Personality engine
│   ├── personality_models.py  # Personality data models
│   ├── mode_manager.py     # Mode manager (Smart/Plan)
│   ├── prompts.py          # System prompt generation
│   ├── prompt_optimizer.py # Prompt optimizer
│   ├── safety.py           # Security detection & high-risk command blocking
│   └── token_utils.py      # Token statistics & display
├── static/                 # Frontend static assets
│   ├── index.html          # Main page
│   ├── css/                # Stylesheets
│   └── js/                 # JavaScript files
│       ├── app.js          # Main application logic
│       ├── api.js          # API request wrapper
│       ├── personality.js  # Persona management UI
│       ├── skill_manager.js # Skill management modal
│       └── patch_segmented.js # Reasoning/tool call segmented display
├── personas/               # Persona definitions (dynamic scan)
│   ├── Tennine/
│   ├── Strict Engineer/
│   ├── Creative Geek/
│   ├── Miao Xiaotang/
│   └── Efficient Assistant/
├── skills/                 # Skill definitions
│   ├── File Search Master/
│   ├── Context Manager/
│   ├── Shell Commander/
│   ├── Intelligence Analyst/
│   └── Code Modifier/
├── skills_custom/          # Custom skills directory
├── sessions/               # Session data (auto-saved)
├── config/                 # User configuration (includes API Key)
├── docs/                   # Development documentation
└── scripts/                # Launch scripts
```

---

## 🔧 Custom Skill Development

### Skill Directory Structure

```
skills_custom/MySkill/
├── skill.json        # Skill metadata + tool definitions (required)
└── implement.py      # Tool implementation (optional, loaded by default)
```

### skill.json Format

```json
{
  "name": "My Skill",
  "description": "Skill description",
  "version": "1.0.0",
  "guide": "Guide text injected into system prompt",
  "personalities": ["Tennine", "Strict Engineer"],
  "tools": [
    {
      "name": "my_tool",
      "description": "Tool description",
      "parameters": {
        "type": "object",
        "properties": {
          "param1": { "type": "string", "description": "Parameter description" }
        },
        "required": ["param1"]
      }
    }
  ]
}
```

---

## 🔗 API Documentation

For detailed API reference, see:

- [API 参考文档（中文）](docs/API_REFERENCE.md)
- [API Reference (English)](docs/API_REFERENCE.en.md)

---

## 📄 License

This project is open-sourced under the MIT License — see the [LICENSE](LICENSE) file for details.
