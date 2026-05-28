# ============================================================
# TennineClaw - 工具包
# ============================================================
# 提供文件操作、命令执行、信息查询等工具的统一注册与入口
# ============================================================

import json
import threading
import traceback
from typing import Any, Dict, Optional

from .cmd_exec import tool_run_cmd
from .file_ops import tool_read_file, tool_write_file, tool_delete_file, tool_edit_file, tool_append_file, tool_rename_file, tool_copy_file, tool_file_info
from .dir_ops import tool_list_files, tool_search_files, tool_create_directory
from .info_ops import tool_get_system_info, tool_get_current_time
from .search_ops import tool_grep, tool_replace, tool_count_lines, tool_find_files, tool_diff
from .git_ops import tool_git_status, tool_git_log, tool_git_diff, tool_git_commit_stats, tool_show_file

# ============================================================
# 自定义技能工具 — 通用动态发现与加载
# 自动扫描 skills_custom/ 目录下所有技能的 skill.json，
# 读取 tools 定义并动态加载实现函数，无需修改源码
# ============================================================

import os as _os
import importlib.util as _import_util

_PROJECT_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), _os.pardir, _os.pardir))
_CUSTOM_SKILLS_DIR = _os.path.join(_PROJECT_ROOT, "skills_custom")


def _discover_and_load_custom_tools():
    """扫描 skills_custom/，自动发现并加载所有自定义技能的工具"""
    import json as _json

    if not _os.path.isdir(_CUSTOM_SKILLS_DIR):
        return 0

    added = 0
    for skill_name in sorted(_os.listdir(_CUSTOM_SKILLS_DIR)):
        skill_dir = _os.path.join(_CUSTOM_SKILLS_DIR, skill_name)
        skill_json_path = _os.path.join(skill_dir, "skill.json")
        if not _os.path.isfile(skill_json_path):
            continue

        try:
            with open(skill_json_path, "r", encoding="utf-8") as _f:
                _meta = _json.load(_f)

            _tools_list = _meta.get("tools", [])
            if not _tools_list:
                continue

            for _tool_def in _tools_list:
                _name = _tool_def.get("name", "")
                _mod_file = _tool_def.get("module", "")
                _func_name = _tool_def.get("function", "")
                if not _name:
                    continue

                # 1) 动态加载工具函数并挂载到当前模块
                if _mod_file and _func_name:
                    _mod_path = _os.path.join(skill_dir, _mod_file)
                    if _os.path.isfile(_mod_path):
                        try:
                            _spec = _import_util.spec_from_file_location(
                                "custom_" + _name, _mod_path
                            )
                            _mod = _import_util.module_from_spec(_spec)
                            _spec.loader.exec_module(_mod)
                            globals()[_func_name] = getattr(_mod, _func_name)
                        except Exception:
                            def _stub(*a, **kw):
                                return _json.dumps({
                                    "success": False,
                                    "error": "技能 %s 工具 %s 加载失败" % (skill_name, _name)
                                }, ensure_ascii=False)
                            globals()[_func_name] = _stub

                # 2) 构建 Function Calling Schema 并注册到 TOOLS
                TOOLS.append({
                    "type": "function",
                    "function": {
                        "name": _name,
                        "description": _tool_def.get("description", ""),
                        "parameters": _tool_def.get("parameters", {
                            "type": "object",
                            "properties": {}
                        })
                    }
                })
                added += 1

        except Exception:
            continue

    return added


