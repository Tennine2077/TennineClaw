# ============================================================
# TennineClaw - 系统信息查询工具
# ============================================================
# 包含：获取系统信息、获取当前时间
# ============================================================

import platform
import os
import locale
import datetime


def tool_get_system_info() -> str:
    """获取系统基本信息

    返回操作系统、Python 版本、CPU 核心数、当前用户、
    工作目录和系统编码等环境信息。

    Returns:
        格式化的系统信息文本
    """
    try:
        info = []
        info.append(f"🖥️  操作系统：{platform.system()} {platform.release()}")
        info.append(f"📌 版本：{platform.version()}")
        info.append(f"🏗️  架构：{platform.machine()}")
        info.append(f"👤 用户：{os.environ.get('USERNAME', os.environ.get('USER', 'unknown'))}")
        info.append(f"📁 当前目录：{os.getcwd()}")
        info.append(f"🕐 当前时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        info.append(f"🌐 系统编码：{locale.getpreferredencoding()}")
        info.append(f"🐍 Python 版本：{platform.python_version()}")
        try:
            cpu_count = os.cpu_count() or 0
            info.append(f"⚙️  CPU 核心数：{cpu_count}")
        except Exception:
            pass
        return "\n".join(info)
    except Exception as e:
        return f"异常：{e}"


def tool_get_current_time() -> str:
    """获取当前日期和时间（含星期）

    Returns:
        格式化的当前时间，包含年-月-日 时:分:秒 和星期几
    """
    now = datetime.datetime.now()
    cal = now.strftime("%Y-%m-%d %H:%M:%S")
    weekday = now.strftime("%A")
    weekdays_cn = {
        "Monday": "星期一", "Tuesday": "星期二", "Wednesday": "星期三",
        "Thursday": "星期四", "Friday": "星期五", "Saturday": "星期六",
        "Sunday": "星期日"
    }
    weekday_cn = weekdays_cn.get(weekday, weekday)
    return f"🕐 当前时间：{cal}\n📅 星期：{weekday_cn}"
