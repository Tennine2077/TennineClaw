# ============================================================
# TennineClaw - 人格化数据模型
# ============================================================
# 定义人格化持久性系统的核心数据结构，包括性格特征（OCEAN）、
# 语言风格、行为偏好、记忆片段等，支持 JSON 序列化/反序列化。
# ============================================================

from __future__ import annotations
import os
import json
import uuid
from enum import Enum, auto
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime


# ============================================================
# 人格维度模型（OCEAN 五大人格）
# ============================================================

@dataclass
class PersonalityTrait:
    """性格特征 — 基于 OCEAN 五因素模型

    每个维度取值 0~100，表示在该维度上的倾向程度。
    """
    openness: int = 50           # 开放性：好奇/创新 ↔ 传统/务实
    conscientiousness: int = 50  # 尽责性：有条理/勤奋 ↔ 随性/灵活
    extraversion: int = 50       # 外向性：热情/活跃 ↔ 内敛/安静
    agreeableness: int = 50      # 宜人性：友善/合作 ↔ 竞争/直接
    neuroticism: int = 30        # 神经质：敏感/谨慎 ↔ 稳定/从容

    def __post_init__(self):
        self._clamp_values()

    def _clamp_values(self):
        """将所有维度的值限制在 0~100 范围内"""
        for attr in ["openness", "conscientiousness", "extraversion",
                     "agreeableness", "neuroticism"]:
            val = getattr(self, attr)
            setattr(self, attr, max(0, min(100, val)))

    def adjust(self, dimension: str, delta: int):
        """调整某个维度的值（增量方式）"""
        if hasattr(self, dimension):
            current = getattr(self, dimension)
            setattr(self, dimension, max(0, min(100, current + delta)))

    def get_dominant_traits(self, top_n: int = 3) -> List[Tuple[str, int, str]]:
        """获取最突出的性格特征

        Returns:
            List of (维度名, 分值, 描述)
        """
        all_traits = [
            ("openness", self.openness, "开放性"),
            ("conscientiousness", self.conscientiousness, "尽责性"),
            ("extraversion", self.extraversion, "外向性"),
            ("agreeableness", self.agreeableness, "宜人性"),
            ("neuroticism", self.neuroticism, "神经质"),
        ]
        # 按距离中间值 (50) 的偏差排序
        all_traits.sort(key=lambda x: abs(x[1] - 50), reverse=True)
        return all_traits[:top_n]

    def get_summary(self) -> str:
        """获取性格特征的文字描述"""
        descriptions = []
        if self.openness > 65:
            descriptions.append("开放好奇，乐于尝试新事物")
        elif self.openness < 35:
            descriptions.append("务实传统，偏好熟悉的方式")

        if self.conscientiousness > 65:
            descriptions.append("有条理且勤奋，注重细节")
        elif self.conscientiousness < 35:
            descriptions.append("随性灵活，不喜欢被约束")

        if self.extraversion > 65:
            descriptions.append("热情活跃，乐于互动")
        elif self.extraversion < 35:
            descriptions.append("内敛安静，偏好独立工作")

        if self.agreeableness > 65:
            descriptions.append("友善合作，重视和谐")
        elif self.agreeableness < 35:
            descriptions.append("直接坦率，注重效率")

        if self.neuroticism > 65:
            descriptions.append("谨慎敏感，注重安全")
        elif self.neuroticism < 35:
            descriptions.append("情绪稳定，从容应对压力")

        return "、".join(descriptions) if descriptions else "性格均衡，适应性强"

    def to_dict(self) -> Dict[str, int]:
        return {
            "openness": self.openness,
            "conscientiousness": self.conscientiousness,
            "extraversion": self.extraversion,
            "agreeableness": self.agreeableness,
            "neuroticism": self.neuroticism,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, int]) -> "PersonalityTrait":
        return cls(
            openness=data.get("openness", 50),
            conscientiousness=data.get("conscientiousness", 50),
            extraversion=data.get("extraversion", 50),
            agreeableness=data.get("agreeableness", 50),
            neuroticism=data.get("neuroticism", 30),
        )


