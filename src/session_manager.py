# ============================================================
# 会话管理器
# ============================================================
# 提供会话的保存与恢复、标题管理、自动保存、列表浏览等功能。
# - 将会话序列化为 JSON 文件进行持久化存储
# - 首次提问自动生成会话标题
# - 每轮对话后自动保存为独立文件
# - 支持会话列表浏览和删除
# ============================================================

import os
import json
import re
import datetime
import threading
import uuid
from typing import List, Dict, Any, Optional, Tuple


def _estimate_msgs_tokens(msgs: list) -> int:
    """内联 Token 估算函数（避免相对导入问题）"""
    total = 0
    for msg in msgs:
        txt = msg.get("content", "") or ""
        cjk = sum(1 for c in txt if '\u4e00' <= c <= '\u9fff')
        other = len(txt) - cjk
        total += max(int(cjk / 1.5 + other / 4), 0) + 4
    return total


def ensure_session_dir(save_dir: str = None) -> str:
    """确保会话保存目录存在，返回目录路径"""
    from .config import SESSION_SAVE_DIR
    session_dir = save_dir or SESSION_SAVE_DIR
    os.makedirs(session_dir, exist_ok=True)
    return session_dir


def save_session(session, path: str = None, save_dir: str = None) -> str:
    """序列化 AgentSession 为 JSON 文件
    
    保存内容：msgs、mode、composer 统计、token 信息、会话标题
    """
    from .config import SESSION_SAVE_DIR
    
    session_dir = ensure_session_dir(save_dir or SESSION_SAVE_DIR)
    
    # ---- Token 兜底计算：确保 current_tokens 有值 ----
    _tokens = session.current_tokens
    if _tokens == 0 and session.msgs:
        try:
            _tokens = _estimate_msgs_tokens(session.msgs)
        except Exception:
            pass
    
    _stats = getattr(session, "last_token_stats", "")
    if not _stats and _tokens > 0:
        _stats = f"输入: {_tokens:,}"
    
    data = {
        "version": "1.0.0",
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "session_title": getattr(session, "session_title", ""),
        "mode": session.get_mode(),
        "mode_name": session.get_mode_name(),
        "msgs": getattr(session, '_display_msgs', session.msgs),
        "current_tokens": _tokens,
        "completion_tokens": getattr(session, "completion_tokens", 0),
        "session_completion_tokens": getattr(session, "session_completion_tokens", 0),  # 累计输出 Token
        "total_tokens": getattr(session, "total_tokens", 0) or _tokens,
        "last_token_stats": _stats,
        # Composer 统计
        "micro_composer_count": getattr(session, "micro_composer_count", 0),
        "auto_composer_count": getattr(session, "auto_composer_count", 0),
        "manual_composer_count": getattr(session, "manual_composer_count", 0),
        "composer_notification": getattr(session, "composer_notification", ""),
        # Python 环境
        "python_env": getattr(session, "python_env", ""),
        # 用户原始输入记录
        "original_user_inputs": getattr(session, "original_user_inputs", {}),
        "optimized_prompts": getattr(session, "optimized_prompts", {}),
        "message_count": len(getattr(session, '_display_msgs', session.msgs)),
        # 分支会话元数据（from branch feature）
        "parent_session_id": getattr(session, "parent_session_id", ""),
        "trigger_message_index": getattr(session, "trigger_message_index", -1),
        "trigger_message_preview": getattr(session, "trigger_message_preview", ""),
    }
    
    # 确定保存路径
    if path:
        save_path = path
    elif getattr(session, '_session_save_path', None):
        # 如果 session 已关联文件路径，覆写原文件
        save_path = session._session_save_path
    else:
        title = data["session_title"] or "untitled"
        safe_title = "".join(c for c in title if c.isalnum() or c in " _-").strip()
        if not safe_title:
            safe_title = "untitled"
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_title}_{timestamp}.json"
        save_path = os.path.join(session_dir, filename)
    
    # 写入文件
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return save_path


def load_session(path: str) -> Dict[str, Any]:
    """从 JSON 文件加载会话数据，返回原始数据字典"""
    if not os.path.exists(path):
        raise FileNotFoundError(f"会话文件不存在: {path}")
    
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    return data


