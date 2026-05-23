# ============================================================
# Prompt 智能优化器
# ============================================================
# 将用户的原始 prompt 改写为更结构化、清晰的格式，
# 保留原始和优化后的 prompt 用于后续参考。
# ============================================================


def optimize_prompt(original: str, client, context_msgs: list = None) -> str:
    """将用户的原始 prompt 优化为更结构化、更清晰的格式

    如果提供了 context_msgs（对话历史），优化时会结合完整上下文，
    使优化后的 prompt 能包含上下文信息（如引用之前的对话内容）。

    Args:
        original: 用户原始输入的 prompt
        client: OpenAI 客户端实例
        context_msgs: 对话历史消息列表（压缩后的 self.msgs），可选

    Returns:
        优化后的结构化 prompt
    """
    if not original or not original.strip():
        return original

    # ---- 构建上下文信息 ----
    context_str = ""
    if context_msgs:
        lines = []
        for msg in context_msgs:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            # 截断过长内容（保留前 200 字符）
            if len(content) > 200:
                content = content[:200] + "..."
            lines.append(f"{role}: {content}")
        context_str = "\n".join(lines)

    system_msg = (
        "你是一个专业的 Prompt 优化助手。你的任务是将用户的原始提问"
        "优化为更清晰、更结构化、更具体的格式，以便 AI 能更好地理解并执行。"
        "不要改变用户的意图和核心需求，只优化表达方式。"
        "直接输出优化后的结果，不要添加任何额外解释或前缀。"
    )

    # 有上下文时：包含完整对话历史
    if context_str:
        user_msg = f"""请基于以下完整的对话上下文来优化用户当前输入。

【对话上下文】
{context_str}

【用户当前输入】
{original}

【优化要求】
- 基于完整的对话上下文，理解用户的真实意图和引用关系
- 如果用户当前输入引用了之前的对话内容，请在优化结果中明确体现
- 补充上下文中对理解当前输入有帮助的关键信息
- 保持用户原始意图和核心需求不变
- 拆解为清晰的步骤或要点（如果有多个要求）
- 使用结构化格式（分段、列表、编号等）
- 语言简洁明确，去掉冗余表达
- 直接输出优化后的结果，不要加任何前缀或解释说明"""
    else:
        user_msg = f"""请将以下用户提问优化为更清晰、更结构化的格式。

【原始提问】
{original}

【优化要求】
- 保持原始意图和核心需求不变
- 拆解为清晰的步骤或要点（如果有多个要求）
- 补充必要的上下文细节（如果原始内容有隐含信息）
- 使用结构化格式（分段、列表、编号等）
- 语言简洁明确，去掉冗余表达
- 如果是复杂任务，按逻辑顺序排列步骤
- 直接输出优化后的结果，不要加任何前缀或解释说明"""

    try:
        res = client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg}
            ],
            max_tokens=8000,
            temperature=0.3
        )
        optimized = res.choices[0].message.content.strip()

        if not optimized or len(optimized) < 5:
            return original

        return optimized

    except Exception as e:
        print(f"\n⚠️ Prompt 优化器调用失败（{e}），将使用原始输入。")
        return original


def format_optimized_prompt(original: str, optimized: str) -> str:
    """将原始 prompt 和优化后的 prompt 合并为一条格式化消息

    如果优化后的内容与原始内容相同，则直接返回原始内容。

    Args:
        original: 用户原始输入的 prompt
        optimized: 优化后的 prompt

    Returns:
        合并后的格式化消息字符串
    """
    if optimized == original or not optimized:
        return original

    return (
        f"🧑 **原始提问**\n"
        f"{original}\n\n"
        f"📝 **优化后的提问**\n"
        f"{optimized}\n\n"
        f"---\n"
        f"💡 请优先基于【优化后的提问】来执行任务。"
    )
