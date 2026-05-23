# ============================================================
# TennineClaw - 技能引擎（SkillEngine）
# ============================================================
# 管理技能注册、学习、经验积累、升级、技能树操作等核心逻辑。
# 支持技能持久化存储与跨会话恢复。
# ============================================================

from __future__ import annotations
import os
import json
import logging
from typing import Optional, List, Dict, Any, Set
from datetime import datetime

from .skill_models import (
    SkillDefinition, SkillType, SkillTier, SkillTree, SkillCombo,
    SkillProficiency, TriggerEvent, calculate_xp_reward,
    xp_for_level,
)

logger = logging.getLogger(__name__)

# ============================================================
# 默认技能存储路径
# ============================================================
DEFAULT_SKILL_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "sessions", "skills"
)


class SkillEngine:
    """技能引擎 — 核心控制器"""

    def __init__(self, skill_tree: Optional[SkillTree] = None,
                 save_dir: str = None):
        self.skill_tree = skill_tree or SkillTree()
        self.save_dir = save_dir or DEFAULT_SKILL_DIR
        self._active_skill_ids: Set[str] = set()
        self._owned_skill_ids: Set[str] = set()
        self._combo_cooldowns: Dict[str, int] = {}
        self._current_round: int = 0

        # 确保保存目录存在
        os.makedirs(self.save_dir, exist_ok=True)
        # 同步已有技能树中的无前置技能到拥有列表
        for sk_id, sk in self.skill_tree.skills.items():
            if sk_id not in self._owned_skill_ids and not sk.prerequisites:
                self._owned_skill_ids.add(sk_id)
                self._active_skill_ids.add(sk_id)


    # ── 技能注册与管理 ──

    def register_skill(self, skill: SkillDefinition) -> bool:
        """注册新技能到技能树"""
        if skill.id in self.skill_tree.skills:
            logger.warning(f"技能 {skill.id} 已存在，跳过注册")
            return False
        self.skill_tree.add_skill(skill)
        # 如果技能没有前置条件，自动拥有
        if not skill.prerequisites:
            self._owned_skill_ids.add(skill.id)
            self._active_skill_ids.add(skill.id)
        return True

    def unregister_skill(self, skill_id: str) -> bool:
        """注销技能"""
        result = self.skill_tree.remove_skill(skill_id)
        if result:
            self._owned_skill_ids.discard(skill_id)
            self._active_skill_ids.discard(skill_id)
        return result

    def learn_skill(self, skill_id: str) -> bool:
        """学习/解锁新技能

        检查前置条件是否满足，满足则解锁。
        """
        if skill_id in self._owned_skill_ids:
            logger.info(f"技能 {skill_id} 已拥有")
            return True

        if not self.skill_tree.can_unlock(skill_id, self._owned_skill_ids):
            skill = self.skill_tree.get_skill(skill_id)
            prereq_names = []
            if skill:
                prereq_names = [
                    self.skill_tree.skills.get(pid, SkillDefinition()).name
                    for pid in skill.prerequisites
                ]
            logger.warning(
                f"无法解锁技能 {skill_id}，前置条件未满足: {prereq_names}"
            )
            return False

        self._owned_skill_ids.add(skill_id)
        self._active_skill_ids.add(skill_id)
        logger.info(f"🎉 解锁新技能: {skill_id}")
        return True

    def activate_skill(self, skill_id: str) -> bool:
        """激活技能"""
        if skill_id in self._owned_skill_ids:
            self._active_skill_ids.add(skill_id)
            return True
        return False

    def deactivate_skill(self, skill_id: str) -> bool:
        """停用技能"""
        self._active_skill_ids.discard(skill_id)
        return True

    def is_skill_active(self, skill_id: str) -> bool:
        """检查技能是否激活"""
        return skill_id in self._active_skill_ids

    # ── 经验与等级 ──

    def gain_experience(self, skill_id: str, amount: int) -> Dict[str, Any]:
        """为指定技能增加经验值

        Returns:
            包含是否升级等信息的字典
        """
        result = {"skill_id": skill_id, "leveled_up": False, "new_level": 1}

        skill = self.skill_tree.get_skill(skill_id)
        if not skill:
            logger.warning(f"技能 {skill_id} 不存在")
            return result

        leveled_up = skill.gain_xp(amount)
        result["leveled_up"] = leveled_up
        result["new_level"] = skill.level

        if leveled_up:
            logger.info(
                f"⭐ 技能升级: {skill.name} → Lv.{skill.level} "
                f"(经验: {skill.xp}/{skill.xp_to_next})"
            )

        # 升级时自动检查可解锁的新技能树分支
        if leveled_up:
            self._check_unlockable_skills()

        return result

    def gain_experience_for_tool(self, tool_name: str, success: bool = True,
                                 task_difficulty: float = 1.0) -> List[Dict[str, Any]]:
        """为关联指定工具的所有技能增加经验值

        查找所有关联到该工具的活跃技能，为它们增加经验。
        """
        results = []
        xp_reward = calculate_xp_reward(
            task_difficulty=task_difficulty,
            success=success,
        )

        for skill_id in self._active_skill_ids:
            skill = self.skill_tree.get_skill(skill_id)
            if skill and tool_name in skill.proficiency.related_tools:
                # 记录使用信息
                skill.proficiency.record_use(success=success)
                skill.tick_cooldown()
                # 增加经验
                result = self.gain_experience(skill_id, xp_reward)
                results.append(result)

        return results

    # ── 技能查询 ──

    def get_available_skills(self) -> List[SkillDefinition]:
        """获取当前活跃且可用的技能列表"""
        available = []
        for skill_id in self._active_skill_ids:
            skill = self.skill_tree.get_skill(skill_id)
            if skill and skill.can_use():
                available.append(skill)
        return available

    def get_skills_by_type(self, skill_type: SkillType) -> List[SkillDefinition]:
        """按类型获取技能"""
        return [
            s for s in self.skill_tree.skills.values()
            if s.type == skill_type and s.id in self._active_skill_ids
        ]

    def get_skills_by_trigger(self, event: TriggerEvent) -> List[SkillDefinition]:
        """按触发事件获取技能"""
        return [
            s for s in self.skill_tree.skills.values()
            if s.trigger_event == event and s.id in self._active_skill_ids
        ]

    def get_unlockable_skills(self) -> List[SkillDefinition]:
        """获取当前可解锁的技能"""
        return self.skill_tree.get_unlockable_skills(self._owned_skill_ids)

    def get_skill_stats(self) -> Dict[str, Any]:
        """获取技能系统统计信息"""
        total = len(self.skill_tree.skills)
        owned = len(self._owned_skill_ids)
        active = len(self._active_skill_ids)
        level_sum = sum(
            self.skill_tree.skills[sid].level
            for sid in self._owned_skill_ids
            if sid in self.skill_tree.skills
        )
        return {
            "total_skills": total,
            "owned_skills": owned,
            "active_skills": active,
            "total_levels": level_sum,
            "avg_level": round(level_sum / max(owned, 1), 1),
            "current_round": self._current_round,
            "available_combos": len(self.get_available_combos()),
        }

    # ── 技能组合 ──

    def register_combo(self, combo: SkillCombo) -> bool:
        """注册技能组合"""
        if combo.id in self.skill_tree.combos:
            return False
        self.skill_tree.combos[combo.id] = combo
        return True

    def get_available_combos(self) -> List[SkillCombo]:
        """获取当前可用的技能组合"""
        return self.skill_tree.get_available_combos(self._active_skill_ids)

    def trigger_combo(self, combo_id: str) -> Optional[Dict[str, Any]]:
        """触发技能组合效果"""
        combo = self.skill_tree.combos.get(combo_id)
        if not combo:
            return None

        # 检查冷却
        if combo_id in self._combo_cooldowns and self._combo_cooldowns[combo_id] > 0:
            return None

        # 检查所需技能是否激活
        for skill_id in combo.required_skills:
            if skill_id not in self._active_skill_ids:
                return None
            skill = self.skill_tree.get_skill(skill_id)
            if skill and combo.min_levels.get(skill_id, 0) > skill.level:
                return None

        # 发放组合经验奖励
        for skill_id in combo.required_skills:
            self.gain_experience(skill_id, 50)

        # 设置组合冷却
        if combo.cooldown_rounds > 0:
            self._combo_cooldowns[combo_id] = combo.cooldown_rounds

        return {
            "combo_id": combo.id,
            "combo_name": combo.name,
            "bonus": combo.combo_bonus,
        }

    # ── 轮次管理 ──

    def new_round(self):
        """进入新的一轮对话"""
        self._current_round += 1
        # 所有技能冷却减一
        for skill in self.skill_tree.skills.values():
            skill.tick_cooldown()
        # 组合冷却减一
        for combo_id in list(self._combo_cooldowns.keys()):
            self._combo_cooldowns[combo_id] -= 1
            if self._combo_cooldowns[combo_id] <= 0:
                del self._combo_cooldowns[combo_id]

    # ── 内部方法 ──

    def _check_unlockable_skills(self):
        """检查是否有新的可解锁技能"""
        unlockable = self.get_unlockable_skills()
        # 自动解锁没有前置条件的技能（不应该发生，但兜底）
        for skill in unlockable:
            if not skill.prerequisites:
                self.learn_skill(skill.id)

    # ── 持久化 ──

    def save(self, filepath: str = None) -> str:
        """保存技能引擎状态到 JSON 文件"""
        if filepath is None:
            filepath = os.path.join(self.save_dir, "skill_engine.json")

        data = {
            "version": "1.0.0",
            "saved_at": datetime.now().isoformat(),
            "current_round": self._current_round,
            "active_skill_ids": list(self._active_skill_ids),
            "owned_skill_ids": list(self._owned_skill_ids),
            "skill_tree": self.skill_tree.to_dict(),
            "combo_cooldowns": self._combo_cooldowns,
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"💾 技能引擎已保存: {filepath}")
        return filepath

    def load(self, filepath: str = None) -> bool:
        """从 JSON 文件加载技能引擎状态"""
        if filepath is None:
            filepath = os.path.join(self.save_dir, "skill_engine.json")

        if not os.path.exists(filepath):
            logger.warning(f"技能引擎存档不存在: {filepath}")
            return False

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            self._current_round = data.get("current_round", 0)
            self._active_skill_ids = set(data.get("active_skill_ids", []))
            self._owned_skill_ids = set(data.get("owned_skill_ids", []))
            self._combo_cooldowns = data.get("combo_cooldowns", {})
            self.skill_tree = SkillTree.from_dict(data.get("skill_tree", {}))

            logger.info(f"📂 技能引擎已加载: {filepath}")
            return True

        except Exception as e:
            logger.error(f"加载技能引擎失败: {e}")
            return False