# ============================================================
# 语言风格
# ============================================================

@dataclass
class LanguageStyle:
    """语言风格参数

    各维度取值 0~100
    """
    formality: int = 50           # 正式度：正式严谨 ↔ 随意口语
    humor: int = 30               # 幽默度：幽默风趣 ↔ 严肃专业
    conciseness: int = 60         # 简洁度：简洁精炼 ↔ 详细丰富
    enthusiasm: int = 50          # 热情度：热情洋溢 ↔ 冷静克制
    technical_depth: int = 50     # 专业深度：专业深入 ↔ 通俗易懂

    def __post_init__(self):
        self._clamp_values()

    def _clamp_values(self):
        """将所有值限制在 0~100 范围内"""
        for attr in ["formality", "humor", "conciseness",
                     "enthusiasm", "technical_depth"]:
            val = getattr(self, attr)
            setattr(self, attr, max(0, min(100, val)))

    def adjust(self, dimension: str, delta: int):
        """调整某个维度的值"""
        if hasattr(self, dimension):
            current = getattr(self, dimension)
            setattr(self, dimension, max(0, min(100, current + delta)))

    def get_style_tags(self) -> List[str]:
        """获取语言风格标签"""
        tags = []
        if self.formality > 65: tags.append("正式")
        elif self.formality < 35: tags.append("随性")
        if self.humor > 65: tags.append("幽默")
        elif self.humor < 35: tags.append("严肃")
        if self.conciseness > 65: tags.append("简洁")
        elif self.conciseness < 35: tags.append("详细")
        if self.enthusiasm > 65: tags.append("热情")
        elif self.enthusiasm < 35: tags.append("冷静")
        if self.technical_depth > 65: tags.append("专业")
        elif self.technical_depth < 35: tags.append("通俗")
        return tags

    def to_dict(self) -> Dict[str, int]:
        return {
            "formality": self.formality,
            "humor": self.humor,
            "conciseness": self.conciseness,
            "enthusiasm": self.enthusiasm,
            "technical_depth": self.technical_depth,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, int]) -> "LanguageStyle":
        return cls(
            formality=data.get("formality", 50),
            humor=data.get("humor", 30),
            conciseness=data.get("conciseness", 60),
            enthusiasm=data.get("enthusiasm", 50),
            technical_depth=data.get("technical_depth", 50),
        )


# ============================================================
# 行为偏好
# ============================================================

@dataclass
class BehaviorPreference:
    """行为偏好"""
    decision_style: str = "balanced"   # 决策风格: cautious | balanced | adventurous
    risk_tolerance: int = 40           # 风险容忍度 (0~100)
    collaboration_mode: str = "auto"   # 协作模式: auto | manual | interactive
    creativity_level: int = 50         # 创造力水平 (0~100)
    detail_orientation: int = 60       # 细节导向 (0~100)
    preferred_tools: List[str] = field(default_factory=list)  # 偏好工具列表
    avoid_topics: List[str] = field(default_factory=list)     # 回避话题
    learning_priority: str = "balance" # 学习优先级: speed | depth | balance

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_style": self.decision_style,
            "risk_tolerance": self.risk_tolerance,
            "collaboration_mode": self.collaboration_mode,
            "creativity_level": self.creativity_level,
            "detail_orientation": self.detail_orientation,
            "preferred_tools": self.preferred_tools,
            "avoid_topics": self.avoid_topics,
            "learning_priority": self.learning_priority,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BehaviorPreference":
        return cls(
            decision_style=data.get("decision_style", "balanced"),
            risk_tolerance=data.get("risk_tolerance", 40),
            collaboration_mode=data.get("collaboration_mode", "auto"),
            creativity_level=data.get("creativity_level", 50),
            detail_orientation=data.get("detail_orientation", 60),
            preferred_tools=data.get("preferred_tools", []),
            avoid_topics=data.get("avoid_topics", []),
            learning_priority=data.get("learning_priority", "balance"),
        )


