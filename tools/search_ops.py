# ============================================================
# TennineClaw - 搜索与替换工具
# ============================================================
# 包含：Grep 搜索、文本替换、代码行数统计、文件查找和差异比较
# ============================================================

import os
import re
import fnmatch


# 默认忽略的目录
IGNORE_DIRS = {
    "__pycache__", ".git", ".svn", ".hg", "node_modules",
    "venv", "env", ".venv", ".env", ".tox", ".mypy_cache",
    ".pytest_cache", ".idea", ".vscode", ".vs", "dist",
    "build", "__MACOSX", "target", "bin", "obj",
}


def _should_ignore(path: str, name: str, extra_ignores: set = None) -> bool:
    """判断是否应忽略该路径"""
    if name in IGNORE_DIRS:
        return True
    if extra_ignores and name in extra_ignores:
        return True
    if name.startswith("."):
        return True
    return False


def _is_binary(path: str) -> bool:
    """简单检测二进制文件"""
    try:
        with open(path, 'rb') as f:
            chunk = f.read(8192)
            return b'\x00' in chunk
    except Exception:
        return True  # 读不了就当二进制


# ============================================================
# tool_grep — 在文件中搜索文本（类似 grep -r）
# ============================================================

def tool_grep(
    pattern: str = "",
    directory: str = ".",
    glob: str = "*",
    max_results: int = 50,
    ignore_case: bool = True,
    context_lines: int = 0,
) -> str:
    """在文件中搜索文本内容（类似 grep -r）

    Args:
        pattern: 搜索模式（支持正则）
        directory: 搜索目录
        glob: 文件通配符过滤，如 "*.py", "*.js", "*.{py,js,ts}"
        max_results: 最大匹配结果数
        ignore_case: 是否忽略大小写
        context_lines: 匹配行前后显示的行数

    Returns:
        格式化的搜索结果文本
    """
    if not pattern:
        return "❌ 搜索模式不能为空"

    try:
        regex = re.compile(pattern, re.IGNORECASE if ignore_case else 0)
    except re.error as e:
        return f"❌ 正则表达式错误: {e}"

    if not os.path.isdir(directory):
        return f"❌ 目录不存在: {directory}"

    # 解析 glob 模式
    globs = glob.split(",") if "," in glob else [glob]
    globs = [g.strip() for g in globs if g.strip()]

    results = []
    total_files = 0
    file_count = 0

    try:
        for root, dirs, files in os.walk(directory):
            # 过滤忽略目录
            dirs[:] = [d for d in dirs if not _should_ignore(root, d)]

            for fname in files:
                # 检查 glob 匹配
                if not any(fnmatch.fnmatch(fname, g) for g in globs):
                    continue

                # 跳过二进制
                fpath = os.path.join(root, fname)
                if _is_binary(fpath):
                    continue

                total_files += 1
                rel_path = os.path.relpath(fpath, directory)

                try:
                    with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
                        lines = f.readlines()
                except Exception:
                    continue

                file_matches = []
                for i, line in enumerate(lines, 1):
                    if regex.search(line):
                        file_matches.append((i, line.rstrip('\n')))

                if not file_matches:
                    continue

                file_count += 1

                # 带上下文的格式
                if context_lines > 0:
                    results.append(f"─── {rel_path} ───")
                    matched_indices = {m[0] for m in file_matches}
                    seen_lines = set()

                    for line_no, line_text in file_matches:
                        start = max(0, line_no - 1 - context_lines)
                        end = min(len(lines), line_no + context_lines)

                        for ctx_i in range(start, end):
                            ctx_no = ctx_i + 1
                            if ctx_no in seen_lines:
                                continue
                            seen_lines.add(ctx_no)

                            ctx_text = lines[ctx_i].rstrip('\n')
                            if ctx_no in matched_indices:
                                results.append(f"  → {ctx_no:>6}: {ctx_text}")
                            else:
                                results.append(f"    {ctx_no:>6}: {ctx_text}")

                        if line_no != file_matches[-1][0]:
                            results.append("    ------")

                else:
                    # 简洁格式
                    for line_no, line_text in file_matches:
                        results.append(f"{rel_path}:{line_no}: {line_text.strip()}")

                    if len(file_matches) > 1:
                        results.append("")

                if len(results) >= max_results * 3:  # 保守截断
                    results.append(f"  ... 更多结果未显示（已达到最大限制 {max_results} 个文件）")
                    break

            if len(results) >= max_results * 3:
                break

    except Exception as e:
        return f"❌ 搜索过程异常: {e}"

    if not results:
        return (
            f"🔍 在 {total_files} 个文件中未找到匹配 '{pattern}' 的内容\n"
            f"   目录: {os.path.abspath(directory)} | 文件: {glob}"
        )

    summary = (
        f"🔍 Grep 结果: '{pattern}'\n"
        f"   目录: {os.path.abspath(directory)} | 文件: {glob if glob else '*'}\n"
        f"   扫描 {total_files} 个文件，找到 {file_count} 个匹配文件\n"
        "─" * 50
    )

    output = [summary] + results
    return "\n".join(output)