# 模块加载时自动执行发现
_discover_and_load_custom_tools()

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "run_cmd",
            "description": "执行系统命令（带安全检测 + 高危确认）。高危命令需用户确认后设置 confirm=True 放行",
            "parameters": {
                "type": "object",
                "properties": {
                    "cmd": {
                        "type": "string",
                        "description": "要执行的命令"
                    },
                    "confirm": {
                        "type": "boolean",
                        "description": "是否确认高危操作（设为 true 表示用户已确认风险，高危命令将放行）"
                    }
                },
                "required": [
                    "cmd"
                ]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "读取文件内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "文件路径"
                    }
                },
                "required": [
                    "path"
                ]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "写入文件内容（自动创建父目录）",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "文件路径"
                    },
                    "content": {
                        "type": "string",
                        "description": "文件内容"
                    }
                },
                "required": [
                    "path",
                    "content"
                ]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "列出目录内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "目录路径"
                    },
                    "show_hidden": {
                        "type": "boolean",
                        "description": "是否显示隐藏文件"
                    },
                    "pattern": {
                        "type": "string",
                        "description": "文件通配符"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": "搜索文件",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "文件名"
                    },
                    "directory": {
                        "type": "string",
                        "description": "搜索目录"
                    },
                    "max_results": {
                        "type": "number",
                        "description": "最大结果数"
                    }
                },
                "required": [
                    "name"
                ]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_system_info",
            "description": "获取系统信息",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "获取当前时间",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_directory",
            "description": "创建目录",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "目录路径"
                    }
                },
                "required": [
                    "path"
                ]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_file",
            "description": "删除文件或空目录（系统路径保护，需 force=True 强制删除）",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "文件/目录路径"
                    },
                    "force": {
                        "type": "boolean",
                        "description": "是否强制删除（跳过系统路径保护检查，设为 true 可删除系统路径下的内容）"
                    }
                },
                "required": [
                    "path"
                ]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "grep",
            "description": "在文件中搜索文本内容（支持正则，类似 grep -r）",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "搜索模式（支持正则表达式）"
                    },
                    "directory": {
                        "type": "string",
                        "description": "搜索目录"
                    },
                    "glob": {
                        "type": "string",
                        "description": "文件通配符，如 *.py,*.js,*.{py,js}"
                    },
                    "max_results": {
                        "type": "number",
                        "description": "最大匹配结果数"
                    },
                    "ignore_case": {
                        "type": "boolean",
                        "description": "是否忽略大小写"
                    },
                    "context_lines": {
                        "type": "number",
                        "description": "匹配行前后显示的行数"
                    }
                },
                "required": [
                    "pattern"
                ]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "replace",
            "description": "搜索并替换文件内容（类似 sed -i），默认预览模式",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "搜索模式（支持正则）"
                    },
                    "replacement": {
                        "type": "string",
                        "description": "替换文本"
                    },
                    "directory": {
                        "type": "string",
                        "description": "搜索目录"
                    },
                    "glob": {
                        "type": "string",
                        "description": "文件通配符，如 *.py,*.txt"
                    },
                    "max_files": {
                        "type": "number",
                        "description": "最多处理的文件数"
                    },
                    "dry_run": {
                        "type": "boolean",
                        "description": "True=预览，False=执行替换"
                    }
                },
                "required": [
                    "pattern",
                    "replacement"
                ]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_files",
            "description": "按名称模式/扩展名查找文件（类似 find + find 命令）",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "文件名模式，如 *.py, *test*, *.{tsx,jsx}"
                    },
                    "directory": {
                        "type": "string",
                        "description": "搜索目录"
                    },
                    "sort_by": {
                        "type": "string",
                        "description": "排序方式 name|time|size"
                    },
                    "max_results": {
                        "type": "number",
                        "description": "最大结果数"
                    }
                },
                "required": [
                    "pattern"
                ]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "count_lines",
            "description": "统计项目代码行数",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "项目目录"
                    },
                    "pattern": {
                        "type": "string",
                        "description": "文件通配符，如 *.py,*.js,*.ts"
                    },
                    "exclude_pattern": {
                        "type": "string",
                        "description": "排除文件名模式"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "diff",
            "description": "比较两个文件的差异",
            "parameters": {
                "type": "object",
                "properties": {
                    "file1": {
                        "type": "string",
                        "description": "第一个文件路径"
                    },
                    "file2": {
                        "type": "string",
                        "description": "第二个文件路径"
                    },
                    "context_lines": {
                        "type": "number",
                        "description": "上下文行数"
                    }
                },
                "required": [
                    "file1",
                    "file2"
                ]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "git_status",
            "description": "查看 Git 仓库状态（分支、变更、冲突等）",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "仓库目录"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "git_log",
            "description": "查看 Git 提交历史",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "仓库目录"
                    },
                    "count": {
                        "type": "number",
                        "description": "显示的提交数"
                    },
                    "branch": {
                        "type": "string",
                        "description": "分支名"
                    },
                    "author": {
                        "type": "string",
                        "description": "作者过滤"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "git_diff",
            "description": "查看 Git 工作区变更差异",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "仓库目录"
                    },
                    "staged": {
                        "type": "boolean",
                        "description": "是否查看暂存区差异"
                    },
                    "path": {
                        "type": "string",
                        "description": "指定文件路径"
                    },
                    "max_lines": {
                        "type": "number",
                        "description": "最大显示行数"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "git_commit_stats",
            "description": "统计 Git 提交贡献",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "仓库目录"
                    },
                    "days": {
                        "type": "number",
                        "description": "统计最近 N 天"
                    },
                    "top_n": {
                        "type": "number",
                        "description": "显示前 N 名贡献者"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "show_file",
            "description": "显示文件内容（带行号，支持分页）",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "文件路径"
                    },
                    "start_line": {
                        "type": "number",
                        "description": "起始行号"
                    },
                    "line_count": {
                        "type": "number",
                        "description": "显示行数"
                    }
                },
                "required": [
                    "path"
                ]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "load_skill_detail",
            "description": "获取指定技能的完整操作指南、使用策略和最佳实践。当你需要使用某个技能时，调用此函数获取该技能的详细说明",
            "parameters": {
                "type": "object",
                "properties": {
                    "skill_name": {
                        "type": "string",
                        "description": "技能名称，例如'文件搜索大师'"
                    }
                },
                "required": [
                    "skill_name"
                ]
            }
        }
    }
]