# ============================================================
# 记忆片段
# ============================================================

@dataclass
class MemoryFragment:
    """记忆片段 — 跨会话保持的关键信息"""
    id: str = ""
    topic: str = ""                  # 话题/主题
    summary: str = ""                # 记忆摘要
    importance: float = 0.5          # 重要性 (0.0~1.0)
    sentiment: float = 0.0           # 情感倾向 (-1.0~1.0)
    created_at: str = ""             # 创建时间
    last_accessed_at: str = ""       # 最后访问时间
    access_count: int = 0            # 访问次数
    tags: List[str] = field(default_factory=list)  # 标签
    source: str = "conversation"     # 来源: conversation | manual | system
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.id:
            self.id = f"mem_{uuid.uuid4().hex[:8]}"
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def access(self):
        """访问记忆（更新访问计数和时间）"""
        self.access_count += 1
        self.last_accessed_at = datetime.now().isoformat()

    def decay_importance(self, decay_rate: float = 0.05):
        """随时间衰减重要性"""
        if self.importance > 0.1:
            self.importance = max(0.1, self.importance * (1 - decay_rate))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "topic": self.topic,
            "summary": self.summary,
            "importance": self.importance,
            "sentiment": self.sentiment,
            "created_at": self.created_at,
            "last_accessed_at": self.last_accessed_at,
            "access_count": self.access_count,
            "tags": self.tags,
            "source": self.source,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryFragment":
        return cls(
            id=data.get("id", ""),
            topic=data.get("topic", ""),
            summary=data.get("summary", ""),
            importance=data.get("importance", 0.5),
            sentiment=data.get("sentiment", 0.0),
            created_at=data.get("created_at", ""),
            last_accessed_at=data.get("last_accessed_at", ""),
            access_count=data.get("access_count", 0),
            tags=data.get("tags", []),
            source=data.get("source", "conversation"),
            metadata=data.get("metadata", {}),
        )


# ============================================================
# 人格档案（PersonalityProfile）
# ============================================================

