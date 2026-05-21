# ============================================================
# TennineClaw - 技能数据模型
# ============================================================
# 定义技能系统的核心数据结构，包括技能类型、等级、定义、
# 技能树、熟练度等，支持 JSON 序列化/反序列化。
# ============================================================

from __future__ import annotations
import json
import os
import uuid
from enum import Enum, auto
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any, Set
from datetime import datetime


# ============================================================
# 枚举定义
# ============================================================

class SkillType(Enum):
    """技能类型"""
    ACTIVE = "active"       # 主动技能 — 用户/Agent 主动调用
    PASSIVE = "passive"     # 被动技能 — 自动触发，无需显式调用
    TALENT = "talent"       # 天赋技能 — 天生具备，不可卸载


class SkillTier(Enum):
    """技能等级阶层"""
    BASIC = "basic"              # 基础
    INTERMEDIATE = "intermediate" # 中级
    ADVANCED = "advanced"        # 高级
    MASTER = "master"            # 大师


class TriggerEvent(Enum):
    """触发事件类型"""
    ON_USER_MESSAGE = "on_user_message"       # 用户发送消息时
    ON_TOOL_CALL = "on_tool_call"             # 工具调用时
    ON_TOOL_RESULT = "on_tool_result"         # 工具返回结果时
    ON_ERROR = "on_error"                    # 发生错误时
    ON_SESSION_START = "on_session_start"    # 会话开始时
    ON_SESSION_END = "on_session_end"        # 会话结束时
    MANUAL = "manual"                        # 手动触发


# ============================================================
# 核心数据类
# ============================================================

@dataclass
class SkillProficiency:
    """技能熟练度与使用统计"""
    total_uses: int = 0               # 总使用次数
    successful_uses: int = 0           # 成功次数
    failed_uses: int = 0               # 失败次数
    last_used_at: Optional[str] = None # 最后使用时间
    consecutive_successes: int = 0     # 连续成功次数
    consecutive_failures: int = 0      # 连续失败次数
    avg_response_time: float = 0.0     # 平均响应时间（秒）
    related_tools: List[str] = field(default_factory=list)  # 相关工具

    @property
    def success_rate(self) -> float:
        """计算成功率"""
        if self.total_uses == 0:
            return 100.0
        return (self.successful_uses / self.total_uses) * 100.0

    def record_use(self, success: bool, response_time: float = 0.0):
        """记录一次使用"""
        self.total_uses += 1
        if success:
            self.successful_uses += 1
            self.consecutive_successes += 1
            self.consecutive_failures = 0
        else:
            self.failed_uses += 1
            self.consecutive_failures += 1
            self.consecutive_successes = 0
        self.last_used_at = datetime.now().isoformat()
        # 更新平均响应时间
        if self.avg_response_time == 0.0:
            self.avg_response_time = response_time
        else:
            self.avg_response_time = (self.avg_response_time * (self.total_uses - 1) + response_time) / self.total_uses

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_uses": self.total_uses,
            "successful_uses": self.successful_uses,
            "failed_uses": self.failed_uses,
            "last_used_at": self.last_used_at,
            "consecutive_successes": self.consecutive_successes,
            "consecutive_failures": self.consecutive_failures,
            "avg_response_time": self.avg_response_time,
            "related_tools": self.related_tools,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SkillProficiency":
        return cls(
            total_uses=data.get("total_uses", 0),
            successful_uses=data.get("successful_uses", 0),
            failed_uses=data.get("failed_uses", 0),
            last_used_at=data.get("last_used_at"),
            consecutive_successes=data.get("consecutive_successes", 0),
            consecutive_failures=data.get("consecutive_failures", 0),
            avg_response_time=data.get("avg_response_time", 0.0),
            related_tools=data.get("related_tools", []),
        )


