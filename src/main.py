# ============================================================
# TennineClaw - 智能终端助手（Gradio 版）
# ============================================================
# 主入口：包含对话逻辑、API 交互、工具调度
# 支持的模块包括：会话管理、模式切换、上下文压缩（Composer）、
# Prompt 优化、Python/Conda 环境管理、自定义模型管理等
# ============================================================

import os
import json
from openai import OpenAI

from .config import (
    API_KEY, API_BASE_URL, API_MODEL,
    MAX_CTX_TOKENS, COMPACT_THRESHOLD,
    MODE_SMART, MODE_PLAN,
    COMPOSER_ENABLED, MICRO_COMPOSER_KEEP_ROUNDS,
    MANUAL_COMPOSER_MAX_CHARS,
    SESSION_SAVE_DIR, SESSION_AUTO_SAVE, SESSION_TITLE_MAX_LEN,
    DEFAULT_PYTHON_PATH, DEFAULT_CONDA_ENV, PYTHON_ENV_MANUAL_OVERRIDE,
)
from .context import micro_composer, auto_composer, manual_composer
from .token_utils import get_token_stats_text
from .prompts import build_system_prompt
from .tools import TOOLS, TOOL_FUNCS
from .prompt_optimizer import optimize_prompt, format_optimized_prompt
from .mode_manager import ModeManager
from .main_stream import AgentSessionStreamMixin
from .skill_engine import SkillEngine, create_default_skills
from .personality_engine import PersonalityEngine


# ============================================================
# Agent 会话类（维护单个对话的状态）
# ============================================================

import uuid