@dataclass
class PersonalityProfile:
    """人格档案 — 整体人格概要"""
    profile_id: str = ""
    name: str = "默认人格"                    # 档案名称
    traits: PersonalityTrait = field(default_factory=PersonalityTrait)
    language_style: LanguageStyle = field(default_factory=LanguageStyle)
    behavior_prefs: BehaviorPreference = field(default_factory=BehaviorPreference)
    memories: List[MemoryFragment] = field(default_factory=list)
    equipped_skill_ids: List[str] = field(default_factory=list)   # 已装备的技能 IDs
    created_skill_ids: List[str] = field(default_factory=list)    # 该人格创造的技能 IDs
    created_at: str = ""
    updated_at: str = ""
    version: str = "1.0.0"

    def __post_init__(self):
        if not self.profile_id:
            self.profile_id = f"profile_{uuid.uuid4().hex[:8]}"
        if not self.created_at:
            now = datetime.now().isoformat()
            self.created_at = now
            self.updated_at = now

    def add_memory(self, memory: MemoryFragment, max_memories: int = 100):
        """添加记忆片段，超出限制时移除最不重要的"""
        self.memories.append(memory)
        if len(self.memories) > max_memories:
            # 按重要性排序，保留最重要的
            self.memories.sort(key=lambda m: m.importance, reverse=True)
            self.memories = self.memories[:max_memories]
        self.updated_at = datetime.now().isoformat()

    def get_important_memories(self, threshold: float = 0.6) -> List[MemoryFragment]:
        """获取重要性高于阈值的记忆"""
        return [m for m in self.memories if m.importance >= threshold]

    def get_recent_memories(self, count: int = 10) -> List[MemoryFragment]:
        """获取最近的记忆"""
        sorted_mems = sorted(
            self.memories,
            key=lambda m: m.last_accessed_at or m.created_at,
            reverse=True,
        )
        return sorted_mems[:count]

    def search_memories(self, keyword: str) -> List[MemoryFragment]:
        """搜索记忆（按关键词匹配 topic/summary/tags）"""
        keyword_lower = keyword.lower()
        results = []
        for mem in self.memories:
            if (keyword_lower in mem.topic.lower() or
                keyword_lower in mem.summary.lower() or
                any(keyword_lower in tag.lower() for tag in mem.tags)):
                results.append(mem)
        return results

    def apply_trait_adjustment(self, interactions: Dict[str, Any]):
        """根据交互反馈调整性格特征

        Args:
            interactions: 交互分析结果，包含各维度的调整建议
        """
        for dim, delta in interactions.items():
            if dim in ("openness", "conscientiousness", "extraversion",
                       "agreeableness", "neuroticism"):
                self.traits.adjust(dim, delta)
        self.updated_at = datetime.now().isoformat()

    def get_response_style_guide(self) -> str:
        """生成影响 response 风格的文字指南（注入 prompt 使用）"""
        trait_summary = self.traits.get_summary()
        style_tags = self.language_style.get_style_tags()

        guide = f"【人格特征】{trait_summary}\n"
        guide += f"【语言风格】{'、'.join(style_tags) if style_tags else '均衡'}\n"
        guide += f"【决策风格】{self.behavior_prefs.decision_style}（风险容忍度: {self.behavior_prefs.risk_tolerance}/100）\n"

        # 如果有重要记忆，添加提示
        important_mems = self.get_important_memories(0.7)
        if important_mems:
            guide += "【重要记忆】\n"
            for mem in important_mems[:5]:
                guide += f"- [{mem.topic}] {mem.summary}\n"

        return guide

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "name": self.name,
            "traits": self.traits.to_dict(),
            "language_style": self.language_style.to_dict(),
            "behavior_prefs": self.behavior_prefs.to_dict(),
            "memories": [m.to_dict() for m in self.memories],
            "equipped_skill_ids": self.equipped_skill_ids,
            "created_skill_ids": self.created_skill_ids,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PersonalityProfile":
        return cls(
            profile_id=data.get("profile_id", ""),
            name=data.get("name", "默认人格"),
            traits=PersonalityTrait.from_dict(data.get("traits", {})),
            language_style=LanguageStyle.from_dict(data.get("language_style", {})),
            behavior_prefs=BehaviorPreference.from_dict(data.get("behavior_prefs", {})),
            memories=[MemoryFragment.from_dict(m) for m in data.get("memories", [])],
            equipped_skill_ids=data.get("equipped_skill_ids", []),
            created_skill_ids=data.get("created_skill_ids", []),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            version=data.get("version", "1.0.0"),
        )




# ============================================================
# 自定义人格模板
# ============================================================

@dataclass
class CustomPersonalityTemplate:
    """用户自定义人格模板"""
    name: str = ""
    description: str = ""
    icon: str = "🧑"
    traits: PersonalityTrait = field(default_factory=PersonalityTrait)
    language_style: LanguageStyle = field(default_factory=LanguageStyle)
    behavior_prefs: BehaviorPreference = field(default_factory=BehaviorPreference)
    equipped_skill_ids: List[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "traits": self.traits.to_dict(),
            "language_style": self.language_style.to_dict(),
            "behavior_prefs": self.behavior_prefs.to_dict(),
            "equipped_skill_ids": self.equipped_skill_ids,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CustomPersonalityTemplate":
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            icon=data.get("icon", "🧑"),
            traits=PersonalityTrait.from_dict(data.get("traits", {})),
            language_style=LanguageStyle.from_dict(data.get("language_style", {})),
            behavior_prefs=BehaviorPreference.from_dict(data.get("behavior_prefs", {})),
            equipped_skill_ids=data.get("equipped_skill_ids", []),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )

    def to_personality_profile(self) -> PersonalityProfile:
        """将模板转为完整人格档案"""
        now = datetime.now().isoformat()
        return PersonalityProfile(
            name=self.name,
            traits=self.traits,
            language_style=self.language_style,
            behavior_prefs=self.behavior_prefs,
            equipped_skill_ids=list(self.equipped_skill_ids),
            created_at=now,
            updated_at=now,
        )


