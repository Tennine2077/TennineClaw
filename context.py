# ============================================================
# 三重上下文管理器（Composer）
# ============================================================
# 管理三种上下文化策略，控制对话历史的内容与长度：
#   1️⃣ Micro Composer  — 每轮自动清理旧 tool 调用信息
#   2️⃣ Auto Composer   — Token 阈值触发语义压缩
#   3️⃣ Manual Composer — 用户手动触发语义压缩
# ============================================================

from config import (
    COMPOSER_ENABLED,
    MICRO_COMPOSER_KEEP_ROUNDS,
    COMPRESS_MAX_CHARS,
    MANUAL_COMPOSER_MAX_CHARS,
)

# ============================================================
# 1️⃣ Micro Composer — 每轮对话后自动调用
# ============================================================
# 功能：保留所有对话消息，但仅保留最近 N 轮中的 tool 调用信息
#       更早的 tool_calls 和 tool role 消息被移除
# 特点：纯删除操作，不做任何总结/压缩
# ============================================================

def micro_composer(msgs: list) -> list:
    """Micro Composer：每轮对话后自动清理旧工具调用信息

    保留所有轮次的对话消息（user、assistant 文本等），
    但仅保留最近 MICRO_COMPOSER_KEEP_ROUNDS 轮中的 tool 调用信息，
    更早的 tool_calls 字段和 role:tool 消息被移除。

    Args:
        msgs: 当前完整的消息列表

    Returns:
        清理后的消息列表
    """
    if not COMPOSER_ENABLED:
        return msgs

    if not msgs:
        return msgs

    # ---- 分离 system 消息和非 system 消息 ----
    system_msgs = [m for m in msgs if m.get("role") == "system"]
    other_msgs = [m for m in msgs if m.get("role") != "system"]

    if len(other_msgs) <= 2:
        return msgs

    # ---- 将消息按"轮次"分组 ----
    # 每轮以 user 消息开始，直到下一条 user 消息之前
    rounds = _split_into_rounds(other_msgs)

    if len(rounds) <= MICRO_COMPOSER_KEEP_ROUNDS:
        return msgs

    # ---- 分离旧轮次和保留轮次 ----
    # 保留最近 MICRO_COMPOSER_KEEP_ROUNDS 轮的完整信息
    keep_rounds = rounds[-MICRO_COMPOSER_KEEP_ROUNDS:]
    old_rounds = rounds[:-MICRO_COMPOSER_KEEP_ROUNDS]

    # ---- 清理旧轮次中的 tool 信息 ----
    cleaned_old_rounds = []
    for round_msgs in old_rounds:
        cleaned_round = []
        for m in round_msgs:
            role = m.get("role", "")
            # 移除 tool 角色消息（工具调用结果）
            if role == "tool":
                continue
            # 保留非 tool 消息，但移除 tool_calls 字段
            new_m = dict(m)
            if role == "assistant" and "tool_calls" in new_m:
                del new_m["tool_calls"]
                # 如果 assistant 消息既没有内容也没有 tool_calls，则跳过
                if not new_m.get("content", ""):
                    continue
            cleaned_round.append(new_m)
        cleaned_old_rounds.append(cleaned_round)

    # ---- 重建消息列表 ----
    new_msgs = system_msgs.copy()
    for r in cleaned_old_rounds:
        new_msgs.extend(r)
    for r in keep_rounds:
        new_msgs.extend(r)

    return new_msgs


# ============================================================
# 2️⃣ Auto Composer — Token 阈值触发语义压缩
# ============================================================
# 功能：当 Token 达到阈值时，对历史上下文进行 LLM 语义总结
#       保留 system prompt + 最近 1 轮完整对话 + 压缩摘要
# 特点：LLM 智能压缩，输出 ≤ COMPRESS_MAX_CHARS 字
# ============================================================