@dataclass
class SkillDefinition:
    """技能定义 — 单个技能的完整描述"""
    id: str = ""                              # 唯一标识
    name: str = ""                            # 技能名称
    short_description: str = ""               # 简短描述（进 prompt，1句话）
    description: str = ""                     # 兼容旧字段 → 映射到 short_description
    detail_content: str = ""                  # 完整技能详情（不进 prompt，按需加载）
    type: SkillType = SkillType.ACTIVE        # 技能类型
    tier: SkillTier = SkillTier.BASIC         # 等级阶层
    level: int = 1                            # 当前等级 (1~10)
    xp: int = 0                               # 当前经验值
    xp_to_next: int = 100                     # 升下级所需经验
    cooldown_rounds: int = 0                  # 冷却轮次（0=无冷却）
    current_cooldown: int = 0                 # 当前剩余冷却轮次
    prerequisites: List[str] = field(default_factory=list)  # 前置技能 ID 列表
    trigger_event: TriggerEvent = TriggerEvent.MANUAL  # 触发事件
    trigger_conditions: Dict[str, Any] = field(default_factory=dict)  # 触发条件
    proficiency: SkillProficiency = field(default_factory=SkillProficiency)  # 熟练度
    tags: List[str] = field(default_factory=list)  # 标签
    icon: str = "⚡"                           # 图标
    associated_tools: List[str] = field(default_factory=list)  # 关联工具列表
    metadata: Dict[str, Any] = field(default_factory=dict)  # 扩展元数据

    def __post_init__(self):
        if not self.id:
            self.id = f"skill_{uuid.uuid4().hex[:8]}"
        # 兼容旧字段：如果 description 有值但 short_description 为空
        if not self.short_description and self.description:
            self.short_description = self.description
        # 如果 short_description 有值但 description 为空
        if not self.description and self.short_description:
            self.description = self.short_description

    def gain_xp(self, amount: int) -> bool:
        """增加经验值，返回是否升级"""
        self.xp += amount
        if self.xp >= self.xp_to_next and self.level < 10:
            self.xp -= self.xp_to_next
            self.level += 1
            self.xp_to_next = int(self.xp_to_next * 1.5)  # 每级需求增长50%
            return True
        return False

    def can_use(self) -> bool:
        """判断技能当前是否可用"""
        return self.current_cooldown <= 0

    def tick_cooldown(self):
        """冷却减一"""
        if self.current_cooldown > 0:
            self.current_cooldown -= 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "short_description": self.short_description,
            "detail_content": self.detail_content,
            "type": self.type.value,
            "tier": self.tier.value,
            "level": self.level,
            "xp": self.xp,
            "xp_to_next": self.xp_to_next,
            "cooldown_rounds": self.cooldown_rounds,
            "current_cooldown": self.current_cooldown,
            "prerequisites": self.prerequisites,
            "trigger_event": self.trigger_event.value,
            "trigger_conditions": self.trigger_conditions,
            "proficiency": self.proficiency.to_dict(),
            "tags": self.tags,
            "icon": self.icon,
            "associated_tools": self.associated_tools,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SkillDefinition":
        prof_data = data.get("proficiency", {})
        if isinstance(prof_data, dict):
            proficiency = SkillProficiency.from_dict(prof_data)
        else:
            proficiency = prof_data

        type_val = data.get("type", "active")
        if isinstance(type_val, str):
            try:
                type_val = SkillType(type_val)
            except ValueError:
                type_val = SkillType.ACTIVE

        tier_val = data.get("tier", "basic")
        if isinstance(tier_val, str):
            try:
                tier_val = SkillTier(tier_val)
            except ValueError:
                tier_val = SkillTier.BASIC

        trigger_val = data.get("trigger_event", "manual")
        if isinstance(trigger_val, str):
            try:
                trigger_val = TriggerEvent(trigger_val)
            except ValueError:
                trigger_val = TriggerEvent.MANUAL

        # 兼容旧字段 description → short_description
        short_desc = data.get("short_description", "") or data.get("description", "")

        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            short_description=short_desc,
            detail_content=data.get("detail_content", ""),
            type=type_val,
            tier=tier_val,
            level=data.get("level", 1),
            xp=data.get("xp", 0),
            xp_to_next=data.get("xp_to_next", 100),
            cooldown_rounds=data.get("cooldown_rounds", 0),
            current_cooldown=data.get("current_cooldown", 0),
            prerequisites=data.get("prerequisites", []),
            trigger_event=trigger_val,
            trigger_conditions=data.get("trigger_conditions", {}),
            proficiency=proficiency,
            tags=data.get("tags", []),
            icon=data.get("icon", "⚡"),
            associated_tools=data.get("associated_tools", []),
            metadata=data.get("metadata", {}),
        )


# ============================================================
# 技能组合
# ============================================================

@dataclass
class SkillCombo:
    """技能组合（多技能协同触发）"""
    id: str = ""                              # 组合唯一标识
    name: str = ""                            # 组合名称
    description: str = ""                     # 组合描述
    required_skills: List[str] = field(default_factory=list)  # 所需技能 ID 列表
    min_levels: Dict[str, int] = field(default_factory=dict)  # 技能最低等级要求
    bonus_description: str = ""               # 组合加成描述
    combo_bonus: Dict[str, Any] = field(default_factory=dict)  # 组合加成效果
    icon: str = "🔗"                             # 组合图标
    cooldown_rounds: int = 3                  # 组合冷却轮次
    current_cooldown: int = 0                 # 当前冷却
    is_discovered: bool = False               # 是否已发现

    def __post_init__(self):
        if not self.id:
            self.id = f"combo_{uuid.uuid4().hex[:8]}"

    def can_use(self) -> bool:
        return self.current_cooldown <= 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "required_skills": self.required_skills,
            "min_levels": self.min_levels,
            "bonus_description": self.bonus_description,
            "combo_bonus": self.combo_bonus,
            "icon": self.icon,
            "cooldown_rounds": self.cooldown_rounds,
            "current_cooldown": self.current_cooldown,
            "is_discovered": self.is_discovered,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SkillCombo":
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            required_skills=data.get("required_skills", []),
            min_levels=data.get("min_levels", {}),
            bonus_description=data.get("bonus_description", ""),
            combo_bonus=data.get("combo_bonus", {}),
            icon=data.get("icon", "🔗"),
            cooldown_rounds=data.get("cooldown_rounds", 3),
            current_cooldown=data.get("current_cooldown", 0),
            is_discovered=data.get("is_discovered", False),
        )


# ============================================================
# 技能树
# ============================================================

@dataclass
class SkillTree:
    """技能树 — 管理所有已注册技能"""
    name: str = "技能树"
    skills: Dict[str, SkillDefinition] = field(default_factory=dict)
    combos: Dict[str, SkillCombo] = field(default_factory=dict)

    def add_skill(self, skill: SkillDefinition):
        self.skills[skill.id] = skill

    def remove_skill(self, skill_id: str) -> bool:
        if skill_id in self.skills:
            del self.skills[skill_id]
            return True
        return False

    def get_skill(self, skill_id: str) -> Optional[SkillDefinition]:
        return self.skills.get(skill_id)

    def can_unlock(self, skill_id: str, owned_skills: Set[str]) -> bool:
        skill = self.skills.get(skill_id)
        if not skill:
            return False
        return all(pre in owned_skills for pre in skill.prerequisites)

    def get_unlockable_skills(self, owned_skills: Set[str]) -> List[SkillDefinition]:
        return [
            sk for sk_id, sk in self.skills.items()
            if sk_id not in owned_skills and self.can_unlock(sk_id, owned_skills)
        ]

    def get_available_combos(self, owned_skills: Set[str]) -> List[SkillCombo]:
        return [
            combo for combo in self.combos.values()
            if combo.is_discovered and combo.can_use()
            and all(sid in owned_skills for sid in combo.required_skills)
        ]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "skills": {k: v.to_dict() for k, v in self.skills.items()},
            "combos": {k: v.to_dict() for k, v in self.combos.items()},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SkillTree":
        skills = {}
        for k, v in data.get("skills", {}).items():
            skills[k] = SkillDefinition.from_dict(v)
        combos = {}
        for k, v in data.get("combos", {}).items():
            combos[k] = SkillCombo.from_dict(v)
        return cls(
            name=data.get("name", "技能树"),
            skills=skills,
            combos=combos,
        )


