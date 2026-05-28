# ============================================================
# TennineClaw - 目录操作工具
# ============================================================
# 包含：列出目录内容、搜索文件、创建目录
# ============================================================

import os
import datetime
import fnmatch


def tool_list_files(directory: str = "", show_hidden: bool = False, pattern: str = "") -> str:
    """列出目录内容（排序后输出）

    显示目录中的文件和子目录，包含大小、修改时间等信息。
    默认隐藏 "." 开头的文件，最多显示 200 项。
    支持 pattern 通配符过滤（如 "*.py", "*.md", "test*"）。

    Args:
        directory: 目录路径（默认为当前目录）
        show_hidden: 是否显示隐藏文件
        pattern: 文件通配符过滤（如 "*.py", "*.md"），为空时不进行过滤

    Returns:
        格式化的目录内容列表
    """
    if not directory:
        directory = "."

    try:
        if not os.path.exists(directory):
            return f"\u274c 目录不存在：{directory}"
        if not os.path.isdir(directory):
            return f"\u274c 路径不是目录：{directory}"

        items = []
        total_size = 0
        dir_count = 0
        file_count = 0

        for entry in os.listdir(directory):
            if not show_hidden and entry.startswith("."):
                continue
            full_path = os.path.join(directory, entry)
            is_dir = os.path.isdir(full_path)
            size = os.path.getsize(full_path) if not is_dir else 0
            mtime = datetime.datetime.fromtimestamp(
                os.path.getmtime(full_path)
            ).strftime("%Y-%m-%d %H:%M:%S")

            # --- pattern 过滤（仅对文件生效） ---
            if pattern and not is_dir:
                # 支持逗号分隔的多个 pattern
                patterns = [p.strip() for p in pattern.split(",") if p.strip()]
                matched = False
                for p in patterns:
                    if fnmatch.fnmatch(entry, p):
                        matched = True
                        break
                if not matched:
                    continue

            if is_dir:
                dir_count += 1
                items.append(f"\U0001f4c1  {entry}/  ({mtime})")
            else:
                file_count += 1
                total_size += size
                if size < 1024:
                    size_str = f"{size}B"
                elif size < 1024 * 1024:
                    size_str = f"{size / 1024:.1f}KB"
                else:
                    size_str = f"{size / 1024 / 1024:.1f}MB"
                items.append(f"\U0001f4c4  {entry}  [{size_str}]  ({mtime})")

        items.sort(key=lambda x: (not x.startswith("\U0001f4c1"), x.lower()))

        max_display = 200
        if len(items) > max_display:
            items = items[:max_display] + [f"... 还有 {len(items) - max_display} 项未显示"]

        result = [
            f"\U0001f4c2 目录：{os.path.abspath(directory)}",
            f"   \U0001f4ca 总计：{dir_count} 个目录，{file_count} 个文件，总大小 {total_size / 1024:.1f}KB",
            "\u2500" * 50,
            *items
        ]
        return "\n".join(result)
    except PermissionError:
        return f"\u274c 权限不足，无法访问：{directory}"
    except Exception as e:
        return f"异常：{e}"


def tool_search_files(name: str = "", directory: str = "", max_results: int = 50) -> str:
    """搜索文件（按名称匹配，支持通配符）

    递归遍历目录，查找名称匹配的文件。
    自动跳过隐藏目录和常见的构建/依赖目录。
    - 如果 name 包含通配符（* ? [），则使用 fnmatch 通配符匹配
    - 否则使用子串包含匹配（不区分大小写）

    Args:
        name: 搜索的文件名关键字或通配符模式
        directory: 搜索目录（默认为当前目录）
        max_results: 最大返回结果数

    Returns:
        搜索结果列表
    """
    if not directory:
        directory = "."
    if not name:
        return "错误：搜索名称不能为空"

    # 判断是否包含通配符
    has_wildcard = any(c in name for c in "*?[")
    name_lower = name.lower()

    try:
        results = []
        for root, dirs, files in os.walk(directory):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            dirs[:] = [d for d in dirs if d not in (
                "node_modules", "__pycache__", ".git", ".svn", "venv", "env"
            )]
            for f in files:
                matched = False
                if has_wildcard:
                    # 通配符匹配（不区分大小写）
                    if fnmatch.fnmatch(f.lower(), name_lower):
                        matched = True
                else:
                    # 子串包含匹配（不区分大小写）
                    if name_lower in f.lower():
                        matched = True

                if matched:
                    full_path = os.path.join(root, f)
                    size = os.path.getsize(full_path)
                    rel_path = os.path.relpath(full_path, directory)
                    results.append(f"\U0001f4c4  {rel_path}  ({size:,}B)")
                    if len(results) >= max_results:
                        break
            if len(results) >= max_results:
                break

        if not results:
            return f"\U0001f50d 在 '{directory}' 中未找到包含 '{name}' 的文件"

        header = f"\U0001f50d 搜索结果：在 '{directory}' 中找到 {len(results)} 个文件（匹配：{name}）"
        return header + "\n" + "\u2500" * 40 + "\n" + "\n".join(results)
    except Exception as e:
        return f"异常：{e}"


def tool_create_directory(path: str = "") -> str:
    """创建目录（自动创建中间目录）

    类似 mkdir -p，如果目录已存在则静默返回成功。

    Args:
        path: 要创建的目录路径

    Returns:
        创建成功或失败信息
    """
    if not path:
        return "错误：路径不能为空"
    try:
        os.makedirs(path, exist_ok=True)
        abs_path = os.path.abspath(path)
        return f"\u2705 目录已创建：{abs_path}"
    except PermissionError:
        return f"\u274c 权限不足，无法创建目录：{path}"
    except Exception as e:
        return f"异常：{e}"
