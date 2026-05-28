# ============================================================
# TennineClaw - 文件操作工具
# ============================================================
# 包含：读取、写入、删除、编辑、追加、重命名、复制、文件信息
# ============================================================

import os
import shutil
import datetime


def tool_read_file(path: str = "") -> str:
    """读取文件完整内容（UTF-8 编码）

    自动处理编码错误和长文件截断。

    Args:
        path: 文件路径

    Returns:
        文件内容字符串；文件过长时自动截断至 500000 字符；
        文件不存在或权限不足时返回错误信息
    """
    if not path:
        return "错误：路径不能为空"
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        if len(content) > 500000:
            content = content[:500000] + f"\n\n...（文件过长，已截断至 500000 字符，共 {len(content)} 字符）"
        return content
    except FileNotFoundError:
        return f"\u274c 文件不存在: {path}"
    except IsADirectoryError:
        return f"\u274c 路径是一个目录，不是文件: {path}"
    except PermissionError:
        return f"\u274c 权限不足，无法读取: {path}"
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
        return f"\u2705 成功写入文件: {path} (共 {len(content)} 字符)"
    except PermissionError:
        return f"\u274c 权限不足，无法写入: {path}"
    except Exception as e:
        return f"异常: {e}"


def tool_edit_file(path: str = "", line: int = None, text: str = "", mode: str = "replace") -> str:
    """编辑文件指定行内容（替换/插入/删除）

    对文件中的指定行进行操作，支持三种模式：
    - replace（默认）：用 text 替换指定行的内容
    - insert：在指定行之后插入 text 内容
    - delete：删除指定行

    Args:
        path: 文件路径
        line: 目标行号（从 1 开始）。mode=replace/delete 时必填，mode=insert 时必填（在该行后插入）
        text: 要写入的文本内容（replace/insert 模式必填）
        mode: 操作模式 — "replace"（替换行）| "insert"（行后插入）| "delete"（删除行）

    Returns:
        操作成功或失败信息，含变更前后的行内容摘要
    """
    if not path:
        return "错误：路径不能为空"

    if not os.path.isfile(path):
        # 如果文件不存在且 mode 为 write/insert，可自动创建
        if mode == "insert" and line == 1:
            return tool_write_file(path=path, content=text)
        return f"\u274c 文件不存在: {path}"

    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except PermissionError:
        return f"\u274c 权限不足，无法读取: {path}"
    except Exception as e:
        return f"异常: {e}"

    total_lines = len(lines)

    if mode in ("replace", "delete"):
        if line is None:
            return "错误：replace/delete 模式需要指定 line 参数（行号）"
        if line < 1 or line > total_lines:
            return f"\u274c 行号越界：文件共 {total_lines} 行，指定行号 {line}"

        old_text = lines[line - 1].rstrip("\n").rstrip("\r")

        if mode == "replace":
            lines[line - 1] = text + "\n"
            action = "替换"
            detail = f"第 {line} 行: '{old_text}' -> '{text}'"
        else:  # delete
            lines.pop(line - 1)
            action = "删除"
            detail = f"已删除第 {line} 行: '{old_text}'"

    elif mode == "insert":
        if line is None:
            return "错误：insert 模式需要指定 line 参数（在哪行后插入）"
        if line < 0 or line > total_lines:
            return f"\u274c 行号越界：文件共 {total_lines} 行，指定行号 {line}"
        # 在指定行后插入（line=0 表示在文件开头插入）
        insert_text = text + "\n" if not text.endswith("\n") else text
        lines.insert(line, insert_text)
        action = "插入"
        detail = f"已在第 {line} 行后插入 {len(text)} 字符"

    else:
        return f"\u274c 未知模式: {mode}，支持的模式: replace, insert, delete"

    try:
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(lines)
        return f"\u2705 成功{action}文件: {path}\n   {detail}"
    except PermissionError:
        return f"\u274c 权限不足，无法写入: {path}"
    except Exception as e:
        return f"异常: {e}"