class AgentSession(AgentSessionStreamMixin):
    """Agent 会话，维护完整的对话状态"""

    def __init__(self, session_id: str = None, mode: int = MODE_SMART):
        self.session_id = session_id or str(uuid.uuid4())
        self.current_model = API_MODEL
        self.custom_models = []
        # 检查 user_config 中当前模型的 API 覆盖（用户通过 Web UI 配置的）
        from .config import get_model_api_overrides
        _overrides = get_model_api_overrides().get(self.current_model, {})
        _api_key = _overrides.get("api_key") or API_KEY
        _base_url = _overrides.get("base_url") or API_BASE_URL
        self.client = OpenAI(
            api_key=_api_key,
            base_url=_base_url,
            timeout=60.0,
        )
        self.mode_mgr = ModeManager(mode)
                # Build system prompt with personality context
        personality_ctx = getattr(self, 'personality_engine', None)
        personality_text = personality_ctx.generate_personality_context() if personality_ctx else ''
        skill_text = self._build_skill_context()
        self.system_prompt = build_system_prompt(
            mode=self.mode_mgr.get_mode(),
            skill_context=skill_text,
            personality_context=personality_text,
        )
        self.msgs = [{"role": "system", "content": self.system_prompt}]
        self._display_msgs = [{"role": "system", "content": self.system_prompt}]
        self.current_tokens = 0
        self.last_token_stats = ""
        self.completion_tokens = 0
        self.total_tokens = 0
        
        # 会话级 Token 累计统计
        self.session_completion_tokens = 0

        # Composer 统计信息
        self.micro_composer_count = 0      # Micro Composer 触发次数
        self.auto_composer_count = 0       # Auto Composer 触发次数
        self.manual_composer_count = 0     # 手动压缩触发次数
        self.last_composer_action = ""     # 最近一次 composer 操作描述
        self.composer_notification = ""    # 最近一次 composer 通知信息

        # 会话标题系统（首次用户消息时自动设定）
        self.session_title = ""
        self._title_set = False

        # Python / Conda 环境配置
        self.python_env = DEFAULT_PYTHON_PATH
        self.conda_env = DEFAULT_CONDA_ENV

        # 自定义模型
        self.custom_models = []
        self.custom_model_configs = {}     # code -> {name, code, base_url, api_key}

        # 状态缓存更新回调（由 web_api 注册，用于流式期间实时刷新 Token 面板）
        self._status_update_callback = None

        # 模式 system prompt 自动注入
        self._round_count = 0              # 用户-助手对话轮次计数
        self._pending_mode_switch = False  # 是否有待处理的模式切换注入

        # 会话自动保存路径与前端展示记录
        # -- Skill & Personality Systems --
        from .skill_engine import SkillEngine, create_default_skills
        from .personality_engine import PersonalityEngine
        self.skill_engine = SkillEngine()
        loaded_skills = self.skill_engine.load()
        if not loaded_skills:
            default_tree = create_default_skills()
            self.skill_engine = SkillEngine(skill_tree=default_tree)
        self.personality_engine = PersonalityEngine(profile_id=self.session_id)
        self.personality_engine.load_profile()
        # Load soul definition
        self.personality_engine.load_soul_definition()
        # Rebuild system prompt with personality context
        self.refresh_personality_in_system_prompt()
        self._last_skill_inject_round = 0
        self._skill_inject_interval = 3
        self._session_save_path = None
        self.original_user_inputs = {}     # msg_index -> original_text
        self.optimized_prompts = {}        # msg_index -> optimized_text

        # 流式控制
        self._stream_interrupted = False
        self._partial_stream_content = ""  # 切换会话时保留的部分回复


    def _build_skill_context(self) -> str:
        """Build skill context text from skill engine for system prompt injection"""
        skill_text = ''
        try:
            engine = getattr(self, 'skill_engine', None)
            if engine:
                available = engine.get_available_skills()
                if available:
                    skill_text = '\u3010\u5f53\u524d\u6280\u80fd\u3011\n'
                    try:
                        from .skill_models import load_global_skill_registry
                        registry = load_global_skill_registry()
                    except ImportError:
                        registry = {}
                    for sk in available:
                        short_desc = ""
                        if sk.id in registry:
                            short_desc = registry[sk.id].get("short_description", "")
                        if not short_desc:
                            short_desc = sk.short_description or sk.description
                        skill_text += f"- {sk.icon} {sk.name}: {short_desc}\n"
        except Exception:
            pass
        return skill_text

    def refresh_personality_in_system_prompt(self):
        """Refresh system prompt with current personality context and skills
        
        Call this after personality changes (template apply, traits update, etc.)
        """
        personality_ctx = getattr(self, 'personality_engine', None)
        if personality_ctx:
            # Reload soul definition
            personality_ctx.load_soul_definition()
            personality_text = personality_ctx.generate_personality_context()
        else:
            personality_text = ''
        skill_text = self._build_skill_context()
        
        # Rebuild system prompt with personality context and skills
        self.system_prompt = build_system_prompt(
            mode=self.mode_mgr.get_mode(),
            skill_context=skill_text,
            personality_context=personality_text,
        )
        
        # Update the first system message
        if len(self.msgs) > 0 and self.msgs[0].get('role') == 'system':
            self.msgs[0]['content'] = self.system_prompt
        if len(self._display_msgs) > 0 and self._display_msgs[0].get('role') == 'system':
            self._display_msgs[0]['content'] = self.system_prompt

    def reset(self):
        """重置会话（清除上下文）"""
                # Build system prompt with personality context
        personality_ctx = getattr(self, 'personality_engine', None)
        personality_text = personality_ctx.generate_personality_context() if personality_ctx else ''
        skill_text = self._build_skill_context()
        self.system_prompt = build_system_prompt(
            mode=self.mode_mgr.get_mode(),
            skill_context=skill_text,
            personality_context=personality_text,
        )
        self.msgs = [{"role": "system", "content": self.system_prompt}]
        self._display_msgs = [{"role": "system", "content": self.system_prompt}]
        self.current_tokens = 0
        self.last_token_stats = ""
        self.completion_tokens = 0
        self.total_tokens = 0
        self.session_completion_tokens = 0

        # 重置 composer 统计
        self.micro_composer_count = 0
        self.auto_composer_count = 0
        self.manual_composer_count = 0
        self.last_composer_action = ""
        self.composer_notification = ""

        # 重置会话标题
        self.session_title = ""
        self._title_set = False

        # 重置模式注入状态
        self._round_count = 0
        self._pending_mode_switch = False

        # 重置会话路径与前端记录
        self._session_save_path = None
        self.original_user_inputs = {}
        self.optimized_prompts = {}

        # 重置流式控制
        self._stream_interrupted = False
        self._partial_stream_content = ""

    # ============================================================
    # Token 估算（用于模式切换/压缩后重算上下文用量）
    # ============================================================
    @staticmethod
    def _estimate_tokens(msgs: list) -> int:
        """根据消息列表内容估算 Token 数"""
        total = 0
        for msg in msgs:
            txt = msg.get("content", "") or ""
            cjk = sum(1 for c in txt if '\u4e00' <= c <= '\u9fff')
            other = len(txt) - cjk
            total += max(int(cjk / 1.5 + other / 4), 0) + 4
        return total

    # ============================================================
    # 统一消息追加（双写：模型用 msgs + 展示用 _display_msgs）
    # ============================================================
    def _append_msg(self, msg: dict):
        """同时追加到 self.msgs（模型用）和 self._display_msgs（展示用）

        确保：
        - 模型上下文始终与展示上下文保持同步（追加新消息时）
        - 压缩只影响 self.msgs，不影响 self._display_msgs
        """
        self.msgs.append(msg)
        self._display_msgs.append(msg)

    # ============================================================

    def get_mode_name(self) -> str:
        return self.mode_mgr.get_mode_name()

    def get_mode(self) -> int:
        return self.mode_mgr.get_mode()

    def get_composer_status(self) -> str:
        """获取 Composer 状态信息"""
        status = []
        status.append(f"🧩 **三重缓存上下文**")
        status.append(f"- Composer 总开关: {'✅ 开启' if COMPOSER_ENABLED else '⛔ 关闭'}")
        status.append(f"- Micro Composer: 已触发 {self.micro_composer_count} 次 (保留最近 {MICRO_COMPOSER_KEEP_ROUNDS} 轮 tool 信息)")
        status.append(f"- Auto Composer: 已触发 {self.auto_composer_count} 次 (阈值: {COMPACT_THRESHOLD:,} tokens)")
        status.append(f"- Manual Composer: 已触发 {self.manual_composer_count} 次 (上限: {MANUAL_COMPOSER_MAX_CHARS:,} 字)")
        if self.last_composer_action:
            status.append(f"- 最近操作: {self.last_composer_action}")
        if self.composer_notification:
            status.append(f"")
            status.append(f"🔔 **最新通知**: {self.composer_notification}")
        return "\n".join(status)

    
    def switch_mode(self, mode: int) -> str:
        """切换模式并返回提示信息"""
        if self.mode_mgr.set_mode(mode):
            # Build system prompt with personality context
            personality_ctx = getattr(self, 'personality_engine', None)
            personality_text = personality_ctx.generate_personality_context() if personality_ctx else ''
            skill_text = self._build_skill_context()
            self.system_prompt = build_system_prompt(
                mode=self.mode_mgr.get_mode(),
                skill_context=skill_text,
                personality_context=personality_text,
            )
            mode_name = self.mode_mgr.get_mode_name()

            # 切换前先清理历史遗留的多余 system prompt
            self._cleanup_old_system_prompts()

            # === 三场景决策逻辑 ===
            if len(self.msgs) <= 1:
                # 场景 1：没有上下文 → 替换 msgs[0]
                self.msgs[0] = {"role": "system", "content": self.system_prompt}
                self._display_msgs[0] = {"role": "system", "content": self.system_prompt}
            else:
                # 有上下文 → 检查最后一条消息的 role
                last_role = self.msgs[-1].get("role", "")

                if last_role == "system":
                    # 场景 3：最后一条是 system → 替换 content（不新增消息）
                    self.msgs[-1]["content"] = self.system_prompt
                    if len(self._display_msgs) > 0:
                        self._display_msgs[-1]["content"] = self.system_prompt
                else:
                    # 场景 2：最后一条不是 system → 追加新的 system（保留旧上下文）
                    self._append_msg({"role": "system", "content": self.system_prompt})

            # 标记有待注入的模式指令（下轮对话前 _inject_mode_prompt_if_needed 处理）
            self._pending_mode_switch = True

            # 从现有消息重新估算 Token 数
            self.current_tokens = self._estimate_tokens(self.msgs)
            self.last_token_stats = (
                f"📊 输入: {self.current_tokens:,} | "
                f"输出: {self.completion_tokens:,} | "
                f"合计: {self.current_tokens + self.completion_tokens:,} | "
                f"占用: {(self.current_tokens / MAX_CTX_TOKENS) * 100:.1f}%"
            )
            self.total_tokens = self.current_tokens + self.completion_tokens
            # 切换模式时重置本轮 completion 累计（上下文 Token 保留）
            self.session_completion_tokens = 0
            return f"🔄 已切换为 {mode_name}"
        return "❌ 模式切换失败"

    # ============================================================
    # 清理历史遗留的多余 System Prompt
    # ============================================================

    def _cleanup_old_system_prompts(self):
        """清理多余的历史 system prompt，只保留最新的两条：
        - msgs[0]：主 system prompt（角色定义、工具定义等）
        - 最后一条 system prompt（当前模式的完整规则）

        如果只有 1~2 条 system，无需清理。
        如果有多条 system，删除中间的，只保留 msgs[0] 和最后一条。
        """
        system_indices = []
        for i, msg in enumerate(self.msgs):
            if msg.get("role") == "system":
                system_indices.append(i)

        if len(system_indices) <= 2:
            return  # 1 或 2 条都是合理的，无需清理

        # 保留 msgs[0]（主 prompt）和最后一个 system（当前模式 prompt）
        keep_indices = {0, system_indices[-1]}

        # 从后往前删除中间多余的 system（避免索引偏移）
        for i in reversed(system_indices):
            if i not in keep_indices:
                del self.msgs[i]
                if i < len(self._display_msgs):
                    del self._display_msgs[i]

        # 重新估算 Token
        self.current_tokens = self._estimate_tokens(self.msgs)
