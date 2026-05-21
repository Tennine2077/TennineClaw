# ============================================================
# 高危命令检测与安全防护
# ============================================================
# 提供命令安全性检测功能，防止系统遭受破坏性操作。
# 包含高危命令拦截和警告机制。
# 高危命令不再直接拦截，而是要求用户确认后放行。
# ============================================================

import re

# -----------------------------------------------------------
# 高危命令模式（Windows 环境）
# 匹配到的命令将被阻止执行（除非用户确认）
# -----------------------------------------------------------
HIGH_RISK_PATTERNS = [
    # 删除/格式化类
    r'\brm\s+-[rf]+\s+/',           # Linux 递归删除根目录
    r'\brm\s+-[rf]+\s+.*[/\\]',      # Linux 递归删除关键路径
    r'\bdel\s+/[fsq].*[/\\]',         # Windows 强制删除目录
    r'\brd\s+/[sq].*[/\\]',           # Windows 递归删除目录
    r'\bformat\s',                    # 格式化
    r'\bmkfs\b',                      # 创建文件系统
    r'\bdd\b.*\bof=',                 # dd 写入
    r'\bfdisk\b',                     # 分区工具
    r'\bmbr2gpt\b',                   # 磁盘转换
    r'\bdiskpart\b',                  # 磁盘分区（交互式危险）
    r'\bclean\s+all\b',               # 磁盘清理全部
    r'\bremove-item\b.*-recurse',     # PowerShell 递归删除
    # 系统破坏类
    r'\bshutdown\s+/[rh]',           # 关机/重启
    r'\bshutdown\s+-[hr]',            # Linux 关机/重启
    r'\binit\s+0\b',                  # Linux 关机
    r'\bpoweroff\b',                  # Linux 关机
    r'\breboot\b',                    # Linux 重启
    r'\bhalt\b',                      # Linux 停机
    # 权限/安全类
    r'\bchmod\s+777\b',               # 赋予所有权限
    r'\bchown\s',                     # 改变所有者（高危滥用）
    r'\bsudo\s+.*rm\b',               # sudo 删除
    r'\bsudo\s+.*shutdown\b',         # sudo 关机
    r'\bsudo\s+.*dd\b',               # sudo dd
    r'\bsudo\s+.*mkfs\b',             # sudo 格式化
    r'\bpasswd\b',                    # 修改密码
    r'\buseradd\b',                   # 添加用户
    r'\buserdel\b',                   # 删除用户
    r'\bnet\s+user\b',                # Windows 用户管理
    r'\breg\s+delete\b',              # 注册表删除
    r'\breg\s+add\b',                 # 注册表添加（危险）
    # 网络攻击类
    r'\bnmap\b',                      # 端口扫描
    r'\bhydra\b',                     # 暴力破解
    r'\bmetasploit\b',                # 渗透工具
    r'\bmsfvenom\b',                  # payload 生成
    r'\bsqlmap\b',                    # SQL 注入
    r'\bburpsuite\b',                 # Web 渗透
    r'\baircrack',                    # WiFi 破解
    r'\breverse\s*shell\b',           # 反弹 shell
    r'\bbind\s*shell\b',              # 绑定 shell
    # 其他危险
    r'\bwget\s+.*\|\s*bash\b',        # 管道执行远程脚本
    r'\bcurl\s+.*\|\s*bash\b',        # 管道执行远程脚本
    r'\b(rm|del|erase)\s+--?no-preserve-root\b',  # 强制删除根
    r'[`$]\(.*rm\b',                  # 命令注入删除
    r'>\s*/dev/sda',                  # 直接写入磁盘设备
    r'>\s*/dev/hda',                  # 直接写入磁盘设备
    r'>\s*\\\\.\\[A-Z]:',             # Windows 直接写入物理磁盘
]

# -----------------------------------------------------------
# 安全但需要确认的命令
# -----------------------------------------------------------
WARN_PATTERNS = [
    r'\btaskkill\b',                  # 结束进程
    r'\bkill\b',                      # Linux 结束进程
    r'\bnet\s+stop\b',                # 停止服务
    r'\bsc\s+delete\b',               # 删除服务
    r'\bwmic\b',                      # WMI 操作
    r'\bvssadmin\b',                  # 卷影复制（勒索软件常用）
]


def check_command_safety(cmd: str) -> dict:
    """检测命令安全性

    返回字段说明：
        - safe: bool          — False 表示需要用户确认或已拦截
        - reason: str         — 提示信息
        - warn: bool          — True 表示是警告级命令（非高危）
        - requires_confirmation: bool — True 表示需要用户确认才能放行

    返回值示例：
        {"safe": True, "warn": False, "reason": "", "requires_confirmation": False}
        {"safe": False, "warn": False, "reason": "...", "requires_confirmation": True}
        {"safe": True, "warn": True, "reason": "...", "requires_confirmation": False}
    """
    cmd_lower = cmd.lower().strip()

    # 检查高危命令 — 需要用户确认
    for pattern in HIGH_RISK_PATTERNS:
        if re.search(pattern, cmd_lower, re.IGNORECASE):
            return {
                "safe": False,
                "reason": (
                    f"⛔ 检测到高危操作！匹配规则: `{pattern}`\n"
                    f"   命令: `{cmd[:200]}`\n"
                    f"   该操作可能对系统造成严重破坏。\n"
                    f"   🔐 如确认要执行，请使用 run_cmd(cmd=..., confirm=True) 放行。"
                ),
                "requires_confirmation": True,
                "warn": False
            }

    # 检查需要警告的命令 — 自动放行，但提示用户
    for pattern in WARN_PATTERNS:
        if re.search(pattern, cmd_lower, re.IGNORECASE):
            return {
                "safe": True,
                "warn": True,
                "reason": f"⚠️ 警告：该命令 (`{cmd[:150]}`) 可能影响系统运行，已自动放行。",
                "requires_confirmation": False
            }

    return {
        "safe": True,
        "warn": False,
        "reason": "",
        "requires_confirmation": False
    }