def tool_append_file(path: str = "", text: str = "") -> str:
    """追加内容到文件末尾

    如果文件不存在，自动创建文件并写入内容。

    Args:
        path: 文件路径
        text: 要追加的文本内容

    Returns:
        追加成功或失败信息
    """
    if not path:
        return "错误：路径不能为空"
    if not text:
        return "错误：追加内容不能为空"

    try:
        # 自动创建父目录
        parent_dir = os.path.dirname(path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

        # 检查文件是否存在及大小
        file_exists = os.path.isfile(path)
        old_size = os.path.getsize(path) if file_exists else 0

        with open(path, "a", encoding="utf-8") as f:
            f.write(text)

        new_size = os.path.getsize(path)
        action = "追加" if file_exists else "创建并写入"

        return f"\u2705 成功{action}文件: {path}\n   写入 {len(text)} 字符（文件大小: {old_size}B -> {new_size}B）"
    except PermissionError:
        return f"\u274c 权限不足，无法写入: {path}"
    except Exception as e:
        return f"异常: {e}"


def tool_rename_file(src: str = "", dst: str = "") -> str:
    """重命名或移动文件/目录

    将源路径重命名为目标路径（也可用于跨目录移动）。

    Args:
        src: 源文件/目录路径
        dst: 目标路径

    Returns:
        重命名成功或失败信息
    """
    if not src:
        return "错误：源路径不能为空"
    if not dst:
        return "错误：目标路径不能为空"

    if not os.path.exists(src):
        return f"\u274c 源路径不存在: {src}"

    try:
        # 自动创建目标父目录
        dst_parent = os.path.dirname(os.path.abspath(dst))
        if dst_parent:
            os.makedirs(dst_parent, exist_ok=True)

        os.rename(src, dst)
        src_type = "目录" if os.path.isdir(dst) else "文件"
        return f"\u2705 成功重命名{src_type}: {src} -> {dst}"
    except PermissionError:
        return f"\u274c 权限不足，无法重命名: {src}"
    except FileExistsError:
        return f"\u274c 目标路径已存在: {dst}"
    except Exception as e:
        return f"异常: {e}"


def tool_copy_file(src: str = "", dst: str = "") -> str:
    """复制文件或目录

    使用 shutil 复制文件（或整个目录树）。

    Args:
        src: 源文件/目录路径
        dst: 目标路径

    Returns:
        复制成功或失败信息
    """
    if not src:
        return "错误：源路径不能为空"
    if not dst:
        return "错误：目标路径不能为空"

    if not os.path.exists(src):
        return f"\u274c 源路径不存在: {src}"

    try:
        # 自动创建目标父目录
        dst_parent = os.path.dirname(os.path.abspath(dst))
        if dst_parent:
            os.makedirs(dst_parent, exist_ok=True)

        if os.path.isdir(src):
            shutil.copytree(src, dst, dirs_exist_ok=True)
            return f"\u2705 成功复制目录: {src} -> {dst}"
        else:
            shutil.copy2(src, dst)
            size = os.path.getsize(dst)
            return f"\u2705 成功复制文件: {src} -> {dst} ({size:,}B)"
    except PermissionError:
        return f"\u274c 权限不足，无法复制: {src}"
    except FileExistsError:
        return f"\u274c 目标路径已存在: {dst}"
    except Exception as e:
        return f"异常: {e}"


def tool_file_info(path: str = "") -> str:
    """获取文件/目录的详细信息

    返回大小、修改时间、创建时间、权限、类型等元数据。

    Args:
        path: 文件或目录路径

    Returns:
        格式化的文件信息
    """
    if not path:
        return "错误：路径不能为空"

    if not os.path.exists(path):
        return f"\u274c 路径不存在: {path}"

    try:
        stat = os.stat(path)
        is_dir = os.path.isdir(path)
        abs_path = os.path.abspath(path)

        # 时间格式化
        mtime = datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        ctime = datetime.datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S")
        atime = datetime.datetime.fromtimestamp(stat.st_atime).strftime("%Y-%m-%d %H:%M:%S")

        # 文件大小
        size = stat.st_size
        if size < 1024:
            size_str = f"{size} B"
        elif size < 1024 * 1024:
            size_str = f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            size_str = f"{size / 1024 / 1024:.1f} MB"
        else:
            size_str = f"{size / 1024 / 1024 / 1024:.2f} GB"

        entry_type = "📁 目录" if is_dir else "📄 文件"
        name = os.path.basename(path)

        lines = [
            f"{entry_type} {name}",
            f"  📍 全路径: {abs_path}",
            f"  📏 大小: {size_str} ({size:,} 字节)",
            f"  🕐 修改时间: {mtime}",
            f"  🕐 创建时间: {ctime}",
            f"  🕐 访问时间: {atime}",
        ]

        if not is_dir:
            _, ext = os.path.splitext(name)
            lines.append(f"  🏷️  扩展名: {ext}")

        # 目录下文件计数
        if is_dir:
            try:
                entries = os.listdir(path)
                files = sum(1 for e in entries if os.path.isfile(os.path.join(path, e)))
                dirs = sum(1 for e in entries if os.path.isdir(os.path.join(path, e)))
                lines.append(f"  📊 内容: {dirs} 个目录, {files} 个文件")
            except PermissionError:
                pass

        return "\n".join(lines)

    except PermissionError:
        return f"\u274c 权限不足，无法访问: {path}"
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
                    f"\u26d4 安全保护：检测到要删除系统关键路径 [{matched_sys_dir}] 下的内容\n"
                    f"   路径: `{path}`\n"
                    f"   \U0001f510 如确认要删除，请调用 `delete_file(path=..., force=True)` 执行。"
                )

        if os.path.isdir(abs_path):
            if os.listdir(abs_path):
                return f"\u274c 目录不为空，无法删除: {path}\n   请先清空目录内容后再删除"
            os.rmdir(abs_path)
            return f"\u2705 成功删除目录: {path}"
        elif os.path.isfile(abs_path):
            os.remove(abs_path)
            return f"\u2705 成功删除文件: {path}"
        else:
            return f"\u274c 路径不存在: {path}"
    except PermissionError:
        return f"\u274c 权限不足，无法删除: {path}"
    except Exception as e:
        return f"异常: {e}"