# ---- 自定义模板存储 ----

CUSTOM_TEMPLATES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "sessions", "personality"
)
CUSTOM_TEMPLATES_PATH = os.path.join(CUSTOM_TEMPLATES_DIR, "custom_templates.json")


def load_custom_templates() -> Dict[str, dict]:
    """加载自定义人格模板"""
    if not os.path.exists(CUSTOM_TEMPLATES_PATH):
        return {}
    try:
        with open(CUSTOM_TEMPLATES_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get("templates", {})
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def save_custom_templates(templates: Dict[str, dict]):
    """保存自定义人格模板"""
    os.makedirs(CUSTOM_TEMPLATES_DIR, exist_ok=True)
    with open(CUSTOM_TEMPLATES_PATH, 'w', encoding='utf-8') as f:
        json.dump({"templates": templates}, f, ensure_ascii=False, indent=2)


def add_custom_template(data: dict) -> dict:
    """添加自定义人格模板"""
    name = data.get("name", "").strip()
    if not name:
        return {"success": False, "error": "模板名称不能为空"}

    # 检查是否与内置模板重名
    # PERSONALITY_TEMPLATES is defined below, will be available at runtime
    # Templates now dynamically loaded from personas/ dir
    import os
    personas_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "personas")
    persona_path = os.path.join(personas_dir, name, "definition.json")
    custom_templates = load_custom_templates()
    if os.path.isfile(persona_path) or name in custom_templates:
        return {"success": False, "error": f"模板「{name}」已存在"}

    templates = load_custom_templates()
    if name in templates:
        return {"success": False, "error": f"模板「{name}」已存在"}

    now = datetime.now().isoformat()
    template_data = {
        "name": name,
        "description": data.get("description", ""),
        "icon": data.get("icon", "🧑"),
        "traits": data.get("traits", {}),
        "language_style": data.get("language_style", {}),
        "behavior_prefs": data.get("behavior_prefs", {}),
        "equipped_skill_ids": data.get("equipped_skill_ids", []),
        "soul_md": data.get("soul_md", ""),
        "created_at": now,
        "updated_at": now,
    }
    templates[name] = template_data
    save_custom_templates(templates)
    return {"success": True, "name": name}


def update_custom_template(name: str, data: dict) -> dict:
    """更新自定义人格模板"""
    templates = load_custom_templates()
    if name not in templates:
        return {"success": False, "error": f"模板「{name}」不存在"}

    template = templates[name]
    if "description" in data:
        template["description"] = data["description"]
    if "icon" in data:
        template["icon"] = data["icon"]
    if "traits" in data:
        template["traits"] = data["traits"]
    if "language_style" in data:
        template["language_style"] = data["language_style"]
    if "behavior_prefs" in data:
        template["behavior_prefs"] = data["behavior_prefs"]
    if "equipped_skill_ids" in data:
        template["equipped_skill_ids"] = data["equipped_skill_ids"]
    # 允许修改名称
    new_name = data.get("name", "").strip()
    if new_name and new_name != name:
        if new_name in templates:
            return {"success": False, "error": f"模板「{new_name}」已存在"}
        templates[new_name] = templates.pop(name)
        templates[new_name]["name"] = new_name
        templates[new_name]["updated_at"] = datetime.now().isoformat()
    else:
        template["updated_at"] = datetime.now().isoformat()

    save_custom_templates(templates)
    return {"success": True}