# ============================================================
# tool_replace — 搜索并替换文件内容
# ============================================================

def tool_replace(
    pattern: str = "",
    replacement: str = "",
    directory: str = ".",
    glob: str = "*",
    max_files: int = 20,
    dry_run: bool = True,
) -> str:
    """搜索并替换文件内容（类似 sed -i）

    默认只预览（dry_run=True），确认后设 dry_run=False 执行替换。

    Args:
        pattern: 搜索模式（支持正则）
        replacement: 替换文本
        directory: 搜索目录
        glob: 文件通配符
        max_files: 最多处理的文件数
        dry_run: 预览模式（True=只显示，False=执行替换）

    Returns:
        替换结果/预览
    """
    if not pattern:
        return "❌ 搜索模式不能为空"

    try:
        regex = re.compile(pattern)
    except re.error as e:
        return f"❌ 正则表达式错误: {e}"

    if not os.path.isdir(directory):
        return f"❌ 目录不存在: {directory}"

    globs = glob.split(",") if "," in glob else [glob]
    globs = [g.strip() for g in globs if g.strip()]

    matches = []
    errors = []

    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if not _should_ignore(root, d)]

        for fname in files:
            if not any(fnmatch.fnmatch(fname, g) for g in globs):
                continue

            fpath = os.path.join(root, fname)
            if _is_binary(fpath):
                continue

            try:
                with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()

                new_content, count = regex.subn(replacement, content)
                if count > 0:
                    rel_path = os.path.relpath(fpath, directory)
                    matches.append((rel_path, count))
            except Exception as e:
                rel_path = os.path.relpath(fpath, directory)
                errors.append(f"  {rel_path}: {e}")

        if len(matches) >= max_files:
            break

    if not matches:
        summary = f"🔍 在 {glob} 文件中未找到匹配 '{pattern}' 的内容"
        if errors:
            summary += f"\n  ⚠️ {len(errors)} 个文件读取失败"
        return summary

    # 预览
    lines = [
        f"{'📋 预览' if dry_run else '✅ 已执行'}: 替换 '{pattern}' → '{replacement}'",
        f"   匹配 {len(matches)} 个文件（共 {sum(m[1] for m in matches)} 处）",
        "─" * 50,
    ]

    for rel_path, count in matches:
        lines.append(f"  {rel_path}  ({count} 处)")

    if errors:
        lines.extend(["", "⚠️ 以下文件读取失败:"] + errors)

    if dry_run and matches:
        lines.extend([
            "",
            "💡 确认执行请使用 dry_run=False",
        ])

    # dry_run=False 时执行替换
    if not dry_run:
        replaced = 0
        for root, dirs, files in os.walk(directory):
            dirs[:] = [d for d in dirs if not _should_ignore(root, d)]
            for fname in files:
                if not any(fnmatch.fnmatch(fname, g) for g in globs):
                    continue
                fpath = os.path.join(root, fname)
                if _is_binary(fpath):
                    continue
                try:
                    with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
                        content = f.read()
                    new_content, count = regex.subn(replacement, content)
                    if count > 0:
                        with open(fpath, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        replaced += count
                except Exception:
                    pass
        lines.append(f"    ✅ 实际替换 {replaced} 处")

    return "\n".join(lines)


# ============================================================
# tool_count_lines — 统计代码行数
# ============================================================

def tool_count_lines(
    directory: str = ".",
    pattern: str = "*.py,*.js,*.ts,*.html,*.css,*.java,*.go,*.rs,*.cpp,*.h,*.c",
    exclude_pattern: str = "",
) -> str:
    """统计代码行数

    Args:
        directory: 项目目录
        pattern: 文件通配符（逗号分隔）
        exclude_pattern: 排除文件名模式

    Returns:
        行数统计报告
    """
    if not os.path.isdir(directory):
        return f"❌ 目录不存在: {directory}"

    globs = [g.strip() for g in pattern.split(",") if g.strip()]
    exclude_globs = [g.strip() for g in exclude_pattern.split(",") if g.strip()] if exclude_pattern else []

    ext_stats = {}  # extension -> {files, lines, blank, comment, code}
    total_files = 0
    total_lines = 0
    total_blank = 0
    total_comment = 0
    total_code = 0

    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if not _should_ignore(root, d)]

        for fname in files:
            # 检查匹配
            if not any(fnmatch.fnmatch(fname, g) for g in globs):
                continue
            if any(fnmatch.fnmatch(fname, g) for g in exclude_globs):
                continue

            fpath = os.path.join(root, fname)
            if _is_binary(fpath):
                continue

            try:
                with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()

                _, ext = os.path.splitext(fname)
                if not ext:
                    ext = "(no ext)"

                lines = content.split('\n')
                line_count = len(lines)
                blank = sum(1 for l in lines if l.strip() == '')
                comment = 0
                for l in lines:
                    strip = l.strip()
                    if strip.startswith('#') or strip.startswith('//') or strip.startswith('/*') or strip.startswith('*') or strip.startswith('"""') or strip.startswith("'''"):
                        comment += 1
                    elif '//' in strip and ext in ('.js', '.ts', '.go', '.cpp', '.c', '.h', '.java', '.rs'):
                        pass  # 简单估算
                    elif '#' in strip and ext in ('.py', '.rb', '.sh', '.yaml', '.yml', '.toml'):
                        pass

                code = line_count - blank

                if ext not in ext_stats:
                    ext_stats[ext] = {'files': 0, 'lines': 0, 'blank': 0, 'comment': 0, 'code': 0}

                ext_stats[ext]['files'] += 1
                ext_stats[ext]['lines'] += line_count
                ext_stats[ext]['blank'] += blank
                ext_stats[ext]['code'] += code
                total_files += 1
                total_lines += line_count
                total_blank += blank
                total_code += code

            except Exception:
                pass

    if not ext_stats:
        return f"📊 在 {os.path.abspath(directory)} 中未找到匹配的文件"

    lines_result = [
        f"📊 代码行数统计: {os.path.abspath(directory)}",
        f"   总文件: {total_files} | 总行数: {total_lines:,} | 代码: {total_code:,} | 空白: {total_blank:,}",
        "─" * 60,
        f"{'语言':<10} {'文件':>5} {'总行':>8} {'代码':>8} {'空白':>8} {'占比':>6}",
        "─" * 60,
    ]

    for ext in sorted(ext_stats.keys(), key=lambda e: -ext_stats[e]['code']):
        s = ext_stats[ext]
        pct = f"{s['code']/total_code*100:.0f}%" if total_code > 0 else "0%"
        lines_result.append(
            f"{ext:<10} {s['files']:>5} {s['lines']:>8,} {s['code']:>8,} {s['blank']:>8,} {pct:>6}"
        )

    return "\n".join(lines_result)