# ============================================================
# 通用工具函数
# ============================================================

def xp_for_level(level: int) -> int:
    """计算指定等级所需的经验值"""
    base = 100
    return int(base * (1.5 ** (level - 1)))


def calculate_xp_reward(success: bool, complexity: float = 1.0) -> int:
    """计算技能经验奖励"""
    base = 10 if success else 2
    return int(base * complexity)


# ============================================================
# 全局技能库（Global Skill Registry）
# ============================================================
# 这是所有技能的统一存储，支持多个人格共享技能。
# 预置技能（builtin）不可编辑/删除，自定义技能可 CRUD。
# 每个技能包含三级描述：
#   - short_description: 1句话摘要（进 prompt）
#   - detail_content: 完整操作指南（按需加载）
# ============================================================

GLOBAL_SKILL_REGISTRY_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "sessions", "skills"
)
GLOBAL_SKILL_REGISTRY_PATH = os.path.join(GLOBAL_SKILL_REGISTRY_DIR, "global_registry.json")


# ---- 预置技能定义 ----

BUILTIN_SKILL_DEFINITIONS = [
    {
        "id": "skill_search",
        "name": "文件搜索大师",
        "icon": "🔍",
        "type": "active",
        "tier": "basic",
        "short_description": "精通文件搜索与内容检索，快速定位目标文件",
        "detail_content": """【文件搜索大师 — 完整操作指南】

## 可用工具
- **search_files**: 按名称模式搜索文件（支持通配符）
- **grep**: 在文件中搜索文本内容（支持正则表达式）
- **find_files**: 按名称模式/扩展名查找文件（支持排序）
- **diff**: 比较两个文件的差异

## 搜索策略
1. **快速定位**: 优先使用 find_files 进行文件名匹配（性能最优）
2. **全文搜索**: 需要搜索文件内容时使用 grep（支持正则）
3. **精确查找**: 确定范围后使用 search_files 精确查找
4. **对比分析**: 对比文件内容时使用 diff

## 最佳实践
- 先使用 list_files 了解目录结构，缩小搜索范围
- 使用通配符 * 进行模糊匹配
- 设置合理的 max_results 限制返回数量
- 组合 grep + find_files 实现精准定位

## 典型场景
- "帮我找到昨天的配置文件" → find_files("config*")
- "搜索包含 API_KEY 的文件" → grep("API_KEY", "*.py")
- "对比两个版本的区别" → diff("file_v1.py", "file_v2.py")""",
        "tags": ["文件", "搜索"],
        "associated_tools": ["search_files", "grep", "find_files", "diff"],
    },
    {
        "id": "skill_edit",
        "name": "代码魔改师",
        "icon": "📝",
        "type": "active",
        "tier": "basic",
        "short_description": "精通文件读写与代码修改，高效编辑代码文件",
        "detail_content": """【代码魔改师 — 完整操作指南】

## 可用工具
- **read_file**: 读取文件内容
- **write_file**: 写入/覆盖文件内容（自动创建目录）
- **replace**: 搜索并替换文件内容（支持正则，预览模式）
- **show_file**: 带行号显示文件内容

## 编辑策略
1. **先读后改**: 修改前先 read_file 了解当前内容
2. **预览先行**: 使用 replace 的 dry_run=True 预览改动
3. **增量修改**: 定位到具体函数/行进行精确修改
4. **验证结果**: 修改后 show_file 验证改动是否正确

## 最佳实践
- 大文件修改前先 show_file 查看行号定位
- 批量替换时使用 replace 的 dry_run 验证
- 修改关键文件前先备份
- 使用正则表达式进行精确的模式匹配替换

## 典型场景
- "修改 config.py 中的数据库地址" → read_file → replace
- "在文件末尾添加新函数" → read_file → 生成新内容 → write_file
- "批量替换所有 js 文件中的 API 地址" → replace(dry_run=True) → replace""",
        "tags": ["代码", "编辑"],
        "associated_tools": ["read_file", "write_file", "replace", "show_file"],
    },
    {
        "id": "skill_cmd",
        "name": "Shell 指挥官",
        "icon": "💻",
        "type": "active",
        "tier": "basic",
        "short_description": "精通系统命令执行，高效完成各类命令行操作",
        "detail_content": """【Shell 指挥官 — 完整操作指南】

## 可用工具
- **run_cmd**: 执行系统命令（带安全检测）

## 执行策略
1. **安全第一**: 高危命令（rm -rf /, format等）会被拦截
2. **确认机制**: 高危操作需要用户确认后才能执行
3. **超时保护**: 命令超过30秒自动终止
4. **输出优化**: 长输出自动截断

## 最佳实践
- 先执行 ls/dir 了解当前目录
- 使用 echo/type 验证路径
- 复杂命令分解为多个简单步骤
- 使用管道 | 连接多个命令

## 典型场景
- "查看当前目录" → run_cmd("dir" / "ls")
- "安装依赖" → run_cmd("pip install ...")
- "查看日志" → run_cmd("tail -n 100 app.log")""",
        "tags": ["命令", "系统"],
        "associated_tools": ["run_cmd"],
    },
    {
        "id": "skill_info",
        "name": "情报分析师",
        "icon": "📊",
        "type": "passive",
        "tier": "basic",
        "short_description": "精通系统信息采集与分析，快速获取关键情报",
        "detail_content": """【情报分析师 — 完整操作指南】

## 可用工具
- **get_system_info**: 获取操作系统、CPU、内存等系统信息
- **get_current_time**: 获取当前日期和时间
- **count_lines**: 统计项目代码行数

## 分析策略
1. **环境感知**: 先获取系统基本信息
2. **时间感知**: 了解当前时间，判断时效性
3. **项目规模**: 使用 count_lines 了解项目规模

## 最佳实践
- 用户提问前自动收集环境信息
- 结合时间和系统状态提供上下文
- 在代码审查时使用 count_lines 评估改动量

## 典型场景
- "这个项目有多大？" → count_lines + list_files
- "现在几点了？" → get_current_time
- "系统环境怎么样？" → get_system_info""",
        "tags": ["信息", "分析"],
        "associated_tools": ["get_system_info", "get_current_time", "count_lines"],
    },
    {
        "id": "skill_git",
        "name": "Git 运维专家",
        "icon": "🔧",
        "type": "active",
        "tier": "intermediate",
        "short_description": "精通 Git 版本控制操作，管理代码历史与分支",
        "detail_content": """【Git 运维专家 — 完整操作指南】

## 可用工具
- **git_status**: 查看仓库状态（分支、变更、冲突）
- **git_log**: 查看提交历史（支持作者/分支过滤）
- **git_diff**: 查看工作区变更差异
- **git_commit_stats**: 统计提交贡献

## 操作策略
1. **先看状态**: 操作前先 git_status 了解仓库状态
2. **再看历史**: git_log 查看最近的提交记录
3. **查看变更**: git_diff 了解具体的代码变更
4. **统计贡献**: git_commit_stats 分析团队贡献

## 最佳实践
- 提交前先 git_status 检查是否有未跟踪文件
- 使用 git_log 的 count/author 参数精确过滤
- diff 时指定文件路径避免信息过载

## 典型场景
- "仓库当前状态如何？" → git_status
- "最近谁改了什么？" → git_log + git_commit_stats
- "这个文件有什么改动？" → git_diff(path="src/main.py")""",
        "tags": ["Git", "版本控制"],
        "associated_tools": ["git_status", "git_log", "git_diff", "git_commit_stats"],
    },
    {
        "id": "skill_context",
        "name": "上下文管理师",
        "icon": "🧠",
        "type": "passive",
        "tier": "intermediate",
        "short_description": "精通上下文管理与优化，保持高效对话",
        "detail_content": """【上下文管理师 — 完整操作指南】

## 可用工具
- 上下文压缩：自动压缩过长的对话历史
- Token统计：监控上下文使用量
- 智能分段：将长文本分割为合理段落

## 管理策略
1. **主动压缩**: 当上下文接近阈值时自动压缩
2. **保留重点**: 保留用户指令和关键信息
3. **分段处理**: 长回复分段输出，提升可读性

## 最佳实践
- 定期检查 token 使用量
- 在关键任务前确保上下文空间充足
- 使用 clear 指令重置上下文

## 典型场景
- "对话太长了，帮我总结一下" → 上下文压缩
- "当前用了多少 token？" → token统计""",
        "tags": ["上下文", "优化"],
        "associated_tools": [],
    },
]

