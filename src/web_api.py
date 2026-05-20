# ============================================================
# TennineClaw - FastAPI Web API 层
# ============================================================
# 提供完整的 RESTful API，支持：
# - 流式/非流式聊天
# - 多会话管理与切换
# - 状态缓存（防止流式期间阻塞）
# - 模式切换、环境配置、Plan 菜单操作
# - 模型管理与自定义模型
# ============================================================

import os
import sys
import json
import threading
import asyncio
import time
import uuid
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional

# 确保项目路径在 sys.path 中
project_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(project_dir)
for p in [project_dir, parent_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

from .main import AgentSession, MODE_SMART, MODE_PLAN
from .config import (
    GRADIO_TITLE, GRADIO_DESCRIPTION, GRADIO_PORT, GRADIO_SHARE,
    MAX_CTX_TOKENS, COMPOSER_ENABLED, SESSION_SAVE_DIR,
    PYTHON_ENV_MANUAL_OVERRIDE,
    _save_user_config, _invalidate_config_cache,
)
from . import __version__

from .session_manager import SessionRegistry

# ============================================================
# 多会话注册表
# 每个会话有独立的 AgentSession 实例和锁，支持真正并发
# ============================================================

_session_registry = SessionRegistry()
_default_session_id = _session_registry.create("default")
_session_registry.set_active(_default_session_id)

# 保留 _session / _session_lock 引用默认会话
_session = _session_registry.get("default")
_session_lock = _session_registry.get_lock("default")

def _get_session(session_id: str = None):
    """获取指定 session，默认为 active"""
    sid = session_id or _session_registry.get_active() or _default_session_id
    _, session, _ = _session_registry.get_or_create(sid)
    return session, sid

def _get_session_lock(session_id: str = None):
    """获取指定 session 的锁"""
    sid = session_id or _session_registry.get_active() or _default_session_id
    _session_registry.get_or_create(sid)  # ensure exists
    return _session_registry.get_lock(sid)


def _get_session_and_lock(session_id: str = None):
    """获取 session 对象和锁"""
    sid = session_id or _session_registry.get_active() or _default_session_id
    _, session, _ = _session_registry.get_or_create(sid)
    lock = _session_registry.get_lock(sid)
    return session, lock


_plan_selected = None  # Plan 菜单选择状态


# ============================================================
# 状态缓存系统
# 作用：当流式请求持有锁时，状态查询可读取缓存，不被阻塞
# ============================================================

_status_cache = {}
_status_cache_lock = threading.Lock()
_status_cache_time = 0.0

def _build_status_snapshot(session_id: str = None):
    """直接从 session 读取当前状态（由 GIL 保证原子性）"""
    session, sid = _get_session(session_id)
    try:
        mode_name = session.get_mode_name()
        msg_count = len(getattr(session, '_display_msgs', session.msgs))
        tokens = session.current_tokens
        completion_tk = getattr(session, "completion_tokens", 0)
        total_tk = getattr(session, "total_tokens", 0) or (tokens + completion_tk)
        usage_pct = (total_tk / MAX_CTX_TOKENS) * 100 if MAX_CTX_TOKENS > 0 else 0
        notification = getattr(session, 'composer_notification', "")
        composer_info = session.get_composer_status() if hasattr(session, 'get_composer_status') else ""
        session_title = session.get_title_display() if hasattr(session, 'get_title_display') else ""


        # 检查是否正在流式处理
        is_streaming = getattr(session, 'is_streaming', False)

        # 获取 plan_ready 状态（用于 /api/plan/check 缓存）
        plan_ready = False
        try:
            plan_ready = session.mode_mgr.is_plan_ready()
        except Exception:
            plan_ready = False

        return {
            "mode_name": mode_name,
            "msg_count": msg_count,
            "total_tk": total_tk,
            "usage_pct": round(usage_pct, 1),
            "notification": notification,
            "composer_info": composer_info,
            "micro_count": getattr(session, 'micro_composer_count', 0),
            "auto_count": getattr(session, 'auto_composer_count', 0),
            "manual_count": getattr(session, 'manual_composer_count', 0),
            "session_title": session_title,
            "version": __version__,
            "is_streaming": is_streaming,
            "plan_ready": plan_ready,
            "session_id": sid,
        }
    except Exception:
        return None

def _update_status_cache():
    """更新状态缓存（线程安全，无需 _session_lock）"""
    snapshot = _build_status_snapshot()
    if snapshot:
        with _status_cache_lock:
            _status_cache.clear()
            _status_cache.update(snapshot)
            global _status_cache_time
            _status_cache_time = time.time()

# Register status update callback (after function definition)
default_session = _session_registry.get("default")
if default_session:
    default_session.set_status_update_callback(_update_status_cache)

def _get_cached_status():
    """获取缓存的状态快照（线程安全）"""
    with _status_cache_lock:
        return dict(_status_cache) if _status_cache else {}

def _get_status_with_cache(timeout=0.3, session_id: str = None):
    """尝试获取锁读取最新状态，超时则返回缓存

    Args:
        timeout: 等待锁的超时时间（秒）
        session_id: 目标会话 ID，None 表示活跃会话
    Returns:
        (data_dict, from_cache) 元组
    """
    lock = _get_session_lock(session_id)
    acquired = lock.acquire(timeout=timeout)
    if acquired:
        try:
            # 成功获取锁，读取最新数据，并更新缓存
            data = _build_status_snapshot(session_id)
            if data:
                with _status_cache_lock:
                    _status_cache.clear()
                    _status_cache.update(data)
                    global _status_cache_time
                    _status_cache_time = time.time()
            return data, False
        finally:
            lock.release()
    else:
        # 锁被占用（流式请求正在处理），返回缓存
        return _get_cached_status(), True


def _try_lock_action(action_func, timeout=0.5, fallback=None):
    """尝试获取锁后执行操作，超时则返回 fallback

    用于所有需要 _session_lock 但不想被阻塞的路由。

    Args:
        action_func: 无参可调用对象，在持有锁时执行
        timeout: 等待锁的超时时间（秒）
        fallback: 超时后的返回值
    Returns:
        action_func 的返回值，或 fallback
    """
    acquired = _session_lock.acquire(timeout=timeout)
    if acquired:
        try:
            return action_func()
        finally:
            _session_lock.release()
    else:
        return fallback


# ============================================================
# FastAPI 应用初始化
# ============================================================

app = FastAPI(
    title=f"TennineClaw v{__version__}",
    description="智能终端助手 Web API",
    version=__version__,
)

# 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件
static_dir = os.path.join(parent_dir, "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


# ============================================================
# Pydantic 请求/响应模型
# ============================================================

class ChatRequest(BaseModel):
    message: str
    session_id: str = ""

class ChatResponse(BaseModel):
    response: str
    status: str
    mode: str

class SessionCreateResponse(BaseModel):
    session_id: str
    status: str

class SessionListResponse(BaseModel):
    sessions: list
    active_id: str

class ModeResponse(BaseModel):
    message: str
    mode: str

class StatusResponse(BaseModel):
    mode: str
    message_count: int
    total_tokens: int
    usage_percent: float
    session_title: str
    composer_info: str
    notification: str
    version: str

class SaveRequest(BaseModel):
    title: Optional[str] = ""

class LoadRequest(BaseModel):
    path: str

class DeleteRequest(BaseModel):
    path: str

class EnvRequest(BaseModel):
    path: str

class PlanActionRequest(BaseModel):
    action: str  # "explore", "modify", "execute", "confirm", "reset"


# ============================================================
# 安全获取会话数据的辅助函数（无锁，用于已持有锁的上下文）
# ============================================================

def _safe_get_status_data(session=None):
    """安全获取状态数据"""
    s = session or _session
    mode_name = s.get_mode_name()
    msg_count = len(getattr(s, '_display_msgs', s.msgs))
    tokens = s.current_tokens
    completion_tk = getattr(s, "completion_tokens", 0)
    total_tk = getattr(s, "total_tokens", 0) or (tokens + completion_tk)
    usage_pct = (total_tk / MAX_CTX_TOKENS) * 100 if MAX_CTX_TOKENS > 0 else 0
    notification = getattr(s, 'composer_notification', "")

    composer_info = s.get_composer_status() if hasattr(s, 'get_composer_status') else ""
    session_title = s.get_title_display() if hasattr(s, 'get_title_display') else ""

    return {
        "mode": mode_name,
        "message_count": msg_count,
        "total_tokens": total_tk,
        "usage_percent": round(usage_pct, 1),
        "session_title": session_title,
        "composer_info": composer_info,
        "notification": notification,
        "version": __version__,
    }


# ============================================================
# API 路由
# ============================================================

@app.get("/", response_class=HTMLResponse)
async def index():
    """返回主页面"""
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return HTMLResponse("<h1>TennineClaw Web UI</h1><p>静态文件未找到</p>")


@app.post("/api/chat")
async def chat(req: ChatRequest):
    """发送聊天消息，返回 AI 回复（非流式）"""
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")

    try:
        session, lock = _get_session_and_lock(req.session_id)
        with lock:
            result = session.process_message(req.message.strip())
            session._auto_save_if_needed()

        with lock:
            mode = session.get_mode_name()

        _update_status_cache()

        return ChatResponse(
            response=result,
            status="success",
            mode=mode,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理消息失败: {str(e)}")


# ============================================================
# 流式输出：SSE 逐段落推送 + 会话 Token 统计 + 流式标记
# ============================================================

@app.post("/api/chat/stream")
async def chat_stream(req: ChatRequest):
    """
    流式聊天，返回 SSE 格式的流式回复

    改进：
    - 支持多会话，接受 session_id 参数
    - 使用 per-session 锁，不同会话可并发流式
    - 支持打断（session._stream_interrupted）

    SSE 事件类型：
      - type: chunk      → AI 文本回复片段（段落）
      - type: tool_call  → 工具调用通知（🔧）
      - type: done       → 流式传输完成（含 Token 统计）
      - type: error      → 错误信息
      - type: interrupted → 用户打断
    """
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")

    # 获取或创建会话
    sid = req.session_id or _session_registry.get_active() or _default_session_id
    _, session, session_lock = _session_registry.get_or_create(sid)

    async def generate():
        """异步生成器：在线程池中运行同步生成器，逐块推送 SSE 事件"""
        loop = asyncio.get_event_loop()

        # 用于标记生成器结束（避免与正常返回的 None 混淆）
        _SENTINEL = object()

        # 段落间隔配置（秒）
        PARAGRAPH_DELAY_MS = 0.3

        try:
            # 重置打断标志和部分内容
            session._stream_interrupted = False
            session._partial_stream_content = ""

            # 流式开始前标记流式状态
            session.is_streaming = True
            _update_status_cache()

            # 使用 per-session 锁迭代 process_message_stream
            def get_chunks():
                with session_lock:
                    for chunk in session.process_message_stream(req.message.strip()):
                        yield chunk

            gen = get_chunks()

            # 逐块从同步生成器中获取
            was_interrupted = False
            chunk_count = 0
            while True:
                chunk = await loop.run_in_executor(
                    None, lambda: next(gen, _SENTINEL)
                )
                if chunk is _SENTINEL:
                    break

                chunk_count += 1

                # 根据 chunk 内容判断类型，推送 SSE 事件
                if chunk.startswith('__OPT__'):
                    opt_content = chunk[7:]  # 去掉 __OPT__ 前缀
                    yield f"data: {json.dumps({'type': 'optimized_prompt', 'content': opt_content})}\n\n"
                elif chunk == "\n\n⏹️ **已中断**":
                    was_interrupted = True
                    yield f"data: {json.dumps({'type': 'interrupted', 'content': chunk})}\n\n"
                elif chunk.startswith('🔧'):
                    yield f"data: {json.dumps({'type': 'tool_call', 'content': chunk})}\n\n"
                else:
                    session._partial_stream_content += chunk
                    yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"

                if chunk_count >= 1:
                    await asyncio.sleep(PARAGRAPH_DELAY_MS)

            # 完成后获取状态
            with session_lock:
                mode = session.get_mode_name()
                input_tokens = session.current_tokens
                output_tokens = getattr(session, 'session_completion_tokens', 0)

            # 清除流式标记
            session.is_streaming = False
            _update_status_cache()

            # done / interrupted 事件
            if was_interrupted:
                done_data = json.dumps({
                    'type': 'interrupted_done',
                    'mode': mode,
                    'total_tokens': input_tokens + output_tokens,
                    'max_tokens': MAX_CTX_TOKENS,
                    'session_id': sid,
                })
                yield f"data: {done_data}\n\n"
            else:
                done_data = json.dumps({
                    'type': 'done',
                    'mode': mode,
                    'total_tokens': input_tokens + output_tokens,
                    'max_tokens': MAX_CTX_TOKENS,
                    'session_id': sid,
                })
                yield f"data: {done_data}\n\n"

        except Exception as e:
            session.is_streaming = False
            _update_status_cache()
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
        finally:
            # 确保流式标记在任何情况下都被清除（包括客户端断开连接）
            session.is_streaming = False
            _update_status_cache()

    return StreamingResponse(generate(), media_type="text/event-stream")


# ============================================================
# 会话管理：创建、列表、切换、打断、删除
# ============================================================

@app.post("/api/session/new")
async def create_session():
    """创建新会话"""
    sid = _session_registry.create()
    _session_registry.set_active(sid)
    session = _session_registry.get(sid)
    session.set_status_update_callback(_update_status_cache)
    # 立即自动保存新会话到磁盘，防止服务器重启后丢失
    from .session_manager import auto_save
    save_path = auto_save(session)
    if save_path:
        session._session_save_path = save_path
    return {"session_id": sid, "status": "success"}


@app.get("/api/sessions/list")
async def list_all_sessions():
    """列出已保存会话文件列表"""
    from .session_manager import list_sessions
    saved_files = list_sessions()

    # 收集活跃会话
    active_sessions = []
    for sid, session in _session_registry.all_sessions().items():
        if not getattr(session, '_display_msgs', None) or getattr(session, 'msgs', None) and sid == 'default':
            continue  # 空的默认会话不显示
        active_sessions.append({
            "session_id": sid,
            "title": getattr(session, 'session_title', '') or sid[:8],
            "msg_count": len(getattr(session, '_display_msgs', None) or getattr(session, 'msgs', [])),
            "is_streaming": getattr(session, 'is_streaming', False),
        })

    return {
        "active_sessions": active_sessions,
        "saved_files": saved_files,  # 不过滤，全部显示
    }
    sessions = []
    for sid, session in _session_registry.all_sessions().items():
        sessions.append({
            "session_id": sid,
            "title": getattr(session, 'session_title', '') or sid[:8],
            "msg_count": len(getattr(session, '_display_msgs', session.msgs)),
        })
    return {"sessions": sessions}


@app.get("/api/session/active")
async def get_active_session():
    """获取当前活动会话信息"""
    sid = _session_registry.get_active() or _default_session_id
    session = _session_registry.get(sid)
    return {
        "session_id": sid,
        "title": getattr(session, 'session_title', '') if session else '',
        "mode": session.get_mode_name() if session else 'smart',
        "msg_count": len(getattr(session, '_display_msgs', session.msgs)) if session else 0,
    }


@app.post("/api/session/{session_id}/activate")
async def activate_session(session_id: str):
    """激活指定会话"""
    session = _session_registry.get(session_id)
    if not session:
        # 尝试从注册表创建（可能文件已在侧栏，首次加载）
        _, session, _ = _session_registry.get_or_create(session_id)
    _session_registry.set_active(session_id)
    session.set_status_update_callback(_update_status_cache)
    return {"session_id": session_id, "status": "success"}


@app.post("/api/chat/{session_id}/interrupt")
async def interrupt_chat(session_id: str):
    """打断指定会话的流式回复"""
    session = _session_registry.get(session_id)
    if session:
        session._stream_interrupted = True
        return {"status": "interrupted", "session_id": session_id}
    raise HTTPException(status_code=404, detail=f"会话 {session_id} 不存在")


@app.delete("/api/session/{session_id}")
async def delete_session(session_id: str):
    """从注册表删除会话"""
    if session_id == "default":
        raise HTTPException(status_code=400, detail="不能删除默认会话")
    _session_registry.remove(session_id)
    return {"status": "deleted"}


@app.post("/api/mode/smart", response_model=ModeResponse)
async def switch_to_smart():
    """切换到 Smart 模式"""
    session, lock = _get_session_and_lock()
    with lock:
        result = session.switch_mode(MODE_SMART)
        mode = session.get_mode_name()
    _update_status_cache()
    return ModeResponse(message=result, mode=mode)


@app.post("/api/mode/plan", response_model=ModeResponse)
async def switch_to_plan():
    """切换到 Plan 模式"""
    session, lock = _get_session_and_lock()
    with lock:
        result = session.switch_mode(MODE_PLAN)
        mode = session.get_mode_name()
    _update_status_cache()
    return ModeResponse(message=result, mode=mode)


@app.post("/api/context/compact")
async def compact_context():
    """手动压缩上下文（/compact）

    使用 loop.run_in_executor 避免阻塞 asyncio 事件循环，
    因为 session.compact_context() 内部会调用同步的 LLM API 请求，
    可能耗时 15~60 秒。
    """
    session, lock = _get_session_and_lock()
    loop = asyncio.get_event_loop()

    def _do_compact():
        """在线程池中执行阻塞操作"""
        acquired = lock.acquire(timeout=30.0)
        if acquired:
            try:
                stats = session.compact_context()
                return stats
            finally:
                lock.release()
        else:
            return "⏳ 当前有流式请求正在处理（等待超时 30 秒），请稍后再试。"

    try:
        result = await asyncio.wait_for(
            loop.run_in_executor(None, _do_compact),
            timeout=180.0  # 3 分钟超时
        )
    except asyncio.TimeoutError:
        result = "⏰ 压缩请求超时（超过 180 秒），请重试。"

    _update_status_cache()
    return {"message": result, "status": "success"}


@app.get("/api/context/help")
async def get_help():
    """获取帮助文本"""
    help_text = ""
    session, lock = _get_session_and_lock()
    acquired = lock.acquire(timeout=0.5)
    if acquired:
        try:
            help_text = session._get_help_text() if hasattr(session, '_get_help_text') else ""
        finally:
            lock.release()
    else:
        help_text = "⏳ 当前有请求正在处理，请稍后再试。"
    return {"message": help_text}


@app.get("/api/context/status")
async def get_context_status():
    """获取 Composer 状态文本"""
    result = ""
    session, lock = _get_session_and_lock()
    acquired = lock.acquire(timeout=0.5)
    if acquired:
        try:
            result = session.get_composer_status() if hasattr(session, 'get_composer_status') else ""
        finally:
            lock.release()
    else:
        result = "⏳ 当前有请求正在处理，请稍后再试。"
    return {"message": result}


@app.get("/api/status", response_model=StatusResponse)
async def get_full_status():
    """获取完整状态信息（支持缓存兜底）"""
    data, from_cache = _get_status_with_cache(timeout=0.5)
    if not data:
        try:
            session, lock = _get_session_and_lock()
            with lock:
                data = _build_status_snapshot()
        except Exception:
            data = {"mode": "unknown", "message_count": 0, "total_tokens": 0, "usage_percent": 0,
                    "session_title": "", "composer_info": "", "notification": "", "version": __version__}

    return StatusResponse(
        mode=data.get("mode_name", "unknown"),
        message_count=data.get("msg_count", 0),
        total_tokens=data.get("total_tk", 0),
        usage_percent=data.get("usage_pct", 0.0),
        session_title=data.get("session_title", ""),
        composer_info=data.get("composer_info", ""),
        notification=data.get("notification", ""),
        version=data.get("version", __version__),
    )


@app.get("/api/status/realtime")
async def get_realtime_status():
    """获取实时状态（简洁版，用于自动刷新）"""
    data, from_cache = _get_status_with_cache(timeout=0.3)

    if not data:
        return {
            "status_text": "**模式**: 未知 | **消息**: 0 条",
            "mode": "unknown",
            "message_count": 0,
            "total_tokens": 0,
            "usage_percent": 0,
            "notification": "",
            "is_streaming": False,
        }

    mode_name = data.get("mode_name", "未知")
    msg_count = data.get("msg_count", 0)
    tokens = data.get("tokens", 0)
    completion_tk = data.get("completion_tk", 0)
    total_tk = data.get("total_tk", 0)
    usage_pct = data.get("usage_pct", 0)
    notification = data.get("notification", "")
    is_streaming = data.get("is_streaming", False)

    if total_tk > 0:
        status = (
            f"**模式**: {mode_name} | "
            f"**消息**: {msg_count} 条 | "
            f"📊合计: {total_tk:,} ({usage_pct:.1f}%)"
        )
    else:
        from .config import MAX_CTX_TOKENS as max_ctx
        status = (
            f"**模式**: {mode_name} | "
            f"**消息**: {msg_count} 条"
        )

    if notification:
        status += f"\n\n🔔 **{notification}**"

    if is_streaming or from_cache:
        status += "\n\n⏳ *AI 响应中...*"

    return {
        "status_text": status,
        "mode": mode_name,
        "message_count": msg_count,
        "total_tokens": total_tk,
        "usage_percent": usage_pct,
        "notification": notification,
        "is_streaming": is_streaming,
        "micro_count": data.get("micro_count", 0),
        "auto_count": data.get("auto_count", 0),
        "manual_count": data.get("manual_count", 0),
    }


@app.get("/api/session/title")
async def get_session_title():
    """获取会话标题（支持缓存兜底）"""
    data, from_cache = _get_status_with_cache(timeout=0.3)
    title = data.get("session_title", "") if data else ""
    return {"title": title}


@app.post("/api/session/save")
async def save_session_api(req: SaveRequest):
    """保存当前会话"""
    session, lock = _get_session_and_lock()
    with lock:
        if req.title and req.title.strip():
            session.set_title(req.title.strip())
        result = session.save()
    _update_status_cache()
    return {"message": result}


# ============================================================
# 会话消息 API
# ============================================================

@app.get("/api/chat/messages")
async def get_session_messages(session_id: str = ""):
    """获取指定会话的消息列表（用于加载会话后渲染）"""
    session, sid = _get_session(session_id or "")
    lock = _get_session_lock(sid)

    # 不阻塞等锁（后台流可能正持有），timeout 0.5s 后无锁读取
    acquired = lock.acquire(timeout=0.5)
    try:
        msgs = getattr(session, '_display_msgs', None) or getattr(session, 'msgs', [])
        original_inputs = getattr(session, 'original_user_inputs', {})
        optimized_map = getattr(session, 'optimized_prompts', {})
        display_msgs = []
        for idx, m in enumerate(msgs):
            role = m.get("role", "")
            if role == "system":
                continue
            if role == "assistant":
                content = m.get("content", "")
                if not content and "tool_calls" in m:
                    content = "[工具调用]"
                display_msgs.append({"role": "assistant", "content": content})
            elif role == "user":
                content = m.get("content", "")
                optimized_text = None
                if idx in original_inputs:
                    content = original_inputs[idx]
                    optimized_text = optimized_map.get(idx)
                if isinstance(content, list):
                    parts = [p.get("text", "") for p in content if p.get("type") == "text"]
                    content = "\n".join(parts) if parts else "[多模态消息]"
                msg_item = {"role": "user", "content": content}
                if optimized_text:
                    msg_item["optimized_prompt"] = optimized_text
                display_msgs.append(msg_item)
            elif role == "tool":
                display_msgs.append({"role": "tool", "content": m.get("content", "")[:200]})
        title = getattr(session, 'session_title', '')
        partial = getattr(session, '_partial_stream_content', '') or ''
    finally:
        if acquired:
            lock.release()

    return {
        "messages": display_msgs,
        "title": title,
        "partial_content": partial,
        "is_streaming": getattr(session, 'is_streaming', False),
    }


# ============================================================
# 模型管理 API
# ============================================================

class ModelSwitchRequest(BaseModel):
    model_name: str


class ModelAddRequest(BaseModel):
    name: str = ""
    code: str = ""
    base_url: str = ""
    api_key: str = ""


@app.get("/api/models")
async def list_models():
    """获取可用模型列表"""
    session, lock = _get_session_and_lock()
    with lock:
        models = session.get_available_models()
        current = session.current_model
    return {"models": models, "current": current}


@app.put("/api/models/switch")
async def switch_model(req: ModelSwitchRequest):
    """切换当前模型"""
    if not req.model_name:
        raise HTTPException(status_code=400, detail="模型 Code 不能为空")
    session, lock = _get_session_and_lock()
    with lock:
        result = session.switch_model(req.model_name.strip())
    if result.startswith("❌"):
        raise HTTPException(status_code=400, detail=result.replace("❌ ", ""))
    _update_status_cache()
    return {"message": result, "current": session.current_model}


@app.post("/api/models/add")
async def add_model(req: ModelAddRequest):
    """添加自定义模型（name, code, base_url, api_key）"""
    if not req.name.strip() or not req.code.strip():
        raise HTTPException(status_code=400, detail="模型名称和标识不能为空")
    session, lock = _get_session_and_lock()
    with lock:
        result = session.add_custom_model(req.name, req.code, req.base_url, req.api_key)
    if result.startswith("❌"):
        raise HTTPException(status_code=400, detail=result.replace("❌ ", ""))
    models = session.get_available_models()
    current = session.current_model
    return {"message": result, "models": models, "current": current}


@app.delete("/api/models/{code}")
async def delete_model(code: str):
    """删除自定义模型"""
    session, lock = _get_session_and_lock()
    with lock:
        result = session.delete_custom_model(code.strip())
    if result.startswith("❌"):
        raise HTTPException(status_code=400, detail=result.replace("❌ ", ""))
    models = session.get_available_models()
    current = session.current_model
    return {"message": result, "models": models, "current": current}


class ConfigRequest(BaseModel):
    api_key: str = ""
    api_base_url: str = ""
    conda_env: str = ""
    python_env: str = ""


@app.put("/api/models/{code}/config")
async def update_model_config(code: str, req: ConfigRequest):
    """更新指定模型的 API 覆盖配置"""
    session, lock = _get_session_and_lock()
    with lock:
        session.update_model_api(code.strip(), req.api_base_url, req.api_key)
    _update_status_cache()
    return {"message": f"✅ 已更新模型 API 配置", "current": session.current_model}


# ============================================================
# 用户持久化配置 API（仅保留 Python/Conda 环境配置）
# ============================================================

@app.get("/api/config")
async def get_config():
    """获取当前环境配置（Python / Conda）"""
    import config as cfg
    return {
        "conda_env": _session.conda_env if hasattr(_session, 'conda_env') else cfg.DEFAULT_CONDA_ENV,
        "python_env": _session.python_env if hasattr(_session, 'python_env') else cfg.DEFAULT_PYTHON_PATH,
    }


@app.put("/api/config")
async def update_config(req: ConfigRequest):
    """更新环境配置（Python / Conda）"""
    import config as cfg
    updates = {}

    # Conda env
    if req.conda_env and req.conda_env.strip():
        updates["conda_env"] = req.conda_env.strip()
        if hasattr(_session, 'conda_env'):
            _session.conda_env = req.conda_env.strip()
        if hasattr(_session, 'switch_conda_env'):
            _session.switch_conda_env(req.conda_env.strip())

    # Python env path
    if req.python_env and req.python_env.strip():
        updates["python_env"] = req.python_env.strip()
        if hasattr(_session, 'python_env'):
            _session.python_env = req.python_env.strip()

    if updates:
        _save_user_config(updates)
        _invalidate_config_cache()

    _update_status_cache()
    return {
        "message": f"已更新 {len(updates)} 项配置",
        "updated": list(updates.keys()),
    }


@app.post("/api/session/load")
async def load_session_api(req: LoadRequest):
    """加载指定会话到注册表，如果已有活跃 session 在跟踪该文件则复用"""
    if not req.path:
        raise HTTPException(status_code=400, detail="会话路径不能为空")
    from .session_manager import restore_session

    # 检查是否有 registry session 已在跟踪此路径
    existing_sid = None
    for sid, s in _session_registry.all_sessions().items():
        if getattr(s, '_session_save_path', None) == req.path:
            existing_sid = sid
            break

    if existing_sid:
        # 已有 session：直接激活，不重新加载
        _session_registry.set_active(existing_sid)
        _update_status_cache()
        return {
            "message": f"已切换到活跃会话",
            "mode": _session_registry.get(existing_sid).get_mode_name(),
            "session_id": existing_sid,
            "already_active": True,
        }

    # 无活跃 session 跟踪此文件：创建新 session
    sid = _session_registry.create()
    _session_registry.set_active(sid)
    session = _session_registry.get(sid)
    session.set_status_update_callback(_update_status_cache)
    restore_session(session, req.path)
    session._session_save_path = req.path
    _update_status_cache()
    return {
        "message": f"已加载会话",
        "mode": session.get_mode_name(),
        "session_id": sid,
        "already_active": False,
    }


@app.post("/api/session/delete")
async def delete_session_api(req: DeleteRequest):
    """删除指定会话"""
    if not req.path:
        raise HTTPException(status_code=400, detail="会话路径不能为空")
    from .session_manager import delete_session
    try:
        result = delete_session(req.path)
        return {"message": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/env/set")
async def set_env_api(req: EnvRequest):
    """设置 Python 环境路径"""
    if not req.path or not req.path.strip():
        raise HTTPException(status_code=400, detail="路径不能为空")
    with _session_lock:
        result = _session.set_python_env(req.path.strip())
    _update_status_cache()
    return {"message": result}


@app.get("/api/env/info")
async def get_env_api():
    """获取 Python 环境信息"""
    with _session_lock:
        info = _session.get_python_env_info()
    return {"info": info}


@app.get("/api/env/current")
async def get_env_current():
    """获取当前 Python 环境状态（前端用）"""
    with _session_lock:
        env = {
            "python_path": _session.python_env,
            "conda_env": _session.conda_env,
            "manual_override": bool(PYTHON_ENV_MANUAL_OVERRIDE),
        }
    return env


@app.get("/api/env/conda/list")
async def list_conda_envs():
    """列出所有 conda 环境"""
    with _session_lock:
        result = _session.list_conda_envs()
    return result


class CondaSwitchRequest(BaseModel):
    env_name: str


@app.post("/api/env/conda/switch")
async def switch_conda_env(req: CondaSwitchRequest):
    """切换 conda 环境"""
    if not req.env_name or not req.env_name.strip():
        raise HTTPException(status_code=400, detail="环境名不能为空")
    with _session_lock:
        result = _session.switch_conda_env(req.env_name.strip())
    if result.startswith("❌"):
        raise HTTPException(status_code=400, detail=result.replace("❌ ", ""))
    _update_status_cache()
    return {"message": result}


class CondaCreateRequest(BaseModel):
    env_name: str
    python_version: str = "3.10"


@app.post("/api/env/conda/create")
async def create_conda_env(req: CondaCreateRequest):
    """创建新的 conda 环境"""
    if not req.env_name or not req.env_name.strip():
        raise HTTPException(status_code=400, detail="环境名不能为空")
    with _session_lock:
        result = _session.create_conda_env(req.env_name.strip(), req.python_version.strip())
    if result.startswith("❌"):
        raise HTTPException(status_code=400, detail=result.replace("❌ ", ""))
    return {"message": result}


# ============================================================
# Plan 菜单 API — 全部改用 try-lock，防止流式期间阻塞
# ============================================================

@app.get("/api/plan/check")
async def check_plan_ready():
    """检查 Plan 菜单是否就绪（支持缓存兜底，不阻塞）"""
    data, from_cache = _get_status_with_cache(timeout=0.3)

    if data:
        return {"ready": data.get("plan_ready", False)}

    # 缓存未命中
    session, lock = _get_session_and_lock()
    acquired = lock.acquire(timeout=0.3)
    if acquired:
        try:
            return {"ready": session.mode_mgr.is_plan_ready()}
        finally:
            lock.release()
    return {"ready": False}


@app.post("/api/plan/action")
async def plan_action(req: PlanActionRequest):
    """处理 Plan 菜单操作（支持 try-lock，不阻塞）"""
    global _plan_selected

    # ---- 不需要锁的操作 ----
    if req.action == "explore":
        _plan_selected = 0
        return {"message": "✅ 已选择: 继续探索"}
    elif req.action == "modify":
        _plan_selected = 1
        return {"message": "✅ 已选择: 修改计划"}
    elif req.action == "reset":
        _plan_selected = None
        return {"message": "🔄 已重置，请重新选择操作"}

    # ---- 需要锁的操作 ----
    session, lock = _get_session_and_lock()

    if req.action == "execute":
        _plan_selected = 2
        acquired = lock.acquire(timeout=1.0)
        if acquired:
            try:
                session.switch_mode(MODE_SMART)
                result = {"message": "✅ 已选择: 🚀 切换 Smart 执行\n\n📕 已切换为 Smart 模式，开始执行计划。"}
            finally:
                lock.release()
        else:
            result = {"message": "⏳ 当前有流式请求正在处理，请稍后再试。"}
        _update_status_cache()
        return result

    elif req.action == "confirm":
        if _plan_selected is None:
            return {"message": "⚠️ 请先选择一个操作"}

        acquired = lock.acquire(timeout=1.0)
        if acquired:
            try:
                if _plan_selected == 0:
                    result_text = "✅ 已选择: 继续探索\n\n📕 请在对话框继续输入消息。"
                elif _plan_selected == 1:
                    session.switch_mode(MODE_SMART)
                    result_text = "✅ 已选择: 修改计划\n\n📕 已切换为 Smart 模式，请直接发送修改指令。"
                elif _plan_selected == 2:
                    session.switch_mode(MODE_SMART)
                    result_text = "✅ 已选择: 🚀 切换 Smart 执行\n\n📕 已切换为 Smart 模式，开始执行计划。"
                else:
                    result_text = "⚠️ 未知选择"
            finally:
                lock.release()
        else:
            result_text = "⏳ 当前有流式请求正在处理，请稍后再试。"

        _plan_selected = None
        _update_status_cache()
        return {"message": result_text}

    else:
        return {"message": f"⚠️ 未知操作: {req.action}"}


# ============================================================
# 启动入口
# ============================================================


def check_port_available(host: str, port: int) -> bool:
    """检查端口是否可用"""
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((host, port))
            return True
    except OSError:
        return False


def find_available_port(host: str = "127.0.0.1", start_port: int = 7860, max_attempts: int = 100) -> int:
    """查找可用端口，如果端口被占用则自动递增"""
    port = start_port
    for i in range(max_attempts):
        if check_port_available(host, port):
            if i > 0:
                print(f"✅ 端口 {start_port} 被占用，已自动切换到端口 {port}")
            return port
        port += 1
    raise RuntimeError(f"无法找到可用端口（尝试范围：{start_port}-{port-1}）")


def start_web_api(host="127.0.0.1", port=None):
    """启动 FastAPI Web API 服务器，端口被占用时自动递增"""
    if port is None:
        port = GRADIO_PORT

    # 自动检测并分配可用端口
    try:
        port = find_available_port(host, port)
    except RuntimeError as e:
        print(f"❌ {e}")
        return

    print(f"{'='*50}")
    print(f"🖥 TennineClaw v{__version__} - Web API")
    print(f"{'='*50}")
    print(f"📍 服务器地址: http://{host}:{port}")
    print(f"📉 API 文档:   http://{host}:{port}/docs")
    print(f"{'='*50}")

    # 无限制超时配置，仅在 AI 报错或连接断开时停止
    # 注意：uvicorn 只支持 timeout_keep_alive 参数
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        timeout_keep_alive=86400,      # 24 小时（几乎无限制）
    )


if __name__ == "__main__":
    start_web_api()