# ============================================================
# tool_find_files — 按扩展名/模式查找文件
# ============================================================

def tool_find_files(
    pattern: str = "",
    directory: str = ".",
    sort_by: str = "name",
    max_results: int = 100,
) -> str:
    """按名称模式查找文件（类似 find + grep）

    Args:
        pattern: 文件名模式（支持通配符 * ?），如 "*.py", "*test*", "*.{tsx,jsx}"
        directory: 搜索目录
        sort_by: 排序方式 name|time|size
        max_results: 最大结果数

    Returns:
        文件列表
    """
    if not pattern:
        return "❌ 文件模式不能为空"

    if not os.path.isdir(directory):
        return f"❌ 目录不存在: {directory}"

    # 支持花括号展开 {a,b,c}
    brace_patterns = re.findall(r'\{([^}]+)\}', pattern)
    if brace_patterns:
        patterns = []
        for bp in brace_patterns:
            alternatives = [a.strip() for a in bp.split(',')]
            for alt in alternatives:
                patterns.append(pattern.replace('{' + bp + '}', alt))
    else:
        patterns = [pattern]

    results = []

    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if not _should_ignore(root, d)]

        for fname in files:
            # 全文匹配
            full_path = os.path.join(root, fname)
            rel_path = os.path.relpath(full_path, directory)

            for pat in patterns:
                if fnmatch.fnmatch(fname, pat):
                    size = os.path.getsize(full_path)
                    mtime = os.path.getmtime(full_path)
                    results.append({
                        'path': rel_path,
                        'name': fname,
                        'size': size,
                        'mtime': mtime,
                    })
                    break

        if len(results) >= max_results:
            break

    if not results:
        return f"🔍 在 {os.path.abspath(directory)} 中未找到匹配 '{pattern}' 的文件"

    # 排序
    if sort_by == 'time':
        results.sort(key=lambda x: x['mtime'], reverse=True)
    elif sort_by == 'size':
        results.sort(key=lambda x: x['size'], reverse=True)
    else:
        results.sort(key=lambda x: x['path'].lower())

    # 截断
    if len(results) > max_results:
        results = results[:max_results]

    total_size = sum(r['size'] for r in results)
    diff_count = len(set(os.path.dirname(r['path']) or '.' for r in results))

    lines = [
        f"🔍 找到 {len(results)} 个文件（匹配: '{pattern}'）",
        f"   目录: {os.path.abspath(directory)}",
        f"   总大小: {total_size/1024:.1f}KB | 涉及 {diff_count} 个目录",
        "─" * 50,
    ]

    for r in results:
        if r['size'] < 1024:
            sz = f"{r['size']}B"
        elif r['size'] < 1024*1024:
            sz = f"{r['size']/1024:.1f}KB"
        else:
            sz = f"{r['size']/1024/1024:.1f}MB"
        lines.append(f"  {sz:>8}  {r['path']}")

    return "\n".join(lines)


