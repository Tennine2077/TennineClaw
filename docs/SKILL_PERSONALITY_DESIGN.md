# 🎯 Skill 技能系统引入 & 人格化持久性 — 设计文档

> **语言**: 中文 | [🌏 English](SKILL_PERSONALITY_DESIGN.en.md)
> **项目**: TennineClaw  
> **版本**: v1.1.0（已实现）  
> **设计目标**: 为 AI Agent 赋予可成长、可组合的 Skill 技能体系，以及跨会话保持一致的人格化记忆与行为特征  
> **设计原则**: 模块化、可扩展、低耦合、渐进式落地

---

## 📖 目录

1. [系统概述](#1-系统概述)
2. [数据结构设计](#2-数据结构设计)
3. [Skill 技能系统](#3-skill-技能系统)
4. [人格化持久性系统](#4-人格化持久性系统)
5. [系统集成与交互流程](#5-系统集成与交互流程)
6. [配置文件与存储规划](#6-配置文件与存储规划)
7. [扩展性设计](#7-扩展性设计)

---

## 1. 系统概述

### 1.1 为什么要引入这两个系统？

| 当前痛点 | 解决方案 |
|----------|----------|
| Agent 每次对话从零开始，没有"成长感" | 引入 Skill 技能系统，按使用频率/成功率积累经验、升级 |
| 工具调用是"平面化"的，无优先级/组合策略 | Skill 系统支持技能树、被动/主动技能、技能组合 |
| 跨会话无任何人格记忆，每次都是"陌生人" | 人格化持久性系统，维护性格特征、语言习惯、偏好 |
| Agent 行为无差异化，换模型也没区别 | 人格特征影响 response 风格、决策偏好 |

### 1.2 架构总览

```
┌─────────────────────────────────────────────────────────────┐
│                    TennineClaw 整体架构                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────┐    ┌───────────────────────────┐   │
│  │   AgentSession      │    │   人格化持久性系统          │   │
│  │   (核心对话引擎)     │◄──►│   PersonalityEngine       │   │
│  │                     │    │   - 性格特征管理            │   │
│  │   - 模式管理         │    │   - 语言风格管理            │   │
│  │   - 工具调度         │    │   - 记忆片段管理            │   │
│  │   - Composer 压缩    │    │   - 行为偏好管理            │   │
│  │   - 会话管理         │    └──────────┬────────────────┘   │
│  └────────┬────────────┘               │                    │
│           │                             │                    │
│           ▼                             ▼                    │
│  ┌──────────────────────────────────────────────┐           │
│  │            Skill 技能系统                      │           │
│  │   SkillEngine                               │           │
│  │   - 技能注册与发现                             │           │
│  │   - 技能树/依赖关系                            │           │
│  │   - 经验值/等级系统                            │           │
│  │   - 技能执行与组合                             │           │
│  │   - 技能触发器(被动/主动)                       │           │
│  └──────────────────────────────────────────────┘           │
│                                                             │
│  ┌──────────────────────────────────────────────┐           │
│  │           持久化存储层                          │           │
│  │   skill_data.json  +  personality.json       │           │
│  │   +  session 文件（内嵌 skill/personality 快照）│           │
│  └──────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. 数据结构设计

### 2.1 Skill 核心数据结构

```python
# ──── Skill 定义结构 ────
@dataclass
class SkillDefinition:
    """技能定义（注册时确定，不可变）"""
    skill_id: str                        # 全局唯一技能 ID，如 "skill_git_ops"
    name: str                            # 技能显示名，如 "Git 操作精通"
    category: str                        # 分类: "tool" | "cognitive" | "communication" | "analysis"
    description: str                     # 功能描述
    prerequisites: List[str]             # 前置技能 ID 列表
    max_level: int = 5                   # 最高等级
    base_experience: int = 100           # 升级基础经验值（每级递增）
    skill_type: str = "active"           # "active" 主动技能 | "passive" 被动技能
    cooldown_rounds: int = 0             # 冷却轮数（0=无冷却）
    tags: List[str] = field(default_factory=list)  # 标签，用于分类检索


@dataclass
class SkillState:
    """技能运行时状态（每个会话/每个 Agent 持有）"""
    skill_id: str                        # 关联的 SkillDefinition.skill_id
    level: int = 1                       # 当前等级（1 起步）
    experience: int = 0                  # 当前经验值
    total_uses: int = 0                  # 累计使用次数
    success_count: int = 0               # 成功次数
    last_used_round: int = 0             # 上次使用的对话轮次（用于冷却）
    is_unlocked: bool = True             # 是否已解锁
    unlocked_at: str = ""                # 解锁时间戳
    context_tags: Dict[str, Any] = field(default_factory=dict)  # 上下文标签


@dataclass
class SkillCombo:
    """技能组合定义"""
    combo_id: str                        # 组合唯一 ID
    name: str                            # 组合名称
    skill_ids: List[str]                 # 需要组合的技能 ID 列表
    description: str                     # 组合效果描述
    trigger_condition: str               # 触发条件描述（正则或关键词）
    priority: int = 0                    # 优先级（数字越大越优先）
```

### 2.2 人格化核心数据结构

```python
# ──── 人格化定义结构 ────
@dataclass
class PersonalityProfile:
    """人格档案（跨会话持久化）"""
    profile_id: str                      # 档案唯一 ID
    name: str = ""                       # 人格名称，如 "小爪"
    
    # ── 性格特征（Big Five 简化版） ──
    traits: Dict[str, float] = field(default_factory=lambda: {
        "openness": 0.7,        # 开放性 0.0~1.0（是否愿意尝试新工具）
        "conscientiousness": 0.8,  # 尽责性 0.0~1.0（是否谨慎执行）
        "extraversion": 0.5,    # 外向性 0.0~1.0（回复详细程度）
        "agreeableness": 0.7,   # 宜人性 0.0~1.0（语气友好程度）
        "neuroticism": 0.3,     # 情绪稳定性 0.0~1.0（对错误的敏感度）
    })
    
    # ── 语言风格 ──
    style: Dict[str, Any] = field(default_factory=lambda: {
        "formality": 0.6,        # 正式程度 0.0~1.0
        "emoji_frequency": 0.7,  # emoji 使用频率 0.0~1.0
        "verbosity": 0.5,        # 啰嗦程度 0.0~1.0
        "code_explanation_style": "detailed",  # "detailed" | "concise" | "example_only"
        "greeting_template": "",  # 自定义问候模板
    })
    
    # ── 记忆片段（轻量级长期记忆） ──
    memories: List[MemoryFragment] = field(default_factory=list)
    
    # ── 行为偏好 ──
    preferences: Dict[str, Any] = field(default_factory=lambda: {
        "preferred_tools": [],      # 偏好的工具列表
        "avoided_tools": [],        # 回避的工具列表
        "preferred_model": "",      # 偏好的模型
        "response_language": "zh",  # 回复语言偏好
        "auto_save": True,          # 是否自动保存
        "plan_before_action": False, # 是否倾向于先计划再行动
    })
    
    # ── 元数据 ──
    created_at: str = ""
    updated_at: str = ""
    total_sessions: int = 0          # 总对话次数
    total_messages: int = 0          # 总消息数
    version: str = "1.0.0"


@dataclass
class MemoryFragment:
    """轻量级记忆片段"""
    memory_id: str                     # 唯一 ID
    content: str                       # 记忆内容（一句话描述）
    category: str                      # "user_preference" | "project_context" | "interaction_history" | "skill_milestone"
    importance: float = 0.5            # 重要性 0.0~1.0（影响保留优先级）
    timestamp: str = ""                # 产生时间
    source_round: int = 0              # 来源对话轮次
    tags: List[str] = field(default_factory=list)
    is_pinned: bool = False            # 是否固定（永不遗忘）
```

---

## 3. Skill 技能系统

### 3.1 系统总览

Skill 技能系统分为四个层级：

```
SkillEngine (技能引擎)
  ├── SkillRegistry   (技能注册中心)  → 管理所有可用的技能定义
  ├── SkillExecutor   (技能执行器)    → 执行技能、计算经验值
  ├── SkillTree       (技能树管理器)  → 管理技能依赖/解锁/组合
  └── SkillTrigger    (技能触发器)    → 被动技能自动触发
```

### 3.2 函数详细设计

---

#### 📍 SkillEngine — 技能引擎（主入口）

```python
class SkillEngine:
    """
    技能引擎：Skill 系统的统一入口。
    挂载在 AgentSession 上，协调注册、执行、升级全流程。
    """

    def __init__(self, session_id: str, skill_data_path: str = None):
        """
        初始化技能引擎。

        Args:
            session_id:  当前会话 ID，用于关联技能状态
            skill_data_path: 技能数据持久化路径，默认 "data/skill_data.json"

        Returns: None

        初始化逻辑：
        1. 创建 SkillRegistry 实例（加载所有内置技能定义）
        2. 从 skill_data_path 加载已保存的技能状态
        3. 如果没有持久化数据，为新会话创建默认技能状态
        4. 初始化 SkillExecutor、SkillTree、SkillTrigger
        """
        pass

    def get_skill(self, skill_id: str) -> Optional[SkillState]:
        """
        获取指定技能的运行时状态。

        Args:
            skill_id: 技能 ID

        Returns:
            SkillState | None: 技能状态，未找到返回 None
        """
        pass

    def get_skill_definition(self, skill_id: str) -> Optional[SkillDefinition]:
        """
        获取技能定义（元信息）。

        Args:
            skill_id: 技能 ID

        Returns:
            SkillDefinition | None: 技能定义
        """
        pass

    def list_skills(self, category: str = None, 
                    unlocked_only: bool = True,
                    sort_by: str = "level") -> List[Dict]:
        """
        列出技能列表（带等级、进度信息）。

        Args:
            category:     筛选分类，None 表示全部
            unlocked_only: 仅返回已解锁的技能
            sort_by:      排序方式: "level" | "name" | "category" | "experience"

        Returns:
            List[Dict]: 每项包含 skill_id, name, level, exp, progress%, category
        """
        pass

    def execute_skill(self, skill_id: str, 
                      context: Dict[str, Any],
                      success: bool = True) -> Dict[str, Any]:
        """
        执行一个主动技能。

        Args:
            skill_id: 要执行的技能 ID
            context:  执行上下文（当前 tool_name, 参数, 结果等）
            success:  本次执行是否成功

        Returns:
            Dict: {
                "skill_id": str,
                "level": int,
                "exp_gained": int,
                "leveled_up": bool,
                "new_level": int,
                "unlocked_skills": List[str],  # 升级后新解锁的技能
                "combo_triggered": str | None,  # 触发的技能组合
            }

        执行流程：
        1. 检查技能是否存在且已解锁
        2. 检查冷却期（若在冷却中，返回跳过）
        3. 调用 SkillExecutor.execute() 执行技能逻辑
        4. 计算经验值并调用 add_experience() 增加
        5. 检查是否需要升级
        6. 检查是否触发技能组合
        7. 返回执行结果
        """
        pass

    def add_experience(self, skill_id: str, exp_amount: int) -> Dict:
        """
        为指定技能增加经验值，触发升级检测。

        Args:
            skill_id:   技能 ID
            exp_amount: 增加的经验值

        Returns:
            Dict: {
                "skill_id": str,
                "old_level": int,
                "new_level": int,
                "leveled_up": bool,
                "unlocked_skills": List[str],
                "exp_to_next_level": int,
            }

        升级公式：
            exp_required(level) = base_experience * (level * 1.5)
            例如 base_experience=100: 
            Lv1→Lv2 = 100, Lv2→Lv3 = 300, Lv3→Lv4 = 600, ...
        """
        pass

    def check_combo(self, recent_skill_ids: List[str],
                    context: Dict[str, Any]) -> Optional[SkillCombo]:
        """
        检测是否满足技能组合触发条件。

        Args:
            recent_skill_ids: 最近执行的技能 ID 列表（按时间倒序）
            context:          当前上下文

        Returns:
            SkillCombo | None: 触发的技能组合，不触发返回 None

        检测逻辑：
        1. 遍历所有注册的 SkillCombo
        2. 检查 comb.skill_ids 是否全部出现在 recent_skill_ids 中
        3. 检查 trigger_condition 是否匹配当前 context
        4. 按 priority 排序返回最高优先级的匹配组合
        """
        pass

    def execute_combo(self, combo_id: str,
                      context: Dict[str, Any]) -> Dict:
        """
        执行技能组合，为所有涉及技能增加额外经验值奖励。

        Args:
            combo_id: 技能组合 ID
            context:  执行上下文

        Returns:
            Dict: {
                "combo_id": str,
                "combo_name": str,
                "skills_involved": List[str],
                "bonus_exp_per_skill": int,
                "total_bonus_exp": int,
            }

        经验奖励：
            组合中每个技能获得额外 bonus 经验
            bonus = combo_priority * 10 + 组合技能数 * 5
        """
        pass

    def get_skill_tree(self, root_skill_id: str = None) -> Dict:
        """
        获取技能树结构（用于前端可视化展示）。

        Args:
            root_skill_id: 根技能 ID，None 则返回完整技能树

        Returns:
            Dict: {
                "nodes": [
                    { "id": str, "name": str, "level": int, 
                      "category": str, "unlocked": bool,
                      "progress": float }
                ],
                "edges": [
                    { "from": str, "to": str, "type": "prerequisite" | "combo" }
                ]
            }
        """
        pass

    def save(self, file_path: str = None) -> str:
        """
        持久化保存所有技能状态到 JSON 文件。

        Args:
            file_path: 保存路径，默认 "data/skill_data.json"

        Returns:
            str: 实际保存的文件路径

        保存内容：
            - 所有 SkillState（等级、经验、使用次数等）
            - 技能解锁记录
            - 技能组合历史
        """
        pass

    def load(self, file_path: str) -> bool:
        """
        从 JSON 文件加载技能状态。

        Args:
            file_path: 加载路径

        Returns:
            bool: 加载是否成功
        """
        pass
```

---

#### 📍 SkillRegistry — 技能注册中心

```python
class SkillRegistry:
    """
    技能注册中心：管理所有 SkillDefinition 的注册、发现、检索。
    所有内置技能在系统启动时自动注册。
    """

    # ── 内置技能清单（注册时定义） ──
    BUILTIN_SKILLS = {
        # ═══ 工具类技能 ═══
        "skill_cmd_exec": SkillDefinition(
            skill_id="skill_cmd_exec",
            name="命令执行精通",
            category="tool",
            description="熟练执行系统命令，降低命令执行错误率",
            prerequisites=[],
            max_level=5,
            base_experience=80,
            skill_type="passive",
            tags=["command", "system", "basic"],
        ),
        "skill_file_ops": SkillDefinition(
            skill_id="skill_file_ops",
            name="文件操作大师",
            category="tool",
            description="读写/搜索/替换文件，提升文件操作效率",
            prerequisites=[],
            max_level=5,
            base_experience=100,
            skill_type="passive",
            tags=["file", "basic"],
        ),
        "skill_git_ops": SkillDefinition(
            skill_id="skill_git_ops",
            name="Git 操作专家",
            category="tool",
            description="高效执行 Git 命令，理解仓库状态",
            prerequisites=["skill_cmd_exec"],
            max_level=5,
            base_experience=120,
            skill_type="passive",
            tags=["git", "vcs", "intermediate"],
        ),
        "skill_search_ops": SkillDefinition(
            skill_id="skill_search_ops",
            name="精准搜索大师",
            category="tool",
            description="快速定位文件与内容，提升搜索准确度",
            prerequisites=[],
            max_level=3,
            base_experience=80,
            skill_type="passive",
            tags=["search", "basic"],
        ),

        # ═══ 认知类技能 ═══
        "skill_code_analysis": SkillDefinition(
            skill_id="skill_code_analysis",
            name="代码分析洞察",
            category="cognitive",
            description="深入理解代码结构，识别潜在问题与优化点",
            prerequisites=["skill_file_ops"],
            max_level=5,
            base_experience=150,
            skill_type="active",
            tags=["code", "analysis", "advanced"],
        ),
        "skill_debug_detection": SkillDefinition(
            skill_id="skill_debug_detection",
            name="Bug 侦测之眼",
            category="cognitive",
            description="快速定位代码中的错误与异常模式",
            prerequisites=["skill_code_analysis"],
            max_level=5,
            base_experience=180,
            skill_type="active",
            cooldown_rounds=1,
            tags=["debug", "analysis", "advanced"],
        ),
        "skill_refactor": SkillDefinition(
            skill_id="skill_refactor",
            name="重构能手",
            category="cognitive",
            description="安全高效地重构代码，保持功能一致性",
            prerequisites=["skill_code_analysis", "skill_git_ops"],
            max_level=4,
            base_experience=200,
            skill_type="active",
            cooldown_rounds=2,
            tags=["refactor", "advanced"],
        ),

        # ═══ 沟通类技能 ═══
        "skill_explanation": SkillDefinition(
            skill_id="skill_explanation",
            name="清晰表达",
            category="communication",
            description="以清晰易懂的方式解释技术概念",
            prerequisites=[],
            max_level=3,
            base_experience=60,
            skill_type="passive",
            tags=["communication", "basic"],
        ),
        "skill_teaching": SkillDefinition(
            skill_id="skill_teaching",
            name="教学指导",
            category="communication",
            description="通过引导式教学帮助用户理解",
            prerequisites=["skill_explanation"],
            max_level=4,
            base_experience=100,
            skill_type="active",
            tags=["communication", "intermediate"],
        ),

        # ═══ 分析类技能 ═══
        "skill_project_insight": SkillDefinition(
            skill_id="skill_project_insight",
            name="项目全局洞察",
            category="analysis",
            description="快速把握项目整体结构与架构",
            prerequisites=["skill_search_ops", "skill_file_ops"],
            max_level=4,
            base_experience=160,
            skill_type="active",
            tags=["project", "analysis", "advanced"],
        ),
        "skill_dep_analysis": SkillDefinition(
            skill_id="skill_dep_analysis",
            name="依赖分析专家",
            category="analysis",
            description="分析项目依赖关系，识别耦合与风险",
            prerequisites=["skill_project_insight"],
            max_level=3,
            base_experience=140,
            skill_type="active",
            tags=["dependency", "analysis", "advanced"],
        ),
    }

    # ── 内置技能组合 ──
    BUILTIN_COMBOS = [
        SkillCombo(
            combo_id="combo_quick_debug",
            name="快速定位 + 修复",
            skill_ids=["skill_debug_detection", "skill_file_ops"],
            description="发现 Bug 后立即执行文件操作修复",
            trigger_condition="tool_call:read_file|grep + 用户反馈问题",
            priority=1,
        ),
        SkillCombo(
            combo_id="combo_safe_refactor",
            name="安全重构流程",
            skill_ids=["skill_refactor", "skill_git_ops", "skill_debug_detection"],
            description="重构前分析→执行重构→Git 提交，完整链路",
            trigger_condition="tool_call:write_file + replace 连续3次以上",
            priority=2,
        ),
        SkillCombo(
            combo_id="combo_project_onboarding",
            name="项目上手全流程",
            skill_ids=["skill_project_insight", "skill_search_ops", "skill_explanation"],
            description="全面了解项目后向用户清晰讲解",
            trigger_condition="首次会话 + list_files 触发",
            priority=3,
        ),
    ]

    def __init__(self):
        """
        初始化注册中心，注册所有内置技能定义和技能组合。
        """
        pass

    def register_skill(self, definition: SkillDefinition) -> bool:
        """
        注册一个新技能定义。

        Args:
            definition: SkillDefinition 对象

        Returns:
            bool: 注册成功返回 True，ID 冲突返回 False

        说明：
            - 如果 skill_id 已存在，拒绝注册并返回 False
            - 注册后可通过 get_definition() 查询
        """
        pass

    def register_combo(self, combo: SkillCombo) -> bool:
        """
        注册一个新的技能组合。

        Args:
            combo: SkillCombo 对象

        Returns:
            bool: 注册成功返回 True
        """
        pass

    def get_definition(self, skill_id: str) -> Optional[SkillDefinition]:
        """
        获取技能定义。

        Args:
            skill_id: 技能 ID

        Returns:
            SkillDefinition | None
        """
        pass

    def get_combo(self, combo_id: str) -> Optional[SkillCombo]:
        """
        获取技能组合定义。

        Args:
            combo_id: 组合 ID

        Returns:
            SkillCombo | None
        """
        pass

    def list_all_definitions(self, category: str = None) -> List[SkillDefinition]:
        """
        列出所有注册的技能定义。

        Args:
            category: 筛选分类，None 返回全部

        Returns:
            List[SkillDefinition]
        """
        pass

    def list_all_combos(self) -> List[SkillCombo]:
        """
        列出所有注册的技能组合。

        Returns:
            List[SkillCombo]
        """
        pass

    def check_prerequisites(self, skill_id: str, 
                            owned_skill_ids: Set[str]) -> Tuple[bool, List[str]]:
        """
        检查前置技能是否满足。

        Args:
            skill_id:        目标技能 ID
            owned_skill_ids: 当前已拥有的技能 ID 集合

        Returns:
            Tuple[bool, List[str]]: 
                (是否满足, [缺失的前置技能 ID 列表])
        """
        pass

    def get_unlockable_skills(self, owned_skill_ids: Set[str]) -> List[SkillDefinition]:
        """
        获取当前可解锁的技能列表（前置条件满足但未解锁的）。

        Args:
            owned_skill_ids: 当前已拥有的技能 ID 集合

        Returns:
            List[SkillDefinition]: 可解锁的技能列表
        """
        pass
```

---

#### 📍 SkillExecutor — 技能执行器

```python
class SkillExecutor:
    """
    技能执行器：负责执行具体技能逻辑、计算经验值奖励、管理冷却。
    """

    def __init__(self, registry: SkillRegistry):
        """
        Args:
            registry: SkillRegistry 实例，用于获取技能定义
        """
        pass

    def execute(self, skill_id: str, 
                state: SkillState,
                context: Dict[str, Any]) -> Dict:
        """
        执行一次技能调用（核心方法）。

        Args:
            skill_id: 技能 ID
            state:    技能的当前运行时状态
            context:  执行上下文，包含：
                {
                    "tool_name": str,           # 触发的工具名（如果是工具类技能）
                    "tool_params": dict,        # 工具参数
                    "tool_result": str,         # 工具执行结果摘要
                    "success": bool,            # 是否成功
                    "user_feedback": str,       # 用户的反馈文本
                    "round_number": int,        # 当前对话轮次
                    "error_type": str | None,   # 错误类型（如果有）
                }

        Returns:
            Dict: {
                "executed": bool,              # 是否实际执行
                "skip_reason": str | None,     # 跳过原因（冷却中/未解锁等）
                "exp_gained": int,             # 获得的经验值
                "combo_triggered": str | None, # 触发的组合 ID
                "effects": Dict,               # 技能效果描述
            }

        经验值计算规则：
            - 成功执行: exp = base_exp * (1 + 0.1 * combo_count)
                其中 base_exp = max(5, 30 - level * 3)  # 等级越高，单次经验越少
            - 失败执行: exp = max(1, base_exp // 4)      # 失败也有少量经验
            - 组合奖励: 触发 combo 时额外 +15 exp
            - 首次使用: 首次执行 +20 bonus exp
        """
        pass

    def get_skill_effects(self, skill_id: str, 
                          level: int,
                          context: Dict[str, Any]) -> Dict[str, Any]:
        """
        获取技能在当前等级下的效果加成（用于 system prompt 注入）。

        Args:
            skill_id: 技能 ID
            level:    当前等级
            context:  上下文

        Returns:
            Dict: {
                "description": str,           # 效果描述文本
                "prompt_boost": str,          # 注入到 system prompt 的增强指令
                "stat_boosts": Dict,          # 属性加成: { "accuracy": 0.05, ... }
            }

        示例：
            等级3的 skill_file_ops 返回:
            {
                "description": "文件操作大师 Lv.3 - 文件读写效率提升明显",
                "prompt_boost": "你在文件操作方面经验丰富，能高效读写和搜索文件",
                "stat_boosts": {"file_ops_speed": 0.15, "file_ops_accuracy": 0.1}
            }
        """
        pass

    def is_on_cooldown(self, state: SkillState, 
                       current_round: int) -> bool:
        """
        检查技能是否在冷却中。

        Args:
            state:         技能状态
            current_round: 当前对话轮次

        Returns:
            bool: True 表示冷却中
        """
        pass

    def calculate_exp(self, skill_def: SkillDefinition,
                      state: SkillState,
                      context: Dict[str, Any]) -> int:
        """
        计算单次执行获得的经验值。

        Args:
            skill_def: 技能定义
            state:     当前技能状态
            context:   执行上下文

        Returns:
            int: 本次获得的经验值
        """
        pass
```

---

#### 📍 SkillTree — 技能树管理器

```python
class SkillTree:
    """
    技能树管理器：管理技能之间的依赖关系、解锁条件、可视化。
    """

    def __init__(self, registry: SkillRegistry):
        """
        Args:
            registry: SkillRegistry 实例
        """
        pass

    def build_tree(self, root_skill_id: str = None) -> Dict:
        """
        构建技能树的有向无环图结构。

        Args:
            root_skill_id: 根节点，None 则构建完整森林

        Returns:
            Dict: 树形结构数据，包含节点和边
        """
        pass

    def get_unlock_path(self, target_skill_id: str,
                        owned_skill_ids: Set[str]) -> List[str]:
        """
        获取从当前状态到目标技能的最短解锁路径。

        Args:
            target_skill_id: 目标技能 ID
            owned_skill_ids: 当前拥有的技能 ID 集合

        Returns:
            List[str]: 需要依次解锁的技能 ID 列表（含目标技能本身）

        算法：BFS 最短路径
        """
        pass

    def get_next_milestone(self, owned_skill_ids: Set[str],
                           all_states: Dict[str, SkillState]) -> List[Dict]:
        """
        获取"下一步最值得解锁的技能"推荐列表。

        Args:
            owned_skill_ids: 当前拥有的技能 ID 集合
            all_states:      所有技能的状态字典

        Returns:
            List[Dict]: [
                {
                    "skill_id": str,
                    "name": str,
                    "unlock_cost": str,      # 需要先解锁的前置技能
                    "level_requirement": int, # 前置技能所需等级
                    "recommendation_score": float, # 推荐分数
                },
            ]

        推荐算法：
            score = (前置已满足 ? 10 : 0) 
                  + (等级达标 ? 5 : 0) 
                  + (组合数 * 3) 
                  - (已拥有技能数 * 0.1)
            按 score 降序排列，取前 5 个
        """
        pass

    def validate_tree_integrity(self) -> List[str]:
        """
        验证技能树完整性（检测循环依赖、孤立节点等）。

        Returns:
            List[str]: 问题列表，空列表表示无问题
        """
        pass
```

---

#### 📍 SkillTrigger — 技能触发器

```python
class SkillTrigger:
    """
    技能触发器：负责被动技能的自动检测与触发，以及主动技能的建议推送。
    """

    def __init__(self, engine: SkillEngine):
        """
        Args:
            engine: SkillEngine 实例
        """
        pass

    def on_tool_call(self, tool_name: str, 
                     params: Dict[str, Any],
                     skill_states: Dict[str, SkillState]) -> List[str]:
        """
        工具调用时触发：检测哪些被动技能应生效。

        Args:
            tool_name:    调用的工具名
            params:       工具参数
            skill_states: 当前所有技能状态

        Returns:
            List[str]: 应生效的被动技能 ID 列表（按优先级排序）

        检测逻辑：
            - 工具类技能：tool_name 匹配技能标签 → 激活
            - 例如调用 read_file → skill_file_ops 激活
            - 例如调用 git_status → skill_git_ops 激活
        """
        pass

    def on_tool_result(self, tool_name: str,
                       result: Any,
                       success: bool,
                       skill_states: Dict[str, SkillState]) -> List[Dict]:
        """
        工具执行完成后触发：计算经验值并更新技能状态。

        Args:
            tool_name:    工具名
            result:       执行结果
            success:      是否成功
            skill_states: 当前技能状态

        Returns:
            List[Dict]: 经验值更新记录列表
                [{ "skill_id": str, "exp_gained": int, "leveled_up": bool }]
        """
        pass

    def on_user_message(self, message: str,
                        skill_states: Dict[str, SkillState]) -> List[str]:
        """
        用户发送消息时触发：分析用户意图，推荐可能适合的技能。

        Args:
            message:      用户消息
            skill_states: 当前技能状态

        Returns:
            List[str]: 推荐的技能 ID 列表

        分析策略：
            - 关键词匹配：包含 "git" → 推荐 skill_git_ops
            - 模式匹配："bug|错误|报错" → 推荐 skill_debug_detection
            - 复杂度分析：长消息+代码块 → 推荐 skill_code_analysis
        """
        pass

    def get_active_passive_skills(self, 
                                  context: Dict[str, Any],
                                  skill_states: Dict[str, SkillState]) -> List[str]:
        """
        获取当前上下文中应激活的被动技能列表。

        Args:
            context:      当前上下文
            skill_states: 技能状态

        Returns:
            List[str]: 激活的被动技能 ID 列表
        """
        pass
```

---

## 4. 人格化持久性系统

### 4.1 系统总览

```
PersonalityEngine (人格引擎)
  ├── TraitManager      (性格特征管理器)  → 管理 Big Five 性格特征
  ├── StyleManager      (语言风格管理器)  → 管理回复风格与表达习惯
  ├── MemoryManager     (记忆片段管理器)  → 管理轻量级长期记忆
  ├── PreferenceManager (偏好管理器)      → 管理行为偏好
  └── PersonalityInjector (人格注入器)  → 将人格信息注入 system prompt
```

### 4.2 函数详细设计

---

#### 📍 PersonalityEngine — 人格引擎（主入口）

```python
class PersonalityEngine:
    """
    人格引擎：人格化持久性系统的统一入口。
    挂载在 AgentSession 上，负责人格档案的加载、变更、注入、持久化。
    """

    def __init__(self, profile_id: str = "default",
                 personality_data_path: str = None):
        """
        初始化人格引擎。

        Args:
            profile_id:          人格档案 ID，默认 "default"
            personality_data_path: 持久化路径，默认 "data/personality.json"

        Returns: None

        初始化逻辑：
        1. 从 personality_data_path 加载 PersonalityProfile
        2. 如果不存在，创建默认人格配置（含默认 TraitManager/StyleManager 等）
        3. 初始化所有子管理器
        """
        pass

    def get_profile(self) -> PersonalityProfile:
        """
        获取当前完整人格档案。

        Returns:
            PersonalityProfile: 当前人格档案
        """
        pass

    def get_trait(self, trait_name: str) -> float:
        """
        获取单一性格特征值。

        Args:
            trait_name: 特征名: "openness" | "conscientiousness" | 
                        "extraversion" | "agreeableness" | "neuroticism"

        Returns:
            float: 0.0 ~ 1.0 之间的值
        """
        pass

    def set_trait(self, trait_name: str, value: float) -> bool:
        """
        设置单一性格特征值，触发自动保存。

        Args:
            trait_name: 特征名
            value:      0.0 ~ 1.0 的新值

        Returns:
            bool: 设置是否成功
        """
        pass

    def adjust_trait(self, trait_name: str, delta: float) -> float:
        """
        微调性格特征值（根据行为反馈逐步调整）。

        Args:
            trait_name: 特征名
            delta:      变化量（-0.1 ~ 0.1），可正可负

        Returns:
            float: 调整后的新值

        说明：
            - 每次调整幅度限制在 ±0.05 以内（防止突变）
            - 调整后值限制在 0.05 ~ 0.95 之间
            - 记录调整历史用于回溯
        """
        pass

    def get_style(self) -> Dict:
        """
        获取当前语言风格配置。

        Returns:
            Dict: 风格配置字典
        """
        pass

    def set_style(self, key: str, value: Any) -> bool:
        """
        设置语言风格的某一项。

        Args:
            key:   配置键，如 "formality", "emoji_frequency"
            value: 新值

        Returns:
            bool: 设置是否成功
        """
        pass

    def add_memory(self, content: str, category: str,
                   importance: float = 0.5,
                   tags: List[str] = None) -> str:
        """
        添加一条记忆片段。

        Args:
            content:    记忆内容
            category:   "user_preference" | "project_context" | 
                        "interaction_history" | "skill_milestone"
            importance: 重要性 0.0~1.0
            tags:       标签列表

        Returns:
            str: 新生成的 memory_id

        说明：
            - 自动检查是否与已有记忆重复（内容相似度 > 0.85 视为重复）
            - 自动触发 MemoryManager.prune() 检查是否需要清理旧记忆
        """
        pass

    def get_memories(self, category: str = None,
                     min_importance: float = 0.0,
                     max_count: int = 10) -> List[MemoryFragment]:
        """
        获取记忆片段列表。

        Args:
            category:      筛选分类，None 返回全部
            min_importance: 最低重要性阈值
            max_count:      最大返回数量

        Returns:
            List[MemoryFragment]: 按重要性降序排列
        """
        pass

    def pin_memory(self, memory_id: str) -> bool:
        """
        固定一条记忆（永不遗忘）。

        Args:
            memory_id: 记忆 ID

        Returns:
            bool: 操作是否成功
        """
        pass

    def unpin_memory(self, memory_id: str) -> bool:
        """
        取消固定一条记忆。

        Args:
            memory_id: 记忆 ID

        Returns:
            bool: 操作是否成功
        """
        pass

    def delete_memory(self, memory_id: str) -> bool:
        """
        删除一条记忆。

        Args:
            memory_id: 记忆 ID

        Returns:
            bool: 操作是否成功
        """
        pass

    def get_preference(self, key: str) -> Any:
        """
        获取行为偏好值。

        Args:
            key: 偏好键名，如 "preferred_tools", "response_language"

        Returns:
            Any: 偏好值
        """
        pass

    def set_preference(self, key: str, value: Any) -> bool:
        """
        设置行为偏好值。

        Args:
            key:   偏好键名
            value: 新值

        Returns:
            bool: 设置是否成功
        """
        pass

    def generate_personality_prompt(self) -> str:
        """
        生成完整的人格注入文本（用于 system prompt 注入）。

        Returns:
            str: 格式化的人格描述文本，包含性格、风格、记忆、偏好

        输出示例：
            '''
            ## 🧬 人格特征
            - 性格：开放性高(0.8)、尽责性高(0.85)、外向性中等(0.5)
            - 风格：倾向于详细解释，喜欢用 emoji，语气友好
            - 偏好：喜欢 Python 项目，习惯先分析再行动
            - 记住：用户偏好简洁回复、用户项目使用 FastAPI 框架
            '''
        """
        pass

    def get_personality_stats(self) -> Dict:
        """
        获取人格统计信息（用于前端展示）。

        Returns:
            Dict: {
                "profile_id": str,
                "name": str,
                "traits_radar": { trait: value },    # 雷达图数据
                "style_preview": str,                 # 风格预览文本
                "memory_count": int,
                "pinned_memories": int,
                "total_sessions": int,
                "total_messages": int,
                "last_updated": str,
            }
        """
        pass

    def save(self, file_path: str = None) -> str:
        """
        持久化保存人格档案到 JSON 文件。

        Args:
            file_path: 保存路径，默认 "data/personality.json"

        Returns:
            str: 实际保存的文件路径
        """
        pass

    def load(self, file_path: str) -> bool:
        """
        从 JSON 文件加载人格档案。

        Args:
            file_path: 加载路径

        Returns:
            bool: 加载是否成功
        """
        pass

    def reset_to_defaults(self) -> bool:
        """
        重置人格配置为出厂默认值。

        Returns:
            bool: 重置是否成功
        """
        pass
```

---

#### 📍 TraitManager — 性格特征管理器

```python
class TraitManager:
    """
    性格特征管理器：管理 Big Five 性格特征的读取、修改、渐变调整。
    """

    def __init__(self, traits: Dict[str, float]):
        """
        Args:
            traits: 初始特征字典，如 {"openness": 0.7, ...}
        """
        pass

    def get(self, trait_name: str) -> Optional[float]:
        """
        获取特征值。

        Args:
            trait_name: 特征名

        Returns:
            float | None: 0.0~1.0 或 None
        """
        pass

    def set(self, trait_name: str, value: float) -> bool:
        """
        设置特征值（带边界检查）。

        Args:
            trait_name: 特征名
            value:      0.0~1.0

        Returns:
            bool: 是否成功
        """
        pass

    def adjust(self, trait_name: str, delta: float) -> float:
        """
        微调特征值（渐变，每次不超过 ±0.05）。

        Args:
            trait_name: 特征名
            delta:      变化量

        Returns:
            float: 调整后的值
        """
        pass

    def get_all(self) -> Dict[str, float]:
        """
        获取所有特征值。

        Returns:
            Dict[str, float]: 特征名字典
        """
        pass

    def get_trait_impact(self, trait_name: str) -> Dict[str, str]:
        """
        获取该特征值对行为的具体影响描述。

        Args:
            trait_name: 特征名

        Returns:
            Dict[str, str]: {
                "high": "开放性高 → 愿意尝试新工具、新方法",
                "low": "开放性低 → 偏好熟悉的工具和工作流",
                "current": "当前值 0.7 → 比较愿意尝试新事物",
            }
        """
        pass

    def to_prompt_text(self) -> str:
        """
        将性格特征转为可读的描述文本。

        Returns:
            str: 如 "你是一位开放性较高、尽责性很高、偏内向的助手"
        """
        pass
```

---

#### 📍 StyleManager — 语言风格管理器

```python
class StyleManager:
    """
    语言风格管理器：管理回复的语言风格、正式程度、emoji 使用等。
    """

    def __init__(self, style: Dict[str, Any]):
        """
        Args:
            style: 风格配置字典
        """
        pass

    def get(self, key: str) -> Any:
        """
        获取风格配置项。

        Args:
            key: 配置键名

        Returns:
            Any: 配置值
        """
        pass

    def set(self, key: str, value: Any) -> bool:
        """
        设置风格配置项（带类型校验）。

        Args:
            key:   配置键名
            value: 新值

        Returns:
            bool: 是否成功
        """
        pass

    def get_all(self) -> Dict[str, Any]:
        """
        获取所有风格配置。

        Returns:
            Dict[str, Any]
        """
        pass

    def get_formatted_style_guide(self) -> str:
        """
        获取格式化的风格指南文本（注入 system prompt）。

        Returns:
            str: 风格指南文本

        示例：
            '''
            你的回复风格：
            - 正式程度：中等（60%）
            - Emoji 使用：较频繁（70%）
            - 详细程度：适中（50%）
            - 代码解释风格：详细讲解
            '''
        """
        pass

    def apply_style_to_text(self, text: str) -> str:
        """
        根据风格配置对文本进行后处理调整。

        Args:
            text: 原始回复文本

        Returns:
            str: 调整后的文本

        调整逻辑：
            - formality < 0.3: 缩略语替换（"不要"→"别"）
            - formality > 0.8: 正式用语替换（"搞"→"执行"）
            - emoji_frequency > 0.6: 在句尾适当添加 emoji
            - verbosity < 0.3: 精简长段落
        """
        pass

    def learn_from_user(self, user_message: str, 
                        agent_reply: str) -> Dict[str, float]:
        """
        从用户的反馈中学习风格偏好（被动学习）。

        Args:
            user_message: 用户消息
            agent_reply:  Agent 的回复

        Returns:
            Dict[str, float]: 建议的调整值
                { "formality": +0.01, "verbosity": -0.02 }

        学习逻辑：
            - 用户回复比 Agent 回复更短 → 降低 verbosity
            - 用户使用大量 emoji → 提高 emoji_frequency
            - 用户使用正式用语 → 提高 formality
        """
        pass
```

---

#### 📍 MemoryManager — 记忆片段管理器

```python
class MemoryManager:
    """
    记忆片段管理器：管理轻量级长期记忆的增删改查、遗忘、压缩。
    记忆数量上限为 50 条（固定条 + 非固定条合计）。
    """

    MAX_MEMORIES = 50        # 最大记忆条数
    MAX_UNPINNED = 30        # 最大非固定记忆条数
    SIMILARITY_THRESHOLD = 0.85  # 重复检测阈值

    def __init__(self, memories: List[MemoryFragment]):
        """
        Args:
            memories: 初始记忆片段列表
        """
        pass

    def add(self, content: str, category: str, 
            importance: float = 0.5,
            tags: List[str] = None) -> str:
        """
        添加一条记忆。

        Args:
            content:    记忆内容
            category:   分类
            importance: 重要性
            tags:       标签

        Returns:
            str: memory_id
        """
        pass

    def get(self, memory_id: str) -> Optional[MemoryFragment]:
        """
        获取单条记忆。

        Args:
            memory_id: 记忆 ID

        Returns:
            MemoryFragment | None
        """
        pass

    def query(self, category: str = None,
              min_importance: float = 0.0,
              max_count: int = 10,
              keyword: str = None) -> List[MemoryFragment]:
        """
        查询记忆（支持分类/重要性/关键词过滤）。

        Args:
            category:      分类过滤
            min_importance: 最低重要性
            max_count:      最大返回数
            keyword:       关键词搜索（模糊匹配）

        Returns:
            List[MemoryFragment]: 按重要性降序
        """
        pass

    def update_importance(self, memory_id: str, 
                          delta: float) -> float:
        """
        更新记忆的重要性分数（使用时增减）。

        Args:
            memory_id: 记忆 ID
            delta:     变化量

        Returns:
            float: 更新后的重要性
        """
        pass

    def delete(self, memory_id: str) -> bool:
        """
        删除一条记忆。

        Args:
            memory_id: 记忆 ID

        Returns:
            bool: 是否成功
        """
        pass

    def pin(self, memory_id: str) -> bool:
        """
        固定记忆（永不遗忘）。

        Args:
            memory_id: 记忆 ID

        Returns:
            bool: 是否成功
        """
        pass

    def unpin(self, memory_id: str) -> bool:
        """
        取消固定记忆。

        Args:
            memory_id: 记忆 ID

        Returns:
            bool: 是否成功
        """
        pass

    def prune(self) -> List[str]:
        """
        清理低重要性记忆（超出上限时触发遗忘）。

        Returns:
            List[str]: 被删除的记忆 ID 列表

        遗忘策略：
            1. 保留所有 pinned 记忆
            2. 按重要性降序保留 MAX_UNPINNED 条非固定记忆
            3. 删除超过上限且重要性 < 0.3 的记忆
            4. 如果仍超上限，删除重要性最低的
        """
        pass

    def search_by_keyword(self, keyword: str) -> List[MemoryFragment]:
        """
        关键词搜索记忆。

        Args:
            keyword: 搜索关键词

        Returns:
            List[MemoryFragment]: 匹配结果
        """
        pass

    def count(self, pinned_only: bool = False) -> int:
        """
        统计记忆数量。

        Args:
            pinned_only: 是否只统计固定的

        Returns:
            int: 数量
        """
        pass

    def to_prompt_text(self, max_count: int = 5) -> str:
        """
        生成记忆摘要文本（用于注入 system prompt）。

        Args:
            max_count: 最多包含的记忆数

        Returns:
            str: 格式化的记忆摘要
        """
        pass

    def get_all(self) -> List[MemoryFragment]:
        """
        获取所有记忆。

        Returns:
            List[MemoryFragment]
        """
        pass
```

---

#### 📍 PreferenceManager — 偏好管理器

```python
class PreferenceManager:
    """
    偏好管理器：管理行为偏好配置的读写、自动学习、推理。
    """

    def __init__(self, preferences: Dict[str, Any]):
        """
        Args:
            preferences: 初始偏好字典
        """
        pass

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取偏好值。

        Args:
            key:     偏好键名
            default: 默认值

        Returns:
            Any: 偏好值
        """
        pass

    def set(self, key: str, value: Any) -> bool:
        """
        设置偏好值。

        Args:
            key:   偏好键名
            value: 新值

        Returns:
            bool: 是否成功
        """
        pass

    def get_all(self) -> Dict[str, Any]:
        """
        获取所有偏好。

        Returns:
            Dict[str, Any]
        """
        pass

    def infer_preference_from_behavior(self, 
                                       tool_usage_log: List[Dict]) -> Dict:
        """
        从工具使用日志推断用户偏好（学习阶段）。

        Args:
            tool_usage_log: 工具使用记录列表
                [{ "tool_name": str, "count": int, "success_rate": float }]

        Returns:
            Dict: 推断出的偏好调整建议
                { "preferred_tools": ["read_file", "grep"], ... }

        推断逻辑：
            - 使用频率前 3 且成功率 > 0.8 → 加入 preferred_tools
            - 使用频率最低且成功率 < 0.5 → 加入 avoided_tools
        """
        pass

    def to_prompt_text(self) -> str:
        """
        生成偏好描述文本。

        Returns:
            str: 偏好描述
        """
        pass
```

---

#### 📍 PersonalityInjector — 人格注入器

```python
class PersonalityInjector:
    """
    人格注入器：负责将人格信息注入到 System Prompt 中，
    以及在回复时进行风格后处理。
    """

    def __init__(self, engine: PersonalityEngine):
        """
        Args:
            engine: PersonalityEngine 实例
        """
        pass

    def inject_into_system_prompt(self, 
                                  base_system_prompt: str) -> str:
        """
        将人格信息注入到系统提示词中。

        Args:
            base_system_prompt: 原始的 system prompt

        Returns:
            str: 注入人格信息后的 system prompt

        注入结构：
            在 system prompt 末尾追加以下内容：
            ```
            ## 🧬 人格特征（跨会话持久）
            [Traits 描述]
            
            ## 💬 语言风格
            [Style 描述]
            
            ## 📝 长期记忆
            [记忆摘要]
            
            ## ⭐ 行为偏好
            [偏好描述]
            ```
        """
        pass

    def post_process_response(self, text: str) -> str:
        """
        对 Agent 的回复进行风格后处理。

        Args:
            text: 原始回复文本

        Returns:
            str: 风格调整后的文本

        调用 StyleManager.apply_style_to_text()
        """
        pass

    def should_use_skill_suggestion(self, 
                                    personality: PersonalityProfile) -> bool:
        """
        根据人格判断是否应该推送技能建议。

        Args:
            personality: 人格档案

        Returns:
            bool: True 表示应该推送

        判断逻辑：
            - openness > 0.6 → 推荐新技能
            - extraversion > 0.5 → 主动展示技能进度
            - 否则仅在用户询问时展示
        """
        pass

    def get_personality_biased_tool_ranking(self, 
                                            available_tools: List[str],
                                            personality: PersonalityProfile
                                            ) -> List[str]:
        """
        根据人格偏好对工具进行排序。

        Args:
            available_tools: 可用工具列表
            personality:     人格档案

        Returns:
            List[str]: 排序后的工具列表

        排序逻辑：
            - 偏好的工具排前面
            - openness 高 → 新工具往前
            - conscientiousness 高 → 安全检查类工具往前
        """
        pass
```

---

## 5. 系统集成与交互流程

### 5.1 与 AgentSession 的集成

```
AgentSession (原)                     AgentSession (新)
┌──────────────────────┐              ┌──────────────────────────────┐
│                      │              │                              │
│  mode_mgr            │              │  mode_mgr                    │
│  msgs                │              │  msgs                        │
│  client              │              │  client                      │
│  ...                 │              │  ...                         │
│                      │              │                              │
│                      │     +------  │  skill_engine: SkillEngine   │◄── Skill 技能系统
│                      │     |       │  personality: PersonalityEngine│◄── 人格化持久性
│                      │     |       │                              │
└──────────────────────┘     |       └──────────────────────────────┘
                             |                    │
                             |                    ▼
                             |       ┌──────────────────────────┐
                             |       │  build_system_prompt()    │
                             |       │   (prompts.py)            │
                             |       │                           │
                             |       │  原逻辑: 模式 + 工具 + 安全 │
                             |       │  +新逻辑: 技能注入 + 人格注入│
                             |       └──────────────────────────┘
                             |
                             |   在 tools/__init__.py 中注册新工具:
                             |   - tool_skill_list       (列出技能)
                             |   - tool_skill_detail     (查看技能详情)
                             |   - tool_personality_show (查看人格档案)
                             |   - tool_personality_set  (设置人格)
                             |   - tool_memory_add       (手动添加记忆)
                             |   - tool_memory_list      (查看记忆列表)
```

### 5.2 核心交互流程

#### 流程A：对话时技能自动触发

```
用户发送消息
    │
    ▼
AgentSession.chat()
    │
    ├─▶ SkillTrigger.on_user_message()     ← 分析用户意图，推荐技能
    │
    ├─▶ PersonalityInjector.inject_into_system_prompt()
    │       │                                ← 注入人格 + 技能 info 到 prompt
    │       └─▶ 增加 system prompt 的 "技能状态" 段落
    │
    ├─▶ 调用 AI API（携带增强后的 system prompt）
    │
    ├─▶ AI 回复 → 决定调用工具
    │       │
    │       ▼
    ├─▶ SkillTrigger.on_tool_call()         ← 激活被动技能
    │       │
    │       ▼
    ├─▶ 执行工具
    │       │
    │       ▼
    ├─▶ SkillTrigger.on_tool_result()       ← 计算经验值、升级检测
    │       │
    │       ├─▶ SkillEngine.add_experience()
    │       ├─▶ SkillEngine.check_combo()
    │       └─▶ PersonalityEngine.adjust_trait()  ← 行为影响性格微调
    │
    ├─▶ PersonalityInjector.post_process_response()  ← 风格后处理
    │
    └─▶ 输出回复给用户
```

#### 流程B：跨会话人格继承

```
新会话启动
    │
    ▼
AgentSession.__init__()
    │
    ├─▶ PersonalityEngine(profile_id="default")
    │       │  └─▶ 从 data/personality.json 加载人格档案
    │       │
    │       ▼
    ├─▶ SkillEngine(session_id)
    │       │  └─▶ 从 data/skill_data.json 加载技能状态
    │       │
    │       ▼
    ├─▶ build_system_prompt()
    │       │  └─▶ PersonalityInjector.inject_into_system_prompt()
    │       │       └─▶ 加入 "你是一位开放性高、喜欢详细解释的助手..."
    │       │
    │       ▼
    └─▶ 用户：人格继承了！🎉
```

#### 流程C：技能升级通知

```
SkillEngine.add_experience()
    │
    ├─▶ 计算是否升级
    │       │
    │       ▼
    ├─▶ [升级] → 生成升级通知文本
    │       │
    │       ├─▶ SkillEngine.check_combo()
    │       │       └─▶ 检查是否解锁新组合
    │       │
    │       └─▶ SkillRegistry.get_unlockable_skills()
    │               └─▶ 检查是否有新技能可解锁
    │
    ▼
将通知插入到回复中：
"✨【技能升级】文件操作大师 Lv.2 → Lv.3！文件读写效率提升15%"
"🔓 新技能可解锁：『代码分析洞察』（需文件操作大师 Lv.2，已满足！）"
```

---

## 6. 配置文件与存储规划

### 6.1 文件结构

```
TennineClaw/
├── data/                          # [新] 数据目录
│   ├── skill_data.json            # [新] 技能状态持久化
│   ├── personality.json           # [新] 人格档案持久化
│   └── skill_personality_schema.json # [新] JSON Schema 校验
│
├── skill_system/                  # [新] 技能系统模块包
│   ├── __init__.py                # 导出 SkillEngine
│   ├── engine.py                  # SkillEngine
│   ├── registry.py                # SkillRegistry（含内置技能定义）
│   ├── executor.py                # SkillExecutor
│   ├── tree.py                    # SkillTree
│   └── trigger.py                 # SkillTrigger
│
├── personality/                   # [新] 人格化系统模块包
│   ├── __init__.py                # 导出 PersonalityEngine
│   ├── engine.py                  # PersonalityEngine
│   ├── trait_manager.py           # TraitManager
│   ├── style_manager.py           # StyleManager
│   ├── memory_manager.py          # MemoryManager
│   ├── preference_manager.py      # PreferenceManager
│   └── injector.py                # PersonalityInjector
│
├── main.py                        # [修改] AgentSession 集成 skill + personality
├── prompts.py                     # [修改] build_system_prompt 增加技能/人格注入
├── tools/__init__.py              # [修改] 注册技能/人格相关工具
├── web_api.py                     # [修改] 增加技能/人格的 API 端点
└── static/                        # [修改] UI 增加技能树/人格面板
```

### 6.2 skill_data.json 存储格式

```json
{
  "version": "1.0.0",
  "last_updated": "2026-05-21 00:43:57",
  "profile_id": "default",
  "skills": {
    "skill_file_ops": {
      "level": 3,
      "experience": 245,
      "total_uses": 28,
      "success_count": 26,
      "last_used_round": 15,
      "is_unlocked": true,
      "unlocked_at": "2026-05-20 15:30:00"
    },
    "skill_git_ops": {
      "level": 2,
      "experience": 120,
      "total_uses": 12,
      "success_count": 11,
      "last_used_round": 12,
      "is_unlocked": true,
      "unlocked_at": "2026-05-20 16:00:00"
    }
  },
  "combo_history": [
    {
      "combo_id": "combo_project_onboarding",
      "triggered_at": "2026-05-20 15:35:00",
      "skills_involved": ["skill_project_insight", "skill_search_ops", "skill_explanation"]
    }
  ]
}
```

### 6.3 personality.json 存储格式

```json
{
  "version": "1.0.0",
  "last_updated": "2026-05-21 00:43:57",
  "profile_id": "default",
  "name": "小爪",
  "traits": {
    "openness": 0.75,
    "conscientiousness": 0.82,
    "extraversion": 0.48,
    "agreeableness": 0.72,
    "neuroticism": 0.28
  },
  "style": {
    "formality": 0.55,
    "emoji_frequency": 0.72,
    "verbosity": 0.50,
    "code_explanation_style": "detailed",
    "greeting_template": ""
  },
  "memories": [
    {
      "memory_id": "mem_001",
      "content": "用户偏好使用 DeepSeek 模型",
      "category": "user_preference",
      "importance": 0.8,
      "timestamp": "2026-05-20 15:30:00",
      "source_round": 1,
      "tags": ["model", "preference"],
      "is_pinned": true
    },
    {
      "memory_id": "mem_002",
      "content": "用户项目 TennineClaw 使用 FastAPI + Gradio",
      "category": "project_context",
      "importance": 0.7,
      "timestamp": "2026-05-20 15:35:00",
      "source_round": 3,
      "tags": ["project", "tech_stack"],
      "is_pinned": false
    }
  ],
  "preferences": {
    "preferred_tools": ["read_file", "grep", "git_status"],
    "avoided_tools": [],
    "preferred_model": "deepseek-chat",
    "response_language": "zh",
    "auto_save": true,
    "plan_before_action": false
  },
  "total_sessions": 5,
  "total_messages": 128
}
```

---

## 7. 扩展性设计

### 7.1 新技能注册方式

开发者在 `registry.py` 的 `BUILTIN_SKILLS` 字典中按格式添加即可：

```python
# 示例：注册一个新技能
"skill_docker_ops": SkillDefinition(
    skill_id="skill_docker_ops",
    name="Docker 容器管理",
    category="tool",
    description="熟练管理 Docker 容器与镜像",
    prerequisites=["skill_cmd_exec"],        # 需要命令执行前置
    max_level=5,
    base_experience=140,
    skill_type="passive",
    tags=["docker", "container", "devops"],
)
```

### 7.2 自定义技能组合

```python
SkillCombo(
    combo_id="combo_devops_pipeline",
    name="DevOps 流水线",
    skill_ids=["skill_cmd_exec", "skill_docker_ops", "skill_git_ops"],
    description="从代码拉取 → 构建 → Docker 部署全流程",
    trigger_condition="连续调用 git + cmd 命令构建相关操作",
    priority=1,
)
```

### 7.3 人格档案多 Profile 支持

```python
# 可创建多个人格档案，适用于不同场景
personality_engine = PersonalityEngine(profile_id="work")   # 工作人格：正式、高效
personality_engine = PersonalityEngine(profile_id="casual") # 休闲人格：轻松、活泼
personality_engine = PersonalityEngine(profile_id="teacher")# 教学人格：耐心、详细
```

### 7.4 未来扩展方向

| 方向 | 说明 |
|------|------|
| 🧩 **技能市场** | 支持从远程仓库下载/分享技能定义 |
| 📈 **成就系统** | 基于技能里程碑生成成就徽章 |
| 🤝 **多 Agent 技能共享** | 不同会话/不同 Agent 间共享技能进度 |
| 🧠 **深度长期记忆** | 引入向量数据库，支持语义级记忆检索 |
| 🎮 **游戏化 UI** | 前端展示技能树、经验条、人格雷达图 |
| 📊 **技能分析报告** | 统计技能使用分布、成长曲线、效率提升 |

---

## 📋 附录：变更清单

### 新增文件

| 文件 | 说明 |
|------|------|
| `data/skill_data.json` | 技能状态持久化文件 |
| `data/personality.json` | 人格档案持久化文件 |
| `data/skill_personality_schema.json` | JSON Schema 校验 |
| `skill_system/__init__.py` | 技能系统包 |
| `skill_system/engine.py` | SkillEngine 主类 |
| `skill_system/registry.py` | SkillRegistry + 内置技能定义 |
| `skill_system/executor.py` | SkillExecutor |
| `skill_system/tree.py` | SkillTree |
| `skill_system/trigger.py` | SkillTrigger |
| `personality/__init__.py` | 人格化系统包 |
| `personality/engine.py` | PersonalityEngine 主类 |
| `personality/trait_manager.py` | TraitManager |
| `personality/style_manager.py` | StyleManager |
| `personality/memory_manager.py` | MemoryManager |
| `personality/preference_manager.py` | PreferenceManager |
| `personality/injector.py` | PersonalityInjector |

### 修改文件

| 文件 | 改动内容 |
|------|----------|
| `main.py` | AgentSession 新增 `skill_engine`、`personality` 属性；`__init__` 中初始化；`chat()` 中集成触发逻辑 |
| `prompts.py` | `build_system_prompt()` 增加技能状态 + 人格注入参数 |
| `tools/__init__.py` | 新增 6 个工具注册：skill_list, skill_detail, personality_show, personality_set, memory_add, memory_list |
| `web_api.py` | 新增技能/人格相关 API 端点（查询、设置、重置） |
| `static/` | 新增技能树可视化面板 + 人格雷达图组件 |
| `config.py` | 新增技能/人格相关配置项（如技能数据路径、记忆上限等） |

---

> **文档版本**: v1.0 | **作者**: TennineClaw Team | **日期**: 2026-05-21