def restore_session(session, path: str) -> str:
    """从 JSON 文件恢复会话到 AgentSession 对象"""
    data = load_session(path)
    
    # 恢复核心数据
    session.msgs = data.get("msgs", [session.msgs])
    # 恢复展示层上下文（与 msgs 同步，展示层永不压缩）
    session._display_msgs = [dict(m) for m in session.msgs]
    
    # Token 恢复：如果保存的为 0，重新估算
    _loaded_tokens = data.get("current_tokens", 0)
    if _loaded_tokens == 0 and session.msgs:
        try:
            _loaded_tokens = _estimate_msgs_tokens(session.msgs)
        except Exception:
            pass
    session.current_tokens = _loaded_tokens
    session.completion_tokens = data.get("completion_tokens", 0)
    session.session_completion_tokens = data.get("session_completion_tokens", 0)  # 恢复累计输出 Token
    session.total_tokens = data.get("total_tokens", _loaded_tokens)
    session.last_token_stats = data.get("last_token_stats", "")
    if not session.last_token_stats and session.current_tokens > 0:
        session.last_token_stats = f"输入: {session.current_tokens:,}"
    
    session.session_title = data.get("session_title", "")
    
    # 恢复分支会话元数据
    session.parent_session_id = data.get("parent_session_id", "")
    session.trigger_message_index = data.get("trigger_message_index", -1)
    session.trigger_message_preview = data.get("trigger_message_preview", "")
    session._title_set = bool(session.session_title)  # 有标题就标记已设定，避免加载后重新生成
    
    # 恢复 Composer 统计
    session.micro_composer_count = data.get("micro_composer_count", 0)
    session.auto_composer_count = data.get("auto_composer_count", 0)
    session.manual_composer_count = data.get("manual_composer_count", 0)
    session.last_composer_action = data.get("last_composer_action", "")
    session.composer_notification = data.get("composer_notification", "")
    
    # 恢复 Python 环境
    python_env = data.get("python_env", "")
    if python_env:
        session.python_env = python_env
    
    # 恢复用户原始输入记录和优化 Prompt 记录
    session.original_user_inputs = data.get("original_user_inputs", {})
    session.optimized_prompts = data.get("optimized_prompts", {})
    # 转换 key 为 int（JSON 序列化时 int key 会变成字符串）
    if session.original_user_inputs:
        session.original_user_inputs = {int(k): v for k, v in session.original_user_inputs.items()}
    if session.optimized_prompts:
        session.optimized_prompts = {int(k): v for k, v in session.optimized_prompts.items()}
    
    # 重新构建 system prompt（基于当前模式）
    from .prompts import build_system_prompt
    session.system_prompt = build_system_prompt(session.get_mode())
    
    # 确保 system prompt 正确
    if session.msgs and session.msgs[0]["role"] == "system":
        session.msgs[0]["content"] = session.system_prompt
    else:
        session.msgs.insert(0, {"role": "system", "content": session.system_prompt})
    
    title_info = f"「{session.session_title}」" if session.session_title else "（无标题）"
    return f"会话已恢复: {title_info} ({len(session.msgs)} 条消息)"


