# TennineClaw

> 智能终端助手 — 基于 AI 的代码分析与任务执行平台

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)]()
[![Python](https://img.shields.io/badge/python-3.10+-green.svg)]()
[![License](https://img.shields.io/badge/license-MIT-yellow.svg)]()

TennineClaw 是一个功能丰富的 AI 编程助手 Web 平台，支持流式对话、代码执行、文件操作、Git 集成、会话管理和上下文压缩。

---

## 📅 更新时间轴

| 日期 | 版本 | 亮点 |
|------|------|------|
| 🆕 2026-05-20 | v1.0.0 | 首个正式版本：Web UI (FastAPI + SSE流式)、19个工具、三重 Composer 上下文压缩、多会话管理、Smart/Plan 双模式 |

---

## ✨ 特性

| 特性 | 说明 |
|------|------|
| 🧠 **AI 对话** | 流式输出，支持 DeepSeek 等模型 |
| 🔍 **Grep 搜索** | 正则搜索文件内容，支持文件过滤 + 上下文行 |
| 💻 **命令执行** | 安全检测的系统命令执行（带黑名单） |
| 📂 **文件操作** | 读/写/搜索/替换/比较，支持分页查看 |
| 🐍 **Conda 环境** | 查看/切换/创建 Python 环境 |
| 📋 **Plan 模式** | 复杂任务的规划、修改、分步执行 |
| 💾 **会话管理** | 独立文件保存，按日期分组，搜索过滤 |
| 🗜️ **上下文压缩** | 自动/手动/微缩三级压缩，防止 Token 溢出 |
| 📊 **Token 监控** | 实时显示输入/输出 Token 和上下文占用率 |
| 🌙 **主题切换** | 深色/浅色主题 |

---

## 🚀 快速开始

### 1. 安装

```bash
git clone https://github.com/your-org/tennineclaw.git
cd TennineClaw
pip install -r requirements.txt
```

### 2. 启动

**Windows 用户：**
```bash
run.bat
```

**或直接运行：**
```bash
python -m web_api
```

### 3. 配置 API

1. 打开浏览器访问 **http://127.0.0.1:7860**
2. 点击右上角模型选择下拉框旁的 **⚙️** 按钮
3. 填入 API Key 和 Base URL
4. 配置自动持久化，下次启动无需重复设置

> API 配置完全通过 Web UI 管理，无需编辑 `.env` 文件。

---

## 🖥️ 界面布局

```
┌──────────────────────────────────────────────────────────┐
│ 🧠 TennineClaw               🌙 🟢 在线    [模型 ▼] [⚙️] │
├─────────┬────────────────────────┬──────────────────────┤
│ 左侧栏    │ 聊天区域                │ 右侧面板              │
│ ✏️ 新开  │                        │ 🎮 控制面板           │
│ 🔍 搜索   │  💬 会话标题             │ 🧩 Composer 状态      │
│ ─── 今天  │                        │ 📊 Token 用量         │
│ 📄 会话A  │  👤 用户消息             │ ⚡ 快捷操作            │
│ 📄 会话B  │  🧠 AI 回复...           │                      │
│ ─── 昨天  │                        │                      │
│ 📄 会话C  │  ┌─────────────┐       │                      │
│          │  │ 输入消息...   │       │                      │
│          │  └─────────────┘       │                      │
└─────────┴────────────────────────┴──────────────────────┘
```

---

## 🔧 可用工具

### 搜索与文件

| 工具 | 功能 | 示例 |
|------|------|------|
| `grep` | 正则搜索文件内容 | `grep("def __init__", glob="*.py", context=2)` |
| `replace` | 搜索替换（默认预览） | `replace("old", "new", dry_run=True)` |
| `find_files` | 按名称查找文件 | `find_files("*.py", sort_by="size")` |
| `count_lines` | 统计代码行数 | `count_lines(pattern="*.py,*.js")` |
| `diff` | 文件差异对比 | `diff("a.py", "b.py")` |
| `show_file` | 带行号查看文件 | `show_file("main.py", start=50, count=30)` |

### Git

| 工具 | 功能 |
|------|------|
| `git_status` | 查看仓库状态（分支、变更、冲突、ahead/behind） |
| `git_log` | 查看提交历史（支持分支/作者过滤） |
| `git_diff` | 查看工作区差异 |
| `git_commit_stats` | 统计贡献者提交数 |

### 系统

| 工具 | 功能 |
|------|------|
| `run_cmd` | 执行系统命令（带安全检测） |
| `read_file` / `write_file` | 文件读写 |
| `list_files` / `create_directory` | 目录操作 |
| `get_system_info` | 系统信息 |
| `get_current_time` | 当前时间 |

---

## 🏗️ 架构

```
┌─────────────────────────────────────────────┐
│         Web UI (FastAPI + Static Files)      │
│   static/index.html + style.css + app.js    │
├─────────────────────────────────────────────┤
│           web_api.py (API 路由层)             │
├─────────────────────────────────────────────┤
│      main.py / main_stream.py (核心引擎)      │
├─────────────────────────────────────────────┤
│   tools/                                      │
│   ├── __init__.py    工具注册表                 │
│   ├── cmd_exec.py    系统命令执行                │
│   ├── file_ops.py    文件读写                   │
│   ├── dir_ops.py     目录操作                   │
│   ├── info_ops.py    系统信息                   │
│   ├── search_ops.py  Grep / 替换 / 统计         │
│   └── git_ops.py     Git 集成                   │
├─────────────────────────────────────────────┤
│   支持层                                       │
│   ├── context.py         上下文管理与压缩        │
│   ├── session_manager.py 会话保存/加载/注册表    │
│   ├── safety.py          命令安全检测            │
│   ├── prompts.py         系统提示词模板          │
│   ├── prompt_optimizer.py 提示词优化            │
│   ├── token_utils.py     Token 统计工具          │
│   └── mode_manager.py    模式管理               │
└─────────────────────────────────────────────┘
```

## 📁 项目结构

```
TennineClaw/
├── __init__.py              # 包初始化 + 版本号
├── config.py                # 配置管理（持久化 + 默认值）
├── main.py                  # 核心对话引擎
├── main_stream.py           # 流式对话引擎
├── web_api.py               # FastAPI Web 接口（37 条路由）
│
├── session_manager.py       # 会话持久化 + 多会话注册表
├── context.py               # 上下文压缩（Micro/Auto/Manual）
├── mode_manager.py          # Smart / Plan 模式管理
├── prompt_optimizer.py      # 用户输入提示词优化
├── prompts.py               # 系统提示词模板
├── safety.py                # 系统命令安全检测
├── token_utils.py           # Token 统计与格式化
│
├── requirements.txt         # Python 依赖
├── run.bat / run.ps1        # Windows 启动脚本
│
├── tools/                   # Function Calling 工具集
│   ├── __init__.py          # 工具注册与调度
│   ├── cmd_exec.py          # 系统命令执行
│   ├── file_ops.py          # 文件读写
│   ├── dir_ops.py           # 目录操作
│   ├── info_ops.py          # 系统信息查询
│   ├── search_ops.py        # Grep / 替换 / 代码统计
│   └── git_ops.py           # Git 状态 / 日志 / 差异
│
└── static/                  # 前端静态资源
    ├── index.html           # 主页面
    ├── js/api.js            # API 调用封装
    ├── js/app.js            # 前端交互逻辑
    └── css/style.css        # 样式（深色/浅色主题）
```

---

## ⚙️ 配置

### 启动参数

| 环境变量 | 说明 | 默认值 |
|----------|------|--------|
| `GRADIO_PORT` | Web 服务端口 | `7860` |
| `GRADIO_HOST` | 监听地址 | `127.0.0.1` |

### API 配置

API Key、Base URL、模型选择均通过 **Web UI 右上角** 模型设置页面配置，配置自动持久化到 `user_config.json`，重启后保留。

### 命令参考

| 命令 | 说明 |
|------|------|
| `/smart` | 切换到 Smart 模式 |
| `/plan` | 切换到 Plan 模式 |
| `/clear` | 清除上下文 |
| `/compact` | 手动压缩上下文 |
| `/save [标题]` | 保存当前会话 |
| `/load <文件名>` | 加载历史会话 |
| `/status` | 查看当前状态 |
| `/tools` | 查看可用工具 |
| `/title <新标题>` | 修改会话标题 |
| `/help` | 查看帮助 |

---

## 💬 使用示例

### 搜索代码

```
你：帮我找出所有 FastAPI 路由定义
→ AI 调用 grep()
→ 返回所有路由定义及其所在文件和行号
```

### Git 状态

```
你：看看当前仓库状态
→ AI 调用 git_status()
→ 显示分支、暂存区、未跟踪文件
```

### 代码统计

```
你：统计一下这个项目有多少行代码
→ AI 调用 count_lines()
→ 按语言显示代码行数统计
```

### 批量替换

```
你：把 print 全部改成 logging.info
→ AI 调用 replace()
→ 先预览，确认再执行
```

---

## 🛡️ 安全

- 高危命令（`rm -rf`、`format`、`dd if=` 等）自动拦截
- API Key 通过 Web UI 配置，不存储在代码中
- `user_config.json` 和 `sessions/` 目录已加入 `.gitignore`

---

## 📄 许可

MIT License

---

## 📋 完整更新日志

### v1.0.0 (2026-04)

**Web UI 全面重构 — FastAPI + 多会话 + SSE 流式**

- 从 Gradio 迁移到 **FastAPI + 静态前端**，支持 37+ RESTful 路由
- 引入 **SSE 流式对话**（`/api/chat/stream`），逐段落推送推理+回复
- 多会话管理：SessionRegistry + per-session 锁 + 独立会话切换
- **状态缓存系统**：流式期间状态查询 0.3s 超时降级，不阻塞流式请求
- 模型 API 覆盖：每个模型可独立配置 base_url / api_key，持久化到 user_config.json
- 自定义模型：支持添加/删除第三方模型（GPT、Claude 等）
- Plan 菜单交互：explore / modify / execute / confirm / reset 五种操作
- 对话中断机制：前端打断时设置 `_stream_interrupted`，安全保存已回复内容
- 原始输入与优化 Prompt 分别记录，前端 UI 中展示优化前后对比
- 深色/浅色主题全面适配
- 右侧面板实时显示 Composer 状态与 Token 监控

### v10.0.0 (2026-03)

**Composer 三重上下文压缩定型**

- **Micro Composer** — 每轮对话后自动清理旧 tool 调用信息，保留最近 N 轮
- **Auto Composer** — Token 达 80% 阈值时自动触发 LLM 语义压缩，降级截断
- **Manual Composer** — 用户通过 `/compact` 手动触发，压缩全部上下文
- LLM 压缩 prompt 优化：区分 Auto 与 Manual 两种摘要策略
- Composer 触发统计：次数记录 + 消息数/Token 变化展示
- 压缩失败降级策略：LLM 异常时自动回退到截断模式
- Token 监控系统：实时输入/输出/总计显示，会话级累计统计

### v9.0.0 (2026-02)

**流式引擎重构**

- 流式对话循环：`process_message_stream()` 生成器模式
- 文本分段输出：`_split_into_paragraphs()` 多策略分割（段落→行→句子→子句）
- 推理摘要提取：`_get_reasoning_summary()` 去除标记符，输出紧凑 thinking
- 工具调用链流式处理：逐工具执行并在流中插入结果通知
- 会话自动保存：每轮完成后保存为 JSON 文件
- Plan 模式自动检测：回复末尾自动附加 Plan 菜单提示
- Token 统计尾部附加：回复完成后显示本轮/累计 Token 数
- 会话标题自动生成：首次用户消息取前 N 字作为标题
- 模式 system prompt 周期性注入：每 3 轮或切换后自动注入

### v8.0.0 (2026-01)

**全面工具集**

- **搜索工具**：`tool_grep()` — 正则搜索 + 文件通配符 + 上下文行
- **替换工具**：`tool_replace()` — 默认预览模式，确认后执行
- **文件查找**：`tool_find_files()` — 花括号展开 + 三种排序
- **代码统计**：`tool_count_lines()` — 按文件类型分组统计
- **差异比较**：`tool_diff()` — unified_diff 格式 + 增减统计
- **Git 工具集**：`git_status` / `git_log` / `git_diff` / `git_commit_stats` / `show_file`
- `git_status`：分支 + ahead/behind + 暂存/未暂存/冲突/未跟踪
- `git_log`：short SHA + 作者 + 相对时间 + 主题
- `git_commit_stats`：条形图 + 百分比排名
- **Conda 环境管理**：`list_conda_envs()` / `switch_conda_env()` / `create_conda_env()`
- **命令执行**：`tool_run_cmd()` — UTF-8 编码适配 + 30s 超时 + 输出截断 10K
- **文件操作**：`tool_read_file()` / `tool_write_file()` / `tool_delete_file()`
- 系统关键路径保护：C:\Windows、C:\Program Files 删除拦截
- 目录操作优化：隐藏文件过滤 + 忽略目录自动跳过

### v7.0.0 (2025-12)

**Gradio 界面 + Prompt 优化 + 双模式**

- Gradio Web UI 初始版本
- Prompt 智能优化：`optimize_prompt()` 调用 LLM 打磨用户输入
- Smart / Plan 双模式切换
- ModeManager 模式管理：`set_mode()` / `get_mode()` / `is_plan_ready()`
- 指令系统：`/clear` / `/compact` / `/smart` / `/plan` / `/help` / `/tools` / `/status`
- 命令安全检测：`check_command_safety()` 高危命令拦截 + 中危警告
- 系统 Prompts 模板：`build_system_prompt()` 双模式差异化
- 工具注册表：`dispatch_tool()` 统一调度 + 超时线程保护
- 32,000 字符结果截断 + 2,000 字符工具结果截断

### v6.0.0 (2025-11)

**初始功能基座**

- OpenAI SDK 集成，Function Calling 风格工具调用
- 基础命令执行 `tool_run_cmd()` 初始版
- 基础文件读写与目录操作
- 系统信息查询与当前时间
- 配置管理：`.env` 环境变量加载
- 会话初始保存/加载机制
- 基础 Token 统计

---

**Made with ❤️**
(2025-11)

**初始功能基座**

- OpenAI SDK 集成，Function Calling 风格工具调用
- 基础命令执行 `tool_run_cmd()` 初始版
- 基础文件读写与目录操作
- 系统信息查询与当前时间
- 配置管理：`.env` 环境变量加载
- 会话初始保存/加载机制
- 基础 Token 统计

---

**Made with ❤️**

