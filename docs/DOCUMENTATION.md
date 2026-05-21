# TennineClaw 项目说明文档

> **版本**: 1.1.0
> **语言**: 中文 | [🌏 English](DOCUMENTATION.en.md)  
> **描述**: 智能终端助手 — 基于 AI 的代码分析与任务执行 Web 平台  
> **许可**: MIT License  
> **项目路径**: `D:\Code\tools\Claude_code_learn\TennineClaw`

---

## 目录

1. [项目概述](#1-项目概述)
2. [架构总览](#2-架构总览)
3. [模块与函数详述](#3-模块与函数详述)
   - [3.1 `__init__.py` — 版本信息](#31-__init__py--版本信息)
   - [3.2 `config.py` — 全局配置](#32-configpy--全局配置)
   - [3.3 `main.py` — Agent 会话主逻辑](#33-mainpy--agent-会话主逻辑)
   - [3.4 `main_stream.py` — 流式对话处理](#34-main_streampy--流式对话处理)
   - [3.5 `context.py` — 三重上下文管理器（Composer）](#35-contextpy--三重上下文管理器composer)
   - [3.6 `mode_manager.py` — 模式管理器](#36-mode_managerpy--模式管理器)
   - [3.7 `prompts.py` — 系统提示词构建](#37-promptspy--系统提示词构建)
   - [3.8 `prompt_optimizer.py` — Prompt 智能优化](#38-prompt_optimizerpy--prompt-智能优化)
   - [3.9 `safety.py` — 命令安全检测](#39-safetypy--命令安全检测)
   - [3.10 `session_manager.py` — 会话持久化管理](#310-session_managerpy--会话持久化管理)
   - [3.11 `token_utils.py` — Token 统计工具](#311-token_utilspy--token-统计工具)
   - [3.12 `web_api.py` — FastAPI Web 服务层](#312-web_apipy--fastapi-web-服务层)
   - [3.13 `tools/__init__.py` — 工具注册与调度](#313-tools__init__py--工具注册与调度)
   - [3.14 `tools/cmd_exec.py` — 命令执行工具](#314-toolscmd_execpy--命令执行工具)
   - [3.15 `tools/file_ops.py` — 文件操作工具](#315-toolsfile_opspy--文件操作工具)
   - [3.16 `tools/dir_ops.py` — 目录操作工具](#316-toolsdir_opspy--目录操作工具)
   - [3.17 `tools/info_ops.py` — 信息查询工具](#317-toolsinfo_opspy--信息查询工具)
   - [3.18 `tools/search_ops.py` — 搜索与替换工具](#318-toolssearch_opspy--搜索与替换工具)
   - [3.19 `tools/git_ops.py` — Git 操作工具](#319-toolsgit_opspy--git-操作工具)
   - [3.20 `personality_models.py` — 人格数据模型](#320-personality_modelspy--人格数据模型)
   - [3.21 `personality_engine.py` — 人格引擎](#321-personality_enginepy--人格引擎)
   - [3.22 `skill_models.py` — 技能数据模型](#322-skill_modelspy--技能数据模型)
   - [3.23 `skill_engine.py` — 技能引擎](#323-skill_enginepy--技能引擎)
   - [3.24 `skill_loader.py` — 技能加载器](#324-skill_loaderpy--技能加载器)
4. [数据流说明](#4-数据流说明)

---

## 1. 项目概述

**TennineClaw** 是一个基于 AI 大语言模型的智能终端助手 Web 平台。其核心能力包括：

- **流式对话** — AI 逐段落流式回复，实时展示推理过程
- **19 个实用工具** — AI 可自主调用的代码分析、文件操作、Git 集成等工具
- **三重上下文压缩（Composer）** — 智能管理对话 Token 消耗
- **双模式架构** — Smart（智能处理）与 Plan（计划驱动）双模式
- **多会话管理** — 同时管理多个对话会话，支持保存/恢复
- **Prompt 智能优化** — AI 自动优化用户输入，提升回复质量
- **Conda 环境管理** — 在线创建和切换 Python 虚拟环境
- **自定义模型管理** — 支持注册和切换多种 AI 模型
- **Web UI** — 基于 FastAPI 的 RESTful API + 静态前端页面

**技术栈**：Python 3.10+, OpenAI SDK, FastAPI, SSE（Server-Sent Events）, JSON 持久化

---

## 2. 架构总览

```
TennineClaw/
├── __init__.py              # 版本声明
├── config.py                # 全局配置（API Key、模型、阈值等）
├── main.py                  # AgentSession 类（同步对话 + 工具调度 + 模式/环境/模型管理）
├── main_stream.py           # AgentSessionStreamMixin（流式对话混入）
├── context.py               # 三重 Composer（Micro/Auto/Manual 压缩器）
├── mode_manager.py          # ModeManager（Smart / Plan 模式状态机）
├── prompts.py               # 系统 Prompt 构建器
├── prompt_optimizer.py      # 用户 Prompt 智能优化
├── safety.py                # 命令安全检测
├── session_manager.py       # 会话 CRUD + SessionRegistry 注册表
├── token_utils.py           # Token 使用量统计工具
├── web_api.py               # FastAPI 服务 + 路由 + 状态缓存
├── tools/                   # 工具包目录
│   ├── __init__.py          # 工具注册表 + dispatch_tool 调度器
│   ├── cmd_exec.py          # 系统命令执行（run_cmd）
│   ├── file_ops.py          # 文件读写删（read/write/delete_file）
│   ├── dir_ops.py           # 目录列搜创（list/search_files, create_directory）
│   ├── info_ops.py          # 系统信息/时间（get_system_info, get_current_time）
│   ├── search_ops.py        # 搜索替换统计差异（grep/replace/count_lines/find_files/diff）
│   └── git_ops.py           # Git 操作（status/log/diff/commit_stats/show_file）
└── static/                  # 前端静态文件
    ├── index.html           # 主页面
    ├── css/style.css        # 样式
    └── js/                  # JavaScript
        ├── api.js           # API 请求封装
        └── app.js           # UI 逻辑
```

**数据流概览**：

```
用户输入 → Web UI / CLI
     ↓
AgentSession.process_message_stream() / process_message()
     ↓
Prompt 优化 (prompt_optimizer.py) → 追加 system prompt 注入
     ↓
→ 特殊指令 (/clear, /save 等) → 直接返回
→ 正常对话 → OpenAI API (stream/non-stream)
     ↓
     ← 工具调用 → 执行 (tools/) → 结果追加回消息列表 → 继续 API 调用
     ← 文本回复 → 分段输出 → Micro Composer 清理 → 自动保存
```

---

## 3. 模块与函数详述

### 3.1 `__init__.py` — 版本信息

**来源**: 项目根入口文件  
**功能**: 声明项目的版本号、描述和许可信息  
**目的**: 为其他模块（特别是 `web_api.py` 和静态前端）提供统一的版本引用入口

| 变量 | 值 | 说明 |
|------|-----|------|
| `__version__` | `"1.1.0"` | 当前版本号，API 响应和前端显示均引用此值 |
| `__description__` | `"Intelligent Terminal Assistant - AI 编程助手"` | 项目描述 |
| `__license__` | `"MIT"` | 开源许可协议 |

---

### 3.2 `config.py` — 全局配置

**来源**: 独立配置模块  
**功能**: 集中管理所有配置项，提供持久化配置存取机制  
**目的**: 解耦配置与业务逻辑，支持用户通过 Web UI 修改配置并自动持久化

#### 配置持久化机制

| 函数 | 来源 | 功能 | 目的 |
|------|------|------|------|
| `_load_user_config()` | `config.py` | 从 `user_config.json` 加载用户持久化配置 | 重启后恢复用户的自定义设置 |
| `_save_user_config(config)` | `config.py` | 将配置字典合并写入 `user_config.json` | 保存用户在 UI 上修改的 API Key、环境路径等 |
| `_get_user_config()` | `config.py` | 懒加载持久化配置（带缓存） | 避免每次调用都读磁盘，提升性能 |
| `_invalidate_config_cache()` | `config.py` | 使配置缓存失效 | 用户修改配置后强制下次重新加载 |
| `get_config(key, env_key, default)` | `config.py` | 按优先级获取配置：user_config.json > 环境变量 > 默认值 | 三级回退策略，灵活且安全 |

#### 模型 API 覆盖配置

| 函数 | 来源 | 功能 | 目的 |
|------|------|------|------|
| `get_model_api_overrides()` | `config.py` | 获取持久化的模型 API 覆盖配置（`{code: {base_url, api_key}}`） | 让每个模型可以独立配置 API 地址和密钥 |
| `save_model_api_override(code, base_url, api_key)` | `config.py` | 保存单个模型的 API 覆盖配置到 user_config.json | 持久化用户在 UI 上为每个模型配置的 API 参数 |
| `apply_model_api_overrides(models)` | `config.py` | 将持久化的 API 覆盖合并到模型列表中 | 在返回模型列表给前端或 AgentSession 前，注入用户的自定义 API 配置 |

#### 核心配置常量

| 变量名 | 值 | 说明 |
|--------|-----|------|
| `API_KEY` | 来自 `user_config.json` | OpenAI 兼容的 API 密钥 |
| `API_BASE_URL` | 默认 `https://api.deepseek.com` | API 基础地址 |
| `API_MODEL` | 默认 `deepseek-v4-flash` | 默认 AI 模型 |
| `API_TIMEOUT` | 60s | API 请求超时 |
| `MAX_CTX_TOKENS` | 128,000 | 上下文最大 Token 数 |
| `COMPACT_THRESHOLD` | 80% of MAX_CTX_TOKENS | Auto Composer 触发阈值 |
| `COMPRESS_MAX_CHARS` | 30,000 | 压缩后最大字符数 |
| `MODE_SMART` / `MODE_PLAN` | 1 / 2 | 模式枚举值 |
| `SESSION_SAVE_DIR` | `"./sessions/"` | 会话文件保存目录 |
| `GRADIO_PORT` | 7860 | Web 服务端口 |
| `COMPOSER_ENABLED` | `True` | 上下文压缩总开关 |
| `MICRO_COMPOSER_KEEP_ROUNDS` | 2 | Micro Composer 保留的最近对话轮数 |
| `HIGH_RISK_PATTERNS` | `["rm -rf", "del /s /q", ...]` | 高危命令模式列表 |

---

### 3.3 `main.py` — Agent 会话主逻辑

**来源**: 核心业务模块  
**功能**: 定义 `AgentSession` 类，包含完整的对话状态管理、工具调用处理、模式切换、模型管理、Python/Conda 环境管理、会话保存/恢复等功能  
**目的**: 作为整个系统的中心枢纽，管理单个对话会话的完整生命周期

#### AgentSession 类

| 方法 | 来源 | 功能 | 目的 |
|------|------|------|------|
| `__init__(self, session_id, mode)` | `main.py` | 初始化会话实例 | 创建完整的会话上下文：API 客户端、消息列表（双轨存储）、Token 计数、Composer 统计、标题系统、环境配置、流式控制等 |
| `reset(self)` | `main.py` | 重置会话到初始状态 | 清除所有上下文、统计数据和状态，相当于重新开始一个对话 |
| `get_mode_name()` | `main.py` | 获取当前模式名称 | 返回带 emoji 的模式显示名（如"🧠 智能模式"） |
| `get_mode()` | `main.py` | 获取当前模式数值 | 返回 `MODE_SMART` 或 `MODE_PLAN` |
| `get_composer_status()` | `main.py` | 获取 Composer 压缩状态文本 | 供前端或 `/status` 命令展示当前三重压缩器的触发次数和阈值信息 |
| `switch_mode(mode)` | `main.py` | 切换工作模式 | 根据用户指令切换到 Smart 或 Plan 模式，重建 system prompt 并重置 Token 计数 |
| `_auto_set_title(user_input)` | `main.py` | 首次用户消息时自动生成标题 | 取用户输入的前 50 个字作为会话标题，提升会话识别度 |
| `set_title(title)` | `main.py` | 手动设置会话标题 | 允许用户通过 `/title` 命令自定义会话名称 |
| `get_title()` | `main.py` | 获取会话标题 | 返回当前标题或无标题占位符 |
| `get_title_display()` | `main.py` | 获取格式化标题显示文字 | 前端展示用，包含"💬 **当前会话**:"前缀 |

#### 会话持久化

| 方法 | 来源 | 功能 | 目的 |
|------|------|------|------|
| `save(path)` | `main.py` | 保存当前会话到文件 | 委托 `session_manager.save_session()` 将 msgs、模式、统计等序列化为 JSON |
| `load(path)` | `main.py` | 从文件恢复会话 | 委托 `session_manager.restore_session()` 反序列化并恢复所有状态 |
| `_auto_save_if_needed()` | `main.py` | 每轮对话后自动保存 | 配置 `SESSION_AUTO_SAVE=True` 时，每轮消息后自动保存为独立文件 |

#### 上下文压缩

| 方法 | 来源 | 功能 | 目的 |
|------|------|------|------|
| `compact_context()` | `main.py` | 手动触发 Manual Composer 压缩 | 用户通过 `/compact` 命令对全部上下文进行 LLM 语义压缩 |
| `_run_micro_composer()` | `main.py` | 每轮对话后清理旧 tool 信息 | 仅保留最近 2 轮的工具调用记录，删除更早的 `tool_calls` 和 `tool` 角色消息 |
| `_run_auto_composer_if_needed()` | `main.py` | Token 达阈值时自动触发语义压缩 | 当输入 Token 达到 80% 阈值时，用 LLM 对历史上下文进行智能摘要 |

#### 模型管理

| 方法 | 来源 | 功能 | 目的 |
|------|------|------|------|
| `get_available_models()` | `main.py` | 获取可用模型列表（内置+自定义，合并 API 覆盖） | 返回前端所需的完整模型清单，含 `is_custom` 标记和覆盖的 API 参数 |
| `switch_model(model_code)` | `main.py` | 按 code 切换当前模型 | 更新 `current_model` 并在必要时重新初始化 OpenAI 客户端 |
| `add_custom_model(name, code, base_url, api_key)` | `main.py` | 添加自定义模型 | 支持用户注册第三方模型（如 GPT-4o、Claude 等） |
| `delete_custom_model(code)` | `main.py` | 删除自定义模型 | 移除已注册的模型，若当前正在使用则自动切回默认模型 |
| `update_model_api(code, base_url, api_key)` | `main.py` | 更新模型的 API 覆盖配置 | 持久化到 `user_config.json`，内置模型和自定义模型分别处理 |
| `reinit_client_with_overrides(base_url, api_key)` | `main.py` | 用指定 API 参数重新初始化客户端 | 当用户修改 API 地址或密钥后立即重连 |
| `reinit_client()` | `main.py` | 用全局配置重新初始化客户端 | 从 `API_KEY` / `API_BASE_URL` 重建客户端 |

#### 环境管理

| 方法 | 来源 | 功能 | 目的 |
|------|------|------|------|
| `set_python_env(path)` | `main.py` | 设置 Python 环境路径 | 供 `/env` 命令和 Web UI 使用，手动指定 Python 解释器路径 |
| `get_python_env_info()` | `main.py` | 获取 Python 环境信息文本 | 展示当前 Python 路径、Conda 环境和覆盖状态 |
| `list_conda_envs()` | `main.py` | 列出所有 conda 环境 | 执行 `conda env list --json` 并解析输出 |
| `switch_conda_env(env_name)` | `main.py` | 切换到指定 conda 环境 | 验证环境存在后更新 `conda_env`、持久化配置、自动推导 Python 路径 |
| `create_conda_env(env_name, python_version)` | `main.py` | 创建新的 conda 环境 | 执行 `conda create -n <name> python=<version> -y` |

#### 模式注入与轮次管理

| 方法 | 来源 | 功能 | 目的 |
|------|------|------|------|
| `_build_mode_inject_text()` | `main.py` | 构建模式指令文本 | 生成当前模式的简短 system prompt，用于周期性注入 |
| `_inject_mode_prompt_if_needed()` | `main.py` | 在用户消息前注入模式 system prompt | 模式切换后立即注入 + 每 3 轮对话自动注入，强化 LLM 的行为约束 |
| `_on_round_complete()` | `main.py` | 轮次完成时递增计数 | 支持周期性模式注入的轮次计数功能 |

#### 同步对话处理

| 方法 | 来源 | 功能 | 目的 |
|------|------|------|------|
| `process_message(user_input)` | `main.py` | 同步处理用户消息 | 完整的同步对话循环：指令解析 → Prompt 优化 → Auto Composer → API 调用 → 工具执行 → Micro Composer → 自动保存 |

**`process_message` 详细流程**：
1. **指令解析** — 检查 `/clear`, `/save`, `/compact` 等特殊命令
2. **模式注入** — 每 3 轮或模式切换后注入 system prompt
3. **Prompt 优化** — 调用 `optimize_prompt` 提升输入质量
4. **Auto Composer** — 检查 Token 阈值，必要时压缩
5. **对话循环**：
   - 调用 `OpenAI chat.completions.create`（非流式）
   - 若有 `tool_calls` → 执行工具 → 结果追加回消息列表 → 继续循环
   - 若无 `tool_calls` → 输出最终回复 → 结束循环
6. **后处理** — Micro Composer 清理 → 自动保存 → 返回结果

#### 辅助方法

| 方法 | 来源 | 功能 | 目的 |
|------|------|------|------|
| `_get_help_text()` | `main.py` | 获取帮助文本 | 供 `/help` 命令使用，列出所有可用命令和模式说明 |
| `_get_tools_text()` | `main.py` | 获取工具列表文本 | 供 `/tools` 命令使用，列出所有可用工具名称和描述 |

---

### 3.4 `main_stream.py` — 流式对话处理

**来源**: 独立模块，作为 `AgentSession` 的混入类  
**功能**: 提供流式版本的对话处理方法，支持 SSE 逐段落推送、推理摘要提取、工具调用链处理  
**目的**: 解决同步处理中用户需要等待完整回复的问题，实现实时流式体验

#### 工具函数

| 函数 | 来源 | 功能 | 目的 |
|------|------|------|------|
| `_split_into_paragraphs(text, min_chars)` | `main_stream.py` | 将文本按自然段落/句子分割成块 | 支持逐段落流式输出，提升前端阅读体验。分割策略：双换行 → 单换行 → 句号/问号 → 逗号/分号 |
| `_get_reasoning_summary(reasoning_text, max_chars)` | `main_stream.py` | 从完整推理内容中提取摘要 | 去除推理过程中的标记符（如 🧹、▊ 等），输出紧凑的 thinking 摘要 |

#### AgentSessionStreamMixin 类

| 方法 | 来源 | 功能 | 目的 |
|------|------|------|------|
| `process_message_stream(user_input)` | `main_stream.py` | 流式处理用户消息（生成器） | 流式版本的核心方法，逐段落 yield AI 回复，支持工具调用链处理 |

**`process_message_stream` 详细流程**：
1. **指令解析** — 同 `process_message`，但使用 `yield` 返回结果
2. **模式注入** — 同样注入 system prompt
3. **Prompt 优化** — 优化后通过 `__OPT__` 前缀 yield 给前端
4. **流式对话循环**：
   - 调用 `OpenAI chat.completions.create`（`stream=True`）
   - **打断检测** — 检查 `self._stream_interrupted` 标志
   - 收集 `content`、`reasoning_content`、`tool_calls`
   - 若有 `tool_calls` → 执行工具 → 流式输出工具调用信息 → 继续循环
   - 若无 `tool_calls` → 逐段落 yield `content` → 结束
5. **后处理** — Micro Composer → 自动保存 → 更新状态缓存回调
6. **异常安全** — `try/finally` 确保即使客户端断连也能 `auto_save`

**中断支持**：当 `_stream_interrupted = True` 时，停止当前流式请求，保存已有结果后退出。

---

### 3.5 `context.py` — 三重上下文管理器（Composer）

**来源**: 独立模块  
**功能**: 提供三种不同粒度的上下文压缩策略，用于控制对话历史的 Token 消耗  
**目的**: 防止长对话超出模型上下文窗口，在保留关键信息的同时降低 Token 成本

#### 1️⃣ Micro Composer — 每轮自动清理

| 函数 | 来源 | 功能 | 目的 |
|------|------|------|------|
| `micro_composer(msgs)` | `context.py` | 每轮对话后自动清理旧工具调用信息 | 保留所有轮次的对话消息（user/assistant 文本），但仅保留最近 2 轮的 tool 调用信息，更早的部分被移除。纯删除操作，不涉及 LLM 调用 |
| `_split_into_rounds(msgs)` | `context.py` | 将消息列表按"轮次"分组 | 每轮以 user 消息开始、下一条 user 消息结束。是 Micro Composer 和 Auto Composer 共同使用的辅助函数 |

**设计原则**：tool 调用结果（代码输出、文件内容）通常很长但只在当前轮次有用，保留多轮会快速填满 Token。

#### 2️⃣ Auto Composer — 阈值触发语义压缩

| 函数 | 来源 | 功能 | 目的 |
|------|------|------|------|
| `auto_composer(msgs, client, system_prompt)` | `context.py` | Token 达到阈值时自动触发 LLM 语义压缩 | 保留 system prompt + 最近 1 轮完整对话，对更早的历史进行 LLM 摘要，输出 ≤ 30,000 字符 |
| `_build_history_text(rounds)` | `context.py` | 构建待压缩的历史对话文本 | 将旧轮次格式化为文本，每条消息标注角色，工具结果截断至 200 字符 |
| `_llm_compress(history_text, client, max_chars, full_summary)` | `context.py` | 调用 LLM 进行对话摘要压缩 | 通过专用 prompt 让 AI 对历史对话进行摘要。`full_summary=True` 时（Manual Composer）prompt 要求更全面的摘要 |

**降级策略**：LLM 压缩失败时自动回退到截断模式，保证任何时候都能完成压缩。

#### 3️⃣ Manual Composer — 用户手动触发

| 函数 | 来源 | 功能 | 目的 |
|------|------|------|------|
| `manual_composer(msgs, client, system_prompt)` | `context.py` | 用户通过 `/compact` 手动触发，压缩全部上下文 | 对全部非 system 消息进行语义压缩，仅保留 system prompt + 压缩摘要，返回详细的压缩统计信息 |
| `_build_complete_history_text(msgs)` | `context.py` | 构建完整的对话历史文本 | 比 `_build_history_text` 保留更多细节（工具结果 300 字符，回复 1000 字符） |

#### 向后兼容接口

| 函数 | 来源 | 功能 | 目的 |
|------|------|------|------|
| `compact_messages(msgs, client)` | `context.py` | （已弃用）旧版本压缩接口 | 内部调用 `auto_composer`，保留此函数以兼容旧代码引用 |

---

### 3.6 `mode_manager.py` — 模式管理器

**来源**: 独立模块  
**功能**: 管理 Smart（智能处理）和 Plan（计划驱动）两种工作模式的状态  
**目的**: 封装模式状态切换和 Plan 就绪检测，解耦模式逻辑与 AgentSession

| 属性/方法 | 来源 | 功能 | 目的 |
|-----------|------|------|------|
| `ModeManager.__init__(self, mode)` | `mode_manager.py` | 初始化模式管理器 | 设置初始模式，初始化 Plan 文件路径和就绪状态 |
| `set_mode(mode)` | `mode_manager.py` | 设置新模式 | 验证模式值是否有效并执行切换 |
| `get_mode()` | `mode_manager.py` | 获取当前模式值 | 返回 `MODE_SMART` 或 `MODE_PLAN` |
| `get_mode_name()` | `mode_manager.py` | 获取当前模式名称 | 返回带 emoji 的显示名，供 UI 展示 |
| `set_plan_ready()` | `mode_manager.py` | 标记 Plan 已就绪 | Plan 模式生成 plan.md 后调用，通知系统弹出选择菜单 |
| `is_plan_ready()` | `mode_manager.py` | 检查 Plan 是否就绪 | 供前端定期轮询（`/api/plan/check`），决定是否显示 Plan 菜单 |

---

### 3.7 `prompts.py` — 系统提示词构建

**来源**: 独立模块  
**功能**: 根据当前模式（Smart / Plan）构建对应的系统提示词  
**目的**: 为 LLM 提供行为约束和角色设定，确保 AI 在不同模式下遵循不同的工作流程

| 函数 | 来源 | 功能 | 目的 |
|------|------|------|------|
| `build_system_prompt(mode)` | `prompts.py` | 根据模式构建系统提示词 | Smart 模式下引导 AI 直接执行；Plan 模式下引导 AI 先分析需求、创建 plan.md，再进入执行阶段 |

---

### 3.8 `prompt_optimizer.py` — Prompt 智能优化

**来源**: 独立模块  
**功能**: 使用 LLM 对用户输入进行智能优化，提升对话质量  
**目的**: 自动将模糊、口语化的用户输入转化为更精确、更结构化的指令，同时保留原始输入用于前端展示对比

| 函数 | 来源 | 功能 | 目的 |
|------|------|------|------|
| `optimize_prompt(user_input, client)` | `prompt_optimizer.py` | 使用 LLM 优化用户输入 | 调用 AI 对用户输入进行"精简、清晰、可执行"的改写。如果输入已足够清晰或优化失败则返回原始输入 |
| `format_optimized_prompt(original, optimized)` | `prompt_optimizer.py` | 将原始输入和优化后的 prompt 合并为最终输入 | 以"用户原始输入 + AI 优化版本"的形式构造最终消息，既保留原始意图又增强可执行性 |

---

### 3.9 `safety.py` — 命令安全检测

**来源**: 独立模块  
**功能**: 对 `run_cmd` 工具执行的系统命令进行安全检测  
**目的**: 防止 AI 执行危险的系统命令，确保 AI 代码执行的安全性

| 函数 | 来源 | 功能 | 目的 |
|------|------|------|------|
| `check_command_safety(cmd)` | `safety.py` | 检查系统命令的安全性 | 返回 `{"safe": bool, "reason": str, "warn": bool}`。对高危命令（如 `rm -rf`）返回拦截；对中危命令返回警告但自动放行 |

---

### 3.10 `session_manager.py` — 会话持久化管理

**来源**: 独立模块  
**功能**: 提供会话的序列化保存、反序列化恢复、自动保存、列表浏览和删除功能  
**目的**: 让用户可以在不同时间恢复之前的工作状态，实现对话的持久化存储

#### 内联函数

| 函数 | 来源 | 功能 | 目的 |
|------|------|------|------|
| `_estimate_msgs_tokens(msgs)` | `session_manager.py` | 内联 Token 估算函数 | 当 API 未返回 usage 字段时，通过 CJK/ASCII 字符比例估算 Token 数，避免保存 0 Token |

#### 核心 CRUD 函数

| 函数 | 来源 | 功能 | 目的 |
|------|------|------|------|
| `ensure_session_dir(save_dir)` | `session_manager.py` | 确保会话保存目录存在 | 自动创建 `sessions/` 目录 |
| `save_session(session, path, save_dir)` | `session_manager.py` | 序列化 AgentSession 为 JSON 文件 | 保存完整的会话状态：msgs、模式、Composer 统计、Token 信息、标题、Python 环境、原始输入记录等 |
| `load_session(path)` | `session_manager.py` | 从 JSON 文件加载会话数据 | 返回原始数据字典，供 `restore_session` 使用 |
| `restore_session(session, path)` | `session_manager.py` | 从 JSON 文件恢复会话到 AgentSession 对象 | 反序列化并恢复所有字段：消息、Token、Composer 统计数据、标题、环境配置，并重建 system prompt |
| `list_sessions(save_dir)` | `session_manager.py` | 列出所有已保存的会话 | 返回包含标题、时间、消息数、模式的排序列表 |
| `delete_session(path)` | `session_manager.py` | 删除指定会话文件 | 从磁盘删除 JSON 文件 |
| `auto_save(session, session_save_path, save_dir)` | `session_manager.py` | 自动保存会话为独立文件 | 首次保存按标题+时间戳命名，后续调用可传入路径覆盖更新 |
| `get_session_display_list(save_dir)` | `session_manager.py` | 获取格式化的会话列表文字 | 供 `/sessions` 命令显示 |
| `get_session_title_from_path(path)` | `session_manager.py` | 从会话文件路径读取标题 | 快速读取标题而不需完整反序列化 |

#### SessionRegistry 类 — 多会话注册表

| 方法 | 来源 | 功能 | 目的 |
|------|------|------|------|
| `create(session_id)` | `session_manager.py` | 创建新会话并注册 | 返回 `session_id`，支持指定 ID 或自动生成 UUID |
| `get(session_id)` | `session_manager.py` | 获取指定 session 实例 | 支持线程安全的并发访问 |
| `get_lock(session_id)` | `session_manager.py` | 获取指定 session 的锁 | 每个 session 有独立的 `threading.Lock`，支持真正并发 |
| `get_or_create(session_id)` | `session_manager.py` | 获取或创建会话 | 返回 `(session_id, session, lock)` 三元组 |
| `remove(session_id)` | `session_manager.py` | 从注册表移除会话 | 只移除不删除文件 |
| `set_active(session_id)` | `session_manager.py` | 设置当前活动会话 | Web API 多会话切换的核心 |
| `get_active()` | `session_manager.py` | 获取当前活动会话 ID | |
| `load_from_path(filepath)` | `session_manager.py` | 从文件加载会话到注册表 | 创建新 session，恢复后注册，返回 session_id |
| `all_sessions()` | `session_manager.py` | 获取所有会话 | 返回 `Dict[str, AgentSession]` |

---

### 3.11 `token_utils.py` — Token 统计工具

**来源**: 独立模块  
**功能**: 提供 Token 使用量的统计计算功能  
**目的**: 用于内部计数和调试日志，不再展示在对话界面中

| 函数 | 来源 | 功能 | 目的 |
|------|------|------|------|
| `show_token_usage(usage, prompt_tokens, completion_tokens, label)` | `token_utils.py` | 显示 Token 消耗信息 | 格式化输出输入/输出 Token、剩余上下文空间和占用百分比（调试用） |
| `get_token_stats_text(usage, prompt_tokens, completion_tokens, label)` | `token_utils.py` | 获取 Token 统计文本 | 与 `show_token_usage` 类似，返回紧凑的单行文本 |

> **注**：Token 统计信息不再出现在 AI 回复末尾。右侧信息面板仅显示总计 Token 数量和占用率，达到 80% 后自动触发上下文压缩。


### 3.12 `web_api.py` — FastAPI Web 服务层

**来源**: 独立模块  
**功能**: 提供完整的 RESTful API，支持流式/非流式聊天、多会话管理、状态缓存、模式切换、模型管理和环境配置  
**目的**: 作为后端服务，供前端 Web UI 调用，实现浏览器端的完整交互体验

#### 多会话注册表与状态缓存

| 组件 | 来源 | 功能 | 目的 |
|------|------|------|------|
| `_session_registry` | `web_api.py` | 全局多会话注册表实例 | 初始创建默认会话 "default" 并设为活跃 |
| `_get_session(session_id)` | `web_api.py` | 获取指定 session（默认活跃） | 支持无锁读取 session 实例 |
| `_get_session_lock(session_id)` | `web_api.py` | 获取指定 session 的锁 | 供需要同步访问的场景使用 |
| `_get_session_and_lock(session_id)` | `web_api.py` | 获取 session + lock | 便捷地一次性获取两者 |
| `_build_status_snapshot(session_id)` | `web_api.py` | 直接从 session 读取当前状态快照 | 线程安全的无锁状态读取（Python GIL 保证原子性） |
| `_update_status_cache()` | `web_api.py` | 更新状态缓存 | 流式请求结束后调用，刷新缓存 |
| `_get_cached_status()` | `web_api.py` | 获取缓存的状态快照 | 线程安全，不需要拿锁 |
| `_get_status_with_cache(timeout, session_id)` | `web_api.py` | 尝试获取锁读取最新状态，超时则返回缓存 | 核心机制：前端状态查询不会被流式请求阻塞，超时 0.3s 后自动降级到缓存 |
| `_try_lock_action(action_func, timeout, fallback)` | `web_api.py` | 尝试获取锁后执行操作 | 所有非读操作的路由通过此函数保护，避免流式期间的锁竞争 |

#### API 路由

| 路由 | 方法 | 功能 | 目的 |
|------|------|------|------|
| `GET /` | index | 返回主页面 HTML | 加载 `static/index.html`，提供前端界面入口 |
| `POST /api/chat` | chat | 发送消息，返回 AI 回复（非流式） | 向后兼容，返回完整的 JSON 响应 |
| `POST /api/chat/stream` | chat_stream | 流式聊天，返回 SSE | 核心流式接口，使用 `StreamingResponse` 推送 SSE 事件（chunk/tool_call/done/interrupted/error） |
| `POST /api/session/new` | create_session | 创建新会话 | 生成 UUID，注册到 SessionRegistry，设为活跃 |
| `GET /api/sessions/list` | list_all_sessions | 列出所有活跃会话和已保存会话 | 同时返回内存中的活跃会话和磁盘上的已保存会话文件 |
| `GET /api/session/active` | get_active_session | 获取当前活动会话信息 | 返回 session_id、标题、模式、消息数 |
| `POST /api/session/{id}/activate` | activate_session | 激活指定会话 | 切换活跃会话，注册状态回调 |
| `POST /api/chat/{id}/interrupt` | interrupt_chat | 打断流式回复 | 设置 `_stream_interrupted = True` |
| `DELETE /api/session/{id}` | delete_session | 从注册表删除会话 | 禁止删除默认会话 |
| `POST /api/mode/smart` | switch_to_smart | 切换到 Smart 模式 | |
| `POST /api/mode/plan` | switch_to_plan | 切换到 Plan 模式 | |
| `POST /api/context/clear` | clear_context | 清除上下文 | 调用 `session.reset()` |
| `POST /api/context/compact` | compact_context | 手动压缩上下文 | 调用 `session.compact_context()`（try-lock 保护） |
| `GET /api/context/help` | get_help | 获取帮助文本 | 调用 `session._get_help_text()` |
| `GET /api/context/status` | get_context_status | 获取 Composer 状态文本 | 调用 `session.get_composer_status()` |
| `GET /api/status` | get_full_status | 获取完整状态信息 | 支持缓存兜底，返回模式、消息数、Token 总计、占用率等 |
| `GET /api/status/realtime` | get_realtime_status | 获取实时简洁状态 | 用于前端自动刷新，返回一行状态文本 |
| `GET /api/session/title` | get_session_title | 获取会话标题 | |
| `POST /api/session/save` | save_session_api | 保存当前会话 | |
| `GET /api/chat/messages` | get_session_messages | 获取指定会话的消息列表 | 用于加载会话后在 UI 渲染历史消息，展示原始输入和优化后 Prompt |
| `GET /api/models` | list_models | 获取可用模型列表 | |
| `PUT /api/models/switch` | switch_model | 切换当前模型 | |
| `POST /api/models/add` | add_model | 添加自定义模型 | |
| `DELETE /api/models/{code}` | delete_model | 删除自定义模型 | |
| `PUT /api/models/{code}/config` | update_model_config | 更新模型的 API 覆盖配置 | |
| `GET /api/config` | get_config | 获取环境配置（Python/Conda） | |
| `PUT /api/config` | update_config | 更新环境配置 | |
| `POST /api/session/load` | load_session_api | 加载指定会话到注册表 | 支持复用已有 session（检测 `_session_save_path`） |
| `POST /api/session/delete` | delete_session_api | 删除指定会话文件 | |
| `POST /api/env/set` | set_env_api | 设置 Python 环境路径 | |
| `GET /api/env/info` | get_env_api | 获取 Python 环境信息 | |
| `GET /api/env/current` | get_env_current | 获取当前环境状态（前端用） | |
| `GET /api/env/conda/list` | list_conda_envs | 列出 conda 环境 | |
| `POST /api/env/conda/switch` | switch_conda_env | 切换 conda 环境 | |
| `POST /api/env/conda/create` | create_conda_env | 创建 conda 环境 | |
| `GET /api/plan/check` | check_plan_ready | 检查 Plan 菜单是否就绪 | 支持缓存兜底，不阻塞 |
| `POST /api/plan/action` | plan_action | 处理 Plan 菜单操作 | explore/modify/execute/confirm/reset 五种操作 |

#### SSE 事件类型（`/api/chat/stream`）

| 事件类型 | 说明 | 数据负载 |
|----------|------|----------|
| `chunk` | AI 文本回复片段 | `{type, content}` |
| `optimized_prompt` | 优化后的 Prompt | `{type, content}` |
| `tool_call` | 工具调用通知 | `{type, content}` |
| `done` | 流式传输完成 | `{type, mode, input_tokens, output_tokens, total_tokens, max_tokens, session_id}` |
| `interrupted` | 用户打断 | `{type, content}` |
| `interrupted_done` | 打断后结束 | `{type, mode, ...tokens}` |
| `error` | 错误信息 | `{type, content}` |

#### 启动函数

| 函数 | 来源 | 功能 | 目的 |
|------|------|------|------|
| `check_port_available(host, port)` | `web_api.py` | 检查端口是否可用 | 通过 socket 尝试绑定，避免端口冲突 |
| `find_available_port(host, start_port, max_attempts)` | `web_api.py` | 查找可用端口 | 端口被占用时自动递增，最多尝试 100 个端口 |
| `start_web_api(host, port)` | `web_api.py` | 启动 FastAPI 服务 | 启动 uvicorn 服务器，配置 24 小时 keep-alive |

---

### 3.13 `tools/__init__.py` — 工具注册与调度

**来源**: `tools/` 包的入口文件  
**功能**: 统一注册所有可用工具，提供 dispatch 调度函数  
**目的**: 集中的工具清单管理，供 LLM 的 Function Calling 机制使用

#### 工具注册表

| 组件 | 来源 | 功能 | 目的 |
|------|------|------|------|
| `TOOLS` | `tools/__init__.py` | OpenAI Function Calling 格式的工具定义列表 | 19 个工具的描述和参数 schema，直接传递给 LLM 的 `tools` 参数 |
| `TOOL_FUNCS` | `tools/__init__.py` | 工具名称到函数的映射字典 | `dispatch_tool` 通过此字典查找对应的 Python 函数 |
| `_TOOL_REQUIRED_PARAMS` | `tools/__init__.py` | 每个工具的必需参数列表 | 在 dispatch 时进行参数校验，向 LLM 提供明确的参数缺失错误 |
| `_TOOL_TIMEOUTS` | `tools/__init__.py` | 每个工具的执行超时配置 | 不同工具有不同的最晚等待时间（如 `run_cmd` 30s，`grep` 30s，`get_current_time` 5s） |
| `MAX_RESULT_CHARS` | `tools/__init__.py` | 结果最大字符数 | 30,000 字符，防止过长输出撑爆 Token |

#### 调度函数

| 函数 | 来源 | 功能 | 目的 |
|------|------|------|------|
| `dispatch_tool(name, args, timeout, max_result_chars)` | `tools/__init__.py` | 统一工具调度入口 | 完整的执行流程：工具存在检查 → 参数校验 → 超时配置 → 线程池执行（带超时保护） → 结果截断 → 错误格式化 |
| `dispatch_tool_from_json(name, args_json, timeout)` | `tools/__init__.py` | 从 JSON 字符串解析参数并调度 | 供旧版接口使用，先反序列化再调用 `dispatch_tool` |

**调度安全机制**：
- 使用 `threading.Thread` + `join(timeout)` 实现超时控制
- 超时后返回 "⚠️ 执行超时（X秒）"
- 异常捕获 + `traceback.format_exc()` 提供详细错误

#### 已注册的 19 个工具

| 工具名 | 来源文件 | 功能分类 |
|--------|----------|----------|
| `run_cmd` | `cmd_exec.py` | 命令执行 |
| `read_file` | `file_ops.py` | 文件操作 |
| `write_file` | `file_ops.py` | 文件操作 |
| `delete_file` | `file_ops.py` | 文件操作 |
| `list_files` | `dir_ops.py` | 目录操作 |
| `search_files` | `dir_ops.py` | 目录操作 |
| `create_directory` | `dir_ops.py` | 目录操作 |
| `get_system_info` | `info_ops.py` | 信息查询 |
| `get_current_time` | `info_ops.py` | 信息查询 |
| `grep` | `search_ops.py` | 搜索替换 |
| `replace` | `search_ops.py` | 搜索替换 |
| `find_files` | `search_ops.py` | 搜索替换 |
| `count_lines` | `search_ops.py` | 搜索替换 |
| `diff` | `search_ops.py` | 搜索替换 |
| `git_status` | `git_ops.py` | Git 操作 |
| `git_log` | `git_ops.py` | Git 操作 |
| `git_diff` | `git_ops.py` | Git 操作 |
| `git_commit_stats` | `git_ops.py` | Git 操作 |
| `show_file` | `git_ops.py` | Git 操作 |

---

### 3.14 `tools/cmd_exec.py` — 命令执行工具

**来源**: `tools/` 子模块  
**功能**: 执行系统命令并提供安全检测  
**目的**: 让 AI 能够执行系统命令进行代码运行、环境配置等操作，同时防止恶意命令

| 函数 | 来源 | 功能 | 目的 |
|------|------|------|------|
| `tool_run_cmd(cmd)` | `cmd_exec.py` | 执行系统命令（带安全检测） | 调用 `check_command_safety` 检测 → Windows 上自动设置 UTF-8 编码 → subprocess 执行 → 输出截断至 10,000 字符 → 30 秒超时 |
| `tool_run_cmd_compat(args)` | `cmd_exec.py` | 向后兼容版本（dict 参数） | 支持旧版调用方式，内部转为具名参数调用新版接口 |

---

### 3.15 `tools/file_ops.py` — 文件操作工具

**来源**: `tools/` 子模块  
**功能**: 提供文件读取、写入、删除功能  
**目的**: 让 AI 能够直接操作文件系统，实现代码生成、文档读取等交互

| 函数 | 来源 | 功能 | 目的 |
|------|------|------|------|
| `tool_read_file(path)` | `file_ops.py` | 读取文件完整内容 | UTF-8 编码读取，自动处理编码错误和长文件截断（20,000 字符），对文件不存在、路径为目录、权限不足分别返回友好错误 |
| `tool_write_file(path, content)` | `file_ops.py` | 写入或覆盖文件内容 | 自动创建所有父目录，返回写入字符数统计 |
| `tool_delete_file(path)` | `file_ops.py` | 删除文件或空目录 | 附带系统关键路径保护（拦截 C:\Windows、C:\Program Files 及其子目录的删除），非空目录返回错误 |
| `tool_read_file_compat(args)` | `file_ops.py` | 向后兼容（dict 参数） | |
| `tool_write_file_compat(args)` | `file_ops.py` | 向后兼容（dict 参数） | |
| `tool_delete_file_compat(args)` | `file_ops.py` | 向后兼容（dict 参数） | |

---

### 3.16 `tools/dir_ops.py` — 目录操作工具

**来源**: `tools/` 子模块  
**功能**: 提供目录内容列出、文件搜索、目录创建功能  
**目的**: 让 AI 能够浏览文件系统结构，快速定位文件

| 函数 | 来源 | 功能 | 目的 |
|------|------|------|------|
| `tool_list_files(directory, show_hidden, pattern)` | `dir_ops.py` | 列出目录内容 | 显示文件和子目录的大小、修改时间，默认隐藏 "." 开头的文件，显示目录/文件统计汇总，最多显示 200 项 |
| `tool_search_files(name, directory, max_results)` | `dir_ops.py` | 按名称搜索文件 | 递归遍历目录，自动跳过隐藏目录和 `node_modules`/`__pycache__`/`.git` 等构建目录 |
| `tool_create_directory(path)` | `dir_ops.py` | 创建目录（类似 `mkdir -p`） | 支持创建多级目录，已存在时静默成功 |

---

### 3.17 `tools/info_ops.py` — 信息查询工具

**来源**: `tools/` 子模块  
**功能**: 提供系统信息和当前时间的查询功能  
**目的**: 让 AI 能够感知运行环境

| 函数 | 来源 | 功能 | 目的 |
|------|------|------|------|
| `tool_get_system_info()` | `info_ops.py` | 获取系统基本信息 | 返回操作系统、Python 版本、CPU 核心数、当前用户、工作目录、系统编码等 |
| `tool_get_current_time()` | `info_ops.py` | 获取当前日期和时间 | 返回精确到秒的时间，含中文星期显示 |

---

### 3.18 `tools/search_ops.py` — 搜索与替换工具

**来源**: `tools/` 子模块  
**功能**: 提供正则搜索、文本替换、代码行数统计、文件查找和差异比较功能  
**目的**: 让 AI 能够进行代码搜索、重构和统计等开发任务

#### 辅助函数

| 函数 | 来源 | 功能 | 目的 |
|------|------|------|------|
| `_should_ignore(path, name, extra_ignores)` | `search_ops.py` | 判断路径是否应忽略 | 基于 `IGNORE_DIRS` 集合和隐藏目录规则过滤，避免搜索构建/依赖目录 |
| `_is_binary(path)` | `search_ops.py` | 检测文件是否为二进制 | 读取前 8KB 检查是否包含 `\x00` 空字节，快速跳过非文本文件 |

#### 搜索工具

| 函数 | 来源 | 功能 | 目的 |
|------|------|------|------|
| `tool_grep(pattern, directory, glob, max_results, ignore_case, context_lines)` | `search_ops.py` | 在文件中搜索文本（类似 `grep -r`） | 支持正则表达式、文件通配符过滤、大小写忽略、上下文行显示，自动跳过二进制和忽略目录 |
| `tool_replace(pattern, replacement, directory, glob, max_files, dry_run)` | `search_ops.py` | 搜索并替换文件内容（类似 `sed -i`） | 默认预览模式（dry_run=True），确认后可执行替换。预览时显示匹配的文件和替换处数 |
| `tool_count_lines(directory, pattern, exclude_pattern)` | `search_ops.py` | 统计代码行数 | 按文件类型分组统计文件数、总行数、代码行数、空白行数，支持排除模式 |
| `tool_find_files(pattern, directory, sort_by, max_results)` | `search_ops.py` | 按名称模式查找文件（类似 `find`） | 支持花括号展开（`*.{tsx,jsx}`）和多种排序方式，显示文件大小和涉及目录数 |
| `tool_diff(file1, file2, context_lines)` | `search_ops.py` | 比较两个文件的差异（类似 `diff`） | 使用 `difflib.unified_diff` 输出统一格式差异，统计增减行数 |

---

### 3.19 `tools/git_ops.py` — Git 操作工具

**来源**: `tools/` 子模块  
**功能**: 提供 Git 仓库状态查看、提交历史、变更差异、贡献统计和文件内容显示功能  
**目的**: 让 AI 能够进行 Git 仓库的代码审查和历史追踪

#### 辅助函数

| 函数 | 来源 | 功能 | 目的 |
|------|------|------|------|
| `_run_git(args, directory, timeout)` | `git_ops.py` | 执行 git 命令并返回输出 | 统一执行入口，处理 `FileNotFoundError`（git 未安装）、超时、其他异常 |
| `_is_git_repo(directory)` | `git_ops.py` | 检查目录是否为 Git 仓库 | 检查 `.git` 目录或 `.git` 文件（用于 submodule 场景） |
| `_format_size(size)` | `git_ops.py` | 字节数转为人类可读格式 | 自动选择 B/KB/MB/GB 单位 |

#### Git 工具

| 函数 | 来源 | 功能 | 目的 |
|------|------|------|------|
| `tool_git_status(directory)` | `git_ops.py` | 显示 Git 仓库状态（类似 `git status --short`） | 显示分支、远程差异（ahead/behind）、暂存区/未暂存/冲突/未跟踪文件的详细统计 |
| `tool_git_log(directory, count, branch, author)` | `git_ops.py` | 查看 Git 提交历史 | 显示短 SHA、提交者、相对时间和主题行，支持分支和作者过滤 |
| `tool_git_diff(directory, staged, path, max_lines)` | `git_ops.py` | 查看 Git 变更差异 | 支持工作区/暂存区差异、指定文件路径，显示文件名列表加增减统计 |
| `tool_git_commit_stats(directory, days, top_n)` | `git_ops.py` | 统计 Git 提交贡献 | 显示指定天数内的提交数、作者排名（带条形图百分比） |
| `tool_show_file(path, start_line, line_count)` | `git_ops.py` | 显示文件内容（带行号） | 从指定行号和行数显示文件，支持分页浏览 |

---

## 4. 数据流说明

### 4.1 完整对话流程

```
┌─────────────────────────────────────────────────────┐
│                   用户输入                            │
└────────────────────┬────────────────────────────────┘
                     ↓
            ┌────────────────┐
            │  指令解析       │ ← /clear, /save, /compact, /help 等
            │  (/命令检测)    │    直接返回，不调 LLM
            └────────────────┘
                     ↓ (正常对话)
            ┌────────────────┐
            │  模式注入       │ ← 每 3 轮或模式切换后注入 system prompt
            └────────────────┘
                     ↓
            ┌────────────────┐
            │  Prompt 优化   │ ← optimize_prompt() 调用 LLM 优化输入
            └────────────────┘
                     ↓
            ┌────────────────┐
            │  Auto Composer │ ← Token ≥ 80% 阈值时自动压缩
            └────────────────┘
                     ↓
            ┌────────────────┐
            │  API 调用       │ ← OpenAI chat.completions.create()
            │  (stream=True)  │
            └────────────────┘
                     ↓
            ┌──────────────────────────────────┐
            │      流式响应处理                   │
            │                                    │
            │  ┌─────────────┐  ┌────────────┐  │
            │  │ tool_calls? │→ │ 执行工具     │  │
            │  │     ↓       │  │ (tools/*)   │→│ 继续循环
            │  │    否       │  └────────────┘  │
            │  │     ↓       │                  │
            │  │ 文本回复     │                  │
            │  └─────────────┘                  │
            └──────────────────────────────────┘
                     ↓
            ┌────────────────┐
            │  Micro Composer│ ← 清理旧 tool 信息
            └────────────────┘
                     ↓
            ┌────────────────┐
            │  自动保存       │ ← 保存为独立 JSON 文件
            └────────────────┘
                     ↓
            ┌────────────────┐
            │  返回给用户     │ ← SSE 事件/JSON 响应
            └────────────────┘
```

### 4.2 多会话并发管理

```
Web API 层                    SessionRegistry              辅助层级
┌──────────────┐            ┌─────────────────┐   ┌─────────────────┐
│ /api/chat    │  ───────→  │ default session │   │ 状态缓存系统     │
│ /api/status  │            │ (thread lock)    │   │ (无锁读取，     │
│              │            │                 │   │  超时降级)      │
│ /api/session │  ───────→  │ session-abc123  │   └─────────────────┘
│ /new         │            │ (thread lock)    │
│              │            │                 │
│ /api/chat    │  ───────→  │ session-def456  │
│ /stream      │            │ (thread lock)    │
└──────────────┘            └─────────────────┘
       │                           │
       │ 流式期间                  │ per-session 锁
       │ 状态查询                  │ 不同 session 可并发
       ↓                           ↓
┌─────────────────┐      ┌─────────────────┐
│ 状态缓存兜底      │      │ 真正并发          │
│ (0.3s 超时缓存)  │      │ (不互相阻塞)      │
└─────────────────┘      └─────────────────┘
```

### 4.3 Composer 三重压缩触发时机

```
Timeline: 用户1 → API → 回复 → 用户2 → API → 回复 → ... → 用户N

每轮后:     ──→ Micro Composer ──→ 清理旧 tool 信息
                                     (保留最近 2 轮)

Token ≥80%: ──→ Auto Composer ──→ LLM 语义压缩
                                     (保留 system + 最近 1 轮完整)

用户主动:   /compact → Manual Composer → LLM 压缩全部
                                     (仅保留 system + 摘要)
```

---

## 5. 未来更新目标

### 5.1 Skill 技能系统引入与人格化持久性

#### 目标描述

将当前面向工具的 Function Calling 架构升级为**可插拔的 Skill 技能系统**，使 TennineClaw 能够像 OpenClaw 一样拥有持续学习、人格记忆和可扩展的能力边界。

#### 详细规划

| 子目标 | 详细说明 | 预期价值 |
|--------|---------|---------|
| **Skill 注册与发现** | 建立统一的 Skill 注册表（类似现有 `TOOL_FUNCS`），每个 Skill 含独立的 `SKILL.md` 描述文件、参数 schema 和调用入口 | 第三方可编写 Skill，扩展 AI 能力时无需修改核心代码 |
| **内存持久化（MEMORY.md 机制）** | 引入文件级长期记忆，每次对话结束时自动将关键决策、用户偏好、项目上下文写入 `memory/YYYY-MM-DD.md`，周期性提炼到 `MEMORY.md` | AI 跨 session 保持人格一致性，不因上下文压缩丢失用户信息 |
| **身份文件（SOUL.md）** | 每个 session 加载时读取身份文件，定义 AI 的角色、人格特质、回复风格和工作原则 | 每次重启或切换 session 后，AI 立即恢复一致的行为模式，无需重复设定 |
| **技能 Skill 与记忆联动** | Skill 执行结果中的"值得记住"的信息自动触发记忆写入；记忆中的长期知识可被 Future Skill 读取作为上下文 | 技能执行本身也具备"学习效应"，越用越聪明 |
| **用户画像文件（USER.md）** | 持续记录用户的技术偏好、常用语言/框架、命名习惯、风格偏好 | 后续代码生成和问题解答时自动调优风格，减少重复说明 |
| **热更新与 Skill 市场** | 支持运行时加载/卸载 Skill，发现 ClawHub 社区 Skill 并一键安装 | 生态可生长，不需要为了新工具重写整个 Agent |

#### 架构影响

```
当前                     →     未来
─────────────────────────────────────────────
TOOLS (固定 19 个工具)   →     Skill Registry (动态注册)
AgentSession 直接调度     →     SkillDispatcher (统一调度+权限+超时)
无持久记忆               →     MEMORY.md · USER.md · SOUL.md 文件系统
所有逻辑在 AgentSession   →     每个 Skill 独立目录 (SKILL.md + scripts)
```

---

### 5.2 多 Agent 协同调用（主子 Agent 架构）

#### 目标描述

引入**主子 Agent 调用机制**，让 TennineClaw 能够将大型复杂任务拆解给多个独立的子 Agent 并行执行，并在执行完成后汇总结果。当前的单 Agent 串行执行模式在任务复杂时效率瓶颈明显。

#### 详细规划

| 子目标 | 详细说明 | 预期价值 |
|--------|---------|---------|
| **子 Agent 会话管理** | 在 `SessionRegistry` 中引入父子关系标记，子 Agent 拥有独立的 `AgentSession`、模型配置和上下文窗口 | 主 Agent 发号施令，子 Agent 专注于单一子任务，互不干扰 |
| **任务分解与分配** | 主 Agent 收到复杂请求后，自动分析并拆解为可并行子任务，为每个子任务分配一个子 Agent | 将"分析项目结构"与"检查代码质量"并行执行，而非串行 |
| **结果聚合机制** | 子 Agent 执行完成后返回结构化结果，主 Agent 自动汇总并输出最终结论 | 用户收到的是整合后的统一回复，而非多个独立的输出碎片 |
| **子 Agent 隔离与安全** | 子 Agent 运行在隔离的上下文空间中，无法相互访问对方的消息历史；通过主 Agent 可信通道中转数据 | 防止子 Agent 间的数据串扰和信息泄露 |
| **异步非阻塞执行** | 主 Agent 下发任务后立即返回，通过回调或轮询机制收集子 Agent 执行结果，支持进度查询 | 主 Agent 不阻塞等待，可在后台并行推进多个子任务 |
| **子 Agent 类型模板** | 定义多种子 Agent 模板：代码审查 Agent、搜索 Agent、文件分析 Agent、Git 历史 Agent 等 | 用户或开发者可按需实例化不同类型的专业子 Agent |

#### 架构影响

```
当前 (单 Agent)                      未来 (主子 Agent)
─────────────────────────────────────────────────────────────
AgentSession                         Master Agent
  └─ process_message_stream()           ├─ 任务分析 → 拆解
       └─ 串行工具循环                   ├─ spawn Sub-Agent-1 (代码审查)
                                           │   └─ 独立 session · 独立工具
                                           ├─ spawn Sub-Agent-2 (Git 历史)
                                           │   └─ 独立 session · 独立工具
                                           └─ 收集结果 → 汇总输出
```

#### 协议设计示意

```
主 Agent  → 子 Agent:
  {
    "task_id": "uuid",
    "type": "code_review",
    "params": { "path": "src/", "focus": "security" },
    "context": { "max_tokens": 4000, ... }
  }

子 Agent → 主 Agent:
  {
    "task_id": "uuid",
    "status": "completed",
    "result": { "summary": "发现 3 个安全漏洞...", "details": [...] },
    "tokens_used": { "input": 2500, "output": 800 }
  }
```

#### 优先实现路线

| 阶段 | 内容 | 里程碑 |
|------|------|--------|
| **Phase 1** | 主子 Agent 基础通信协议 + 子 Agent 生命周期管理 | 主 Agent 能 spawn 一个子 Agent 并获取结果 |
| **Phase 2** | 任务自动分解 + 并行调度 | 复杂请求自动拆解并并行执行子任务 |
| **Phase 3** | 结果聚合 + 失败重试 + 超时控制 | 多个子 Agent 的产出能自动汇总成连贯回复 |
| **Phase 4** | Agent 模板市场 + 子 Agent 持久化 | 不同类型的子 Agent 可复用、可保存/恢复 |

---

> **文档版本**: 1.0  
> **生成日期**: 2026年5月19日  
> **对应代码版本**: v1.1.0  
> **最近更新**: 2026年5月19日 — 首个正式版本


