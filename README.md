# TennineClaw

> 智能终端助手 · 基于 AI 的代码分析与任务执行平台

[![Version](https://img.shields.io/badge/version-1.1.0-blue.svg)]()
[![Python](https://img.shields.io/badge/python-3.10+-green.svg)]()
[![License](https://img.shields.io/badge/license-MIT-yellow.svg)]()

[🌏 **English**](README.en.md) | [🇨🇳 **中文**](README.md)

TennineClaw 是一个功能丰富的 AI 编程助手 Web 平台，支持流式对话、命令执行、文件操作、Git 集成、会话管理、上下文压缩等功能。

---

## 📅 发行时间线

| 日期 | 版本 | 说明 |
|------|------|------|
| 2026年5月22日 | v1.1.0 | 自定义角色系统（personas/目录动态扫描）、技能管理弹窗（增删/开关）、人格模板动态加载、soul.md 灵魂定义、修复角色切换与技能同步 Bug |
| 2026年5月19日 | v1.0.0 | 首个正式版本：Web UI (FastAPI + SSE 流式)、19 个工具、内置 Composer 上下文压缩、会话管理、Smart/Plan 双模式 |

---

## ✨ 功能

| 功能 | 说明 |
|------|------|
| 🤖 **AI 对话** | 流式响应，支持 DeepSeek 等模型 |
| 🔍 **Grep 搜索** | 递归搜索文件内容，支持文件过滤 + 上下文显示 |
| ⚡ **命令执行** | 安全检测的系统命令执行，支持超时控制 |
| 📁 **文件操作** | 读/写/删除/替换/比较，支持分页查看 |
| 🐍 **Conda 管理** | 查看/切换/创建 Python 环境 |
| 📋 **Plan 模式** | 结构化任务的规划、修改、分步执行 |
| 💬 **会话管理** | 自动文件保存，支持分组、搜索、重命名 |
| 🧩 **上下文压缩** | 自动/手动/微压缩，防止 Token 溢出 |
| 📊 **Token 监控** | 实时显示输入/输出 Token 数量及占比 |
| 🎭 **自定义角色** | 支持通过 personas/ 目录动态加载角色，包含完整人格定义（OCEAN五因素、语言风格、行为偏好）+ soul.md 灵魂定义 |
| 🛠️ **技能管理弹窗** | 技能面板精简为管理按钮，点击弹出独立窗口，支持技能开关、新增（名称+描述+guide）、删除自定义技能 |
| 🧩 **动态模板扫描** | 内置模板已导出到 personas/ 目录，一切角色由目录自动发现，无需硬编码 |
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
│ 🧠 TennineClaw               🌓 主题切换    [模型 ▼] [⚙️] │
├─────────────────┬──────────────────────────────────┬──────────────────────┤
│ 左侧面板         │ 中间区域                          │ 右侧面板             │
│ 💬 新建对话      │                                   │ 🤖 模型信息          │
│ 📂 历史对话      │  🧠 对话区域                       │ 🧩 Composer 状态     │
│ ─────────       │                                   │ 📊 Token 用量        │
│ 📁 会话A        │  🧑 用户信息                       │ 📝 详细参数          │
│ 📁 会话B        │  🤖 AI 回复...                    │                      │
│ ─────────       │                                   │                      │
│ 📁 会话C        │                                   │                      │
│ 📁 ...          │                                   │                      │
├─────────────────┴──────────────────────────────────┴──────────────────────┤
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ 工具清单

### 文件搜索

| 命令 | 功能 | 示例 |
|------|------|------|
| `grep` | 递归搜索文件内容 | `grep("def __init__", glob="*.py", context=2)` |
| `replace` | 批量替换，默认预检 | `replace("old", "new", dry_run=True)` |
| `find_files` | 按扩展名搜索文件 | `find_files("*.py", sort_by="size")` |
| `count_lines` | 统计代码行数 | `count_lines(pattern="*.py,*.js")` |
| `diff` | 文件内容对比 | `diff("a.py", "b.py")` |
| `show_file` | 带行号查看文件 | `show_file("main.py", start=50, count=30)` |

### Git

| 命令 | 功能 |
|------|------|
| `git_status` | 查看仓库状态，含分支、远程、ahead/behind |
| `git_log` | 查看提交历史，支持分支/作者过滤 |
| `git_diff` | 查看未暂存的变更 |
| `git_commit_stats` | 统计文件变更和提交数 |

### 系统

| 命令 | 功能 |
|------|------|
| `run_cmd` | 执行系统命令（含安全检测） |
| `read_file` / `write_file` | 文件读写 |
| `list_files` / `create_directory` | 目录管理 |
| `get_system_info` | 系统信息查询 |
| `get_current_time` | 当前时间 |

---

## 🏗️ 架构

```
┌──────────────────────────────────────────────────────────┐
│         Web UI (FastAPI + Static Files)                  │
│   static/index.html + style.css + app.js                │
├──────────────────────────────────────────────────────────┤
│           web_api.py (API 路由层)                        │
├──────────────────────────────────────────────────────────┤
│      main.py / main_stream.py (对话处理)                 │
├──────────────────────────────────────────────────────────┤
│   tools/                                                 │
│   ├── __init__.py    工具注册                            │
│   ├── cmd_exec.py    系统命令执行                         │
│   ├── file_ops.py    文件读写                            │
│   ├── dir_ops.py     目录操作                            │
│   ├── info_ops.py    系统信息                            │
│   ├── search_ops.py  Grep / 替换 / 统计                  │
│   └── git_ops.py     Git 操作                            │
├──────────────────────────────────────────────────────────┤
│   支持层                                                 │
│   ├── context.py         上下文管理与压缩                 │
│   ├── session_manager.py 会话保存/加载/注册              │
│   ├── safety.py          命令安全检测                     │
│   ├── prompts.py         系统提示词模板                   │
│   ├── prompt_optimizer.py 提示词优化                     │
│   ├── token_utils.py     Token 用量工具                  │
│   └── mode_manager.py    模式管理                        │
└──────────────────────────────────────────────────────────┘
```

## 📁 项目结构

```
TennineClaw/
├── __init__.py              # 包初始化 + 版本号
├── config.py                # 配置管理（持久化 + 默认值）
├── main.py                  # 核心对话逻辑
├── main_stream.py           # 流式对话逻辑
├── web_api.py               # FastAPI Web 接口（37 条路由）
│
├── session_manager.py       # 会话持久化 + 全局会话注册
├── context.py               # 上下文压缩（Micro/Auto/Manual）
├── mode_manager.py          # Smart / Plan 模式管理
├── prompt_optimizer.py      # 用户输入提示词优化
├── prompts.py               # 系统提示词模板
├── safety.py                # 系统命令安全检测
├── token_utils.py           # Token 用量与格式化
│
├── requirements.txt         # Python 依赖
├── run.bat / run.ps1        # Windows 启动脚本
│
├── tools/                   # Function Calling 工具集
│   ├── __init__.py          # 工具注册装饰器
│   ├── cmd_exec.py          # 系统命令执行
│   ├── file_ops.py          # 文件读写
│   ├── dir_ops.py           # 目录操作
│   ├── info_ops.py          # 系统信息查询
│   ├── search_ops.py        # Grep / 替换 / 行数统计
│   └── git_ops.py           # Git 状态 / 日志 / 对比
│
└── static/                  # 前端静态资源
    ├── index.html           # 主页面
    ├── js/api.js            # API 调用封装
    ├── js/app.js            # 前端交互逻辑
    └── css/style.css        # 样式（深色/浅色主题）
```

---

## ⚙️ 配置

### 服务器配置

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `GRADIO_PORT` | Web 服务端口 | `7860` |
| `GRADIO_HOST` | 监听地址 | `127.0.0.1` |

### API 配置

API Key、Base URL、模型选择均通过 **Web UI 右上角** 模型设置页面配置，自动持久化到 `user_config.json`，无需手动编辑。

### 指令参考

| 指令 | 说明 |
|------|------|
| `/smart` | 切换到 Smart 模式 |
| `/plan` | 切换到 Plan 模式 |
| `/clear` | 清除对话历史 |
| `/compact` | 手动压缩上下文 |
| `/save [名称]` | 保存当前会话 |
| `/load <文件名>` | 加载历史会话 |
| `/status` | 查看当前状态 |
| `/tools` | 查看可用工具 |
| `/title <新标题>` | 修改会话标题 |
| `/help` | 查看帮助 |

---

## 💡 使用示例

### 代码搜索

```
你：帮我找到 FastAPI 路由定义
→ AI 调用 grep()
→ 返回所有路由定义及对应文件行号
```

### Git 状态

```
你：查看当前仓库状态
→ AI 调用 git_status()
→ 显示分支、暂存区、未跟踪文件
```

### 行数统计

```
你：统计一下这个项目中有多少行代码
→ AI 调用 count_lines()
→ 分类型显示代码行数统计
```

### 批量替换

```
你：把 print 全部改成 logging.info
→ AI 调用 replace()
→ 先预览后确认再执行
```

---

## 🔒 安全

- 危险命令（`rm -rf`、`format`、`dd if=` 等）自动拦截
- API Key 通过 Web UI 设置，仅存储在内存中
- `user_config.json` 和 `sessions/` 目录已加入 `.gitignore`

---

## 📄 许可

MIT License

---

## 📝 更新日志

### v1.1.0（2026年5月22日）

#### 🎭 自定义角色系统
- 新增：personas/ 目录动态扫描，自动发现所有角色
- 新增：自定义角色支持 soul.md 灵魂定义文件
- 新增：内置角色（严谨工程师、创意极客、高效助手）导出到 personas/ 目录
- 新增：默认角色 Tennine（🎀）— 主人的专属 AI 助手精灵
- 优化：角色卡片紧凑水平布局，节省空间
- 修复：角色切换双向可逆，不再卡死

#### 🛠️ 技能管理重构
- 新增：技能管理弹窗（点击「⚙️ 管理技能」弹出独立窗口）
- 新增：技能新增表单（技能名称 + 描述 + Guide）
- 新增：自定义技能可删除，内置技能不可删除
- 新增：默认技能自动加载
- 优化：技能面板精简为仅 Title + 管理按钮

#### 🧩 人格系统改进
- 修复：`list_personality_templates()` 动态扫描 personas/ 目录
- 修复：`get_personality_template()` 正确过滤未知字段（如 learning_priority）
- 修复：`load_profile()` 三次回退查找（profile_id → 扁平文件 → 目录扫描）
- 修复：`apply_personality_template()` 检查 `apply_template()` 返回值
- 修复：后端锁超时从 1s → 10s，避免 423 竞争冲突

#### ⚡ 性能与代码清理
- 优化：前端 `applyRole()` 使用模板缓存，减少网络请求
- 清理：移除 6 个未使用的函数
- 清理：删除备份文件、pycache、过期 plan.md
- 清理：归档旧会话记录

### v1.0.0（2026年5月19日）

**首个正式版本发布**

- **Web UI 全量重构**：从 Gradio 迁移至 **FastAPI + 静态前端**，支持 37+ RESTful 路由
- **流式 SSE 对话**：`/api/chat/stream` 端点，支持实时流式传输 + 中断恢复
- **19 个实用工具**：
  - 文件操作：搜索、替换、读取、写入、删除、对比
  - Git 集成：状态查看、提交历史、差异对比、提交统计
  - 系统操作：命令执行（安全检测）、目录管理、信息查询
  - Conda 管理：环境查看、切换、创建
- **Composer 上下文压缩**：Micro（自动裁剪工具信息）、Auto（Token 达 80% 自动压缩）、Manual（`/compact` 手动触发）
- **会话管理系统**：文件级持久化、全局注册表、分组/搜索/重命名
- **Smart / Plan 双模式**：Plan 模式包含 explore → modify → execute → confirm → reset 工作流
- **Token 监控系统**：实时显示输入/输出/总计用量，会话累计统计
- **状态管理**：流式请求期间状态查询（0.3s 超时）、中断后自动恢复
- **主题支持**：深色/浅色主题切换
- **提示词优化**：使用 LLM 优化用户原始输入，UI 展示优化前后对比
- **模型 API 封装**：支持多模型独立配置（base_url / api_key），持久化到 `user_config.json`

---

**Made with 💙**
