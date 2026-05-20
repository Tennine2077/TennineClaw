# ============================================================
# TennineClaw - Git 操作工具
# ============================================================
# 提供 Git 仓库状态查看、提交历史、变更差异和贡献统计功能
# ============================================================

import os
import subprocess


def _run_git(args: list, directory: str = ".", timeout: int = 30) -> str:
    """执行 git 命令并返回输出

    Args:
        args: git 命令参数列表（不含 "git" 本身）
        directory: 执行命令的目录
        timeout: 超时秒数

    Returns:
        命令标准输出，或错误信息
    """
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=directory,
            capture_output=True, text=True,
            encoding='utf-8', errors='replace',
            timeout=timeout,
        )
        if result.returncode == 0:
            return result.stdout
        else:
            return result.stderr.strip()
    except FileNotFoundError:
        return "❌ git 未安装或不在 PATH 中"
    except subprocess.TimeoutExpired:
        return "⏱️ git 命令超时"
    except Exception as e:
        return f"❌ git 执行错误: {e}"


def _is_git_repo(directory: str = ".") -> bool:
    """检查指定目录是否为 Git 仓库（存在 .git 目录或文件）

    Args:
        directory: 待检查的目录路径

    Returns:
        是否为 Git 仓库
    """
    git_dir = os.path.join(directory, ".git")
    return os.path.isdir(git_dir) or os.path.isfile(git_dir)


def _format_size(size: int) -> str:
    """将字节数转换为人类可读的大小格式

    根据数值大小自动选择 B / KB / MB / GB 单位。

    Args:
        size: 文件大小（字节）

    Returns:
        格式化后的大小字符串，如 "1.5MB"
    """
    if size < 1024:
        return f"{size}B"
    elif size < 1024*1024:
        return f"{size/1024:.1f}KB"
    elif size < 1024*1024*1024:
        return f"{size/1024/1024:.1f}MB"
    return f"{size/1024/1024/1024:.1f}GB"


# ============================================================
# tool_git_status — Git 状态概览
# ============================================================

def tool_git_status(directory: str = ".") -> str:
    """显示 Git 仓库状态（类似 git status --short）

    Args:
        directory: 仓库目录

    Returns:
        格式化后的状态信息
    """
    if not _is_git_repo(directory):
        return "❌ 当前目录不是 git 仓库（未找到 .git 目录）"

    abs_dir = os.path.abspath(directory)
    repo_name = os.path.basename(abs_dir)

    # 获取分支
    branch = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], directory).strip()
    if branch.startswith("❌"):
        branch = _run_git(["branch", "--show-current"], directory).strip()

    # 获取状态
    status_text = _run_git(["status", "--short"], directory)

    # 获取未跟踪文件数
    untracked = _run_git(["ls-files", "--others", "--exclude-standard"], directory)
    untracked_count = len([l for l in untracked.split('\n') if l.strip()]) if untracked else 0

    # 解析状态
    staged = []
    unstaged = []
    conflicted = []

    for line in status_text.strip().split('\n'):
        line = line.rstrip()
        if not line:
            continue
        xy = line[:2]
        path = line[3:]
        if 'U' in xy or xy in ('DD', 'AA', 'UU'):
            conflicted.append(path)
        elif xy.strip() and xy[1] == ' ':
            staged.append(path)
        elif xy[0] == ' ' and xy[1] != ' ':
            unstaged.append(path)
        elif xy.strip():
            staged.append(path)

    # 获取 ahead/behind
    ahead_behind = _run_git(["rev-list", "--left-right", "--count", f"{branch}...{branch}@{{upstream}}"], directory)
    ahead = behind = 0
    if not ahead_behind.startswith("❌") and not ahead_behind.startswith("fatal"):
        parts = ahead_behind.strip().split()
        if len(parts) >= 2:
            behind, ahead = int(parts[0]), int(parts[1])

    lines = [
        f"📂 Git 仓库: {repo_name}",
        f"   路径: {abs_dir}",
        f"   分支: {branch}",
    ]

    if ahead > 0 or behind > 0:
        diff_parts = []
        if ahead > 0: diff_parts.append(f"↑ {ahead} ahead")
        if behind > 0: diff_parts.append(f"↓ {behind} behind")
        lines.append(f"   远程差异: {' '.join(diff_parts)}")

    lines.append("─" * 50)

    # 变更状态
    total_changes = len(staged) + len(unstaged) + len(conflicted)

    if total_changes == 0 and untracked_count == 0:
        lines.append("✅ 干净的工作区（无变更）")
    else:
        lines.append(f"📊 变更: {total_changes} | 未跟踪: {untracked_count}")

        if conflicted:
            lines.append(f"  ⚠️ 冲突 ({len(conflicted)}):")
            for p in conflicted[:10]:
                lines.append(f"    ⚠️  {p}")

        if staged:
            lines.append(f"  📦 暂存 ({len(staged)}):")
            for p in staged[:10]:
                lines.append(f"    📦  {p}")

        if unstaged:
            lines.append(f"  ✏️  未暂存 ({len(staged)}):")
            for p in unstaged[:10]:
                lines.append(f"    ✏️  {p}")

        if untracked_count > 0:
            lines.append(f"  ❔ 未跟踪 ({untracked_count}):")
            for line_ut in untracked.strip().split('\n')[:10]:
                if line_ut.strip():
                    lines.append(f"    ❔  {line_ut.strip()}")

    return "\n".join(lines)