def delete_custom_template(name: str) -> dict:
    """删除自定义人格模板（也处理 personas 目录中的角色）"""
    # 1. Try custom templates JSON
    templates = load_custom_templates()
    if name in templates:
        del templates[name]
        save_custom_templates(templates)
        return {"success": True}
    
    # 2. Try personas directory
    try:
        import os, shutil
        personas_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "personas")
        role_dir = os.path.join(personas_dir, name)
        if os.path.isdir(role_dir):
            shutil.rmtree(role_dir)
            return {"success": True}
    except Exception as e:
        return {"success": False, "error": f"删除角色目录失败: {e}"}
    
    return {"success": False, "error": f"模板「{name}」不存在"}


def get_all_templates_with_custom() -> Dict[str, dict]:
    """获取所有模板（内置 + 自定义 + personas目录），返回可序列化字典"""
    result = {}

    # 内置模板（从 personas/ 目录动态扫描）
    # 注意：personas/ 目录下的 definition.json 中 is_builtin=true 的会被标记为内置
    # 此处的循环已被动态扫描替代，下面 personas 扫描部分会处理

    # 自定义模板（通过 API 创建）
    custom = load_custom_templates()
    for name, tmpl in custom.items():
        result[name] = dict(tmpl)
        result[name]["is_builtin"] = False

    # 扫描 personas/ 目录中的角色
    try:
        import os
        personas_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "personas")
        if os.path.isdir(personas_dir):
            for name in os.listdir(personas_dir):
                if name.startswith('.'):
                    continue
                role_dir = os.path.join(personas_dir, name)
                def_file = os.path.join(role_dir, "definition.json")
                if os.path.isdir(role_dir) and os.path.isfile(def_file) and name not in result:
                    try:
                        with open(def_file, 'r', encoding='utf-8') as f:
                            def_data = json.load(f)
                        desc = ""
                        desc_file = os.path.join(role_dir, "description.md")
                        if os.path.isfile(desc_file):
                            with open(desc_file, 'r', encoding='utf-8') as f:
                                desc = f.read().strip()[:200]
                        is_builtin_role = (name == "Tennine")
                        result[name] = {
                            "name": name,
                            "icon": "🎀",
                            "description": desc or def_data.get("description", ""),
                            "is_builtin": is_builtin_role,
                            "traits": def_data.get("traits", {}),
                            "language_style": def_data.get("language_style", {}),
                            "behavior_prefs": def_data.get("behavior_prefs", {}),
                            "equipped_skill_ids": def_data.get("equipped_skill_ids", []),
                            "from_personas_dir": True,
                        }
                    except Exception as e:
                        print(f"[personality_models] ⚠️ 读取 personas/{name} 失败: {e}")
    except Exception as e:
        print(f"[personality_models] ⚠️ 扫描 personas 目录失败: {e}")

    return result


PERSONALITY_TEMPLATES = {}  # 已废弃！请使用动态扫描 personas/ 目录
# 所有模板现在由以下函数动态加载：
# - list_personality_templates()  → 扫描 personas/ + custom_templates.json
# - get_all_templates_with_custom() → 扫描 personas/ + builtin + custom
# - get_personality_template() → 从 personas/ 或 custom_templates.json 加载
# 
# 如需添加新模板，请在 personas/ 目录下创建 角色名/ 子目录，
# 包含 definition.json 和可选的 description.md 文件
PERSONALITY_TEMPLATES = {}  # 动态加载：所有模板从 personas/目录扫描



