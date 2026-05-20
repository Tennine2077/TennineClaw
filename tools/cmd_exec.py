# ============================================================
# TennineClaw - 系统命令执行工具
# ============================================================
# 提供带安全检测的系统命令执行功能
# ============================================================

import subprocess
import platform

from safety import check_command_safety


def tool_run_cmd(cmd: str = "") -> str:
    """执行系统命令（带安全检测）

    通过安全检查模块检测命令安全性后，在系统 shell 中执行。
    自动处理平台差异（Windows 编码转换）和超时控制。

    Args:
        cmd: 要执行的系统命令

    Returns:
        命令的标准输出；命令执行成功但无输出时返回成功提示；
        执行失败时返回错误信息
    """
    if not cmd:
        return "错误：命令不能为空"

    safety = check_command_safety(cmd)
    if not safety["safe"]:
        return safety["reason"]

    if safety.get("warn"):
        print(f"\n⚠️ {safety['reason']}")
        print("   🔄 已自动放行（可继续执行）")

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
        命令执行结果
    """
    if args is None:
        args = {}
    return tool_run_cmd(cmd=args.get("cmd", ""))





