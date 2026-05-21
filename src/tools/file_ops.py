# ============================================================
# TennineClaw - 文件操作工具
# ============================================================
# 包含：读取文件、写入文件、删除文件（带安全路径检查 + 用户确认）
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


def tool_delete_file(path: str = "", force: bool = False) -> str:
    """删除文件或空目录（附带系统关键路径保护 + 用户确认）

    安全删除文件或空目录。对系统关键路径（如 C:\\Windows, C:\\Program Files
    及其子目录）实施删除拦截保护。
    当 force=True 时，跳过系统路径保护检查，允许删除。

    Args:
        path: 要删除的文件或空目录路径
        force: 是否强制删除（跳过系统路径保护检查）

    Returns:
        删除成功或失败信息；系统路径保护被触发时返回确认提示
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

        # 检测系统路径保护
        is_system_path = False
        matched_sys_dir = ""
        for sys_dir in system_dirs:
            norm_sys = os.path.normpath(sys_dir).lower()
            norm_path = os.path.normpath(abs_path).lower()
            if norm_path == norm_sys or norm_path.startswith(norm_sys + os.sep):
                is_system_path = True
                matched_sys_dir = sys_dir
                break

        if is_system_path:
            if force:
                # 用户已确认强制删除，跳过保护
                pass
            else:
                return (
                    f"⛔ 安全保护：检测到要删除系统关键路径 [{matched_sys_dir}] 下的内容\n"
                    f"   路径: `{path}`\n"
                    f"   🔐 如确认要删除，请调用 `delete_file(path=..., force=True)` 执行。"
                )

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
# dict 参数包装器
# ============================================================
def tool_read_file_compat(args: dict = None) -> str:
    """接受 dict 参数调用 tool_read_file

    Args:
        args: 包含 "path" 键的参数字典

    Returns:
        文件内容
    """
    if args is None:
        args = {}
    return tool_read_file(path=args.get("path", ""))


def tool_write_file_compat(args: dict = None) -> str:
    """接受 dict 参数调用 tool_write_file

    Args:
        args: 包含 "path" 和 "content" 键的参数字典

    Returns:
        写入结果
    """
    if args is None:
        args = {}
    return tool_write_file(path=args.get("path", ""), content=args.get("content", ""))


def tool_delete_file_compat(args: dict = None) -> str:
    """接受 dict 参数调用 tool_delete_file

    Args:
        args: 包含 "path" 键的参数字典

    Returns:
        删除结果
    """
    if args is None:
        args = {}
    return tool_delete_file(
        path=args.get("path", ""),
        force=args.get("force", False)
    )
