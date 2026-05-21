# ============================================================
# TennineClaw - 人格引擎（PersonalityEngine）
# ============================================================
# 管理人格档案的加载/保存、性格特征自适应更新、
# 记忆片段管理、风格指南生成等核心逻辑。
# 支持跨会话保持人格一致性和持久记忆。
# ============================================================

from __future__ import annotations
import os
import json
import re
import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

from .personality_models import (
    PersonalityProfile, PersonalityTrait, LanguageStyle,
    BehaviorPreference, MemoryFragment,
    get_personality_template, list_personality_templates,
)

logger = logging.getLogger(__name__)

# ============================================================
# 默认存储路径
# ============================================================
DEFAULT_PERSONALITY_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "personas"
)


class PersonalityEngine:
    """人格引擎 — 人格化持久性控制器"""

    def __init__(self, profile: Optional[PersonalityProfile] = None,
                 save_dir: str = None,
                 profile_id: str = "default"):
        self.profile = profile or PersonalityProfile(profile_id=profile_id)
        self.save_dir = save_dir or DEFAULT_PERSONALITY_DIR
        self.profile_id = profile_id
        self._interaction_count: int = 0
        self._session_memories: List[MemoryFragment] = []
        self._soul_content: str = ''

        # 确保保存目录存在
        os.makedirs(self.save_dir, exist_ok=True)

    # ---- Personas folder helpers ----

    @staticmethod
    def _sanitize_folder_name(name: str) -> str:
        """Sanitize a name for use as a folder name"""
        # Replace invalid chars with underscore
        safe = re.sub(r'[<>:"/\\|?*]', '_', name)
        safe = safe.strip()
        if not safe:
            safe = 'default'
        return safe

    def _find_profile_filepath(self, profile_id: str) -> str:
        """Find a profile file in the personas/ folder structure
        
        Searches: personas/persona_name/definition.json
        Returns the full path if found, None otherwise
        """
        if not os.path.isdir(self.save_dir):
            return None
        
        for folder_name in os.listdir(self.save_dir):
            folder_path = os.path.join(self.save_dir, folder_name)
            if not os.path.isdir(folder_path):
                continue
            def_path = os.path.join(folder_path, 'definition.json')
            if os.path.isfile(def_path):
                try:
                    with open(def_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    if data.get('profile_id') == profile_id:
                        return def_path
                except:
                    continue
        
        # Also try matching by folder name
        for folder_name in os.listdir(self.save_dir):
            folder_path = os.path.join(self.save_dir, folder_name)
            if not os.path.isdir(folder_path):
                continue
            def_path = os.path.join(folder_path, 'definition.json')
            if os.path.isfile(def_path):
                if folder_name == profile_id or folder_name == self._sanitize_folder_name(profile_id):
                    return def_path
        
        return None

    def get_persona_folder(self) -> str:
        """Get the persona folder path for the current profile"""
        persona_name = self.profile.name or self.profile_id
        safe_name = self._sanitize_folder_name(persona_name)
        persona_dir = os.path.join(self.save_dir, safe_name)
        return persona_dir

    def get_memories_folder(self) -> str:
        """Get the memories folder path for the current persona"""
        persona_dir = self.get_persona_folder()
        memories_dir = os.path.join(persona_dir, 'memories')
        os.makedirs(memories_dir, exist_ok=True)
        return memories_dir


    # ── 人格档案管理 ──

    # ---- Soul definition loading ----

    def load_soul_definition(self) -> str:
        """Load the soul.md file for the current persona
        
        Reads the soul.md file from the persona folder and caches it.
        Returns the soul content as a string, or empty string if not found.
        """
        persona_dir = self.get_persona_folder()
        soul_path = os.path.join(persona_dir, 'soul.md')
        
        if os.path.isfile(soul_path):
            try:
                with open(soul_path, 'r', encoding='utf-8') as f:
                    self._soul_content = f.read().strip()
                return self._soul_content
            except Exception as e:
                logger.warning(f"Failed to load soul.md: {e}")
        
        self._soul_content = ''
        return self._soul_content

    def get_soul_content(self) -> str:
        """Get the cached soul definition content"""
        return self._soul_content

    def save_soul_definition(self, content: str) -> bool:
        """Save new soul definition to soul.md
        
        Args:
            content: The soul.md content to save
            
        Returns:
            True if saved successfully
        """
        persona_dir = self.get_persona_folder()
        soul_path = os.path.join(persona_dir, 'soul.md')
        
        try:
            with open(soul_path, 'w', encoding='utf-8') as f:
                f.write(content)
            self._soul_content = content
            return True
        except Exception as e:
            logger.error(f"Failed to save soul.md: {e}")
            return False


    def load_profile(self, profile_id: str = None) -> bool:
        """从文件加载人格档案（支持 personas/ 文件夹结构）"""
        pid = profile_id or self.profile_id
        # Try new folder structure first: personas/persona_name/definition.json
        filepath = self._find_profile_filepath(pid)
        if filepath is None:
            # Fall back to old flat structure
            filepath = os.path.join(self.save_dir, f"{pid}.json")

        if not os.path.exists(filepath):
            # Final fallback: scan all personas/ dirs for any valid definition.json
            # This handles the case where profile_id is a session UUID but the
            # profile was saved under a persona name (e.g., "Tennine")
            logger.info(f"人格档案 {filepath} 不存在，扫描 personas/ 目录查找替代...")
            try:
                if os.path.isdir(self.save_dir):
                    for folder_name in sorted(os.listdir(self.save_dir)):
                        folder_path = os.path.join(self.save_dir, folder_name)
                        def_path = os.path.join(folder_path, 'definition.json')
                        if os.path.isdir(folder_path) and os.path.isfile(def_path):
                            filepath = def_path
                            logger.info(f"找到替代人格档案: {filepath}")
                            break
            except Exception:
                pass
        
        if not os.path.exists(filepath):
            logger.warning(f"人格档案不存在: {filepath}")
            return False

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.profile = PersonalityProfile.from_dict(data)
            self.profile_id = pid
            logger.info(f"📂 人格档案已加载: {filepath}")
            return True
        except Exception as e:
            logger.error(f"加载人格档案失败: {e}")
            return False

    def save_profile(self, filepath: str = None) -> str:
        """保存人格档案到文件（使用 personas/ 文件夹结构）"""
        if filepath is None:
            # Use folder structure: personas/persona_name/definition.json
            persona_name = self.profile.name or self.profile_id
            safe_name = self._sanitize_folder_name(persona_name)
            persona_dir = os.path.join(self.save_dir, safe_name)
            os.makedirs(persona_dir, exist_ok=True)
            filepath = os.path.join(persona_dir, "definition.json")

        data = self.profile.to_dict()
        data["saved_at"] = datetime.now().isoformat()
        data["interaction_count"] = self._interaction_count

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"💾 人格档案已保存: {filepath}")
        return filepath

    def apply_template(self, template_name: str) -> bool:
        """应用人格模板"""
        template = get_personality_template(template_name)
        if template:
            old_id = self.profile.profile_id
            self.profile = template
            self.profile.profile_id = old_id  # 保留原有 ID
            self.profile.created_at = datetime.now().isoformat()
            self.profile.updated_at = datetime.now().isoformat()
            logger.info(f"🎭 已应用人格模板: {template_name}")
            return True
        return False

    # ── 性格特征管理 ──

    def update_trait(self, dimension: str, delta: int):
        """更新性格特征（增量方式）

        Args:
            dimension: 维度名 (openness, conscientiousness, 等)
            delta: 变化值 (-20 ~ 20)
        """
        self.profile.traits.adjust(dimension, delta)
        self.profile.updated_at = datetime.now().isoformat()

    def analyze_and_adjust_traits(self, interaction_data: Dict[str, Any]):
        """根据交互数据分析并调整性格特征

        Args:
            interaction_data: 包含交互分析结果，如：
                - task_type: 任务类型
                - user_sentiment: 用户情感倾向
                - complexity: 任务复杂度
                - success: 是否成功
                - user_feedback: 用户反馈 (positive/negative/neutral)
        """
        adjustments = {}

        task_type = interaction_data.get("task_type", "general")
        user_feedback = interaction_data.get("user_feedback", "neutral")
        complexity = interaction_data.get("complexity", 0.5)
        success = interaction_data.get("success", True)

        # 任务类型影响
        if task_type == "creative":
            adjustments["openness"] = 2
        elif task_type == "analytical":
            adjustments["conscientiousness"] = 2

        # 复杂度影响
        if complexity > 0.8:
            adjustments["conscientiousness"] = adjustments.get("conscientiousness", 0) + 1
            adjustments["neuroticism"] = adjustments.get("neuroticism", 0) + 1
        elif complexity < 0.3:
            adjustments["openness"] = adjustments.get("openness", 0) + 1

        # 用户反馈影响
        if user_feedback == "positive":
            adjustments["agreeableness"] = adjustments.get("agreeableness", 0) + 1
            adjustments["extraversion"] = adjustments.get("extraversion", 0) + 1
        elif user_feedback == "negative":
            adjustments["neuroticism"] = adjustments.get("neuroticism", 0) - 1
            adjustments["agreeableness"] = adjustments.get("agreeableness", 0) - 1

        # 成功/失败影响
        if success:
            adjustments["conscientiousness"] = adjustments.get("conscientiousness", 0) + 1
        else:
            adjustments["neuroticism"] = adjustments.get("neuroticism", 0) + 2

        # 应用调整
        for dim, delta in adjustments.items():
            self.update_trait(dim, delta)

        self._interaction_count += 1

    # ── 语言风格管理 ──

    def adapt_language_style(self, context: Dict[str, Any]):
        """根据对话情境自适应调整语言风格

        Args:
            context: 对话上下文信息，如：
                - user_style: 用户语言风格 (formal/casual)
                - topic: 话题领域
                - urgency: 紧急程度
        """
        user_style = context.get("user_style", "neutral")
        topic = context.get("topic", "general")
        urgency = context.get("urgency", 0.5)

        # 适应用户风格
        if user_style == "formal":
            self.profile.language_style.adjust("formality", 5)
            self.profile.language_style.adjust("humor", -5)
        elif user_style == "casual":
            self.profile.language_style.adjust("formality", -5)
            self.profile.language_style.adjust("humor", 3)

        # 话题适配
        technical_topics = ["code", "programming", "system", "technical",
                           "代码", "编程", "系统", "技术"]
        if any(t in topic.lower() for t in technical_topics):
            self.profile.language_style.adjust("technical_depth", 5)
            self.profile.language_style.adjust("conciseness", 3)

        # 紧急程度适配
        if urgency > 0.7:
            self.profile.language_style.adjust("conciseness", 10)
            self.profile.language_style.adjust("enthusiasm", -5)
        elif urgency < 0.3:
            self.profile.language_style.adjust("conciseness", -3)
            self.profile.language_style.adjust("enthusiasm", 3)

        self.profile.updated_at = datetime.now().isoformat()

    # ── 记忆管理 ──

    def record_memory(self, topic: str, summary: str,
                      importance: float = 0.5,
                      sentiment: float = 0.0,
                      tags: List[str] = None,
                      source: str = "conversation") -> MemoryFragment:
        """记录一段记忆

        Args:
            topic: 记忆主题
            summary: 记忆内容摘要
            importance: 重要性 (0.0~1.0)
            sentiment: 情感倾向 (-1.0~1.0)
            tags: 标签列表
            source: 来源

        Returns:
            创建的 MemoryFragment 对象
        """
        memory = MemoryFragment(
            topic=topic,
            summary=summary,
            importance=importance,
            sentiment=sentiment,
            tags=tags or [],
            source=source,
        )

        self.profile.add_memory(memory)
        self._session_memories.append(memory)
        self.profile.updated_at = datetime.now().isoformat()

        # Also save to daily .md file
        try:
            sentiment_str = "positive" if memory.sentiment > 0.3 else ("negative" if memory.sentiment < -0.3 else "neutral")
            self.save_daily_memory(
                topic=memory.topic,
                summary=memory.summary,
                sentiment=sentiment_str,
                tags=memory.tags,
            )
        except Exception as e:
            logger.warning(f"Failed to save daily memory: {e}")

        logger.info(
            f"💭 新记忆已记录: [{topic}] (重要性: {importance:.2f})"
        )
        return memory

    def get_important_memories(self, threshold: float = 0.6) -> List[MemoryFragment]:
        """获取重要记忆"""
        return self.profile.get_important_memories(threshold)

    def search_memories(self, keyword: str) -> List[MemoryFragment]:
        """搜索记忆"""
        return self.profile.search_memories(keyword)

    def summarize_memories(self, max_count: int = 5) -> str:
        """生成记忆总结文本

        汇总最重要的记忆，用于注入 system prompt
        """
        important = self.get_important_memories(0.6)
        if not important:
            return "暂无重要记忆。"

        # 按重要性排序，取 top N
        important.sort(key=lambda m: m.importance, reverse=True)
        top_memories = important[:max_count]

        lines = ["【跨会话记忆】"]
        for mem in top_memories:
            sentiment_tag = "😊" if mem.sentiment > 0.3 else (
                "😟" if mem.sentiment < -0.3 else "😐"
            )
            lines.append(
                f"- [{mem.topic}] {mem.summary} {sentiment_tag} "
                f"(重要度: {mem.importance:.0%})"
            )

        return "\n".join(lines)

    def cleanup_old_memories(self, max_memories: int = 100,
                             importance_threshold: float = 0.2):
        """清理旧记忆 — 移除重要性低的记忆"""
        # 先按重要性排序
        self.profile.memories.sort(key=lambda m: m.importance, reverse=True)

        # 移除低于阈值且数量过多的记忆
        self.profile.memories = [
            m for m in self.profile.memories
            if m.importance >= importance_threshold
            or m.access_count > 2
        ]

        # 如果还是太多，截断
        if len(self.profile.memories) > max_memories:
            self.profile.memories = self.profile.memories[:max_memories]

        logger.info(
            f"🧹 记忆已清理: 当前 {len(self.profile.memories)} 条"
        )

    # ── 风格指南生成 ──

    def get_response_style_guide(self) -> str:
        """生成影响 response 风格的指南文字

        此文本将被注入到 system prompt 中，
        指导模型的回复风格。
        """
        return self.profile.get_response_style_guide()

    def get_memory_context_prompt(self) -> str:
        """生成包含记忆信息的上下文 prompt 片段"""
        parts = []

        # 人格特征
        parts.append(f"🎭 当前人格: {self.profile.name}")
        parts.append(self.profile.traits.get_summary())

        # 语言风格标签
        style_tags = self.profile.language_style.get_style_tags()
        if style_tags:
            parts.append(f"语言风格: {'、'.join(style_tags)}")

        # 重要记忆
        mem_summary = self.summarize_memories(3)
        if mem_summary:
            parts.append(mem_summary)

        return "\n".join(parts)

    # ── 会话管理 ──

    def on_session_start(self):
        """会话开始时的初始化"""
        self._session_memories = []
        self._interaction_count = 0
        # Load soul definition
        self.load_soul_definition()

    def on_session_end(self):
        """会话结束时的清理与保存"""
        # 将会话记忆整合到长期记忆
        if self._session_memories:
            logger.info(
                f"📝 本轮对话记录了 {len(self._session_memories)} 条记忆"
            )
        self.save_profile()

    # ── 统计信息 ──

    def get_stats(self) -> Dict[str, Any]:
        """获取人格引擎统计信息"""
        return {
            "profile_name": self.profile.name,
            "profile_id": self.profile_id,
            "traits": self.profile.traits.to_dict(),
            "language_style": self.profile.language_style.to_dict(),
            "memories_count": len(self.profile.memories),
            "session_memories": len(self._session_memories),
            "interaction_count": self._interaction_count,
            "created_at": self.profile.created_at,
            "updated_at": self.profile.updated_at,
        }
    # ---- Personality context generation ----


    # ---- Daily memory .md file system ----

    def save_daily_memory(self, topic: str, summary: str, 
                          sentiment: str = "neutral",
                          tags: list = None) -> str:
        """Save a daily memory entry to the persona's memories .md file
        
        The memory is saved to: personas/persona_name/memories/YYYY-MM-DD.md
        
        Args:
            topic: Memory topic/title
            summary: Memory content summary
            sentiment: Emotional sentiment (positive/negative/neutral)
            tags: List of tags
            
        Returns:
            Path to the saved memory file
        """
        from datetime import date
        today = date.today().isoformat()
        memories_dir = self.get_memories_folder()
        mem_file = os.path.join(memories_dir, f"{today}.md")
        
        # Build the memory entry
        entry_parts = []
        entry_parts.append(f"## {topic}")
        entry_parts.append("")
        entry_parts.append(f"- **Time**: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        if sentiment:
            entry_parts.append(f"- **Sentiment**: {sentiment}")
        if tags:
            entry_parts.append(f"- **Tags**: {', '.join(tags)}")
        entry_parts.append("")
        entry_parts.append(summary)
        entry_parts.append("")
        entry_parts.append("---")
        entry_parts.append("")
        
        entry_text = "\n".join(entry_parts)
        
        # Append to the daily file
        with open(mem_file, 'a', encoding='utf-8') as f:
            f.write(entry_text)
        
        return mem_file

    def get_daily_memories(self, days: int = 7) -> str:
        """Get recent daily memory entries as a formatted string
        
        Args:
            days: Number of past days to include
            
        Returns:
            Formatted memory text for system prompt injection
        """
        from datetime import date, timedelta
        memories_dir = self.get_memories_folder()
        
        if not os.path.isdir(memories_dir):
            return ""
        
        result_parts = []
        today = date.today()
        
        for i in range(days):
            d = today - timedelta(days=i)
            filename = f"{d.isoformat()}.md"
            filepath = os.path.join(memories_dir, filename)
            if os.path.isfile(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                result_parts.append(f"=== {d.isoformat()} ===")
                result_parts.append(content)
        
        if not result_parts:
            return ""
        
        return "\n".join(result_parts)

    def get_recent_memories_summary(self, max_days: int = 3) -> str:
        """Get a brief summary of recent daily memories
        
        Args:
            max_days: Number of past days to summarize
            
        Returns:
            Brief summary text
        """
        from datetime import date, timedelta
        memories_dir = self.get_memories_folder()
        
        if not os.path.isdir(memories_dir):
            return ""
        
        summaries = []
        today = date.today()
        
        for i in range(max_days):
            d = today - timedelta(days=i)
            filename = f"{d.isoformat()}.md"
            filepath = os.path.join(memories_dir, filename)
            if os.path.isfile(filepath):
                # Just note that this day has memories
                summaries.append(d.isoformat())
        
        if summaries:
            return f"Recent memory days: {', '.join(summaries)}"
        return ""
    def generate_personality_context(self) -> str:
        """Generate personality context text for system prompt injection

        Returns identity-framed text for the role definition section.
        """
        name = self.profile.name or 'Default'
        parts = []

        # Identity header
        parts.append(f'\u4f60\u5f53\u524d\u7684\u89d2\u8272\u662f\uff1a\u3010{name}\u3011')
        parts.append('')

        # Soul definition content (core personality)
        if self._soul_content:
            for line in self._soul_content.split('\n'):
                stripped = line.strip()
                if stripped and not stripped.startswith('#'):
                    parts.append(stripped)
            parts.append('')

        # Important memories (context, not identity)
        important = self.get_important_memories(0.6)
        if important:
            top = sorted(important, key=lambda m: m.importance, reverse=True)[:3]
            parts.append('\u3010\u76f8\u5173\u8bb0\u5fc6\u3011')
            for mem in top:
                summary = mem.summary[:80] if len(mem.summary) > 80 else mem.summary
                parts.append('  - ' + mem.topic + ': ' + summary)
            parts.append('')

        # Recent daily memories
        try:
            daily_summary = self.get_recent_memories_summary(max_days=3)
            if daily_summary:
                parts.append('\u3010\u8fd1\u671f\u7ecf\u5386\u3011' + daily_summary)
                parts.append('')
        except Exception:
            pass

        if not parts:
            return ''
        return '\n'.join(parts)