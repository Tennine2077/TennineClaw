# TennineClaw

> 智能终端助手 · 基于 AI 的代码分析与任务执行平台

[![Version](https://img.shields.io/badge/version-1.1.2-blue.svg)]()
[![Python](https://img.shields.io/badge/python-3.10+-green.svg)]()
[![License](https://img.shields.io/badge/license-MIT-yellow.svg)]()

[🌏 **English**](README.en.md) | [🇨🇳 **中文**](README.md)

TennineClaw 是一个功能丰富的 AI 编程助手 Web 平台，支持流式对话、命令执行、文件操作、Git 集成、会话管理、上下文压缩、分支会话、智能 Prompt 优化等功能。

---

## 📅 发行时间线

| 日期 | 版本 | 说明 |
|------|------|------|
| 2026年5月23日 | **v1.1.2** | 🌿 **分支会话**：支持从任意 AI 回复创建独立分支会话（完整上下文继承）、智能 Prompt 优化（结合对话历史优化输入）、自动保存稳定性增强（修复 Windows 文件名非法字符问题） |
| 2026年5月23日 | **v1.1.1** | 🎨 **UI 全面升级**：重构技能管理界面（独立弹窗、实时开关、增删自定义技能）、角色管理界面优化（角色切换、灵魂定义展示）、思考过程独立折叠展示、工具调用分段展示 |
| 2026年5月22日 | v1.1.0 | 自定义角色系统（personas/目录动态扫描）、技能管理弹窗（增删/开关）、人格模板动态加载、soul.md 灵魂定义、修复角色切换与技能同步 Bug |
| 2026年5月19日 | v1.0.0 | 首个正式版本：Web UI (FastAPI + SSE 流式)、19 个工具、内置 Composer 上下文压缩、会话管理、Smart/Plan 双模式 |

---

## ✨ 功能

| 功能 | 说明 |
|------|------|
| 🤖 **AI 对话** | 流式响应，支持 DeepSeek 等模型；思考过程与回复独立分段展示 |
| 🔍 **Grep 搜索** | 递归搜索文件内容，支持文件过滤 + 上下文显示 |
| ⚡ **命令执行** | 安全检测的系统命令执行，支持超时控制 |
| 📁 **文件操作** | 读/写/删除/替换/比较，支持分页查看 |
| 🐍 **Conda 管理** | 查看/切换/创建 Python 环境 |
| 📋 **Plan 模式** | 结构化任务的规划、修改、分步执行 |
| 💬 **会话管理** | 自动文件保存，支持分组、搜索、重命名 |
| 🌿 **分支会话** | 在任意 AI 回复上创建独立分支，完整继承上文上下文，支持递归多层分支 |
| 🧩 **上下文压缩** | 自动/手动/微压缩（Micro Composer），防止 Token 溢出 |
| 🤖 **智能 Prompt 优化** | 结合完整对话历史对用户输入进行智能优化，使 AI 更准确理解上下文 |
| 📊 **Token 监控** | 实时显示输入/输出 Token 数量及占比 |
| 🎭 **自定义角色** | 支持通过 personas/ 目录动态加载角色，包含完整人格定义（OCEAN五因素、语言风格、行为偏好）+ soul.md 灵魂定义；角色切换界面优化，灵魂展示更直观 |
| 🛠️ **技能管理弹窗** | 独立弹窗管理，支持技能实时开关、新增（名称+描述+guide）、删除自定义技能，界面全面重构更易用 |
| 🧩 **动态模板扫描** | 内置模板已导出到 personas/ 目录，一切角色由目录自动发现，无需硬编码 |
| 💭 **思考过程展示** | 每个推理步骤独立折叠区块展示，支持全局折叠/展开，状态自动持久化 |
| 🔧 **工具调用展示** | 每次工具调用独立折叠显示，参数与返回结果分段清晰，支持全局折叠/展开 |
| 🌓 **主题切换** | 深色/浅色主题 |

---

## 🚀 快速开始

### 1. 安装

```bash
git clone https://github.com/your-org/tennineclaw.git
cd TennineClaw
pip install -r requirements.txt
```

### 2. 启动

```
python -m src.web_api
```

### 3. 配置 API

1. 打开浏览器访问 **http://127.0.0.1:7860**
2. 点击右上角模型选择旁边的 **⚙️** 按钮
3. 填写 API Key 和 Base URL
4. 配置会自动持久化，下次启动无需重复设置

> API 配置完全通过 Web UI 管理，无需编辑 `.env` 文件。

---

## 📐 整体布局

```
┌────────────────────────────────────────────────────────────────────────────┐
│ 🧠 TennineClaw                            v1.1.2          模型选择 ⚙️ 🌓 │
├────────────────────────────────────────────────────────────────────────────┤
│ ┌─────────────┐  ┌──────────────────────────────────────────────────────┐ │
│ │ 📂 会话列表    │  │  💬 对话区域                                        │ │
│ │              │  │                                                     │ │
│ │  📅 今天      │  │  🧑 用户消息                                       │ │
│ │  ├ 分支对话 🌿 │  │  🤖 AI 回复                     [🌿 创建分支]     │ │
│ │  ├ 项目分析    │  │    ├ 💭 思考过程(可折叠)                           │ │
│ │  ├ ...        │  │    ├ 🔧 工具调用(可折叠)                           │ │
│ │  📅 昨天      │  │    └ 📝 最终回复                                   │ │
│ │  └ ...        │  │                                                     │ │
│ │              │  │  🧑 用户消息（已优化✨）                              │ │
│ │  🌿 分支标签   │  │  🤖 AI 回复                     [🌿 创建分支]     │ │
│ │              │  │                                                     │ │
│ └─────────────┘  │  ┌────────────────────────────────────────────────┐   │
│                  │  │ 💬 输入消息...                    [发送] [打断] │   │
│                  │  └────────────────────────────────────────────────┘   │
│                  └──────────────────────────────────────────────────────┘ │
├────────────────────────────────────────────────────────────────────────────┤
│ 📊 Token: 1,234 / 8,000 (15.4%)  📦 消息数: 6  ⚡ 工具: 3 🧩 Composer   │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔌 API 参考

### 会话管理

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/session/new` | POST | 创建新会话 |
| `/api/session/load` | POST | 加载指定会话文件 |
| `/api/session/save` | POST | 保存当前会话 |
| `/api/session/branch` | POST | **从指定消息创建分支会话**（v1.1.2 新增） |
| `/api/session/title` | GET | 获取会话标题 |
| `/api/sessions/list` | GET | 列出所有已保存会话 |

#### POST /api/session/branch

**功能**：从当前会话的某条 AI 回复创建分支会话，完整继承该回复之前的所有上下文。

**请求体**：
```json
{
  "session_id": "源会话ID",
  "message_index": 3
}
```

**响应**：
```json
{
  "session_id": "新分支会话ID",
  "save_path": "sessions/[分支]xxx.json",
  "parent_session_id": "源会话ID",
  "trigger_message_index": 3,
  "trigger_message_preview": "AI 回复的预览文本",
  "message_count": 4
}
```

**分支数据模型**：分支会话的 JSON 文件包含以下元数据：
- `parent_session_id`: 源会话 ID
- `trigger_message_index`: 触发分支的消息索引
- `trigger_message_preview`: 触发消息的预览文本

### 对话

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/chat/stream` | POST | 流式聊天（SSE） |
| `/api/chat/messages` | GET | 获取会话消息列表 |

### 状态

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/status` | GET | 获取会话状态摘要 |
| `/api/status/realtime` | GET | 获取实时 Token 状态 |

### 角色与技能

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/personality/template` | POST | 应用人格模板 |
| `/api/personality/templates/all` | GET | 列出所有人格模板 |
| `/api/personality/equipped-skills` | GET | 获取已装备技能 |
| `/api/skills/registry` | GET | 获取技能注册表 |

### 其他

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/env/current` | GET | 获取当前环境信息 |
| `/api/models` | GET | 获取可用模型列表 |
| `/api/plan/check` | GET | 检查当前 Plan 状态 |

---

## 🗂️ 项目结构

```
TennineClaw/
├── src/
│   ├── web_api.py            # FastAPI Web 服务（所有 API 端点）
│   ├── main.py               # AgentSession 核心类
│   ├── main_stream.py        # 流式消息处理（SSE 流式生成）
│   ├── session_manager.py    # 会话持久化（保存/加载/自动保存）
│   ├── prompt_optimizer.py   # Prompt 智能优化器（含上下文感知优化）
│   ├── prompts.py            # 系统提示词构建
│   ├── context.py            # Composer 上下文压缩（Micro/Auto/Manual）
│   ├── config.py             # 全局配置
│   ├── mode_manager.py       # Smart/Plan 模式管理
│   ├── tools.py              # 工具定义与注册
│   ├── token_utils.py        # Token 计数工具
│   ├── prompt_optimizer.py   # Prompt 优化
│   ├── skill_engine.py       # 技能引擎
│   ├── personality_engine.py # 人格引擎
│   └── prompt_optimizer.py   # Prompt 优化
├── static/
│   ├── index.html            # 前端入口
│   ├── js/
│   │   ├── app.js            # 主应用逻辑（会话管理、消息渲染、分支会话）
│   │   └── api.js            # API 客户端封装
│   └── css/
│       └── style.css         # 样式表
├── sessions/                 # 会话文件存储目录
├── personas/                 # 角色定义目录
├── requirements.txt
├── run.bat
└── README.md
```

---

## 🧑‍💻 开发

### 环境要求

- **Python** 3.10+
- **pip** (Python 包管理器)

### 本地开发

```bash
# 克隆仓库
git clone https://github.com/your-org/tennineclaw.git
cd TennineClaw

# 安装依赖
pip install -r requirements.txt

# 启动开发服务器（热重载）
python -m src.web_api

# 访问
open http://127.0.0.1:7861
```

### 常用命令

```bash
# 启动服务
python -m src.web_api

# 启动服务（指定端口）
python -m src.web_api --port 7861
```

### 代码风格

- Python：遵循 [PEP 8](https://peps.python.org/pep-0008/) 规范
- JavaScript：ES6+
- HTML/CSS：语义化标签，CSS 变量主题

---

## 🧠 工作原理

### AI 对话流程

```
用户输入
  ↓
Prompt 优化器（可选）
  ↓  结合完整对话历史（self.msgs）进行智能优化
  ↓
Micro Composer（自动）
  ↓  压缩过长上下文，保留最近 N 轮对话
  ↓
构建系统提示词 + 工具定义
  ↓
调用 AI 模型（流式）
  ↓
工具调用 ↔ 工具执行
  ↓
流式输出回复
  ↓
自动保存到会话文件
```

### 上下文压缩策略

本系统采用分层次的上下文压缩策略：

| 层级 | 名称 | 触发条件 | 说明 |
|------|------|---------|------|
| 1 | Micro Composer | 自动（每轮） | 移除 tool_call/function 中间消息，保留最近 N 轮完整对话 |
| 2 | Auto Composer | 自动（超阈值） | 超出 Token 阈值时自动摘要历史对话 |
| 3 | Manual Composer | 手动（/compact） | 用户手动触发，人工控制摘要粒度 |

### 分支会话机制（v1.1.2 新增）

```
源会话:
  👤: 第一个问题
  🤖: 第一个回答  ──→ 🌿 点击创建分支
  👤: 第二个问题
  🤖: 第二个回答

分支会话（独立）:
  👤: 第一个问题（继承自源会话）
  🤖: 第一个回答（继承自源会话）
  👤: 在分支中继续提问（独立发展）
  🤖: 分支中的回答
```

- 分支独立保存为单独的 JSON 文件
- 分支元数据记录 `parent_session_id` 和 `trigger_message_index`
- 支持递归多层分支（分支中再创建分支）
- 原会话完全不受影响

---

## 🗺️ 路线图

- [x] 基础 AI 对话（流式 SSE）
- [x] 工具调用（19 个内置工具）
- [x] Smart / Plan 双模式
- [x] 会话持久化与管理
- [x] 上下文压缩（Micro/Auto/Manual Composer）
- [x] Token 实时监控
- [x] 自定义角色系统（personas 动态扫描）
- [x] 技能管理弹窗
- [x] 思考过程独立展示
- [x] 工具调用分段展示
- [x] 分支会话（从任意 AI 回复创建独立会话）
- [x] 智能 Prompt 优化（结合上下文优化输入）
- [ ] 多人协作会话
- [ ] 插件系统
- [ ] 会话导出（Markdown / PDF）
- [ ] 更多模型支持（Claude, Gemini 等）
- [ ] 知识库 RAG 集成

---

## 📄 许可证

MIT License

---

> **TennineClaw** — 由 **Tennine** 开发与维护
