# ============================================================
# 运行模式管理器
# ============================================================
# 管理两种运行模式：
#   1️⃣ 智能处理模式 — 直接执行任务
#   2️⃣ Plan驱动模式 — 先写 plan.md，显示选择菜单供用户决策
#      用户通过 ↑↓ 选择：继续探索 / 修改计划 / 切换 Smart 执行
# ============================================================

import os
import datetime
from config import MODE_SMART, MODE_PLAN, MODE_NAMES, PLAN_FILE


class ModeManager:
    """运行模式管理器"""

    def __init__(self, mode: int = MODE_SMART):
        self.mode = mode
        self.plan_phase = "idle"  # idle | planning | executing | done
        self._plan_menu_shown = False

    def get_mode(self) -> int:
        return self.mode

    def set_mode(self, mode: int) -> bool:
        """切换模式"""
        if mode in (MODE_SMART, MODE_PLAN):
            self.mode = mode
            if mode == MODE_SMART:
                self.plan_phase = "idle"
                self._plan_menu_shown = False
            elif mode == MODE_PLAN:
                self.plan_phase = "planning"
                self._plan_menu_shown = False
            return True
        return False

    def get_mode_name(self) -> str:
        return MODE_NAMES.get(self.mode, "未知模式")

    def is_smart_mode(self) -> bool:
        return self.mode == MODE_SMART

    def is_plan_mode(self) -> bool:
        return self.mode == MODE_PLAN

    def get_plan_phase(self) -> str:
        return self.plan_phase

    def set_plan_phase(self, phase: str):
        self.plan_phase = phase
        if phase == "idle" or phase == "done":
            self._plan_menu_shown = False

    def is_plan_menu_shown(self) -> bool:
        return self._plan_menu_shown

    def set_plan_menu_shown(self, shown: bool = True):
        self._plan_menu_shown = shown

    def check_plan_file_exists(self) -> bool:
        return os.path.exists(PLAN_FILE)

    # ── 仅检查 Plan 是否已就绪（不检查 _plan_menu_shown） ──
    def is_plan_ready(self) -> bool:
        """判断 Plan 是否已就绪（plan.md 已存在且处于 planning 阶段）
        与 should_show_plan_menu() 不同，此方法不检查 _plan_menu_shown，
        专门用于 UI 层独立控制菜单显示
        """
        return (
            self.is_plan_mode()
            and self.plan_phase == "planning"
            and self.check_plan_file_exists()
        )

    def should_show_plan_menu(self) -> bool:
        """判断是否应该显示 Plan 菜单（业务逻辑层使用）

        UI 层请优先使用 is_plan_ready() + 独立控制。

        Returns:
            如果满足显示条件且菜单尚未展示，返回 True
        """
        return (
            self.is_plan_mode()
            and self.plan_phase == "planning"
            and self.check_plan_file_exists()
            and not self._plan_menu_shown
        )

    def get_mode_description(self) -> str:
        descriptions = {
            MODE_SMART: (
                "🧠 **智能处理模式**\n"
                "   - 直接执行用户请求，无需额外步骤\n"
                "   - 具备完整的 Prompt 优化、工具调用功能\n"
                "   - 适合日常快速交互"
            ),
            MODE_PLAN: (
                "📋 **Plan驱动模式**\n"
                "   - 收到请求后，先生成 `plan.md` 行动计划\n"
                "   - 然后显示选择菜单（↑↓选择，Enter确认）：\n"
                "     1️⃣ 继续探索 — 继续对话讨论\n"
                "     2️⃣ 修改计划 — 修改 plan.md\n"
                "     3️⃣ 切换Smart执行 — 自动切 /smart 并执行"
            ),
        }
        return descriptions.get(self.mode, "未知模式")