# ============================================================
# load_skill_detail - 技能详情惰性加载
# ============================================================

def tool_load_skill_detail(skill_name: str) -> str:
    try:
        from ..skill_models import get_skill_detail
        detail = get_skill_detail(skill_name)
        if detail:
            return detail
        from ..skill_models import load_global_skill_registry
        registry = load_global_skill_registry()
        for sk_id, sk in registry.items():
            if sk.get("name") == skill_name:
                return sk.get("detail_content", "") or ("技能 " + skill_name + " 暂无详细说明")
        return "未找到技能 " + skill_name + "，可用技能列表可通过 get_registry_skills_list 查看"
    except Exception as e:
        return "加载技能详情时出错: " + str(e)

TOOL_FUNCS: Dict[str, Any] = {
    "run_cmd": tool_run_cmd,
    "read_file": tool_read_file,
    "write_file": tool_write_file,
    "list_files": tool_list_files,
    "search_files": tool_search_files,
    "get_system_info": tool_get_system_info,
    "get_current_time": tool_get_current_time,
    "create_directory": tool_create_directory,
    "delete_file": tool_delete_file,

    # 搜索与替换
    "grep": tool_grep,
    "replace": tool_replace,
    "find_files": tool_find_files,
    "count_lines": tool_count_lines,
    "diff": tool_diff,

    # Git 操作
    "git_status": tool_git_status,
    "git_log": tool_git_log,
    "git_diff": tool_git_diff,
    "git_commit_stats": tool_git_commit_stats,
    "show_file": tool_show_file,
    "load_skill_detail": tool_load_skill_detail,
}


# ============================================================
# 自定义技能工具 -- 通用动态发现与注册
# 自动扫描 skills_custom/ 目录，从 skill.json 读取 tools 定义，
# 动态加载实现函数并注册到 TOOLS 和 TOOL_FUNCS
# 新增自定义技能无需修改本文件！
# ============================================================


def _register_custom_skill_tools():
    import os as _os
    import importlib.util as _import_util
    import json as _json

    project_root = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), _os.pardir, _os.pardir))
    custom_dir = _os.path.join(project_root, "skills_custom")

    if not _os.path.isdir(custom_dir):
        return 0

    count = 0
    for skill_name in sorted(_os.listdir(custom_dir)):
        skill_dir = _os.path.join(custom_dir, skill_name)
        json_path = _os.path.join(skill_dir, "skill.json")
        if not _os.path.isfile(json_path):
            continue

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                meta = _json.load(f)

            tool_defs = meta.get("tools", [])
            if not tool_defs:
                continue

            for td in tool_defs:
                name = td.get("name", "")
                mod_file = td.get("module", "")
                func_name = td.get("function", "")
                if not name:
                    continue

                # Step 1: Dynamically load the function
                if mod_file and func_name:
                    mod_path = _os.path.join(skill_dir, mod_file)
                    if _os.path.isfile(mod_path):
                        try:
                            spec = _import_util.spec_from_file_location(
                                "custom_" + name, mod_path
                            )
                            mod = _import_util.module_from_spec(spec)
                            spec.loader.exec_module(mod)
                            func = getattr(mod, func_name)
                            globals()[func_name] = func
                            TOOL_FUNCS[name] = func
                        except Exception:
                            continue

                # Step 2: Register schema to TOOLS list
                TOOLS.append({
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": td.get("description", ""),
                        "parameters": td.get("parameters", {
                            "type": "object",
                            "properties": {}
                        })
                    }
                })
                count += 1

        except Exception:
            continue

    return count