# ============================================================
# tool_git_log — 查看 Git 提交历史
# ============================================================

def tool_git_log(
    directory: str = ".",
    count: int = 10,
    branch: str = "",
    author: str = "",
) -> str:
    """查看 Git 提交历史

    Args:
        directory: 仓库目录
        count: 显示的提交数
        branch: 分支名
        author: 作者过滤

    Returns:
        提交历史
    """
    if not _is_git_repo(directory):
        return "❌ 当前目录不是 git 仓库"

    args = ["log", f"--max-count={count}", "--format=%H|%an|%ar|%s"]
    if branch:
        args.extend([branch])
    if author:
        args.extend([f"--author={author}"])

    log_text = _run_git(args, directory)
    if log_text.startswith("❌") or log_text.startswith("fatal"):
        return f"❌ 获取日志失败: {log_text[:200]}"

    repo_name = os.path.basename(os.path.abspath(directory))
    lines = [
        f"📋 Git 提交历史: {repo_name}",
        f"   最近 {count} 条提交",
        "─" * 50,
    ]

    commits = [c for c in log_text.strip().split('\n') if c.strip()]
    for i, commit in enumerate(commits, 1):
        parts = commit.split('|', 3)
        if len(parts) >= 4:
            sha, author_rel, time_rel, subject = parts[0], parts[1], parts[2], parts[3]
            short_sha = sha[:8]
            lines.append(f"  {i:>2}. {short_sha}  {subject}")
            lines.append(f"      {author_rel}  ({time_rel})")
        elif len(parts) >= 1:
            lines.append(f"  {i:>2}. {parts[0][:8]}")

    return "\n".join(lines)


# ============================================================
# tool_git_diff — 查看变更差异
# ============================================================

def tool_git_diff(
    directory: str = ".",
    staged: bool = False,
    path: str = "",
    max_lines: int = 80,
) -> str:
    """查看 Git 工作区变更差异

    Args:
        directory: 仓库目录
        staged: 是否查看暂存区差异
        path: 指定文件路径
        max_lines: 最大显示行数

    Returns:
        差异内容
    """
    if not _is_git_repo(directory):
        return "❌ 当前目录不是 git 仓库"

    args = ["diff"]
    if staged:
        args.append("--cached")

    if path:
        args.append("--")
        args.append(path)

    diff_text = _run_git(args, directory)

    if diff_text.startswith("❌") or diff_text.startswith("fatal"):
        return f"❌ 获取差异失败: {diff_text[:200]}"

    if not diff_text.strip():
        return "✅ 无变更差异"

    # 统计
    added = 0
    removed = 0
    for line in diff_text.split('\n'):
        if line.startswith('+') and not line.startswith('+++'):
            added += 1
        elif line.startswith('-') and not line.startswith('---'):
            removed += 1

    # 截断
    lines = diff_text.split('\n')
    if len(lines) > max_lines:
        lines = lines[:max_lines] + [f"...（输出过长，已截断至 {max_lines} 行，共 {len(lines)} 行）"]

    result = [
        f"📋 {'暂存区' if staged else '工作区'}差异:",
        f"   📊 +{added} / -{removed} 行变化",
    ]

    # 只显示文件概要
    file_changes = {}
    for line in diff_text.split('\n'):
        if line.startswith('diff --git'):
            parts = line.split()
            if len(parts) >= 3:
                fname = parts[2].replace('a/', '', 1)
                file_changes[fname] = {'added': 0, 'removed': 0}

    staging = None
    for line in diff_text.split('\n'):
        if line.startswith('---') or line.startswith('+++'):
            continue
        if line.startswith('@@'):
            staging = None
            continue
        if line.startswith('+'):
            added += 1
        elif line.startswith('-'):
            removed += 1

    result.append("─" * 50)

    # 显示文件列表
    for fname in list(file_changes.keys())[:20]:
        result.append(f"  {fname}")

    result.append("")
    result.append("💡 查看具体差异请使用 path 参数指定文件")

    return "\n".join(result)