def auto_composer(msgs: list, client=None, system_prompt: str = "") -> list:
    """Auto Composer：Token 达到阈值时自动触发语义压缩

    对历史上下文进行 LLM 语义总结压缩，
    system prompt 更新为当前模式的最新版本 + 压缩摘要。

    Args:
        msgs: 当前完整的消息列表
        client: OpenAI 客户端实例（用于 LLM 压缩）
        system_prompt: 当前模式的系统提示词（替换 msgs[0]）

    Returns:
        压缩后的消息列表
    """
    if not COMPOSER_ENABLED:
        return msgs

    if not msgs:
        return msgs

    system_msgs = [m for m in msgs if m.get("role") == "system"]
    other_msgs = [m for m in msgs if m.get("role") != "system"]

    if len(other_msgs) <= 4:
        return msgs

    # ---- 将消息按轮次分组 ----
    rounds = _split_into_rounds(other_msgs)

    if len(rounds) <= 1:
        return msgs

    # 保留最近 1 轮完整对话
    keep_rounds = rounds[-1:]
    summarize_rounds = rounds[:-1]

    # ---- 构建待压缩的历史文本 ----
    summary_text = _build_history_text(summarize_rounds)

    if not summary_text.strip():
        # 没有可压缩的内容
        new_msgs = [{"role": "system", "content": system_prompt}]
        for r in keep_rounds:
            new_msgs.extend(r)
        return new_msgs

    # 如果文本很短，直接作为摘要
    if len(summary_text) < COMPRESS_MAX_CHARS * 0.3:
        summary_content = (
            f"以下为历史对话摘要（已压缩）：\n\n{summary_text}"
        )
        new_msgs = [{"role": "system", "content": system_prompt}]
        new_msgs.append({"role": "user", "content": summary_content})
        for r in keep_rounds:
            new_msgs.extend(r)
        return new_msgs

    # ---- 尝试 LLM 压缩 ----
    if client is not None:
        try:
            compressed = _llm_compress(summary_text, client, max_chars=COMPRESS_MAX_CHARS)
            summary_content = (
                f"以下为 AI 智能压缩的历史对话摘要（{COMPRESS_MAX_CHARS}字以内）：\n\n{compressed}"
            )
        except Exception as e:
            print(f"\n⚠️ Auto Composer LLM 压缩失败（{e}），降级为截断模式...")
            fallback_text = summary_text[:COMPRESS_MAX_CHARS]
            summary_content = (
                f"以下为历史对话摘要（压缩失败，降级截断）：\n\n{fallback_text}"
            )
    else:
        # 无 client，直接截断
        summary_content = (
            f"以下为历史对话摘要（无 LLM，截断模式）：\n\n{summary_text[:COMPRESS_MAX_CHARS]}"
        )

    # ---- 重建消息列表 ----
    new_msgs = [{"role": "system", "content": system_prompt}]
    new_msgs.append({"role": "user", "content": summary_content})
    for r in keep_rounds:
        new_msgs.extend(r)

    return new_msgs


# ============================================================
# 3️⃣ Manual Composer — 用户手动触发语义压缩
# ============================================================
# 功能：用户通过 /compact 命令手动触发
#       不管上下文多少，立即对全部内容进行语义总结
# 特点：保留 system prompt + 压缩摘要
# ============================================================

def manual_composer(msgs: list, client=None, system_prompt: str = "") -> list:
    """Manual Composer：用户手动触发，压缩全部上下文

    对全部非 system 消息进行 LLM 语义总结压缩，
    仅保留 system prompt + 压缩摘要。

    Args:
        msgs: 当前完整的消息列表
        client: OpenAI 客户端实例（用于 LLM 压缩）

    Returns:
        压缩后的消息列表
    """
    if not COMPOSER_ENABLED:
        return msgs, "⛔ Composer 已禁用，无法压缩"

    if not msgs:
        return msgs, "📭 没有可压缩的上下文"

    system_msgs = [m for m in msgs if m.get("role") == "system"]
    other_msgs = [m for m in msgs if m.get("role") != "system"]

    if not other_msgs:
        return msgs, "📭 没有可压缩的对话历史"

    old_count = len(msgs)

    # ---- 构建完整的对话历史文本 ----
    history_text = _build_complete_history_text(other_msgs)

    if not history_text.strip():
        return msgs, "📭 对话历史为空，无需压缩"

    # ---- 尝试 LLM 压缩 ----
    if client is not None:
        try:
            compressed = _llm_compress(
                history_text, client,
                max_chars=MANUAL_COMPOSER_MAX_CHARS,
                full_summary=True
            )
            summary_content = (
                f"以下为完整对话历史的 AI 摘要（已压缩至 {MANUAL_COMPOSER_MAX_CHARS} 字以内）：\n\n"
                f"{compressed}"
            )
            compress_method = "LLM 智能压缩"
        except Exception as e:
            print(f"\n⚠️ Manual Composer LLM 压缩失败（{e}），降级为截断模式...")
            fallback_text = history_text[:MANUAL_COMPOSER_MAX_CHARS]
            summary_content = (
                f"以下为完整对话历史摘要（压缩失败，降级截断）：\n\n{fallback_text}"
            )
            compress_method = "降级截断"
    else:
        # 无 client，直接截断
        summary_content = (
            f"以下为完整对话历史摘要（无 LLM，截断模式）：\n\n{history_text[:MANUAL_COMPOSER_MAX_CHARS]}"
        )
        compress_method = "截断模式"

    # ---- 重建消息列表 ----
    new_msgs = [{"role": "system", "content": system_prompt}]
    new_msgs.append({"role": "user", "content": summary_content})

    new_count = len(new_msgs)

    # ---- 构建统计信息 ----
    old_chars = len(history_text)
    new_chars = len(summary_content)
    stats = (
        f"📦 **手动压缩完成！**\n"
        f"- 压缩方式：{compress_method}\n"
        f"- 消息数：{old_count} → {new_count}\n"
        f"- 字符数：{old_chars:,} → {new_chars:,}\n"
        f"- 压缩比：{new_chars / max(old_chars, 1) * 100:.1f}%\n"
        f"- 压缩上限：{MANUAL_COMPOSER_MAX_CHARS:,} 字"
    )

    return new_msgs, stats


