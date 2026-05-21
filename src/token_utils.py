# ============================================================
# Token 统计与展示
# ============================================================
# 提供 Token 使用量的统计显示功能。
# Token 数据直接从 API 返回的 usage 字段获取。
# ============================================================

from .config import MAX_CTX_TOKENS

def get_token_stats_text(usage=None, prompt_tokens: int = None, completion_tokens: int = None, label="本次"):
    """获取 Token 统计文本（用于 Gradio 界面展示）
    
    Args:
        usage: API 返回的 usage 对象（可选）
        prompt_tokens: 直接传入 prompt token 数（usage 为 None 时使用）
        completion_tokens: 直接传入 completion token 数（usage 为 None 时使用）
    
    Returns:
        格式化的 Token 统计字符串，如 "📊 输入: 1,234 | 输出: 567 | 合计: 1,801 | ..."
    """
    if usage is not None:
        prompt_tk = usage.prompt_tokens or 0
        completion_tk = usage.completion_tokens or 0
        total_tk = usage.total_tokens or 0
    elif prompt_tokens is not None:
        prompt_tk = prompt_tokens
        completion_tk = completion_tokens or 0
        total_tk = prompt_tk + completion_tk
    else:
        return ""
    
    remaining = max(MAX_CTX_TOKENS - prompt_tk, 0)
    pct = (prompt_tk / MAX_CTX_TOKENS) * 100
    return (
        f"📊 输入: {prompt_tk:,} | 输出: {completion_tk:,} | "
        f"合计: {total_tk:,} | 剩余: {remaining:,} | 占用: {pct:.1f}%"
    )
