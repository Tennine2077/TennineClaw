# TennineClaw Function Reference

> Version: 1.0.0 | Auto-generated on May 19, 2026

[🇨🇳 **中文**](API_REFERENCE.md) | [🌏 **English**](API_REFERENCE.en.md)

---

## Table of Contents

- [Core Modules](#core-modules)
  - [config.py](#configpy)
  - [main.py](#mainpy)
  - [main_stream.py](#main_streampy)
  - [web_api.py](#web_apipy)
- [Support Modules](#support-modules)
  - [session_manager.py](#session_managerpy)
  - [context.py](#contextpy)
  - [mode_manager.py](#mode_managerpy)
  - [prompts.py](#promptspy)
  - [prompt_optimizer.py](#prompt_optimizerpy)
  - [safety.py](#safetypy)
  - [token_utils.py](#token_utilspy)
- [Tool Modules](#tool-modules)
  - [tools/\_\_init\_\_.py](#tools__init__py)
  - [tools/cmd_exec.py](#toolscmd_execpy)
  - [tools/file_ops.py](#toolsfile_ospy)
  - [tools/dir_ops.py](#toolsdir_ospy)
  - [tools/info_ops.py](#toolsinfo_ospy)
  - [tools/search_ops.py](#toolssearch_ospy)
  - [tools/git_ops.py](#toolsgit_ospy)

---

## Core Modules

### config.py

Global configuration management. Responsible for loading configuration from `user_config.json` and environment variables, providing a persistent write interface.

| Function | Description |
|----------|-------------|
| `_load_user_config()` | Load persistent configuration from `user_config.json` |
| `_save_user_config(config)` | Merge and write configuration to `user_config.json` |
| `_get_user_config()` | Lazy-load user configuration (with caching) |
| `_invalidate_config_cache()` | Invalidate config cache, force reload on next access |
| `get_model_api_overrides()` | Get per-model API override configurations |
| `save_model_api_override(code, base_url, api_key)` | Save API override for a single model |
| `apply_model_api_overrides(models)` | Merge API overrides into the model list |
| `get_config(key, env_key, default)` | Get config by priority: user_config > env variable > default |

### main.py

Core conversation engine. Manages session state, tool scheduling, Python/Conda environments, and model switching.

| Function | Description |
|----------|-------------|
| `__init__(session_id, mode)` | Initialize session, create OpenAI client, set initial state |
| `reset()` | Reset session, clear context and token statistics |
| `get_mode_name()` / `get_mode()` | Get current mode (Smart / Plan) |
| `get_composer_status()` | Get Composer status information |
| `switch_mode(mode)` | Switch mode (Smart ↔ Plan) |
| `_auto_set_title(user_input)` | Auto-extract title from first message |
| `set_title(title)` / `get_title()` | Set/Get session title |
| `save(path)` | Save session to file |
| `load(path)` | Restore session from file |
| `compact_context()` | Manually compress context |
| `get_available_models()` | Get list of available models |
| `switch_model(code)` | Switch current model |
| `add_custom_model(name, code, base_url, api_key)` | Add a custom model |
| `remove_custom_model(code)` | Remove a custom model |

### main_stream.py

Streaming conversation processing. Handles SSE streaming, tool call execution, and context management.

| Function | Description |
|----------|-------------|
| `stream_chat(messages, ...)` | Main streaming chat handler, returns SSE events |
| `_process_tool_calls(tool_calls)` | Process tool call requests from the model |
| `_build_system_prompt()` | Build system prompt including tools, mode, personality |
| `_update_context(response)` | Update context with new response content |
| `_check_token_limit()` | Check if token limit is approaching, trigger compression if needed |

### web_api.py

FastAPI web service layer. Provides RESTful API endpoints and static file serving.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat/stream` | POST | Streaming chat (SSE) |
| `/api/sessions` | GET | List all sessions |
| `/api/sessions` | POST | Create new session |
| `/api/sessions/{id}` | GET | Get session details |
| `/api/sessions/{id}` | DELETE | Delete session |
| `/api/sessions/{id}/save` | POST | Save session |
| `/api/models` | GET | List available models |
| `/api/models/switch` | POST | Switch current model |
| `/api/config` | GET | Get configuration |
| `/api/config` | POST | Update configuration |
| `/api/status` | GET | Get system status |
| `/api/tools` | GET | List available tools |
| ... and more (37+ routes total) | | |

---

## Support Modules

### session_manager.py

Session persistence and management. Handles saving, loading, searching, and registration of chat sessions.

| Function | Description |
|----------|-------------|
| `save_session(session_id, data)` | Save session data to file |
| `load_session(session_id)` | Load session from file |
| `delete_session(session_id)` | Delete a session |
| `list_sessions(group=None)` | List all sessions, optionally filtered by group |
| `search_sessions(keyword)` | Search sessions by keyword |
| `rename_session(session_id, new_name)` | Rename a session |
| `get_session_path(session_id)` | Get the file path for a session |
| `get_global_registry()` | Get the global session registry |

### context.py

Context management and compression (Composer system). Provides three levels of compression.

| Function | Description |
|----------|-------------|
| `get_composer_status()` | Get current Composer status (level, token counts) |
| `micro_compress(context)` | Micro compression: trim tool call details |
| `auto_compress(context)` | Auto compression: triggered at 80% token threshold |
| `manual_compress(context)` | Manual compression: triggered by `/compact` |
| `_summarize_messages(messages)` | Summarize a batch of messages |
| `_get_token_count(text)` | Calculate token count for text |

### mode_manager.py

Mode management for Smart/Plan dual-mode architecture.

| Function | Description |
|----------|-------------|
| `switch_mode(mode)` | Switch between Smart and Plan modes |
| `get_mode()` | Get current mode |
| `get_mode_instructions()` | Get mode-specific system instructions |
| `PlanMode` class | Plan mode workflow management |
| `SmartMode` class | Smart mode direct execution |

### prompts.py

System prompt construction. Builds different system prompts based on mode, tools, and personality.

| Function | Description |
|----------|-------------|
| `build_system_prompt(mode, tools, personality)` | Build complete system prompt |
| `get_base_prompt()` | Get base system prompt |
| `get_tool_descriptions(tools)` | Generate tool descriptions for the model |
| `get_mode_prompt(mode)` | Get mode-specific prompt additions |
| `get_personality_prompt(personality)` | Get personality prompt if available |

### prompt_optimizer.py

AI-powered prompt optimization. Automatically improves user input for better responses.

| Function | Description |
|----------|-------------|
| `optimize_prompt(user_input, context)` | Optimize user input using LLM |
| `get_optimization_result()` | Get the optimization result with before/after comparison |
| `is_optimization_enabled()` | Check if optimization is enabled |

### safety.py

System command safety detection. Prevents execution of dangerous commands.

| Function | Description |
|----------|-------------|
| `check_command(cmd)` | Check if a command is safe to execute |
| `is_dangerous(cmd)` | Check against dangerous command patterns |
| `sanitize_command(cmd)` | Sanitize and normalize command input |
| `get_dangerous_patterns()` | Get list of blocked command patterns |

### token_utils.py

Token counting and formatting utilities.

| Function | Description |
|----------|-------------|
| `count_tokens(text)` | Count tokens in text |
| `format_token_count(count)` | Format token count for display (e.g., "1.2K") |
| `calculate_token_ratio(used, total)` | Calculate token usage ratio |
| `get_token_limit()` | Get current model's token limit |

---

## Tool Modules

### tools/__init__.py

Tool registration and dispatch system. Uses a decorator pattern for registering tools.

| Function | Description |
|----------|-------------|
| `register_tool(name, description)` | Decorator to register a function as a tool |
| `get_all_tools()` | Get all registered tools |
| `get_tool_schemas()` | Get tool schemas in OpenAI function-calling format |
| `execute_tool(name, params)` | Execute a tool by name with parameters |
| `get_tool(name)` | Get a specific tool by name |

### tools/cmd_exec.py

System command execution with safety checks and timeout control.

| Function | Description |
|----------|-------------|
| `run_cmd(cmd)` | Execute a system command with safety checks |
| `_check_dangerous(cmd)` | Check for dangerous commands |
| `_execute_with_timeout(cmd, timeout)` | Execute command with timeout control |

### tools/file_ops.py

File read/write/delete operations.

| Function | Description |
|----------|-------------|
| `read_file(path)` | Read file content |
| `write_file(path, content)` | Write content to file |
| `delete_file(path)` | Delete file or empty directory |
| `show_file(path, start, count)` | View file with line numbers and pagination |
| `diff(file1, file2)` | Compare two files |

### tools/dir_ops.py

Directory operations.

| Function | Description |
|----------|-------------|
| `list_files(directory, pattern, show_hidden)` | List directory contents with optional filter |
| `create_directory(path)` | Create directory (including parent directories) |
| `search_files(name, directory)` | Search for files by name |

### tools/info_ops.py

System information queries.

| Function | Description |
|----------|-------------|
| `get_system_info()` | Get system information (OS, CPU, memory, etc.) |
| `get_current_time()` | Get current date and time |

### tools/search_ops.py

Content search, replace, and code statistics.

| Function | Description |
|----------|-------------|
| `grep(pattern, directory, glob, context_lines)` | Recursive file content search with regex |
| `replace(pattern, replacement, glob, dry_run)` | Search and replace file content |
| `count_lines(directory, pattern)` | Count lines of code, grouped by file type |
| `find_files(pattern, directory, sort_by)` | Find files by name pattern |

### tools/git_ops.py

Git integration tools.

| Function | Description |
|----------|-------------|
| `git_status(directory)` | View repository status (branch, remote, changes) |
| `git_log(directory, count, branch, author)` | View commit history |
| `git_diff(directory, staged, path)` | View file differences |
| `git_commit_stats(directory, days, top_n)` | View commit statistics |

---

**Made with 💙**