def get_personality_template(name: str) -> Optional[PersonalityProfile]:
    """获取人格模板（内置 + 自定义 + personas目录）"""
    # 1. Try built-in templates
    tmpl = PERSONALITY_TEMPLATES.get(name)
    if tmpl:
        return tmpl
    
    # 2. Try custom templates (build from JSON data)
    try:
        custom_templates = load_custom_templates()
        ctmpl = custom_templates.get(name)
        if ctmpl:
            bp_data = ctmpl.get("behavior_prefs", {})
            bp_known = {k: bp_data[k] for k in ['decision_style', 'risk_tolerance', 'collaboration_mode', 
                                                 'creativity_level', 'detail_orientation', 
                                                 'preferred_tools', 'avoid_topics'] if k in bp_data}
            ls_data = ctmpl.get("language_style", {})
            ls_known = {k: ls_data[k] for k in ['formality', 'humor', 'conciseness', 
                                                 'enthusiasm', 'technical_depth'] if k in ls_data}
            tr_data = ctmpl.get("traits", {})
            tr_known = {k: tr_data[k] for k in ['openness', 'conscientiousness', 'extraversion',
                                                 'agreeableness', 'neuroticism'] if k in tr_data}
            profile = PersonalityProfile(
                name=ctmpl.get("name", name),
                traits=PersonalityTrait(**tr_known),
                language_style=LanguageStyle(**ls_known),
                behavior_prefs=BehaviorPreference(**bp_known),
            )
            profile.equipped_skill_ids = ctmpl.get("equipped_skill_ids", [])
            return profile
    except Exception:
        pass
    
    # 3. Try personas directory
    try:
        import os, json
        personas_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "personas")
        def_file = os.path.join(personas_dir, name, "definition.json")
        if os.path.isfile(def_file):
            with open(def_file, 'r', encoding='utf-8') as f:
                def_data = json.load(f)
            
            # Safely construct dataclasses: extract only known fields
            bp_data = def_data.get("behavior_prefs", {})
            bp_known = {k: bp_data[k] for k in ['decision_style', 'risk_tolerance', 'collaboration_mode', 
                                                 'creativity_level', 'detail_orientation', 
                                                 'preferred_tools', 'avoid_topics'] if k in bp_data}
            
            ls_data = def_data.get("language_style", {})
            ls_known = {k: ls_data[k] for k in ['formality', 'humor', 'conciseness', 
                                                 'enthusiasm', 'technical_depth'] if k in ls_data}
            
            tr_data = def_data.get("traits", {})
            tr_known = {k: tr_data[k] for k in ['openness', 'conscientiousness', 'extraversion',
                                                 'agreeableness', 'neuroticism'] if k in tr_data}
            
            profile = PersonalityProfile(
                name=def_data.get("name", name),
                traits=PersonalityTrait(**tr_known),
                language_style=LanguageStyle(**ls_known),
                behavior_prefs=BehaviorPreference(**bp_known),
            )
            profile.equipped_skill_ids = def_data.get("equipped_skill_ids", [])
            print(f"[personality_models] ✅ Loaded role '{name}' from personas/{name}/", flush=True)
            return profile
    except Exception as e:
        print(f"[personality_models] ⚠️ 加载 personas/{name} 失败: {e}", flush=True)
    
    return None


def list_personality_templates() -> List[str]:
    """列出所有可用人格模板名称（内置+自定义+personas目录，动态扫描）"""
    builtin = list(PERSONALITY_TEMPLATES.keys())
    try:
        custom = list(load_custom_templates().keys())
    except Exception:
        custom = []
    result = builtin + custom
    
    # 扫描 personas/ 目录中的角色（动态，不写死）
    try:
        import os
        personas_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "personas")
        if os.path.isdir(personas_dir):
            for name in sorted(os.listdir(personas_dir)):
                if name.startswith('.'):
                    continue
                role_dir = os.path.join(personas_dir, name)
                def_file = os.path.join(role_dir, "definition.json")
                if os.path.isdir(role_dir) and os.path.isfile(def_file) and name not in result:
                    result.append(name)
    except Exception:
        pass
    
    return result