# ============================================================
# 快捷函数
# ============================================================

def create_default_skills() -> SkillTree:
    """创建默认技能树（预置基础技能）"""
    tree = SkillTree(name="TennineClaw 默认技能树")

    # 1. 文件搜索大师
    search_skill = SkillDefinition(
        name="文件搜索大师",
        description="精通文件搜索与内容检索，快速定位目标文件",
        type=SkillType.ACTIVE,
        tier=SkillTier.BASIC,
        cooldown_rounds=0,
        trigger_event=TriggerEvent.ON_USER_MESSAGE,
        proficiency=SkillProficiency(related_tools=["search_files", "grep", "find_files"]),
        tags=["文件", "搜索"],
        icon="🔍",
    )
    tree.add_skill(search_skill)

    # 2. 代码魔改师
    edit_skill = SkillDefinition(
        name="代码魔改师",
        description="精通文件读写与代码修改，高效编辑代码文件",
        type=SkillType.ACTIVE,
        tier=SkillTier.BASIC,
        cooldown_rounds=0,
        trigger_event=TriggerEvent.ON_USER_MESSAGE,
        proficiency=SkillProficiency(related_tools=["read_file", "write_file", "replace"]),
        tags=["代码", "编辑"],
        icon="📝",
    )
    tree.add_skill(edit_skill)

    # 3. Shell 指挥官
    cmd_skill = SkillDefinition(
        name="Shell 指挥官",
        description="精通系统命令执行，高效完成各类命令行操作",
        type=SkillType.ACTIVE,
        tier=SkillTier.BASIC,
        cooldown_rounds=0,
        trigger_event=TriggerEvent.ON_USER_MESSAGE,
        proficiency=SkillProficiency(related_tools=["run_cmd"]),
        tags=["命令", "系统"],
        icon="💻",
    )
    tree.add_skill(cmd_skill)

    # 4. 情报分析师
    info_skill = SkillDefinition(
        name="情报分析师",
        description="精通系统信息采集与分析，快速获取关键情报",
        type=SkillType.PASSIVE,
        tier=SkillTier.BASIC,
        cooldown_rounds=1,
        trigger_event=TriggerEvent.ON_USER_MESSAGE,
        proficiency=SkillProficiency(related_tools=["get_system_info", "get_current_time"]),
        tags=["信息", "分析"],
        icon="📊",
    )
    tree.add_skill(info_skill)

    # 5. Git 运维专家
    git_skill = SkillDefinition(
        name="Git 运维专家",
        description="精通 Git 版本控制操作，管理代码历史与分支",
        type=SkillType.ACTIVE,
        tier=SkillTier.INTERMEDIATE,
        prerequisites=[edit_skill.id],
        cooldown_rounds=0,
        trigger_event=TriggerEvent.ON_USER_MESSAGE,
        proficiency=SkillProficiency(related_tools=[
            "git_status", "git_log", "git_diff", "git_commit_stats"
        ]),
        tags=["Git", "版本控制"],
        icon="🔧",
    )
    tree.add_skill(git_skill)

    # 6. 上下文管理师（天赋技能）
    ctx_skill = SkillDefinition(
        name="上下文管理师",
        description="天赋技能：精通上下文管理与压缩，保持对话高效",
        type=SkillType.TALENT,
        tier=SkillTier.TALENT if hasattr(SkillTier, 'TALENT') else SkillTier.BASIC,
        cooldown_rounds=0,
        trigger_event=TriggerEvent.ON_SESSION_START,
        proficiency=SkillProficiency(related_tools=["micro_composer", "auto_composer"]),
        tags=["上下文", "管理"],
        icon="🧠",
    )
    # 如果是 TALENT 类型，尝试用 ADVANCED tier
    ctx_skill.tier = SkillTier.ADVANCED
    tree.add_skill(ctx_skill)

    # 注册技能组合
    combo_debug = SkillCombo(
        name="深度调试",
        description="结合文件搜索与代码编辑能力进行深度调试",
        required_skills=[search_skill.id, edit_skill.id],
        min_levels={search_skill.id: 3, edit_skill.id: 3},
        combo_bonus={"search_depth": 2, "edit_precision": 1.5},
        cooldown_rounds=3,
        icon="🔬",
    )
    tree.combos[combo_debug.id] = combo_debug

    combo_ops = SkillCombo(
        name="运维自动化",
        description="结合命令执行与 Git 操作实现运维自动化",
        required_skills=[cmd_skill.id, git_skill.id],
        min_levels={cmd_skill.id: 2, git_skill.id: 2},
        combo_bonus={"speed_multiplier": 1.3},
        cooldown_rounds=2,
        icon="⚙️",
    )
    tree.combos[combo_ops.id] = combo_ops

    # ── 第 7 步：扫描 skills_custom/ 目录，注册自定义技能 ──
    try:
        from . import skill_loader
        scanned = skill_loader.scan_all_skills()
        for sk_id, meta in scanned.items():
            if not meta.get("is_builtin", True) and sk_id not in tree.skills:
                extra_skill = SkillDefinition(
                    id=sk_id,
                    name=meta.get("name", sk_id),
                    description=meta.get("short_description", ""),
                    type=SkillType.ACTIVE,
                    tier=SkillTier.BASIC,
                    cooldown_rounds=0,
                    trigger_event=TriggerEvent.ON_USER_MESSAGE,
                    proficiency=SkillProficiency(
                        related_tools=meta.get("associated_tools", [])
                    ),
                    tags=meta.get("tags", []),
                    icon=meta.get("icon", "⚡"),
                )
                tree.add_skill(extra_skill)
                print(f"[skill_engine] 已注册自定义技能: {meta.get('name', sk_id)}")
    except Exception as e:
        print(f"[skill_engine] 扫描自定义技能失败: {e}")

    return tree