# ============================================================
# 辅助函数
# ============================================================

def _split_into_rounds(msgs: list) -> list:
    """将消息列表按轮次分组

    每轮以 user 消息开始，直到下一条 user 消息之前
    """
    rounds = []
    current_round = []

    for m in msgs:
        if m.get("role") == "user" and current_round:
            rounds.append(current_round)
            current_round = [m]
        else:
            current_round.append(m)

    if current_round:
        rounds.append(current_round)

    return rounds


def _build_history_text(rounds: list) -> str:
    """构建待压缩的历史对话文本（用于 Auto Composer）"""
    lines = []

    for round_msgs in rounds:
        for m in round_msgs:
            role = m.get("role", "unknown")
            content = m.get("content", "") or ""
            tc = m.get("tool_calls")

            if role == "tool":
                # 工具结果：只保留关键信息
                tool_name = m.get("name", "?")
                if len(content) > 200:
                    content = content[:200] + "..."
                lines.append(f"[工具结果 - {tool_name}]: {content}")
            elif role == "assistant" and tc:
                # 有工具调用的助手消息
                tool_names = [t.get("function", {}).get("name", "?") for t in tc]
                lines.append(f"[助手调用工具]: {', '.join(tool_names)}")
                if content:
                    lines.append(f"[助手回复]: {content[:500]}")
            else:
                lines.append(f"[{role}]: {content[:800]}")

    return "\n".join(lines)


def _build_complete_history_text(msgs: list) -> str:
    """构建完整的对话历史文本（用于 Manual Composer）"""
    lines = []

    for m in msgs:
        role = m.get("role", "unknown")
        content = m.get("content", "") or ""
        tc = m.get("tool_calls")

        if role == "tool":
            tool_name = m.get("name", "?")
            lines.append(f"[工具结果 - {tool_name}]: {content[:300]}")
        elif role == "assistant" and tc:
            tool_names = [t.get("function", {}).get("name", "?") for t in tc]
            lines.append(f"[助手调用工具]: {', '.join(tool_names)}")
            if content:
                lines.append(f"[助手回复]: {content[:1000]}")
        else:
            lines.append(f"[{role}]: {content[:1500]}")

    return "\n".join(lines)


def _llm_compress(history_text: str, client, max_chars: int = 30000, full_summary: bool = False) -> str:
    """调用 LLM 进行对话摘要压缩

    Args:
        history_text: 待压缩的历史对话文本
        client: OpenAI 客户端实例
        max_chars: 压缩后最大字符数
        full_summary: 是否为完整摘要（Manual Composer）

    Returns:
        压缩后的摘要文本
    """
    if full_summary:
        compress_prompt = f"""你是一个专业的对话摘要助手。请将以下完整对话历史压缩成一段全面的摘要（严格控制在 {max_chars} 字以内）。

要求：
- 保留用户的核心需求、所有问题和关注点
- 记录助手执行了哪些关键操作和工具调用
- 包含重要的执行结果、发现和结论
- 保留已达成的共识和待办事项
- 语言简洁精炼，保留关键细节
- 按时间顺序组织，确保逻辑连贯

完整对话历史：
{history_text}

请直接输出压缩后的摘要（不超过 {max_chars} 字）："""
    else:
        compress_prompt = f"""你是一个专业的对话摘要助手。请将以下历史对话内容压缩成一段简洁的摘要（严格控制在 {max_chars} 字以内）。

要求：
- 保留用户的核心需求、问题和关注点
- 记录助手执行了哪些关键操作和工具调用
- 包含重要的执行结果、发现和结论
- 保留已达成的共识和待办事项
- 语言简洁精炼，保留关键细节

历史对话内容：
{history_text}

请直接输出压缩后的摘要（不超过 {max_chars} 字）："""

    compress_res = client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=[
            {"role": "system", "content": "你是一个专业的对话摘要助手，擅长精确提炼关键信息，输出简洁有力的摘要。"},
            {"role": "user", "content": compress_prompt}
        ],
        max_tokens=max_chars,
        temperature=0.3
    )

    compressed = compress_res.choices[0].message.content.strip()

    if len(compressed) > max_chars:
        compressed = compressed[:max_chars] + "\n\n...（摘要已截断）"

    return compressed


# ============================================================
# 兼容旧接口（保留向后兼容）
# ============================================================

def compact_messages(msgs: list, client=None) -> list:
    """（兼容旧接口）压缩上下文，内部调用 auto_composer

    Args:
        msgs: 当前完整的消息列表
        client: OpenAI 客户端实例

    Returns:
        压缩后的消息列表（由 auto_composer 处理）
    """
    return auto_composer(msgs, client)
