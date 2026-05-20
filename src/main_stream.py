# ============================================================
# TennineClaw - 流式对话处理模块
# ============================================================
# 核心功能：Agent 会话的流式响应生成、文本分段输出、
# 推理摘要提取、工具调用链处理
# ============================================================

import os
import json
import re

from .config import (
    API_MODEL,
    MAX_CTX_TOKENS,
    MODE_SMART, MODE_PLAN,
    SESSION_SAVE_DIR,
)
from .context import micro_composer, auto_composer, manual_composer
from .token_utils import get_token_stats_text
from .tools import TOOLS, TOOL_FUNCS
from .prompt_optimizer import optimize_prompt, format_optimized_prompt


# ============================================================
# 工具函数 — 文本分段与推理摘要
# ============================================================

def _split_into_paragraphs(text: str, min_chars: int = 80) -> list:
    """将文本按自然段落/句子分割成块，用于逐段输出
    
    分割策略（优先级从高到低）：
    1. 双换行符 \n\n → 段落分割
    2. 单换行符 \n → 行分割
    3. 句号/问号/感叹号 → 句子分割
    4. 逗号/分号 → 子句分割（仅在块过长时）
    
    Args:
        text: 要分割的文本
        min_chars: 每个块的最小字符数（低于此值会合并）
    
    Returns:
        分割后的文本块列表
    """
    if not text or not text.strip():
        return []
    
    text = text.strip()
    
    # 如果文本很短，直接返回
    if len(text) <= min_chars * 1.5:
        return [text]
    
    chunks = []
    
    # 策略1：按双换行分段落
    paragraphs = re.split(r'\n\s*\n', text)
    
    # 如果只有一个段落，尝试更细粒度的分割
    if len(paragraphs) <= 1:
        # 策略2：按单换行分割
        lines = text.split('\n')
        if len(lines) > 1:
            current = ""
            for line in lines:
                if not line.strip():
                    if current.strip():
                        chunks.append(current.strip())
                        current = ""
                    continue
                if not current:
                    current = line
                elif len(current) + len(line) < min_chars * 2:
                    current += '\n' + line
                else:
                    chunks.append(current.strip())
                    current = line
            if current.strip():
                chunks.append(current.strip())
            
            if len(chunks) > 1:
                return chunks
        
        # 策略3：按句子分割
        sentences = re.split(r'(?<=[。！？.!?])\s*', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if len(sentences) > 1:
            current = ""
            for sent in sentences:
                if not current:
                    current = sent
                elif len(current) + len(sent) < min_chars:
                    current += sent
                else:
                    chunks.append(current.strip())
                    current = sent
            if current.strip():
                chunks.append(current.strip())
            return chunks if chunks else [text]
        
        return [text]
    
    # 有多个段落，逐段落处理
    current = ""
    for para in paragraphs:
        para = para.strip()
        if not para:
            if current:
                chunks.append(current.strip())
                current = ""
            continue
        
        if not current:
            current = para
        elif len(current) + len(para) < min_chars * 3:
            current += '\n\n' + para
        else:
            chunks.append(current.strip())
            current = para
    
    if current.strip():
        chunks.append(current.strip())
    
    return chunks if chunks else [text]


def _get_reasoning_summary(reasoning_text: str, max_chars: int = -1) -> str:
    """从完整推理内容中提取摘要

    去除常见的 token 标记符（如 🧹、▊、◆ 等），默认显示完整 thinking 内容。

    Args:
        reasoning_text: 完整的推理内容
        max_chars: 摘要最大字符数，-1 表示不限制（显示完整内容）

    Returns:
        推理摘要（默认完整显示）
    """
    if not reasoning_text or not reasoning_text.strip():
        return ""
    
    # 去除常见的 token 标记符
    cleaned = reasoning_text.strip()
    for marker in ['🧹', '▊', '◆', '◇', '→', '←', '●', '○']:
        cleaned = cleaned.replace(marker, '')
    
    # 合并多余空格
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    # 默认不限制长度，显示完整 thinking
    if max_chars < 0:
        return cleaned.strip()
    
    # 仅在指定 max_chars 时截断
    summary = cleaned[:max_chars]
    if len(cleaned) > max_chars:
        summary += "..."
    
    return summary.strip()


# ============================================================
# Agent 会话类 — 流式处理方法
# ============================================================

class AgentSessionStreamMixin:
    """为 AgentSession 提供流式处理方法（混入类）"""

    def process_message_stream(self, user_input: str):
        """处理用户消息，流式返回响应（生成器）
        
        功能：
        - 逐段落输出：将回复分割为段落/句子块逐段 yield
        - 简洁推理摘要：去除标记符号，输出紧凑的推理摘要
        - 会话 Token 统计：对话完成时自动展示累计 Token 数
        """
        if not user_input or not user_input.strip():
            yield ""
            return

        user_input = user_input.strip()

        # ---- 处理特殊指令 ----
        cmd = user_input.lower()

        if cmd in ("esc", "exit", "quit", "q"):
            yield "👋 已退出程序。"
            return

        if cmd == "/clear":
            self.reset()
            yield "🧹 上下文已清除，Agent 已重置为初始状态。"
            return

        if cmd == "/compact":
            yield self.compact_context()
            return

        if cmd == "/smart":
            yield self.switch_mode(MODE_SMART)
            return

        if cmd == "/plan":
            yield self.switch_mode(MODE_PLAN)
            return

        if cmd == "/help":
            yield self._get_help_text()
            return

        if cmd == "/tools":
            yield self._get_tools_text()
            return

        if cmd == "/status":
            yield (
                f"📊 **当前状态**\n"
                f"- 模式: {self.mode_mgr.get_mode_name()}\n"
                f"- 上下文消息数: {len(self.msgs)}\n"
                f"- 当前 Token: {self.current_tokens:,} / {MAX_CTX_TOKENS:,}\n"
                f"- Token 占用: {(self.current_tokens / MAX_CTX_TOKENS) * 100:.1f}%\n\n"
                f"{self.get_composer_status()}\n\n"
                f"{self.get_title_display()}\n\n"
                f"{self.get_python_env_info()}"
            )
            return

        if cmd.startswith("/save"):
            parts = user_input.split(maxsplit=1)
            custom_name = parts[1] if len(parts) > 1 else None
            if custom_name:
                self.set_title(custom_name)
            yield self.save()
            return

        if cmd.startswith("/load"):
            parts = user_input.split(maxsplit=1)
            if len(parts) < 2:
                from session_manager import get_session_display_list
                yield get_session_display_list() + "\n\n💡 使用 `/load <文件名>` 加载指定会话"
                return
            load_name = parts[1]
            load_path = load_name
            if not os.path.isabs(load_path):
                from .config import SESSION_SAVE_DIR
                load_path = os.path.join(SESSION_SAVE_DIR, load_name)
                if not os.path.exists(load_path):
                    from session_manager import list_sessions
                    sessions = list_sessions()
                    matches = [s for s in sessions if load_name in s["filename"]]
                    if matches:
                        load_path = matches[0]["path"]
                    else:
                        yield f"❌ 未找到匹配的会话: {load_name}\n💡 使用 `/sessions` 查看所有保存的会话"
                        return
            yield self.load(load_path)
            return

        if cmd == "/sessions":
            from session_manager import get_session_display_list
            yield get_session_display_list()
            return

        if cmd.startswith("/env"):
            parts = user_input.split(maxsplit=1)
            if len(parts) > 1:
                yield self.set_python_env(parts[1])
            else:
                yield self.get_python_env_info()
            return

        if cmd.startswith("/title"):
            parts = user_input.split(maxsplit=1)
            if len(parts) > 1:
                yield self.set_title(parts[1])
            else:
                yield f"📌 **当前标题**: {self.get_title()}\n💡 使用 `/title <新标题>` 修改标题"
            return

        # ---- 注入当前模式 system prompt（每 3 轮或模式切换后） ----
        self._inject_mode_prompt_if_needed()

        # ---- try/finally 覆盖整个流式回复区域 ————
        # 确保即使生成器被外部 close()（客户端断连）也能 auto_save
        try:
            # ---- Prompt 智能优化 ----
            optimized_prompt = optimize_prompt(user_input, self.client)
            if optimized_prompt != user_input and optimized_prompt:
                # 使用优化后的 prompt 作为会话标题（更准确）
                self._auto_set_title(optimized_prompt)
                # 记录原始输入和优化后 Prompt（用于前端展示）
                self.original_user_inputs[len(self.msgs)] = user_input
                self.optimized_prompts[len(self.msgs)] = optimized_prompt
                merged_input = format_optimized_prompt(user_input, optimized_prompt)
                self.msgs.append({"role": "user", "content": merged_input})
                yield "__OPT__" + optimized_prompt
            else:
                # 没有优化时，用原始输入作为标题
                self._auto_set_title(user_input)
                self.msgs.append({"role": "user", "content": user_input})

            # ---- Auto Composer 检查（Token 阈值触发语义压缩） ----
            self._run_auto_composer_if_needed()

            # ---- 流式对话循环（处理工具调用链） ----
            final_content = ""
            collected_content = ""
            collected_reasoning = ""
            tool_calls_data = {}
            tool_call_order = []
            is_collecting_tool = False
            
            # 本轮累计的输出 Token（用于会话统计）
            round_completion_tokens = 0

            while True:
                # ---- 打断检测 ----
                if self._stream_interrupted:
                    yield "\n\n⏹️ **已中断**"
                    # 中断时保存当前消息状态
                    self._auto_save_if_needed()
                    break

                collected_content = ""
                collected_reasoning = ""
                tool_calls_data = {}
                tool_call_order = []
                is_collecting_tool = False

                try:
                    stream = self.client.chat.completions.create(
                        model=self.current_model,
                        messages=self.msgs,
                        tools=TOOLS,
                        stream=True
                    )
                except Exception as e:
                    error_msg = f"❌ API 调用失败: {e}"
                    yield error_msg
                    return

                last_chunk = None

                for chunk in stream:
                    # ---- 流式中断检测 ----
                    if self._stream_interrupted:
                        break

                    last_chunk = chunk

                    if chunk.choices and len(chunk.choices) > 0:
                        delta = chunk.choices[0].delta

                        # 收集 reasoning_content（思考过程）
                        if hasattr(delta, "reasoning_content") and delta.reasoning_content:
                            collected_reasoning += delta.reasoning_content

                        # 收集 content（回复文本）
                        if delta.content:
                            collected_content += delta.content

                        # 收集 tool_calls
                        if delta.tool_calls:
                            is_collecting_tool = True
                            for tc in delta.tool_calls:
                                idx = tc.index
                                if idx not in tool_calls_data:
                                    tool_calls_data[idx] = {
                                        "index": idx,
                                        "id": tc.id or "",
                                        "type": "function",
                                        "function": {"name": "", "arguments": ""}
                                    }
                                    tool_call_order.append(idx)
                                if tc.id:
                                    tool_calls_data[idx]["id"] = tc.id
                                if tc.function:
                                    if tc.function.name:
                                        tool_calls_data[idx]["function"]["name"] += tc.function.name
                                    if tc.function.arguments:
                                        tool_calls_data[idx]["function"]["arguments"] += tc.function.arguments

                # 更新 Token（从流式最后一个 chunk 提取 API 真实 usage）
                if last_chunk and hasattr(last_chunk, 'usage') and last_chunk.usage:
                    usage = last_chunk.usage
                    self.current_tokens = usage.prompt_tokens or 0
                    self.completion_tokens = usage.completion_tokens or 0
                    self.total_tokens = usage.total_tokens or (self.current_tokens + self.completion_tokens)
                    self.last_token_stats = get_token_stats_text(usage)
                    
                    # 累计会话级输出 Token
                    round_completion_tokens += self.completion_tokens

                # ---- 有工具调用：执行工具 ----
                if tool_calls_data:
                    # 构建助手消息
                    assistant_msg = {"role": "assistant", "content": collected_content or ""}
                    if collected_reasoning:
                        assistant_msg["reasoning_content"] = collected_reasoning

                    formatted_tc = []
                    # 按 index 顺序排列 tool calls
                    for idx in sorted(tool_calls_data.keys()):
                        tc_data = tool_calls_data[idx]
                        formatted_tc.append({
                            "id": tc_data["id"],
                            "type": "function",
                            "function": {
                                "name": tc_data["function"]["name"],
                                "arguments": tc_data["function"]["arguments"]
                            }
                        })
                    assistant_msg["tool_calls"] = formatted_tc
                    self.msgs.append(assistant_msg)

                    # 回传 thinking 内容（工具调用时显示 reasoning）
                    has_reasoning = bool(collected_reasoning and collected_reasoning.strip())
                    if has_reasoning:
                        reasoning_summary = _get_reasoning_summary(collected_reasoning)
                        yield f"💭 *推理摘要*: {reasoning_summary}\n\n---\n\n"

                    # 执行每个工具
                    for idx in sorted(tool_calls_data.keys()):
                        tc_data = tool_calls_data[idx]
                        func_name = tc_data["function"]["name"]
                        func_args = tc_data["function"]["arguments"]

                        try:
                            args = json.loads(func_args) if func_args else {}
                            result = TOOL_FUNCS[func_name](**args)
                        except Exception as e:
                            result = f"❌ 工具执行失败: {e}"

                        if isinstance(result, str) and len(result) > 2000:
                            result = result[:2000] + "\n\n...（结果已截断）"

                        self.msgs.append({
                            "role": "tool",
                            "tool_call_id": tc_data["id"],
                            "content": str(result)
                        })

                        # 流式输出工具调用信息
                        yield f"\n🔧 调用工具: {func_name}(...工具结果已返回...)\n"

                    # 继续循环，处理下一轮
                    continue

                # ---- 没有工具调用：输出回复 ----
                else:
                    content = collected_content or ""
                    has_reasoning = bool(collected_reasoning and collected_reasoning.strip())
                    
                    if content:
                        # 简洁显示推理摘要（如有）
                        if has_reasoning:
                            reasoning_summary = _get_reasoning_summary(collected_reasoning)
                            yield f"💭 *推理摘要*: {reasoning_summary}\n\n---\n\n"
                        
                        # 逐段落输出内容
                        chunks = _split_into_paragraphs(content)
                        for i, chunk in enumerate(chunks):
                            yield chunk
                            # 段落间添加小小的延迟效果（由前端控制，这里只是分段）
                            if i < len(chunks) - 1:
                                yield "\n\n"
                        
                        # 保存助手消息（包含推理内容以备后用）
                        assistant_msg = {"role": "assistant", "content": content}
                        if collected_reasoning:
                            assistant_msg["reasoning_content"] = collected_reasoning
                        self.msgs.append(assistant_msg)
                    
                    # 添加会话级 Token 统计
                    if self.session_completion_tokens is None:
                        self.session_completion_tokens = 0
                    self.session_completion_tokens += round_completion_tokens
                    
                    # 最终 Token 统计信息
                    if self.completion_tokens > 0 or self.session_completion_tokens > 0:
                        token_summary = (
                            f"\n\n---\n📊 **Token 统计**\n"
                            f"输入 Token: {self.current_tokens:,}\n"
                            f"输出 Token: {self.session_completion_tokens:,}\n"
                            f"合计: {(self.current_tokens or 0) + self.session_completion_tokens:,}"
                        )
                        yield token_summary
                    
                    # 更新 last_token_stats
                    if self.current_tokens == 0:
                        self.last_token_stats = "📊 Token: 暂未获取到 API usage 数据"
                    
                    # Plan 菜单自动检测
                    if self.mode_mgr.is_plan_ready():
                        yield "\n\n📋 **Plan 已就绪！** 系统会自动弹出选择菜单..."
                    
                    # 每轮结束递增计数
                    self._on_round_complete()

                    # 每轮对话后运行 Micro Composer
                    self._run_micro_composer()
                    
                    # 自动保存
                    self._auto_save_if_needed()
                    
                    # 更新状态缓存回调（如果有）
                    if hasattr(self, '_status_update_callback') and self._status_update_callback:
                        try:
                            self._status_update_callback()
                        except Exception:
                            pass
                    
                    break  # 结束循环
        except GeneratorExit:
            # 生成器被外部 close()（客户端断开连接等）
            pass
        finally:
            # 任何情况下都尝试保存会话（包括生成器被 close）
            self._auto_save_if_needed()

    # ============================================================
    # 帮助和工具列表文本
    # ============================================================

    def _get_help_text(self) -> str:
        """获取帮助文本"""
        lines = [
            "🤖 **TennineClaw 帮助**\n",
            "**可用命令：**",
            "- `/smart` — 切换到智能处理模式",
            "- `/plan` — 切换到 Plan 驱动模式",
            "- `/clear` — 清除上下文",
            "- `/compact` — 手动压缩上下文",
            "- `/status` — 查看当前状态",
            "- `/tools` — 查看可用工具列表",
            "- `/save [标题]` — 保存当前会话",
            "- `/load <文件名>` — 加载指定会话",
            "- `/sessions` — 查看所有保存的会话",
            "- `/title <新标题>` — 设置会话标题",
            "- `/env [路径]` — 查看/设置 Python 环境",
            "- `/help` — 显示此帮助信息",
            "",
            "**模式说明：**",
            "1. 🧠 **智能处理模式** — 直接执行用户请求",
            "2. 📋 **Plan驱动模式** — 先生成计划再执行",
            "",
            "**快捷键：**",
            "- Enter 发送消息",
            "- Shift+Enter 换行",
            "- Esc / exit / quit 退出程序",
        ]
        return "\n".join(lines)

    def _get_tools_text(self) -> str:
        """获取可用工具列表"""
        lines = [
            "🔧 **可用工具列表**\n",
        ]
        tool_descs = {
            "run_cmd": "执行系统命令（带安全检测）",
            "read_file": "读取文件完整内容",
            "write_file": "写入或覆盖文件内容",
            "list_files": "列出目录内容",
            "search_files": "搜索文件",
            "get_system_info": "获取系统信息",
            "get_current_time": "获取当前时间",
            "create_directory": "创建目录",
            "delete_file": "删除文件或空目录",
        }
        for name, desc in tool_descs.items():
            lines.append(f"- **{name}**: {desc}")
        return "\n".join(lines)

