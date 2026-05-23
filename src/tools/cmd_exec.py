# ============================================================
# TennineClaw - 系统命令执行工具
# ============================================================
# 提供带安全检测的系统命令执行功能
# 高危命令会要求用户确认后方可执行
# ============================================================

import subprocess
import platform

from ..safety import check_command_safety


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

    # 【修改】高危命令：直接拦截，不再要求用户确认
    if not safety["safe"] and safety.get("requires_confirmation"):
        return "当前指令安全性不通过，请尝试其他方法"

    # 其他不安全的场景（非 requires_confirmation 的 safe=False——预留）
    if not safety["safe"]:
        return safety["reason"]

    # 【修改】警告级命令：直接拦截，不再自动放行执行
    if safety.get("warn"):
        return "当前指令安全性不通过，请尝试其他方法"

    # ---- 执行命令 ----
    try:
        safe_cmd = f"chcp 65001 >nul 2>&1 && {cmd}" if platform.system() == "Windows" else cmd
        proc = subprocess.run(
            safe_cmd, shell=True, capture_output=True, text=True,
            encoding='utf-8', errors='replace', timeout=30
        )
        if proc.returncode == 0:
            output = proc.stdout
            if not output.strip():
                return "✅ 命令执行成功（无输出）"
            if len(output) > 100000:
                output = output[:100000] + "\n\n...（输出过长，已截断）"
            return output
        else:
            error_msg = proc.stderr.strip() if proc.stderr.strip() else f"命令执行失败（返回码: {proc.returncode}）"
            if len(error_msg) > 2000:
                error_msg = error_msg[:2000] + "\n...（错误信息过长，已截断）"
            return f"❌ 命令执行失败\n{error_msg}"
    except subprocess.TimeoutExpired:
        return "❌ 命令执行超时（超过 30 秒）"
    except Exception as e:
        return f"❌ 命令执行异常: {e}"


# ============================================================
# dict 参数兼容包装
# ============================================================
def tool_run_cmd_compat(args: dict = None) -> str:
    """通过 dict 参数调用 tool_run_cmd

    使用 tool_run_cmd_compat({"cmd": "..."}) 调用，
    内部转换为关键字参数调用标准接口。

    Args:
        args: 包含 "cmd" 等参数的字典

    Returns:
        同 tool_run_cmd
    """
    if args is None:
        args = {}
    return tool_run_cmd(
        cmd=args.get("cmd", ""),
        confirm=args.get("confirm", False)
    )
