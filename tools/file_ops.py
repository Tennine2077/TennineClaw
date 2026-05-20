# ============================================================
# TennineClaw - 文件操作工具
# ============================================================
# 包含：读取文件、写入文件、删除文件（带安全路径检查）
# ============================================================

import os


def tool_read_file(path: str = "") -> str:
    """读取文件完整内容（UTF-8 编码）

    自动处理编码错误和长文件截断。

    Args:
        path: 文件路径

    Returns:
        文件内容字符串；文件过长时自动截断至 20000 字符；
        文件不存在或权限不足时返回错误信息
    """
    if not path:
        return "错误：路径不能为空"
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        if len(content) > 20000:
            content = content[:20000] + f"\n\n...（文件过长，已截断至 20000 字符，共 {len(content)} 字符）"
        return content
    except FileNotFoundError:
        return f"❌ 文件不存在: {path}"
    except IsADirectoryError:
        return f"❌ 路径是一个目录，不是文件: {path}"
    except PermissionError:
        return f"❌ 权限不足，无法读取: {path}"
    except Exception as e:
        return f"异常: {e}"


def tool_write_file(path: str = "", content: str = "") -> str:
    """写入或覆盖文件内容（自动创建父目录）

    Args:
        path: 文件路径
        content: 要写入的文件内容

    Returns:
        写入成功或失败信息
    """
    if not path:
        return "错误：路径不能为空"
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"✅ 成功写入文件: {path} (共 {len(content)} 字符)"
    except PermissionError:
        return f"❌ 权限不足，无法写入: {path}"
    except Exception as e:
        return f"异常: {e}"


def tool_delete_file(path: str = "") -> str:
    """删除文件或空目录（附带系统关键路径保护）

    安全删除文件或空目录。对系统关键路径（如 C:\\Windows, C:\\Program Files
    及其子目录）实施删除拦截保护。

    Args:
        path: 要删除的文件或空目录路径

    Returns:
        删除成功或失败信息
    """
    if not path:
        return "错误：路径不能为空"

    try:
        abs_path = os.path.abspath(path)
        # 仅拦截真正的系统关键路径，不拦截整个驱动器根目录
        system_dirs = [
            os.environ.get("WINDIR", "C:\\Windows"),
            os.environ.get("SystemRoot", "C:\\Windows"),
            "C:\\Windows\\System32",
            os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "System32"),
            "C:\\Program Files",
            "C:\\Program Files (x86)",
        ]
        for sys_dir in system_dirs:
            norm_sys = os.path.normpath(sys_dir).lower()
            norm_path = os.path.normpath(abs_path).lower()
            if norm_path == norm_sys or norm_path.startswith(norm_sys + os.sep):
                return f"❌ 安全拦截: 不允许删除系统关键路径 [{sys_dir}] 下的内容"

        if os.path.isdir(abs_path):
            if os.listdir(abs_path):
                return f"❌ 目录不为空，无法删除: {path}\n   请先清空目录内容后再删除"
            os.rmdir(abs_path)
            return f"✅ 成功删除目录: {path}"
        elif os.path.isfile(abs_path):
            os.remove(abs_path)
            return f"✅ 成功删除文件: {path}"
        else:
            return f"❌ 路径不存在: {path}"
    except PermissionError:
        return f"❌ 权限不足，无法删除: {path}"
    except Exception as e:
        return f"异常: {e}"


# ============================================================
# 向后兼容包装器 — 支持旧版 dict 参数调用
# ============================================================
def tool_read_file_compat(args: dict = None) -> str:
    """向后兼容版本：接受 dict 参数调用 tool_read_file

    Args:
        args: 包含 "path" 键的参数字典

    Returns:
        文件内容
    """
    if args is None:
        args = {}
    return tool_read_file(path=args.get("path", ""))


def tool_write_file_compat(args: dict = None) -> str:
    """向后兼容版本：接受 dict 参数调用 tool_write_file

    Args:
        args: 包含 "path" 和 "content" 键的参数字典

    Returns:
        写入结果
    """
    if args is None:
        args = {}
    return tool_write_file(path=args.get("path", ""), content=args.get("content", ""))


def tool_delete_file_compat(args: dict = None) -> str:
    """向后兼容版本：接受 dict 参数调用 tool_delete_file

    Args:
        args: 包含 "path" 键的参数字典

    Returns:
        删除结果
    """
    if args is None:
        args = {}
    return tool_delete_file(path=args.get("path", ""))
