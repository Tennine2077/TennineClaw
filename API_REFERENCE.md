# TennineClaw 函数参考

> 版本：11.0.0 | 自动生成于 2026-05-20

---

## 目录

- [核心模块](#核心模块)
  - [config.py](#configpy)
  - [main.py](#mainpy)
  - [main_stream.py](#main_streampy)
  - [web_api.py](#web_apipy)
- [支持模块](#支持模块)
  - [session_manager.py](#session_managerpy)
  - [context.py](#contextpy)
  - [mode_manager.py](#mode_managerpy)
  - [prompts.py](#promptspy)
  - [prompt_optimizer.py](#prompt_optimizerpy)
  - [safety.py](#safetypy)
  - [token_utils.py](#token_utilspy)
- [工具模块](#工具模块)
  - [tools/\_\_init\_\_.py](#tools__init__py)
  - [tools/cmd_exec.py](#toolscmd_execpy)
  - [tools/file_ops.py](#toolsfile_ospy)
  - [tools/dir_ops.py](#toolsdir_ospy)
  - [tools/info_ops.py](#toolsinfo_ospy)
  - [tools/search_ops.py](#toolssearch_ospy)
  - [tools/git_ops.py](#toolsgit_ospy)

---

## 核心模块

### config.py

全局配置管理。负责从 `user_config.json` 和环境变量加载配置，提供持久化写入接口。

| 函数 | 说明 |
|------|------|
| `_load_user_config()` | 从 `user_config.json` 加载持久化配置 |
| `_save_user_config(config)` | 合并写入配置到 `user_config.json` |
| `_get_user_config()` | 懒加载获取用户配置（带缓存） |
| `_invalidate_config_cache()` | 使配置缓存失效，下次自动重载 |
| `get_model_api_overrides()` | 获取每模型 API 覆盖配置 |
| `save_model_api_override(code, base_url, api_key)` | 保存单个模型的 API 覆盖 |
| `apply_model_api_overrides(models)` | 将 API 覆盖合并到模型列表 |
| `get_config(key, env_key, default)` | 按优先级获取配置：user_config > 环境变量 > 默认值 |

### main.py

核心对话引擎。管理会话状态、工具调度、Python/Conda 环境、模型切换。

| 函数 | 说明 |
|------|------|
| `__init__(session_id, mode)` | 初始化会话，创建 OpenAI 客户端，设置初始状态 |
| `reset()` | 重置会话，清除上下文和 Token 统计 |
| `get_mode_name()` / `get_mode()` | 获取当前模式（Smart / Plan） |
| `get_composer_status()` | 获取 Composer 状态信息 |
| `switch_mode(mode)` | 切换模式（Smart ↔ Plan） |
| `_auto_set_title(user_input)` | 首次消息自动截取标题 |
| `set_title(title)` / `get_title()` | 设置/获取会话标题 |
| `save(path)` | 保存会话到文件 |
| `load(path)` | 从文件恢复会话 |
| `compact_context()` | 手动压缩上下文 |
| `get_available_models()` | 获取可用模型列表 |
| `switch_model(code)` | 切换当前模型 |
| `add_custom_model(name, code, base_url, api_key)` | 添加自定义模型 |
| `delete_custom_model(code)` | 删除自定义模型 |
| `update_model_api(code, base_url, api_key)` | 更新模型 API 覆盖 |
| `reinit_client_with_overrides(base_url, api_key)` | 用指定参数重连 OpenAI 客户端 |
| `reinit_client()` | 使用默认配置重连 OpenAI 客户端 |
| `set_python_env(path)` | 设置 Python 环境路径 |
| `get_python_env_info()` | 获取 Python 环境信息 |
| `list_conda_envs()` | 列出所有 conda 环境 |
| `switch_conda_env(env_name)` | 切换 conda 环境 |
| `create_conda_env(env_name, python_version)` | 创建 conda 环境 |
| `set_status_update_callback(callback)` | 注册状态更新回调 |
| `process_message(user_input)` | 同步处理用户消息 |

### main_stream.py

流式对话引擎。支持 SSE 流式输出、推理摘要、工具调用链。

| 函数 | 说明 |
|------|------|
| `_split_into_paragraphs(text)` | 将文本分割为段落块用于流式输出 |
| `_get_reasoning_summary(content)` | 从推理内容提取摘要 |
| `process_message_stream(user_input, session)` | 流式处理用户消息（生成器） |

### web_api.py

FastAPI Web 服务。37 条 REST API 路由，处理前端请求。

| 路由 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 返回主页面 |
| `/api/chat` | POST | 发送消息（非流式） |
| `/api/chat/stream` | POST | 发送消息（SSE 流式） |
| `/api/session/create` | POST | 创建新会话 |
| `/api/sessions/list` | GET | 列出已保存会话文件 |
| `/api/session/active` | GET | 获取当前活跃会话 |
| `/api/session/activate` | POST | 激活指定会话 |
| `/api/session/interrupt` | POST | 打断流式回复 |
| `/api/session/delete` | DELETE | 从注册表删除会话 |
| `/api/session/switch/smart` | POST | 切换到 Smart 模式 |
| `/api/session/switch/plan` | POST | 切换到 Plan 模式 |
| `/api/session/clear` | POST | 清除上下文 |
| `/api/session/compact` | POST | 压缩上下文 |
| `/api/help` | GET | 获取帮助文本 |
| `/api/status` | GET | 获取完整状态（Token 面板数据） |
| `/api/status/realtime` | GET | 实时状态（简洁版） |
| `/api/session/title` | GET | 获取会话标题 |
| `/api/session/save` | POST | 保存会话 |
| `/api/chat/messages` | GET | 获取会话消息列表 |
| `/api/models` | GET | 获取模型列表 |
| `/api/models/switch` | POST | 切换模型 |
| `/api/models/add` | POST | 添加自定义模型 |
| `/api/models/delete` | POST | 删除自定义模型 |
| `/api/models/{code}/config` | PUT | 更新模型 API 配置 |
| `/api/config` | GET/PUT | 获取/更新环境配置 |
| `/api/session/load` | POST | 加载历史会话 |
| `/api/session/delete-file` | DELETE | 删除会话文件 |
| `/api/env/set` | POST | 设置 Python 环境 |
| `/api/env/get` | GET | 获取 Python 环境信息 |
| `/api/env/current` | GET | 获取当前环境状态 |
| `/api/conda/list` | GET | 列出 conda 环境 |
| `/api/conda/switch` | POST | 切换 conda 环境 |
| `/api/conda/create` | POST | 创建 conda 环境 |
| `/api/plan/ready` | GET | 检查 Plan 就绪状态 |
| `/api/plan/action` | POST | Plan 菜单操作 |

内部辅助函数：

| 函数 | 说明 |
|------|------|
| `_get_session(session_id)` | 获取指定 session，默认 active |
| `_get_session_lock(session_id)` | 获取指定 session 的锁 |
| `_get_session_and_lock()` | 获取 session + 锁（元组） |
| `_build_status_snapshot(session_id)` | 构建状态快照字典 |
| `_update_status_cache()` | 更新状态缓存 |
| `_get_status_with_cache(timeout)` | 带缓存的状态读取 |
| `_try_lock_action(session_id, action, timeout, fallback)` | 锁保护的操作执行 |
| `generate()` | SSE 事件生成器 |

---

## 支持模块

### session_manager.py

会话持久化与多会话注册表。管理会话文件的保存、加载、列表和注册表操作。

| 函数 | 说明 |
|------|------|
| `_estimate_msgs_tokens(msgs)` | 估算消息列表的 Token 数 |
| `ensure_session_dir(save_dir)` | 确保会话目录存在 |
| `save_session(session, path, save_dir)` | 序列化会话为 JSON 文件 |
| `load_session(path)` | 从 JSON 文件加载会话数据 |
| `restore_session(session, path)` | 从文件恢复会话状态到 session 对象 |
| `list_sessions()` | 列出所有已保存会话 |
| `delete_session(path)` | 删除会话文件 |
| `auto_save(session)` | 自动保存为独立文件 |
| `get_session_display_list()` | 获取格式化的会话列表 |
| `get_session_title_from_path(path)` | 从文件路径读取标题 |
| `SessionRegistry.create()` | 创建新会话，返回 session_id |
| `SessionRegistry.get(session_id)` | 获取 session 实例 |
| `SessionRegistry.get_lock(session_id)` | 获取 session 锁 |
| `SessionRegistry.get_or_create(session_id)` | 获取或创建会话 |
| `SessionRegistry.remove(session_id)` | 从注册表移除会话 |
| `SessionRegistry.set_active(session_id)` | 设置活跃会话 |
| `SessionRegistry.get_active()` | 获取活跃会话 ID |
| `SessionRegistry.load_from_path(path)` | 从文件加载到注册表 |
| `SessionRegistry.all_sessions()` | 获取所有会话 |

### context.py

三级上下文压缩系统。防止 Token 溢出。

| 函数 | 说明 |
|------|------|
| `micro_composer(session)` | 微缩压缩：每轮清理旧 tool 调用 |
| `auto_composer(session)` | 自动压缩：Token 超阈值时触发语义摘要 |
| `manual_composer(session)` | 手动压缩：用户触发的全量压缩 |
| `_split_into_rounds(msgs)` | 将消息按轮次分组 |
| `_build_history_text(msgs, preserve_last)` | 构建待压缩的历史文本 |
| `_llm_compress(text, max_chars)` | 调用 LLM 做语义摘要 |
| `compact_messages(session)` | 消息压缩包装 |

### mode_manager.py

Smart / Plan 双模式管理。

| 函数 | 说明 |
|------|------|
| `__init__(mode)` | 初始化模式管理器 |
| `get_mode()` / `set_mode(mode)` | 获取/设置模式 |
| `get_mode_name()` | 获取模式名称 |
| `is_smart_mode()` / `is_plan_mode()` | 模式判断 |
| `get_plan_phase()` / `set_plan_phase(phase)` | Plan 阶段管理 |
| `is_plan_menu_shown()` / `set_plan_menu_shown(val)` | Plan 菜单状态 |
| `is_plan_ready()` | 判断 Plan 是否就绪 |
| `should_show_plan_menu()` | 是否显示 Plan 菜单 |
| `get_mode_description()` | 获取模式说明 |

### prompts.py

系统提示词模板构建。

| 函数 | 说明 |
|------|------|
| `build_system_prompt(mode)` | 构建系统提示词（包含动态信息） |

### safety.py

系统命令安全检测（黑名单模式）。

| 函数 | 说明 |
|------|------|
| `check_command_safety(command)` | 检测命令安全性 |

### token_utils.py

Token 统计与格式化。

| 函数 | 说明 |
|------|------|
| `show_token_usage(usage)` | 显示 Token 消耗信息 |
| `get_token_stats_text(usage)` | 获取格式化 Token 统计文本 |

---

## 工具模块（Function Calling）

### tools/\_\_init\_\_.py

工具注册与调度。统一入口，管理 19 个工具。

| 函数 | 说明 |
|------|------|
| `dispatch_tool(name, args)` | 统一工具调度入口 |
| `dispatch_tool_from_json(json_str)` | 从 JSON 字符串调度工具 |

### tools/cmd_exec.py

系统命令执行。

| 函数 | 说明 |
|------|------|
| `tool_run_cmd(command, workdir)` | 执行系统命令（带安全检测） |
| `tool_run_cmd_compat(kwargs)` | dict 参数版本 |

### tools/file_ops.py

文件读写操作。

| 函数 | 说明 |
|------|------|
| `tool_read_file(path)` | 读取文件完整内容 |
| `tool_write_file(path, content)` | 写入/覆盖文件 |
| `tool_delete_file(path)` | 删除文件或空目录 |
| `tool_read_file_compat(kwargs)` | dict 参数版本 |
| `tool_write_file_compat(kwargs)` | dict 参数版本 |
| `tool_delete_file_compat(kwargs)` | dict 参数版本 |

### tools/dir_ops.py

目录操作。

| 函数 | 说明 |
|------|------|
| `tool_list_files(path, pattern, sort_by)` | 列出目录内容 |
| `tool_search_files(pattern, root_dir)` | 按名称搜索文件 |
| `tool_create_directory(path)` | 创建目录 |

### tools/info_ops.py

系统信息查询。

| 函数 | 说明 |
|------|------|
| `tool_get_system_info()` | 获取系统信息 |
| `tool_get_current_time()` | 获取当前时间 |

### tools/search_ops.py

搜索、替换、统计、文件查找、差异对比。

| 函数 | 说明 |
|------|------|
| `tool_grep(pattern, glob, root_dir, context, include_hidden)` | 正则搜索文件内容 |
| `tool_replace(search_text, replace_text, glob, dry_run, root_dir)` | 搜索替换 |
| `tool_count_lines(pattern, root_dir, exclude)` | 统计代码行数 |
| `tool_find_files(pattern, root_dir, sort_by, max_results)` | 按名称查找文件 |
| `tool_diff(file_a, file_b)` | 文件差异对比 |

### tools/git_ops.py

Git 集成。

| 函数 | 说明 |
|------|------|
| `tool_git_status(repo_path)` | Git 仓库状态 |
| `tool_git_log(branch, author, max_count, repo_path)` | 提交历史 |
| `tool_git_diff(repo_path)` | 工作区变更差异 |
| `tool_git_commit_stats(author, months, repo_path)` | 贡献统计 |
| `tool_show_file(path, start, count)` | 带行号查看文件 |

---

## 前端（JavaScript）

### static/js/app.js

前端交互逻辑。

| 函数 | 说明 |
|------|------|
| `init()` | 页面初始化，绑定事件，启动轮询 |
| `switchTheme(theme)` | 切换深色/浅色主题 |
| `newChat()` | 创建新会话 |
| `loadSessionByPath(path)` | 加载历史会话 |
| `sendMessage()` | 发送消息 |
| `renderMessage(msg, msgIndex, isOptimized)` | 渲染单条消息 |
| `renderMessages(messages)` | 渲染消息列表 |
| `renderSessionList()` | 渲染侧栏会话列表 |
| `updateFullStatus()` | 更新右侧面板状态 |
| `updateTokenStatus(input, output, total, max)` | 更新 Token 面板 |
| `showToast(text, type)` | 显示 Toast 通知 |
| `startSmartPolling()` | 启动智能轮询 |

### static/js/api.js

API 调用封装。

| 函数 | 说明 |
|------|------|
| `sendMessage(input, sessionId)` | 发送消息（流式，返 EventSource） |
| `createSession()` | 创建新会话 |
| `loadSession(path)` | 加载会话 |
| `getSessionMessages(sessionId)` | 获取消息列表 |
| `saveSession()` | 保存当前会话 |
| `deleteSession(path)` | 删除会话文件 |
| `getStatus()` | 获取状态 |
| `getModels()` | 获取模型列表 |
| `switchModel(code)` | 切换模型 |
| `updateModelConfig(code, base_url, api_key)` | 更新模型 API |
| `checkPlanReady()` | 检查 Plan 就绪 |
| `planAction(action)` | 执行 Plan 操作 |
| `fetchJson(url, options)` | JSON 请求封装 |
| `fetchJsonWithTimeout(url, timeout)` | 带超时的 JSON 请求 |

---

## 数据结构

### AgentSession (`main.py`)

| 属性 | 类型 | 说明 |
|------|------|------|
| `session_id` | str | 会话唯一 ID |
| `client` | OpenAI | OpenAI 客户端实例 |
| `msgs` | list | 消息列表（含 system prompt） |
| `current_mode` | int | 当前模式（Smart / Plan） |
| `current_model` | str | 当前模型 code |
| `current_tokens` | int | 当前输入 Token 数 |
| `completion_tokens` | int | 累计输出 Token 数 |
| `session_completion_tokens` | int | 会话级输出 Token 累计 |
| `total_tokens` | int | 总 Token 数 |
| `session_title` | str | 会话标题 |
| `python_env` | str | Python 路径 |
| `conda_env` | str | Conda 环境名 |

### StatusResponse (`web_api.py`)

| 字段 | 类型 | 说明 |
|------|------|------|
| `mode` | str | 当前模式名称 |
| `message_count` | int | 消息数 |
| `current_tokens` | int | 输入 Token |
| `completion_tokens` | int | 累计输出 Token |
| `total_tokens` | int | 总 Token |
| `session_completion_tokens` | int | 会话级输出 Token |
| `usage_percent` | float | 上下文占用率 |
| `session_title` | str | 会话标题 |
| `composer_info` | str | Composer 统计文本 |
| `notification` | str | 通知信息 |
| `version` | str | 版本号 |

### Session JSON 文件

| 字段 | 说明 |
|------|------|
| `version` | 保存版本 |
| `timestamp` | 保存时间戳 |
| `session_title` | 会话标题 |
| `mode` / `mode_name` | 会话模式 |
| `msgs` | 消息列表 |
| `current_tokens` | 保存时的输入 Token |
| `completion_tokens` | 累计输出 Token |
| `session_completion_tokens` | 会话输出 Token 累计 |
| `total_tokens` | 总 Token |
| `last_token_stats` | Token 统计文本 |
| `message_count` | 消息数 |

---

> 本文档覆盖 TennineClaw 项目全部模块和主要函数。