# ============================================================
# tool_diff — 比较两个文件
# ============================================================

def tool_diff(
    file1: str = "",
    file2: str = "",
    context_lines: int = 3,
) -> str:
    """比较两个文件的差异（类似 diff）

    Args:
        file1: 第一个文件路径
        file2: 第二个文件路径
        context_lines: 上下文行数

    Returns:
        差异内容
    """
    if not file1 or not file2:
        return "❌ 需要两个文件路径"

    for f in [file1, file2]:
        if not os.path.isfile(f):
            return f"❌ 文件不存在: {f}"
        if _is_binary(f):
            return f"❌ 不支持二进制文件: {f}"

    try:
        with open(file1, 'r', encoding='utf-8', errors='replace') as f:
            lines1 = f.readlines()
        with open(file2, 'r', encoding='utf-8', errors='replace') as f:
            lines2 = f.readlines()
    except Exception as e:
        return f"❌ 读取文件失败: {e}"

    import difflib

    differ = difflib.unified_diff(
        lines1, lines2,
        fromfile=file1, tofile=file2,
        n=context_lines,
        lineterm='',
    )

    diff_lines = list(differ)

    if not diff_lines:
        return f"✅ 文件相同: {file1} 和 {file2} 内容一致"

    # 统计
    added = sum(1 for l in diff_lines if l.startswith('+') and not l.startswith('+++'))
    removed = sum(1 for l in diff_lines if l.startswith('-') and not l.startswith('---'))

    result = [
        f"📋 文件差异:",
        f"  --- {file1}",
        f"  +++ {file2}",
        f"  📊 +{added} / -{removed}",
        "─" * 50,
    ] + diff_lines

    return "\n".join(result)
