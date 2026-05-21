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

    # 高危命令：需要用户确认
    if not safety["safe"] and safety.get("requires_confirmation"):
        if confirm:
            # 用户已确认，跳过安全检查直接执行
            pass
        else:
            # 返回确认提示，等待用户确认
            return (
                f"{safety['reason']}\n\n"
                f"🔐 **需要确认**\n"
                f"请在对话框中输入 `CONFIRM_RISK` 确认执行该命令，"
                f"或输入 `CANCEL` 取消操作。\n"
                f"确认后 AI 将使用 `run_cmd(cmd=..., confirm=True)` 执行。"
            )

    # 其他不安全的场景（非 requires_confirmation 的 safe=False——预留）
    if not safety["safe"]:
        return safety["reason"]

    # 警告级命令：自动放行，打印提示
    if safety.get("warn"):
        print(f"\n⚠️ {safety['reason']}")
        print("   🔄 已自动放行（可继续执行）")

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
            if len(output) > 10000:
                output = output[:10000] + f"\n\n...（输出过长，已截断至 10000 字符，共 {len(output)} 字符）"
            return output
        else:
            error_msg = proc.stderr.strip() if proc.stderr.strip() else "未知错误"
            return f"❌ 命令执行失败 (返回码: {proc.returncode})\n错误信息: {error_msg[:2000]}"
    except subprocess.TimeoutExpired:
        return "⚠️ 命令执行超时（30秒），已自动终止"
    except Exception as e:
        return f"异常: {e}"


# ============================================================
# dict 参数包装器
# ============================================================
def tool_run_cmd_compat(args: dict = None) -> str:
    """接受 dict 参数调用 tool_run_cmd

    （tool_run_cmd_compat({"cmd": "..."})），
    内部转换为具名参数调用标准接口。

    Args:
        args: 包含 "cmd" 键的参数字典

    Returns:
        与 tool_run_cmd 相同
    """
    if args is None:
        args = {}
    return tool_run_cmd(
        cmd=args.get("cmd", ""),
        confirm=args.get("confirm", False)
    )
