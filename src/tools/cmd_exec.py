# ============================================================
# TennineClaw - 系统命令执行工具
# ============================================================
# 提供带安全检测的系统命令执行功能
# 高危命令会要求用户确认后方可执行
# ============================================================

import subprocess
import platform
import locale
import os as _os

from ..safety import check_command_safety


def _decode_output(data: bytes) -> str:
    """智能解码子进程输出，自动适配系统编码

    解码策略（按优先级）：
    1. 先尝试 UTF-8 解码（chcp 65001 模式下输出为 UTF-8）
    2. 失败后回退到系统编码（如 GBK/cp936，普通模式下输出为 GBK）
    3. 最终兜底：忽略无法解码的字节

    这样无论 chcp 是否生效，都能正确解码中文和 emoji 字符。
    """
    if not data:
        return ""

    # 1. 优先尝试 UTF-8（chcp 65001 模式）
    try:
        return data.decode('utf-8')
    except UnicodeDecodeError:
        pass

    # 2. 回退到系统编码（如 GBK）
    try:
        system_encoding = locale.getpreferredencoding()
        return data.decode(system_encoding, errors='replace')
    except (LookupError, UnicodeDecodeError):
        pass

    # 3. 终极兜底：UTF-8 忽略错误
    return data.decode('utf-8', errors='ignore')


def _build_env() -> dict:
    """构建子进程环境变量，确保 UTF-8 编码兼容"""
    env = _os.environ.copy()
    # 设置 PYTHONIOENCODING 确保 Python 子进程的 stdout/stderr 使用 UTF-8
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def tool_run_cmd(cmd: str = "", confirm: bool = False) -> str:
    """执行系统命令（带安全检测 + 用户确认）

    通过安全检查模块检测命令安全性后，在系统 shell 中执行。
    - 高危命令需要用户设置 confirm=True 才能放行
    - 警告级命令自动放行，仅提示
    - 安全命令直接执行

    Args:
        cmd: 要执行的系统命令
        confirm: 是否确认高危操作（设为 True 表示用户已确认风险）

    Returns:
        命令的标准输出；或确认提示信息；或错误信息
    """
    if not cmd:
        return "错误：命令不能为空"

    # ---- 安全检查 ----
    safety = check_command_safety(cmd)

    # 高危命令：直接拦截，不再要求用户确认
    if not safety["safe"] and safety.get("requires_confirmation"):
        return "当前指令安全性不通过，请尝试其他方法"

    # 其他不安全的场景（非 requires_confirmation 的 safe=False——预留）
    if not safety["safe"]:
        return safety["reason"]

    # 警告级命令：直接拦截，不再自动放行执行
    if safety.get("warn"):
        return "当前指令安全性不通过，请尝试其他方法"

    # ---- 执行命令 ----
    try:
        # Windows 下设置 UTF-8 代码页，确保中文正常输出
        safe_cmd = f"chcp 65001 >nul 2>&1 && {cmd}" if platform.system() == "Windows" else cmd

        # 构建 UTF-8 友好的环境变量
        env = _build_env()

        # 使用 bytes 模式捕获输出，避免 text=True 时的编码问题
        proc = subprocess.run(
            safe_cmd, shell=True, capture_output=True,
            timeout=30, env=env
        )

        # 智能解码 stdout 和 stderr
        stdout_str = _decode_output(proc.stdout)
        stderr_str = _decode_output(proc.stderr)

        if proc.returncode == 0:
            output = stdout_str
            if not output.strip():
                return "命令执行成功（无输出）"
            if len(output) > 100000:
                output = output[:100000] + "\n\n...（输出过长，已截断）"
            return output
        else:
            error_msg = stderr_str.strip() if stderr_str.strip() else f"命令执行失败（返回码: {proc.returncode}）"
            if len(error_msg) > 2000:
                error_msg = error_msg[:2000] + "\n...（错误信息过长，已截断）"
            return f"命令执行失败\n{error_msg}"
    except subprocess.TimeoutExpired:
        return "命令执行超时（超过 30 秒）"
    except Exception as e:
        return f"异常: {e}"