def list_sessions(save_dir: str = None) -> List[Dict[str, Any]]:
    """列出所有已保存的会话，返回包含标题、时间、消息数的列表"""
    from .config import SESSION_SAVE_DIR
    
    session_dir = ensure_session_dir(save_dir or SESSION_SAVE_DIR)
    sessions = []
    
    if not os.path.exists(session_dir):
        return sessions
    
    for filename in sorted(os.listdir(session_dir), reverse=True):
        if not filename.endswith(".json"):
            continue
        
        filepath = os.path.join(session_dir, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            sessions.append({
                "filename": filename,
                "path": filepath,
                "title": data.get("session_title", "（无标题）"),
                "timestamp": data.get("timestamp", "未知"),
                "mode": data.get("mode_name", "未知"),
                "messages": data.get("message_count", 0),
                "version": data.get("version", "未知"),
                "parent_session_id": data.get("parent_session_id", ""),
                "trigger_message_index": data.get("trigger_message_index", -1),
                "trigger_message_preview": data.get("trigger_message_preview", ""),
            })
        except (json.JSONDecodeError, IOError):
            continue
    
    return sessions


def delete_session(path: str) -> str:
    """删除指定会话文件"""
    if not os.path.exists(path):
        return f"会话文件不存在: {path}"
    
    os.remove(path)
    return f"已删除会话: {os.path.basename(path)}"


def auto_save(session, session_save_path: str = None, save_dir: str = None) -> str:
    """自动保存会话为独立的会话文件

    每个会话有自己的文件（以标题+时间戳命名），而非覆盖同一个 auto_save.json。
    首次保存时生成新文件并返回路径，后续调用可传入该路径以覆盖更新。

    Args:
        session: AgentSession 实例
        session_save_path: 之前自动保存的文件路径（后续保存时传入以覆盖）
        save_dir: 保存目录（可选，默认使用配置的 SESSION_SAVE_DIR）

    Returns:
        保存的文件路径，失败返回空字符串
    """
    from .config import SESSION_SAVE_DIR
    
    session_dir = ensure_session_dir(save_dir or SESSION_SAVE_DIR)
    
    # [DEBUG] 追踪 auto_save
    sid = getattr(session, 'session_id', 'unknown')[:12]
    print(f"[DEBUG_AUTO] auto_save called: session={sid} session_save_path={session_save_path}", flush=True)
    
    # 已有保存路径：直接覆盖更新
    if session_save_path:
        try:
            save_session(session, path=session_save_path)
            print(f"[DEBUG_AUTO] SAVED TO EXISTING PATH: {session_save_path}", flush=True)
            return session_save_path
        except Exception as e:
            print(f"[DEBUG_AUTO] FAILED write to {session_save_path}: {e}", flush=True)
            return ""
    
    # 首次保存：用标题+时间戳生成文件名
    print(f"[DEBUG_AUTO] NO PATH - generating new filename", flush=True)
    
    # 首次保存：用标题+时间戳生成文件名
    title = getattr(session, "session_title", "") or "新会话"
    # 只保留安全的文件名字符（中英文、数字、空格、短横、下划线）
    safe_title = re.sub(r'[\\/:*?"<>|\n\r\t]', '', title).strip()
    if not safe_title:
        safe_title = "新会话"
    safe_title = safe_title[:60]  # 限制长度
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{safe_title}_{timestamp}.json"
    auto_save_path = os.path.join(session_dir, filename)
    
    try:
        save_session(session, path=auto_save_path)
        return auto_save_path
    except Exception as e:
        return ""


def get_session_display_list(save_dir: str = None) -> str:
    """获取格式化的会话列表文字（用于命令行显示）"""
    sessions = list_sessions(save_dir)
    
    if not sessions:
        return "暂无保存的会话"
    
    lines = ["已保存的会话：\n"]
    for i, s in enumerate(sessions, 1):
        title = s["title"] if len(s["title"]) <= 40 else s["title"][:37] + "..."
        lines.append(
            f"{i}. {title}\n"
            f"   {s['timestamp']} | {s['messages']} 条消息 | "
            f"{s['filename']}"
        )
    
    return "\n".join(lines)


# ============================================================
# 会话注册表（支持多会话并发管理）
# ============================================================

class SessionRegistry:
    """多会话注册表，管理多个 AgentSession 实例及其独立的锁"""

    def __init__(self):
        self._sessions: Dict[str, Any] = {}
        self._locks: Dict[str, threading.Lock] = {}
        self._active_id: Optional[str] = None

    def create(self, session_id: Optional[str] = None) -> Any:
        """创建新会话，返回 session_id"""
        from .main import AgentSession
        sid = session_id or str(uuid.uuid4())
        session = AgentSession(session_id=sid)
        self._sessions[sid] = session
        self._locks[sid] = threading.Lock()
        return sid

    def get(self, session_id: str) -> Any:
        """获取指定 session 实例"""
        return self._sessions.get(session_id)

    def get_lock(self, session_id: str) -> Optional[threading.Lock]:
        """获取指定 session 的锁"""
        return self._locks.get(session_id)

    def get_or_create(self, session_id: Optional[str] = None) -> Tuple[str, Any, threading.Lock]:
        """获取或创建会话，返回 (session_id, session, lock)"""
        sid = session_id or str(uuid.uuid4())
        if sid not in self._sessions:
            from .main import AgentSession
            self._sessions[sid] = AgentSession(session_id=sid)
            self._locks[sid] = threading.Lock()
        return sid, self._sessions[sid], self._locks[sid]

    def remove(self, session_id: str) -> bool:
        """删除会话（从注册表移除，不删除文件）"""
        self._sessions.pop(session_id, None)
        self._locks.pop(session_id, None)
        if self._active_id == session_id:
            self._active_id = None
        return True

    def set_active(self, session_id: str):
        """设置当前活动会话 ID"""
        self._active_id = session_id

    def get_active(self) -> Optional[str]:
        """获取当前活动会话 ID"""
        return self._active_id
    def all_sessions(self) -> Dict[str, Any]:
        """获取所有会话"""
        return dict(self._sessions)