# ============================================================
# tool_git_commit_stats — 统计贡献
# ============================================================

def tool_git_commit_stats(
    directory: str = ".",
    days: int = 30,
    top_n: int = 5,
) -> str:
    """统计 Git 提交贡献

    Args:
        directory: 仓库目录
        days: 统计最近 N 天
        top_n: 显示前 N 名贡献者

    Returns:
        贡献统计
    """
    if not _is_git_repo(directory):
        return "❌ 当前目录不是 git 仓库"

    repo_name = os.path.basename(os.path.abspath(directory))
    since = f"{days}.days.ago"

    # 获取提交统计 per author
    shortlog = _run_git(
        ["shortlog", "-sne", f"--since={since}"],
        directory
    )

    if shortlog.startswith("❌") or shortlog.startswith("fatal"):
        return f"❌ 获取统计失败: {shortlog[:200]}"

    # 解析
    author_stats = []
    for line in shortlog.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        # 格式: "  42  Author Name <email>"
        parts = line.split('\t', 1)
        if len(parts) >= 2:
            try:
                count = int(parts[0].strip())
                author = parts[1].strip()
                author_stats.append((count, author))
            except ValueError:
                pass

    # 总提交数
    total_commits = _run_git(["rev-list", "--count", f"--since={since}", "HEAD"], directory)
    total = total_commits.strip()

    lines = [
        f"📊 Git 贡献统计: {repo_name}",
        f"   最近 {days} 天",
        f"   总提交: {total}",
        "─" * 50,
    ]

    for i, (count, author) in enumerate(author_stats[:top_n], 1):
        pct = f"{count/int(total)*100:.1f}%" if total and int(total) > 0 else "0%"
        bar = "█" * min(count, 40)
        lines.append(f"  {i}. {bar} {count} ({pct})")
        lines.append(f"     {author}")

    if len(author_stats) > top_n:
        lines.append(f"  ... 还有 {len(author_stats) - top_n} 位贡献者")

    return "\n".join(lines)


# ============================================================
# tool_show_file — 显示文件内容（带行号）
# ============================================================

def tool_show_file(
    path: str = "",
    start_line: int = 1,
    line_count: int = 50,
) -> str:
    """显示文件内容（带行号，支持从指定行开始）

    Args:
        path: 文件路径
        start_line: 起始行号（从 1 开始）
        line_count: 显示行数

    Returns:
        带行号的文件内容
    """
    if not path:
        return "❌ 文件路径不能为空"

    if not os.path.isfile(path):
        return f"❌ 文件不存在: {path}"

    if _is_binary(path):
        return f"❌ 不支持二进制文件: {path}"

    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            all_lines = f.readlines()
    except Exception as e:
        return f"❌ 读取文件失败: {e}"

    total = len(all_lines)
    start = max(0, start_line - 1)
    end = min(total, start + line_count)

    selected = all_lines[start:end]

    # 行号的宽度
    num_width = len(str(end))

    result = [
        f"📄 {path}  (共 {total} 行，显示 {start+1}-{end})",
        "─" * 60,
    ]

    for i, line in enumerate(selected, start + 1):
        text = line.rstrip('\n').rstrip('\r')
        result.append(f"  {i:>{num_width}} │ {text}")

    if total > end:
        result.append(f"  ... 还有 {total - end} 行未显示（使用 start_line={end+1} 查看更多）")

    return "\n".join(result)