# ============================================================

    def _auto_set_title(self, user_input: str):
        """首次收到用户消息时自动截取前 N 字作为标题"""
        if not self._title_set and user_input and not user_input.startswith("/"):
            # 取用户输入的前 SESSION_TITLE_MAX_LEN 个字符作为标题
            title = user_input.strip()[:SESSION_TITLE_MAX_LEN]
            if len(user_input.strip()) > SESSION_TITLE_MAX_LEN:
                title += "..."
            self.session_title = title
            self._title_set = True

    def set_title(self, title: str) -> str:
        """手动设置会话标题"""
        if not title or not title.strip():
            return "❌ 标题不能为空"
        self.session_title = title.strip()[:SESSION_TITLE_MAX_LEN]
        self._title_set = True
        return f"✅ 会话标题已设置为: {self.session_title}"

    def get_title(self) -> str:
        """获取会话标题"""
        return self.session_title if self.session_title else "（无标题）"

    def get_title_display(self) -> str:
        """获取格式化的标题显示文字"""
        if self.session_title:
            return f"💬 **当前会话**: {self.session_title}"
        return "💬 **当前会话**: （暂无标题，发送消息后自动生成）"

    # ============================================================
    # 会话保存/恢复
    # ============================================================

    def save(self, path: str = None) -> str:
        """保存当前会话到文件"""
        from .session_manager import save_session
        try:
            save_path = save_session(self, path=path)
            title_info = f"「{self.session_title}」" if self.session_title else ""
            return f"💾 会话已保存 {title_info} → {os.path.basename(save_path)}"
        except Exception as e:
            return f"❌ 保存失败: {e}"

    def load(self, path: str) -> str:
        """从文件恢复会话"""
        from .session_manager import restore_session
        try:
            result = restore_session(self, path)
            # 设置自动保存路径为原文件，后续消息直接覆盖更新
            self._session_save_path = path
            # 已加载的会话不需要自动生成新标题
            self._title_set = True
            return result
        except FileNotFoundError as e:
            return str(e)
        except Exception as e:
            return f"❌ 加载失败: {e}"

    def _auto_save_if_needed(self):
        """每轮对话后自动保存为独立的会话文件"""
        if SESSION_AUTO_SAVE:
            from .session_manager import auto_save
            path = auto_save(self, session_save_path=self._session_save_path)
            if path:
                self._session_save_path = path

    # ============================================================
    # 手动压缩（Manual Composer）
    # ============================================================

    def compact_context(self) -> str:
        """手动压缩上下文 - 使用 Manual Composer"""
        old_len = len(self.msgs)
        before_tokens = self.current_tokens
        self.msgs, stats = manual_composer(self.msgs, self.client, self.system_prompt)
        # 压缩完成后立即重新计算 Token
        self.current_tokens = self._estimate_tokens(self.msgs)
        self.last_token_stats = (
            f"📊 输入: {self.current_tokens:,} | "
            f"输出: {self.completion_tokens:,} | "
            f"合计: {self.current_tokens + self.completion_tokens:,} | "
            f"占用: {(self.current_tokens / MAX_CTX_TOKENS) * 100:.1f}%"
        )
        self.total_tokens = self.current_tokens + self.completion_tokens
        self.manual_composer_count += 1
        self.last_composer_action = f"Manual Composer: {old_len} → {len(self.msgs)} 条消息"
        # 补充 Token 变化信息
        token_change = ""
        if before_tokens > 0 and self.current_tokens > 0:
            saved = before_tokens - self.current_tokens
            pct = (1 - self.current_tokens / before_tokens) * 100
            token_change = f" | Token: {before_tokens:,} → {self.current_tokens:,} (-{pct:.0f}%)"
        self.composer_notification = (
            f"🟡 Manual Composer 已触发: "
            f"{old_len} → {len(self.msgs)} 条消息{token_change}"
        )
        return stats

    # ============================================================
    # Micro Composer（每轮对话后清理旧 tool 信息）
    # ============================================================

    def _run_micro_composer(self):
        """运行 Micro Composer（每轮对话后自动清理旧 tool 信息）"""
        old_len = len(self.msgs)
        self.msgs = micro_composer(self.msgs)
        if len(self.msgs) < old_len:
            self.micro_composer_count += 1
            removed = old_len - len(self.msgs)
            self.last_composer_action = f"Micro Composer: 清理了 {removed} 条旧 tool 消息"
            self.composer_notification = (
                f"🟢 Micro Composer 已触发: "
                f"清理了 {removed} 条旧 tool 消息"
            )

    # ============================================================
    # Auto Composer（Token 阈值触发语义压缩）
    # ============================================================

    def _run_auto_composer_if_needed(self):
        """检查 Token 阈值，必要时运行 Auto Composer"""
        if self.current_tokens >= COMPACT_THRESHOLD:
            old_len = len(self.msgs)
            self.msgs = auto_composer(self.msgs, self.client, self.system_prompt)
            self.current_tokens = 0
            self.auto_composer_count += 1
            self.last_composer_action = (
                f"Auto Composer: {old_len} → {len(self.msgs)} 条消息 "
                f"(Token 达 {COMPACT_THRESHOLD:,} 阈值)"
            )
            self.composer_notification = (
                f"🔵 Auto Composer 已触发: "
                f"{old_len} → {len(self.msgs)} 条消息 "
                f"(Token 达 {COMPACT_THRESHOLD:,} 阈值)"
            )

    # ============================================================
    # 模型管理

    def get_available_models(self) -> list:
        """获取可用模型列表（内置 + 自定义，合并每模型 API 覆盖），返回 [{name, code, base_url, api_key, is_custom}]"""
        from .config import AVAILABLE_MODELS, apply_model_api_overrides
        builtin = [dict(m) for m in AVAILABLE_MODELS]
        for m in builtin:
            m["is_custom"] = False
        custom = []
        for cfg in self.custom_model_configs.values():
            c = dict(cfg)
            c["is_custom"] = True
            custom.append(c)
        all_models = apply_model_api_overrides(builtin) + custom
        return all_models

    def switch_model(self, model_code: str) -> str:
        """切换当前模型（通过 model code）"""
        available = self.get_available_models()
        # 查找匹配的 model 对象（按 code 匹配）
        model_obj = None
        for m in available:
            if m["code"] == model_code:
                model_obj = m
                break
        if not model_obj:
            return f"❌ 模型 '{model_code}' 不在可用列表中"
        
        old_model = self.current_model
        self.current_model = model_code
        
        # 如果该模型有自定义 base_url 或 api_key，重新初始化客户端
        if model_obj.get("base_url") or model_obj.get("api_key"):
            from .config import API_KEY, API_BASE_URL
            from openai import OpenAI
            base_url = model_obj.get("base_url") or API_BASE_URL
            api_key = model_obj.get("api_key") or API_KEY
            self.client = OpenAI(api_key=api_key)
            self.client.base_url = base_url
        
        return f"✅ 已切换至模型: {model_obj['name']}"

    def add_custom_model(self, name: str, code: str, base_url: str = "", api_key: str = "") -> str:
        """添加自定义模型"""
        if not name.strip() or not code.strip():
            return "❌ 模型名称和标识不能为空"
        
        available = self.get_available_models()
        for m in available:
            if m["code"] == code.strip():
                return f"ℹ️ 模型 '{name.strip()}' (code: {code.strip()}) 已存在"
        
        cfg = {
            "name": name.strip(),
            "code": code.strip(),
            "base_url": base_url.strip() if base_url.strip() else None,
            "api_key": api_key.strip() if api_key.strip() else None,
        }
        self.custom_model_configs[code.strip()] = cfg
        self.custom_models.append(code.strip())
        return f"✅ 已添加自定义模型: {name.strip()} ({code.strip()})"

    def delete_custom_model(self, code: str) -> str:
        """删除自定义模型"""
        if code not in self.custom_model_configs:
            return f"❌ 找不到自定义模型: {code}"
        name = self.custom_model_configs[code]["name"]
        del self.custom_model_configs[code]
        if code in self.custom_models:
            self.custom_models.remove(code)
        # 如果当前正在使用该模型，切回默认模型
        if self.current_model == code:
            from .config import AVAILABLE_MODELS
            if AVAILABLE_MODELS:
                default_code = AVAILABLE_MODELS[0]["code"]
                self.current_model = default_code
                self.reinit_client()
        return f"✅ 已删除自定义模型: {name}"

    def update_model_api(self, code: str, base_url: str = "", api_key: str = ""):
        """更新指定模型的 API 覆盖配置（base_url / api_key），持久化到 user_config.json"""
        from . import config as cfg
        # 如果是自定义模型，直接更新 custom_model_configs
        if code in self.custom_model_configs:
            self.custom_model_configs[code]["base_url"] = base_url.strip() if base_url.strip() else None
            self.custom_model_configs[code]["api_key"] = api_key.strip() if api_key.strip() else None
        else:
            # 内置模型：持久化到 user_config.json
            cfg.save_model_api_override(code, base_url, api_key)
            cfg._invalidate_config_cache()
        # 如果该模型是当前模型，立即重连客户端
        if self.current_model == code:
            self.reinit_client_with_overrides(base_url, api_key)

    def reinit_client_with_overrides(self, base_url: str = "", api_key: str = ""):
        """用指定的 base_url/api_key 重新初始化客户端"""
        from openai import OpenAI
        from .config import API_KEY, API_BASE_URL
        effective_url = base_url.strip() or API_BASE_URL
        effective_key = api_key.strip() or API_KEY
        self.client = OpenAI(
            api_key=effective_key,
            base_url=effective_url,
            timeout=60.0,
        )

    def reinit_client(self):
        """重新初始化 OpenAI 客户端（API Key / Base URL 变更后调用）"""
        from openai import OpenAI
        from .config import API_KEY, API_BASE_URL
        self.client = OpenAI(
            api_key=API_KEY,
            base_url=API_BASE_URL,
            timeout=60.0,
        )

    # ============================================================
    # ============================================================
    # Python 环境管理
    # ============================================================

    def set_python_env(self, path: str) -> str:
        """设置 Python 环境路径"""
        if not path or not path.strip():
            return "❌ 路径不能为空"
        self.python_env = path.strip()
        global PYTHON_ENV_MANUAL_OVERRIDE
        PYTHON_ENV_MANUAL_OVERRIDE = path.strip()
        return f"✅ Python 环境已更新: {self.python_env}"

    def get_python_env_info(self) -> str:
        """获取 Python 环境信息"""
        return (
            f"🐍 **Python 环境配置**\n"
            f"- 当前路径: `{self.python_env}`\n"
            f"- Conda 环境: `{self.conda_env}`\n"
            f"- 手动覆盖: {'✅ 已设置' if PYTHON_ENV_MANUAL_OVERRIDE else '❌ 未设置（使用默认）'}"
        )

    # ============================================================
    # Conda 环境管理
    # ============================================================

    def list_conda_envs(self) -> dict:
        """列出所有 conda 环境"""
        import subprocess
        try:
            result = subprocess.run(
                ["conda", "env", "list", "--json"],
                capture_output=True, text=True, timeout=15
            )
            if result.returncode != 0:
                return {"success": False, "error": result.stderr.strip(), "envs": [], "current": ""}
            data = json.loads(result.stdout)
            envs = data.get("envs", [])
            # 提取环境名（路径末尾的目录名）
            env_names = []
            for e in envs:
                name = os.path.basename(e)
                if name: env_names.append(name)
            return {
                "success": True,
                "envs": env_names,
                "current": self.conda_env,
            }
        except FileNotFoundError:
            return {"success": False, "error": "conda 未安装或不在 PATH 中", "envs": [], "current": ""}
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "conda 命令超时", "envs": [], "current": ""}
        except Exception as e:
            return {"success": False, "error": str(e), "envs": [], "current": ""}

    def switch_conda_env(self, env_name: str) -> str:
        """切换 conda 环境"""
        # 先列出可用环境，验证目标是否存在
        import subprocess
        try:
            result = subprocess.run(
                ["conda", "env", "list", "--json"],
                capture_output=True, text=True, timeout=15
            )
            if result.returncode != 0:
                return f"❌ 无法获取 conda 环境列表: {result.stderr.strip()}"
            data = json.loads(result.stdout)
            envs = data.get("envs", [])
            env_names = [os.path.basename(e) for e in envs if os.path.basename(e)]

            if env_name not in env_names:
                return f"❌ 环境 '{env_name}' 不存在。可用环境: {', '.join(env_names)}"

            self.conda_env = env_name

            # 持久化保存 conda_env 配置
            from .config import _save_user_config
            _save_user_config({"conda_env": env_name})

            # 获取对应环境的 Python 路径
            for e in envs:
                if os.path.basename(e) == env_name:
                    python_path = os.path.join(e, "python.exe") if os.name == "nt" else os.path.join(e, "bin", "python")
                    if os.path.isfile(python_path):
                        self.python_env = python_path
                    return f"✅ 已切换到 conda 环境: {env_name}"
            return f"✅ 已切换到 conda 环境: {env_name}"
        except FileNotFoundError:
            return "❌ conda 未安装或不在 PATH 中"
        except Exception as e:
            return f"❌ 切换失败: {str(e)}"

    def create_conda_env(self, env_name: str, python_version: str = "3.10") -> str:
        """创建新的 conda 环境"""
        import subprocess
        try:
            result = subprocess.run(
                ["conda", "create", "-n", env_name, f"python={python_version}", "-y"],
                capture_output=True, text=True, timeout=120
            )
            if result.returncode != 0:
                return f"❌ 创建环境失败: {result.stderr.strip()}"
            return f"✅ 已创建 conda 环境: {env_name} (Python {python_version})"
        except subprocess.TimeoutExpired:
            return "❌ 创建环境超时（120s）"
        except FileNotFoundError:
            return "❌ conda 未安装或不在 PATH 中"
        except Exception as e:
            return f"❌ 创建失败: {str(e)}"

    # ============================================================
    # 状态缓存更新回调
    # ============================================================

    def set_status_update_callback(self, callback):
        """注册状态更新回调（用于流式期间实时刷新前端 Token 面板）

        Args:
            callback: 无参可调用对象，每次 Token 更新后被调用
        """
        self._status_update_callback = callback

    # ============================================================
    # 模式 system prompt 周期性注入
    # ============================================================

    def _build_mode_inject_text(self) -> str:
        """构建当前模式的简短指令文本（用于周期性注入）"""
        mode = self.mode_mgr.get_mode()
        if mode == MODE_SMART:
            return (
                "## 🧠 当前模式：智能处理模式（Smart）\n\n"
                "请直接执行用户的请求，使用全部可用工具完成用户的需求。"
            )
        else:
            return (
                "## 📋 当前模式：Plan 驱动模式\n\n"
                "收到用户请求后，请严格按流程执行：\n"
                "1. 分析需求并创建 `plan.md`\n"
                "2. 告知用户计划已就绪\n"
                "3. 系统会自动弹出选择菜单，由用户选择后续操作"
            )

    def _inject_mode_prompt_if_needed(self):
        """在用户消息前注入当前模式的简短提醒（每 3 轮或切换后）

        与 switch_mode() 的分工：
        - switch_mode() 处理完整的 system prompt（工具定义+角色+规则）
        - 本方法注入简短的模式指令（仅提醒当前模式，~50 tokens）

        注入策略：
        - 从后往前找非 msgs[0] 的 system 消息，替换为最新模式指令
        - 如果没有找到（异常），追加一条新的
        - 避免与 switch_mode() 刚追加/替换的完整 system prompt 并存
        """
        if len(self.msgs) <= 1:
            return  # 无上下文时不注入（msgs[0] 已有完整 prompt）

        should_inject = self._pending_mode_switch

        # 每 3 轮对话自动注入（防止 AI 遗忘当前模式）
        if not should_inject and self._round_count > 0 and self._round_count % 3 == 0:
            should_inject = True

        if should_inject:
            inject_text = self._build_mode_inject_text()

            # 从后往前找，替换最后一个非 msgs[0] 的 system 消息
            replaced = False
            for i in range(len(self.msgs) - 1, 0, -1):  # 从倒数第一条到索引 1
                if self.msgs[i].get("role") == "system":
                    # 替换为最新的模式指令
                    self.msgs[i]["content"] = inject_text
                    if i < len(self._display_msgs):
                        self._display_msgs[i]["content"] = inject_text
                    replaced = True
                    break

            if not replaced:
                # 没有 system 消息（除了 msgs[0]），追加一条
                self._append_msg({"role": "system", "content": inject_text})

            self._pending_mode_switch = False
    def _on_round_complete(self):
        """对话轮次完成时调用（每轮结束递增计数）"""
        self._round_count += 1

    # ============================================================
    # 同步处理
    # ============================================================

    def process_message(self, user_input: str) -> str:
        """处理用户消息，返回 Agent 响应文本（同步版）"""
        if not user_input or not user_input.strip():
            return ""

        user_input = user_input.strip()

        # ---- 处理特殊指令 ----
        cmd = user_input.lower()

        if cmd in ("esc", "exit", "quit", "q"):
            return "👋 已退出程序。"

        if cmd == "/clear":
            self.reset()
            return "🧹 上下文已清除，Agent 已重置为初始状态。"

        if cmd == "/compact":
            return self.compact_context()

        if cmd == "/smart":
            result = self.switch_mode(MODE_SMART)
            return result

        if cmd == "/plan":
            result = self.switch_mode(MODE_PLAN)
            return result

        if cmd == "/help":
            return self._get_help_text()

        if cmd == "/tools":
            return self._get_tools_text()

        if cmd == "/status":
            return (
                f"📊 **当前状态**\n"
                f"- 模式: {self.mode_mgr.get_mode_name()}\n"
                f"- 上下文消息数: {len(self.msgs)}\n"
                f"- 当前 Token: {self.current_tokens:,} / {MAX_CTX_TOKENS:,}\n"
                f"- Token 占用: {(self.current_tokens / MAX_CTX_TOKENS) * 100:.1f}%\n\n"
                f"{self.get_composer_status()}\n\n"
                f"{self.get_title_display()}\n\n"
                f"{self.get_python_env_info()}"
            )

        # ---- 新命令：会话保存/加载/标题/环境 ----
        if cmd.startswith("/save"):
            parts = user_input.split(maxsplit=1)
            custom_name = parts[1] if len(parts) > 1 else None
            if custom_name:
                self.set_title(custom_name)
            return self.save()

        if cmd.startswith("/load"):
            parts = user_input.split(maxsplit=1)
            if len(parts) < 2:
                # 列出所有会话让用户选择
                from .session_manager import get_session_display_list
                return get_session_display_list() + "\n\n💡 使用 `/load <文件名>` 加载指定会话"
            load_name = parts[1]
            load_path = load_name
            # 如果路径不是绝对路径，尝试在会话目录中查找
            if not os.path.isabs(load_path):
                from .config import SESSION_SAVE_DIR
                load_path = os.path.join(SESSION_SAVE_DIR, load_name)
                if not os.path.exists(load_path):
                    # 尝试查找匹配的文件
                    from .session_manager import list_sessions
                    sessions = list_sessions()
                    matches = [s for s in sessions if load_name in s["filename"]]
                    if matches:
                        load_path = matches[0]["path"]
                    else:
                        return f"❌ 未找到匹配的会话: {load_name}\n💡 使用 `/sessions` 查看所有保存的会话"
            return self.load(load_path)

        if cmd == "/sessions":
            from .session_manager import get_session_display_list
            return get_session_display_list()

        if cmd.startswith("/env"):
            parts = user_input.split(maxsplit=1)
            if len(parts) > 1:
                return self.set_python_env(parts[1])
            return self.get_python_env_info()

        if cmd.startswith("/title"):
            parts = user_input.split(maxsplit=1)
            if len(parts) > 1:
                return self.set_title(parts[1])
            return f"📌 **当前标题**: {self.get_title()}\n💡 使用 `/title <新标题>` 修改标题"

        # ---- 自动设定标题（首次用户消息时，优先使用优化后的 prompt） ----
        # （已移至优化后处理）

        # ---- 注入当前模式 system prompt（每 3 轮或模式切换后） ----
        # ---- Skill & Personality Context ----
        self.skill_engine.new_round()
        round_num = self._round_count
        
        # Refresh personality and skills via rebuild (avoid unbounded prompt growth)
        if (round_num - self._last_skill_inject_round >= self._skill_inject_interval
                or self._last_skill_inject_round == 0):
            self.refresh_personality_in_system_prompt()
            
            # Update the first system message with the rebuilt prompt
            if self.msgs and self.msgs[0].get("role") == "system":
                self.msgs[0]["content"] = self.system_prompt
                if self._display_msgs and self._display_msgs[0].get("role") == "system":
                    self._display_msgs[0]["content"] = self.system_prompt
            self._last_skill_inject_round = round_num

        self._inject_mode_prompt_if_needed()

        # ---- Prompt 智能优化 ----
        optimized_prompt = optimize_prompt(user_input, self.client)

        if optimized_prompt != user_input and optimized_prompt:
            # 使用优化后的 prompt 作为会话标题（更准确）
            self._auto_set_title(optimized_prompt)
            # 记录原始输入和优化后 Prompt（用于前端展示）
            self.original_user_inputs[len(self.msgs)] = user_input
            self.optimized_prompts[len(self.msgs)] = optimized_prompt
            merged_input = format_optimized_prompt(user_input, optimized_prompt)
            self._append_msg({"role": "user", "content": merged_input})
        else:
            # 没有优化时，用原始输入作为标题
            self._auto_set_title(user_input)
            self._append_msg({"role": "user", "content": user_input})

        # ---- Auto Composer 检查（Token 阈值触发语义压缩） ----
        self._run_auto_composer_if_needed()

        # ---- 同步对话循环（处理工具调用链） ----
        final_content = ""
        round_completion_tokens = 0

        while True:
            try:
                response = self.client.chat.completions.create(
                    model=self.current_model,
                    messages=self.msgs,
                    tools=TOOLS,
                    stream=False
                )
            except Exception as e:
                return f"❌ API 调用失败: {e}"

            msg = response.choices[0].message

            # 更新 Token（从 API 响应获取真实 usage）
            if hasattr(response, 'usage') and response.usage:
                usage = response.usage
                self.current_tokens = usage.prompt_tokens or 0
                self.completion_tokens = usage.completion_tokens or 0
                self.total_tokens = usage.total_tokens or (self.current_tokens + self.completion_tokens)
                self.last_token_stats = get_token_stats_text(usage)
                round_completion_tokens += self.completion_tokens

            # ---- 有工具调用 ----
            if msg.tool_calls:
                # 构建助手消息
                assistant_msg = {"role": "assistant", "content": msg.content or ""}
                if hasattr(msg, 'reasoning_content') and msg.reasoning_content:
                    assistant_msg["reasoning_content"] = msg.reasoning_content

                formatted_tc = []
                for tc in msg.tool_calls:
                    formatted_tc.append({
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    })
                assistant_msg["tool_calls"] = formatted_tc
                self._append_msg(assistant_msg)

                # 回传 thinking 内容（工具调用时显示 reasoning）
                if hasattr(msg, "reasoning_content") and msg.reasoning_content:
                    from .main_stream import _get_reasoning_summary
                    reasoning_summary = _get_reasoning_summary(msg.reasoning_content)
                    final_content += f"💭 *推理摘要*: {reasoning_summary}\n\n---\n\n"

                # 执行每个工具
                tool_results_text = ""
                for tc in msg.tool_calls:
                    try:
                        args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                        result = TOOL_FUNCS[tc.function.name](**args)
                    except Exception as e:
                        result = f"❌ 工具执行失败: {e}"

                    if isinstance(result, str) and len(result) > 2000:
                        result = result[:2000] + "\n\n...（结果已截断）"

                    self._append_msg({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": str(result)
                    })
                    # -- Skill: 记录工具使用经验 --
                    try:
                        self.skill_engine.gain_experience_for_tool(
                            tc.function.name, success=True, task_difficulty=1.0
                        )
                    except Exception:
                        pass
                    tool_results_text += f"\n🔧 调用工具: {tc.function.name}(...工具结果已返回...)\n"

                final_content += tool_results_text
                continue  # 继续循环，处理下一轮 API 调用

            # ---- 没有工具调用：输出回复 ----
            else:
                content = msg.content or ""
                has_reasoning = hasattr(msg, 'reasoning_content') and msg.reasoning_content

                if content:
                    # 简洁显示推理摘要
                    if has_reasoning:
                        from .main_stream import _get_reasoning_summary
                        reasoning_summary = _get_reasoning_summary(msg.reasoning_content)
                        final_content += f"💭 *推理摘要*: {reasoning_summary}\n\n---\n\n"

                    final_content += content

                    # 保存助手消息
                    self._append_msg({"role": "assistant", "content": content})
                    if has_reasoning:
                        self.msgs[-1]["reasoning_content"] = msg.reasoning_content

                # 更新会话 Token 累计
                if not hasattr(self, 'session_completion_tokens'):
                    self.session_completion_tokens = 0
                self.session_completion_tokens += round_completion_tokens

                # Token 统计已移除（前端不再显示）

                # Plan 模式菜单提示
                if self.mode_mgr.is_plan_ready():
                    final_content += (
                        "\n\n📋 **Plan 已就绪！**\n"
                        "请在界面上方使用 Plan 菜单选择下一步操作：\n"
                        "1️⃣ 继续探索\n"
                        "2️⃣ 修改计划\n"
                        "3️⃣ 切换为 Smart 模式并执行"
                    )

                # 每轮结束递增计数
                # -- Personality: 交互分析与调整 --
                try:
                    interaction_data = {
                        "task_type": "general",
                        "user_feedback": "neutral",
                        "complexity": 0.5,
                        "success": True,
                    }
                    self.personality_engine.analyze_and_adjust_traits(interaction_data)
                    self.personality_engine.adapt_language_style({
                        "user_style": "neutral",
                        "topic": "general",
                        "urgency": 0.5,
                    })
                except Exception:
                    pass
                # -- 自动保存技能与人格 --
                try:
                    self.skill_engine.save()
                    self.personality_engine.save_profile()
                except Exception:
                    pass

                self._on_round_complete()

                # Micro Composer
                self._run_micro_composer()

                # 自动保存
                self._auto_save_if_needed()

                return final_content

    # ============================================================
    # 辅助方法
    # ============================================================

    def _get_help_text(self):
        """获取帮助文本"""
        return (
            "📋 **可用命令**\n\n"
            "**模式切换**\n"
            "- `/smart` — 切换到智能处理模式\n"
            "- `/plan` — 切换到 Plan 驱动模式\n\n"
            "**上下文管理**\n"
            "- `/clear` — 清除上下文\n"
            "- `/compact` — 手动压缩上下文\n"
            "- `/status` — 查看当前状态\n\n"
            "**会话管理**\n"
            "- `/save [标题]` — 保存当前会话\n"
            "- `/load <文件名>` — 加载会话\n"
            "- `/sessions` — 列出所有会话\n"
            "- `/title <新标题>` — 修改会话标题\n\n"
            "**环境配置**\n"
            "- `/env [路径]` — 查看/设置 Python 环境\n\n"
            "**其他**\n"
            "- `/tools` — 查看可用工具\n"
            "- `/help` — 显示此帮助\n"
            "- `exit/quit/q` — 退出"
        )

    def _get_tools_text(self):
        """获取工具列表文本"""
        lines = ["🔧 **可用工具**\n"]
        for tool in TOOLS:
            name = tool["function"]["name"]
            desc = tool["function"]["description"]
            lines.append(f"- **{name}**: {desc}")
        return "\n".join(lines)