# Auto-discover custom skill tools on module load
_register_custom_skill_tools()

# 工具参数校验规则
_TOOL_REQUIRED_PARAMS: Dict[str, list] = {
    "run_cmd": ["cmd"],
    "read_file": ["path"],
    "write_file": ["path", "content"],
    "list_files": [],
    "search_files": ["name"],
    "get_system_info": [],
    "get_current_time": [],
    "create_directory": ["path"],
    "delete_file": ["path"],
    # 搜索与替换
    "grep": ["pattern"],
    "replace": ["pattern", "replacement"],
    "find_files": ["pattern"],
    "count_lines": [],
    "diff": ["file1", "file2"],
    # Git 操作
    "git_status": [],
    "git_log": [],
    "git_diff": [],
    "git_commit_stats": [],
    "show_file": ["path"],
}
# 工具超时配置（秒）
_TOOL_TIMEOUTS: Dict[str, float] = {
    "run_cmd": 30.0,
    "read_file": 10.0,
    "write_file": 10.0,
    "list_files": 10.0,
    "search_files": 15.0,
    "get_system_info": 5.0,
    "get_current_time": 5.0,
    "create_directory": 10.0,
    "delete_file": 10.0,
    # 搜索与替换
    "grep": 30.0,
    "replace": 30.0,
    "find_files": 30.0,
    "count_lines": 30.0,
    "diff": 10.0,
    # Git 操作
    "git_status": 15.0,
    "git_log": 15.0,
    "git_diff": 15.0,
    "git_commit_stats": 15.0,
    "show_file": 10.0,
}
MAX_RESULT_CHARS = 30000  # 结果最大字符数
def dispatch_tool(
    name: str,
    args: Optional[Dict[str, Any]] = None,
    timeout: Optional[float] = None,
    max_result_chars: int = MAX_RESULT_CHARS,
) -> str:
    """
    统一工具调度入口
    Args:
        name: 工具名称
        args: 参数字典
        timeout: 超时秒数
        max_result_chars: 结果截断阈值
    Returns:
        工具执行结果
    """
    if args is None:
        args = {}
    # 检查工具是否存在
    func = TOOL_FUNCS.get(name)
    if func is None:
        return f"❌ 未知工具：{name}"
    # 参数校验
    required = _TOOL_REQUIRED_PARAMS.get(name, [])
    for key in required:
        if key not in args:
            return f"❌ 缺少必需参数：{key}"
    # 确定超时
    if timeout is None:
        timeout = _TOOL_TIMEOUTS.get(name, 10.0)
    # 执行（带超时保护）
    result_container: Dict[str, Any] = {"result": None, "error": None, "done": False}
    def _run():
        try:
            raw = func(**args)
            result_container["result"] = str(raw) if raw is not None else "✅ 执行成功"
        except Exception as e:
            result_container["error"] = f"{e}\n{traceback.format_exc()}"
        finally:
            result_container["done"] = True
    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    thread.join(timeout=timeout)
    if not result_container["done"]:
        return f"⚠️ 执行超时（{timeout}秒）"
    if result_container["error"]:
        return f"❌ 执行异常:\n{result_container['error']}"
    result = result_container["result"] or ""
    # 结果截断
    if isinstance(result, str) and len(result) > max_result_chars:
        result = result[:max_result_chars] + f"\n\n...（已截断至 {max_result_chars} 字符）"
    return result
def dispatch_tool_from_json(
    name: str,
    args_json: str,
    timeout: Optional[float] = None,
) -> str:
    """从 JSON 字符串解析参数并调度工具
    将 JSON 格式的参数字符串反序列化后，调用 dispatch_tool 执行。
    Args:
        name: 工具名称
        args_json: JSON 格式的参数字符串
        timeout: 超时秒数（可选）
    Returns:
        工具执行结果字符串
    """
    try:
        args = json.loads(args_json) if args_json else {}
    except json.JSONDecodeError as e:
        return f"❌ JSON 解析失败：{e}"
    if not isinstance(args, dict):
        return f"❌ 参数格式错误"
    return dispatch_tool(name, args, timeout=timeout)