# 预置技能组合
BUILTIN_SKILL_COMBOS = [
    {
        "id": "combo_debug",
        "name": "深度调试",
        "description": "结合搜索、编辑和 Git 技能进行深度调试",
        "required_skills": ["skill_search", "skill_edit", "skill_git"],
        "bonus_description": "组合激活：搜索定位问题 → 查看代码 → 检查 Git 历史 → 修复",
        "cooldown_rounds": 2,
    },
    {
        "id": "combo_devops",
        "name": "运维自动化",
        "description": "结合命令执行和 Git 技能进行运维操作",
        "required_skills": ["skill_cmd", "skill_git"],
        "bonus_description": "组合激活：执行命令 → 检查状态 → 提交变更",
        "cooldown_rounds": 3,
    },
]


def init_global_skill_registry() -> Dict[str, dict]:
    """
    初始化全局技能库。
    如果技能库不存在或为空，创建并写入预置技能。
    返回注册表字典 {skill_id: skill_dict}
    """
    os.makedirs(GLOBAL_SKILL_REGISTRY_DIR, exist_ok=True)

    if os.path.exists(GLOBAL_SKILL_REGISTRY_PATH):
        try:
            with open(GLOBAL_SKILL_REGISTRY_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
            registry = data.get("skills", {})
            # 确保所有预置技能存在
            changed = False
            for builtin in BUILTIN_SKILL_DEFINITIONS:
                sk_id = builtin["id"]
                if sk_id not in registry:
                    entry = dict(builtin)
                    entry["is_builtin"] = True
                    entry["created_by"] = "system"
                    entry["created_at"] = datetime.now().isoformat()
                    entry["updated_at"] = datetime.now().isoformat()
                    registry[sk_id] = entry
                    changed = True
                else:
                    # 确保 builtin 标记正确
                    registry[sk_id]["is_builtin"] = True
                    registry[sk_id]["created_by"] = "system"
            if changed:
                with open(GLOBAL_SKILL_REGISTRY_PATH, 'w', encoding='utf-8') as f:
                    json.dump({"skills": registry}, f, ensure_ascii=False, indent=2)
            return registry
        except (json.JSONDecodeError, KeyError):
            pass

    # 创建新注册表
    registry = {}
    for builtin in BUILTIN_SKILL_DEFINITIONS:
        sk_id = builtin["id"]
        entry = dict(builtin)
        entry["is_builtin"] = True
        entry["created_by"] = "system"
        entry["created_at"] = datetime.now().isoformat()
        entry["updated_at"] = datetime.now().isoformat()
        registry[sk_id] = entry

    with open(GLOBAL_SKILL_REGISTRY_PATH, 'w', encoding='utf-8') as f:
        json.dump({"skills": registry}, f, ensure_ascii=False, indent=2)

    return registry


def load_global_skill_registry() -> Dict[str, dict]:
    """加载全局技能库"""
    if not os.path.exists(GLOBAL_SKILL_REGISTRY_PATH):
        return init_global_skill_registry()
    try:
        with open(GLOBAL_SKILL_REGISTRY_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get("skills", {})
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def save_global_skill_registry(registry: Dict[str, dict]):
    """保存全局技能库"""
    os.makedirs(GLOBAL_SKILL_REGISTRY_DIR, exist_ok=True)
    with open(GLOBAL_SKILL_REGISTRY_PATH, 'w', encoding='utf-8') as f:
        json.dump({"skills": registry}, f, ensure_ascii=False, indent=2)


def get_skill_detail(skill_id_or_name: str) -> Optional[str]:
    """
    通过技能 ID 或名称查找技能详情。
    优先从 skills/ 目录读取 guide.md，回退注册表。
    返回 detail_content 或 None。
    """
    # 优先从文件读取
    try:
        import skill_loader
        guide = skill_loader.load_skill_guide(skill_id_or_name)
        if guide:
            return guide
    except Exception:
        pass
    registry = load_global_skill_registry()
    if skill_id_or_name in registry:
        return registry[skill_id_or_name].get("detail_content", "")
    for sk_id, sk in registry.items():
        if sk.get("name") == skill_id_or_name:
            return sk.get("detail_content", "")
    return None

def add_custom_skill(data: dict) -> dict:
    """
    添加自定义技能到全局库。
    data 需包含: name, short_description; 可选: detail_content, icon, type, tier, tags, associated_tools, created_by
    返回 {success: bool, skill_id: str, error: str}
    """
    name = data.get("name", "").strip()
    if not name:
        return {"success": False, "error": "技能名称不能为空"}

    short_description = data.get("short_description", "").strip()
    if not short_description:
        return {"success": False, "error": "简短描述不能为空"}

    registry = load_global_skill_registry()

    # 检查名称是否重复
    for sk_id, sk in registry.items():
        if sk.get("name") == name:
            return {"success": False, "error": f"技能「{name}」已存在"}

    sk_id = f"skill_{uuid.uuid4().hex[:8]}"
    now = datetime.now().isoformat()

    entry = {
        "id": sk_id,
        "name": name,
        "icon": data.get("icon", "⚡"),
        "type": data.get("type", "active"),
        "tier": data.get("tier", "basic"),
        "short_description": short_description,
        "guide": data.get("guide", ""),
        "detail_content": data.get("detail_content", ""),
        "tags": data.get("tags", []),
        "associated_tools": data.get("associated_tools", []),
        "is_builtin": False,
        "created_by": data.get("created_by", "anonymous"),
        "created_at": now,
        "updated_at": now,
    }

    registry[sk_id] = entry
    save_global_skill_registry(registry)

    # 同时保存为文件
    try:
        import skill_loader
        skill_loader.save_custom_skill(
            name=entry["name"],
            metadata=entry,
            description=entry.get("short_description", ""),
            guide=entry.get("detail_content", ""),
        )
    except Exception:
        pass

    return {"success": True, "skill_id": sk_id}


def update_custom_skill(skill_id: str, data: dict) -> dict:
    """更新自定义技能"""
    registry = load_global_skill_registry()

    if skill_id not in registry:
        return {"success": False, "error": f"技能 {skill_id} 不存在"}

    if registry[skill_id].get("is_builtin"):
        return {"success": False, "error": "预置技能不可编辑"}

    name = data.get("name", "").strip()
    if name:
        # 检查名称是否与其他技能重复
        for sid, sk in registry.items():
            if sid != skill_id and sk.get("name") == name:
                return {"success": False, "error": f"技能「{name}」已存在"}
        registry[skill_id]["name"] = name

    if "short_description" in data:
        registry[skill_id]["short_description"] = data["short_description"].strip()
    if "detail_content" in data:
        registry[skill_id]["detail_content"] = data["detail_content"]
    if "icon" in data:
        registry[skill_id]["icon"] = data["icon"]
    if "type" in data:
        registry[skill_id]["type"] = data["type"]
    if "tier" in data:
        registry[skill_id]["tier"] = data["tier"]
    if "tags" in data:
        registry[skill_id]["tags"] = data["tags"]
    if "associated_tools" in data:
        registry[skill_id]["associated_tools"] = data["associated_tools"]

    registry[skill_id]["updated_at"] = datetime.now().isoformat()
    save_global_skill_registry(registry)

    # 同步更新文件
    try:
        import skill_loader
        skill_loader.save_custom_skill(
            name=registry[skill_id]["name"],
            metadata=registry[skill_id],
            description=registry[skill_id].get("short_description", ""),
            guide=registry[skill_id].get("detail_content", ""),
        )
    except Exception:
        pass

    return {"success": True}


def delete_custom_skill(skill_id: str) -> dict:
    """删除自定义技能"""
    registry = load_global_skill_registry()

    if skill_id not in registry:
        return {"success": False, "error": f"技能 {skill_id} 不存在"}

    if registry[skill_id].get("is_builtin"):
        return {"success": False, "error": "预置技能不可删除"}

    del registry[skill_id]
    save_global_skill_registry(registry)

    # 同时删除文件
    try:
        import skill_loader
        skill_loader.delete_custom_skill(skill_id)
    except Exception:
        pass

    return {"success": True}

def get_registry_skills_list(include_detail: bool = False) -> list:
    """
    Get all skills from the global registry + directory scan as a list.
    Each skill dict includes: id, name, icon, short_description, is_builtin, etc.
    
    Args:
        include_detail: If True, include detail_content (can be large)
    
    Returns:
        List of skill dicts
    """
    registry = load_global_skill_registry()
    seen_ids = set()
    result = []
    
    # 1. From registry (the main source)
    for sk_id, sk in registry.items():
        seen_ids.add(sk_id)
        entry = {
            "id": sk_id,
            "name": sk.get("name", sk_id),
            "icon": sk.get("icon", "⚡"),
            "type": sk.get("type", "active"),
            "tier": sk.get("tier", "basic"),
            "short_description": sk.get("short_description", ""),
            "is_builtin": sk.get("is_builtin", False),
        }
        if include_detail:
            entry["detail_content"] = sk.get("detail_content", "")
        result.append(entry)
    
    # 2. Scan skills/ and skills_custom/ directories for unregistered skills
    try:
        from . import skill_loader
        scanned = skill_loader.scan_all_skills()
        for sk_id, meta in scanned.items():
            if sk_id not in seen_ids:
                seen_ids.add(sk_id)
                entry = {
                    "id": sk_id,
                    "name": meta.get("name", sk_id),
                    "icon": meta.get("icon", "⚡"),
                    "type": meta.get("type", "active"),
                    "tier": meta.get("tier", "basic"),
                    "short_description": meta.get("short_description", ""),
                    "is_builtin": meta.get("is_builtin", False),
                }
                if include_detail:
                    guide_data = skill_loader.load_skill_guide(sk_id)
                    entry["detail_content"] = guide_data or ""
                result.append(entry)
    except Exception as e:
        print(f"[skill_models] ⚠️ 扫描技能目录失败: {e}")
    
    return result


def xp_for_level(level: int) -> int:
    """计算指定等级所需的经验值"""
    base = 100
    return int(base * (1.5 ** (level - 1)))


def calculate_xp_reward(success: bool, complexity: float = 1.0) -> int:
    """计算技能经验奖励"""
    base = 10 if success else 2
    return int(base * complexity)


# ============================================================
# 全局技能库（Global Skill Registry）
# ============================================================
# 这是所有技能的统一存储，支持多个人格共享技能。
# 预置技能（builtin）不可编辑/删除，自定义技能可 CRUD。
# 每个技能包含三级描述：
#   - short_description: 1句话摘要（进 prompt）
#   - detail_content: 完整操作指南（按需加载）
# ============================================================

GLOBAL_SKILL_REGISTRY_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "sessions", "skills"
)
GLOBAL_SKILL_REGISTRY_PATH = os.path.join(GLOBAL_SKILL_REGISTRY_DIR, "global_registry.json")


# ---- 预置技能定义 ----

BUILTIN_SKILL_DEFINITIONS = [
    {
        "id": "skill_search",
        "name": "文件搜索大师",
        "icon": "🔍",
        "type": "active",
        "tier": "basic",
        "short_description": "精通文件搜索与内容检索，快速定位目标文件",
        "detail_content": """【文件搜索大师 — 完整操作指南】

## 可用工具
- **search_files**: 按名称模式搜索文件（支持通配符）
- **grep**: 在文件中搜索文本内容（支持正则表达式）
- **find_files**: 按名称模式/扩展名查找文件（支持排序）
- **diff**: 比较两个文件的差异

## 搜索策略
1. **快速定位**: 优先使用 find_files 进行文件名匹配（性能最优）
2. **全文搜索**: 需要搜索文件内容时使用 grep（支持正则）
3. **精确查找**: 确定范围后使用 search_files 精确查找
4. **对比分析**: 对比文件内容时使用 diff

## 最佳实践
- 先使用 list_files 了解目录结构，缩小搜索范围
- 使用通配符 * 进行模糊匹配
- 设置合理的 max_results 限制返回数量
- 组合 grep + find_files 实现精准定位

## 典型场景
- "帮我找到昨天的配置文件" → find_files("config*")
- "搜索包含 API_KEY 的文件" → grep("API_KEY", "*.py")
- "对比两个版本的区别" → diff("file_v1.py", "file_v2.py")""",
        "tags": ["文件", "搜索"],
        "associated_tools": ["search_files", "grep", "find_files", "diff"],
    },
    {
        "id": "skill_edit",
        "name": "代码魔改师",
        "icon": "📝",
        "type": "active",
        "tier": "basic",
        "short_description": "精通文件读写与代码修改，高效编辑代码文件",
        "detail_content": """【代码魔改师 — 完整操作指南】

## 可用工具
- **read_file**: 读取文件内容
- **write_file**: 写入/覆盖文件内容（自动创建目录）
- **replace**: 搜索并替换文件内容（支持正则，预览模式）
- **show_file**: 带行号显示文件内容

## 编辑策略
1. **先读后改**: 修改前先 read_file 了解当前内容
2. **预览先行**: 使用 replace 的 dry_run=True 预览改动
3. **增量修改**: 定位到具体函数/行进行精确修改
4. **验证结果**: 修改后 show_file 验证改动是否正确

## 最佳实践
- 大文件修改前先 show_file 查看行号定位
- 批量替换时使用 replace 的 dry_run 验证
- 修改关键文件前先备份
- 使用正则表达式进行精确的模式匹配替换

## 典型场景
- "修改 config.py 中的数据库地址" → read_file → replace
- "在文件末尾添加新函数" → read_file → 生成新内容 → write_file
- "批量替换所有 js 文件中的 API 地址" → replace(dry_run=True) → replace""",
        "tags": ["代码", "编辑"],
        "associated_tools": ["read_file", "write_file", "replace", "show_file"],
    },
    {
        "id": "skill_cmd",
        "name": "Shell 指挥官",
        "icon": "💻",
        "type": "active",
        "tier": "basic",
        "short_description": "精通系统命令执行，高效完成各类命令行操作",
        "detail_content": """【Shell 指挥官 — 完整操作指南】

## 可用工具
- **run_cmd**: 执行系统命令（带安全检测）

## 执行策略
1. **安全第一**: 高危命令（rm -rf /, format等）会被拦截
2. **确认机制**: 高危操作需要用户确认后才能执行
3. **超时保护**: 命令超过30秒自动终止
4. **输出优化**: 长输出自动截断

## 最佳实践
- 先执行 ls/dir 了解当前目录
- 使用 echo/type 验证路径
- 复杂命令分解为多个简单步骤
- 使用管道 | 连接多个命令

## 典型场景
- "查看当前目录" → run_cmd("dir" / "ls")
- "安装依赖" → run_cmd("pip install ...")
- "查看日志" → run_cmd("tail -n 100 app.log")""",
        "tags": ["命令", "系统"],
        "associated_tools": ["run_cmd"],
    },
    {
        "id": "skill_info",
        "name": "情报分析师",
        "icon": "📊",
        "type": "passive",
        "tier": "basic",
        "short_description": "精通系统信息采集与分析，快速获取关键情报",
        "detail_content": """【情报分析师 — 完整操作指南】

## 可用工具
- **get_system_info**: 获取操作系统、CPU、内存等系统信息
- **get_current_time**: 获取当前日期和时间
- **count_lines**: 统计项目代码行数

## 分析策略
1. **环境感知**: 先获取系统基本信息
2. **时间感知**: 了解当前时间，判断时效性
3. **项目规模**: 使用 count_lines 了解项目规模

## 最佳实践
- 用户提问前自动收集环境信息
- 结合时间和系统状态提供上下文
- 在代码审查时使用 count_lines 评估改动量

## 典型场景
- "这个项目有多大？" → count_lines + list_files
- "现在几点了？" → get_current_time
- "系统环境怎么样？" → get_system_info""",
        "tags": ["信息", "分析"],
        "associated_tools": ["get_system_info", "get_current_time", "count_lines"],
    },
    {
        "id": "skill_git",
        "name": "Git 运维专家",
        "icon": "🔧",
        "type": "active",
        "tier": "intermediate",
        "short_description": "精通 Git 版本控制操作，管理代码历史与分支",
        "detail_content": """【Git 运维专家 — 完整操作指南】

## 可用工具
- **git_status**: 查看仓库状态（分支、变更、冲突）
- **git_log**: 查看提交历史（支持作者/分支过滤）
- **git_diff**: 查看工作区变更差异
- **git_commit_stats**: 统计提交贡献

## 操作策略
1. **先看状态**: 操作前先 git_status 了解仓库状态
2. **再看历史**: git_log 查看最近的提交记录
3. **查看变更**: git_diff 了解具体的代码变更
4. **统计贡献**: git_commit_stats 分析团队贡献

## 最佳实践
- 提交前先 git_status 检查是否有未跟踪文件
- 使用 git_log 的 count/author 参数精确过滤
- diff 时指定文件路径避免信息过载

## 典型场景
- "仓库当前状态如何？" → git_status
- "最近谁改了什么？" → git_log + git_commit_stats
- "这个文件有什么改动？" → git_diff(path="src/main.py")""",
        "tags": ["Git", "版本控制"],
        "associated_tools": ["git_status", "git_log", "git_diff", "git_commit_stats"],
    },
    {
        "id": "skill_context",
        "name": "上下文管理师",
        "icon": "🧠",
        "type": "passive",
        "tier": "intermediate",
        "short_description": "精通上下文管理与优化，保持高效对话",
        "detail_content": """【上下文管理师 — 完整操作指南】

## 可用工具
- 上下文压缩：自动压缩过长的对话历史
- Token统计：监控上下文使用量
- 智能分段：将长文本分割为合理段落

## 管理策略
1. **主动压缩**: 当上下文接近阈值时自动压缩
2. **保留重点**: 保留用户指令和关键信息
3. **分段处理**: 长回复分段输出，提升可读性

## 最佳实践
- 定期检查 token 使用量
- 在关键任务前确保上下文空间充足
- 使用 clear 指令重置上下文

## 典型场景
- "对话太长了，帮我总结一下" → 上下文压缩
- "当前用了多少 token？" → token统计""",
        "tags": ["上下文", "优化"],
        "associated_tools": [],
    },
]

# 预置技能组合
BUILTIN_SKILL_COMBOS = [
    {
        "id": "combo_debug",
        "name": "深度调试",
        "description": "结合搜索、编辑和 Git 技能进行深度调试",
        "required_skills": ["skill_search", "skill_edit", "skill_git"],
        "bonus_description": "组合激活：搜索定位问题 → 查看代码 → 检查 Git 历史 → 修复",
        "cooldown_rounds": 2,
    },
    {
        "id": "combo_devops",
        "name": "运维自动化",
        "description": "结合命令执行和 Git 技能进行运维操作",
        "required_skills": ["skill_cmd", "skill_git"],
        "bonus_description": "组合激活：执行命令 → 检查状态 → 提交变更",
        "cooldown_rounds": 3,
    },
]


def init_global_skill_registry() -> Dict[str, dict]:
    """
    初始化全局技能库。
    如果技能库不存在或为空，创建并写入预置技能。
    返回注册表字典 {skill_id: skill_dict}
    """
    os.makedirs(GLOBAL_SKILL_REGISTRY_DIR, exist_ok=True)

    if os.path.exists(GLOBAL_SKILL_REGISTRY_PATH):
        try:
            with open(GLOBAL_SKILL_REGISTRY_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
            registry = data.get("skills", {})
            # 确保所有预置技能存在
            changed = False
            for builtin in BUILTIN_SKILL_DEFINITIONS:
                sk_id = builtin["id"]
                if sk_id not in registry:
                    entry = dict(builtin)
                    entry["is_builtin"] = True
                    entry["created_by"] = "system"
                    entry["created_at"] = datetime.now().isoformat()
                    entry["updated_at"] = datetime.now().isoformat()
                    registry[sk_id] = entry
                    changed = True
                else:
                    # 确保 builtin 标记正确
                    registry[sk_id]["is_builtin"] = True
                    registry[sk_id]["created_by"] = "system"
            if changed:
                with open(GLOBAL_SKILL_REGISTRY_PATH, 'w', encoding='utf-8') as f:
                    json.dump({"skills": registry}, f, ensure_ascii=False, indent=2)
            return registry
        except (json.JSONDecodeError, KeyError):
            pass

    # 创建新注册表
    registry = {}
    for builtin in BUILTIN_SKILL_DEFINITIONS:
        sk_id = builtin["id"]
        entry = dict(builtin)
        entry["is_builtin"] = True
        entry["created_by"] = "system"
        entry["created_at"] = datetime.now().isoformat()
        entry["updated_at"] = datetime.now().isoformat()
        registry[sk_id] = entry

    with open(GLOBAL_SKILL_REGISTRY_PATH, 'w', encoding='utf-8') as f:
        json.dump({"skills": registry}, f, ensure_ascii=False, indent=2)

    return registry


def load_global_skill_registry() -> Dict[str, dict]:
    """加载全局技能库"""
    if not os.path.exists(GLOBAL_SKILL_REGISTRY_PATH):
        return init_global_skill_registry()
    try:
        with open(GLOBAL_SKILL_REGISTRY_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get("skills", {})
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def save_global_skill_registry(registry: Dict[str, dict]):
    """保存全局技能库"""
    os.makedirs(GLOBAL_SKILL_REGISTRY_DIR, exist_ok=True)
    with open(GLOBAL_SKILL_REGISTRY_PATH, 'w', encoding='utf-8') as f:
        json.dump({"skills": registry}, f, ensure_ascii=False, indent=2)


def get_skill_detail(skill_id_or_name: str) -> Optional[str]:
    """
    通过技能 ID 或名称查找技能详情。
    优先从 skills/ 目录读取 guide.md，回退注册表。
    返回 detail_content 或 None。
    """
    # 优先从文件读取
    try:
        import skill_loader
        guide = skill_loader.load_skill_guide(skill_id_or_name)
        if guide:
            return guide
    except Exception:
        pass
    registry = load_global_skill_registry()
    if skill_id_or_name in registry:
        return registry[skill_id_or_name].get("detail_content", "")
    for sk_id, sk in registry.items():
        if sk.get("name") == skill_id_or_name:
            return sk.get("detail_content", "")
    return None

def add_custom_skill(data: dict) -> dict:
    """
    添加自定义技能到全局库。
    data 需包含: name, short_description; 可选: detail_content, icon, type, tier, tags, associated_tools, created_by
    返回 {success: bool, skill_id: str, error: str}
    """
    name = data.get("name", "").strip()
    if not name:
        return {"success": False, "error": "技能名称不能为空"}

    short_description = data.get("short_description", "").strip()
    if not short_description:
        return {"success": False, "error": "简短描述不能为空"}

    registry = load_global_skill_registry()

    # 检查名称是否重复
    for sk_id, sk in registry.items():
        if sk.get("name") == name:
            return {"success": False, "error": f"技能「{name}」已存在"}

    sk_id = f"skill_{uuid.uuid4().hex[:8]}"
    now = datetime.now().isoformat()

    entry = {
        "id": sk_id,
        "name": name,
        "icon": data.get("icon", "⚡"),
        "type": data.get("type", "active"),
        "tier": data.get("tier", "basic"),
        "short_description": short_description,
        "guide": data.get("guide", ""),
        "detail_content": data.get("detail_content", ""),
        "tags": data.get("tags", []),
        "associated_tools": data.get("associated_tools", []),
        "is_builtin": False,
        "created_by": data.get("created_by", "anonymous"),
        "created_at": now,
        "updated_at": now,
    }

    registry[sk_id] = entry
    save_global_skill_registry(registry)

    # 同时保存为文件
    try:
        import skill_loader
        skill_loader.save_custom_skill(
            name=entry["name"],
            metadata=entry,
            description=entry.get("short_description", ""),
            guide=entry.get("detail_content", ""),
        )
    except Exception:
        pass

    return {"success": True, "skill_id": sk_id}


def update_custom_skill(skill_id: str, data: dict) -> dict:
    """更新自定义技能"""
    registry = load_global_skill_registry()

    if skill_id not in registry:
        return {"success": False, "error": f"技能 {skill_id} 不存在"}

    if registry[skill_id].get("is_builtin"):
        return {"success": False, "error": "预置技能不可编辑"}

    name = data.get("name", "").strip()
    if name:
        # 检查名称是否与其他技能重复
        for sid, sk in registry.items():
            if sid != skill_id and sk.get("name") == name:
                return {"success": False, "error": f"技能「{name}」已存在"}
        registry[skill_id]["name"] = name

    if "short_description" in data:
        registry[skill_id]["short_description"] = data["short_description"].strip()
    if "detail_content" in data:
        registry[skill_id]["detail_content"] = data["detail_content"]
    if "icon" in data:
        registry[skill_id]["icon"] = data["icon"]
    if "type" in data:
        registry[skill_id]["type"] = data["type"]
    if "tier" in data:
        registry[skill_id]["tier"] = data["tier"]
    if "tags" in data:
        registry[skill_id]["tags"] = data["tags"]
    if "associated_tools" in data:
        registry[skill_id]["associated_tools"] = data["associated_tools"]

    registry[skill_id]["updated_at"] = datetime.now().isoformat()
    save_global_skill_registry(registry)

    # 同步更新文件
    try:
        import skill_loader
        skill_loader.save_custom_skill(
            name=registry[skill_id]["name"],
            metadata=registry[skill_id],
            description=registry[skill_id].get("short_description", ""),
            guide=registry[skill_id].get("detail_content", ""),
        )
    except Exception:
        pass

    return {"success": True}


def delete_custom_skill(skill_id: str) -> dict:
    """删除自定义技能"""
    registry = load_global_skill_registry()

    if skill_id not in registry:
        return {"success": False, "error": f"技能 {skill_id} 不存在"}

    if registry[skill_id].get("is_builtin"):
        return {"success": False, "error": "预置技能不可删除"}

    del registry[skill_id]
    save_global_skill_registry(registry)

    # 同时删除文件
    try:
        import skill_loader
        skill_loader.delete_custom_skill(skill_id)
    except Exception:
        pass

    return {"success": True}

def get_registry_skills_list(include_detail: bool = False) -> list:
    """
    Get all skills from the global registry as a list.
    Each skill dict includes: id, name, icon, short_description, is_builtin, etc.
    
    Args:
        include_detail: If True, include detail_content (can be large)
    
    Returns:
        List of skill dicts
    """
    registry = load_global_skill_registry()
    result = []
    for sk_id, sk in registry.items():
        entry = {
            "id": sk_id,
            "name": sk.get("name", sk_id),
            "icon": sk.get("icon", "⚡"),
            "type": sk.get("type", "active"),
            "tier": sk.get("tier", "basic"),
            "short_description": sk.get("short_description", ""),
            "is_builtin": sk.get("is_builtin", False),
        }
        if include_detail:
            entry["detail_content"] = sk.get("detail_content", "")
        result.append(entry)
    
    # Sort by name
    result.sort(key=lambda x: x.get("name", ""))
    return result
