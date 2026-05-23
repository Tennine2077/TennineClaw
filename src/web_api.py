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
import logging
logger = logging.getLogger(__name__)
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

_status_cache = {}  # key=session_id -> data  # key=session_id -> data  # key=session_id, value=data dict (per-session)
_status_cache_lock = threading.Lock()
_status_cache_time = {}  # key=session_id, value=timestamp

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

def _update_status_cache(session_id=None):
    """更新指定会话的状态缓存（线程安全，无需 _session_lock）

    Args:
        session_id: 目标会话 ID，None 时使用活跃会话
    """
    snapshot = _build_status_snapshot(session_id)
    if snapshot:
        sid = snapshot.get("session_id", session_id or _session_registry.get_active() or _default_session_id)
        with _status_cache_lock:
            _status_cache[sid] = snapshot
            _status_cache_time[sid] = time.time()

def _get_cached_status(session_id=None):
    """获取指定会话的缓存状态（线程安全）

    Args:
        session_id: 目标会话 ID，None 时使用活跃会话
    Returns:
        缓存数据字典，不存在则返回空 dict
    """
    if session_id is None:
        session_id = _session_registry.get_active() or _default_session_id
    with _status_cache_lock:
        cached = _status_cache.get(session_id)
        return dict(cached) if cached else {}

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
                sid = data.get("session_id", session_id or _session_registry.get_active() or _default_session_id)
                with _status_cache_lock:
                    _status_cache[sid] = data
                    _status_cache_time[sid] = time.time()
            return data, False
        finally:
            lock.release()
    else:
        # 锁被占用（流式请求正在处理），返回该会话的缓存
        return _get_cached_status(session_id), True

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
    micro_count: int = 0
    auto_count: int = 0
    manual_count: int = 0

class SaveRequest(BaseModel):
    title: Optional[str] = ""
    session_id: str = ""

class LoadRequest(BaseModel):
    path: str

class DeleteRequest(BaseModel):
    path: str
class BranchRequest(BaseModel):
    """分支会话请求"""
    session_id: str
    message_index: int




class EnvRequest(BaseModel):
    path: str

class PlanActionRequest(BaseModel):
    action: str  # "explore", "modify", "execute", "confirm", "reset"


# ============================================================
# 安全获取会话数据的辅助函数（无锁，用于已持有锁的上下文）
# ============================================================
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
      - type: tool_call  → 工具调用通知（[U+1F527]）
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
                elif chunk.startswith('__TOOL_CALL__'):
                    tool_content = chunk[13:]  # 去掉 __TOOL_CALL__ 前缀
                    yield f"data: {json.dumps({'type': 'tool_call', 'content': tool_content})}\n\n"
                elif chunk.startswith('__FINAL__'):
                    yield f"data: {json.dumps({'type': 'final', 'content': ''})}\n\n"
                elif chunk == "\n\n⏹️ **已中断**":
                    was_interrupted = True
                    yield f"data: {json.dumps({'type': 'interrupted', 'content': chunk})}\n\n"
                elif chunk.startswith('[U+1F527]'):
                    yield f"data: {json.dumps({'type': 'tool_call', 'content': chunk})}\n\n"
                elif chunk.startswith('__REASONING__'):
                    reasoning_content = chunk[13:]  # 去掉前缀（__REASONING__ 共13字符）
                    yield f"data: {json.dumps({'type': 'reasoning', 'content': reasoning_content})}\n\n"
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

            # 流式完成后自动保存会话
            try:
                session._auto_save_if_needed()
            except Exception:
                pass

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
    session.set_status_update_callback(lambda: _update_status_cache(session.session_id))
    # 立即自动保存新会话到磁盘，防止服务器重启后丢失
    from .session_manager import auto_save
    save_path = auto_save(session)
    if save_path:
        session._session_save_path = save_path

    return {"session_id": sid, "status": "success"}


@app.post("/api/session/branch")
async def create_branch_session(req: BranchRequest):
    """从指定消息创建分支会话"""
    # 获取源会话
    src_session, src_lock = _get_session_and_lock(req.session_id)
    if src_session is None:
        raise HTTPException(status_code=404, detail=f"源会话不存在: {req.session_id}")
    
    with src_lock:
        src_msgs = list(getattr(src_session, '_display_msgs', src_session.msgs))
        msg_idx = req.message_index
    
    if msg_idx < 0 or msg_idx >= len(src_msgs):
        raise HTTPException(status_code=400, detail=f"消息索引越界: {msg_idx}, 总消息数: {len(src_msgs)}")
    
    # 获取触发消息的预览文本
    trigger_msg = src_msgs[msg_idx]
    trigger_content = trigger_msg.get("content", "")
    trigger_preview = (trigger_content[:80] + "...") if len(trigger_content) > 80 else trigger_content
    
    # 截取上下文：从第一条到触发消息之后最近的 AI 回复（含）
    # 确保分支的最后一条消息由 AI 发出
    branch_end = msg_idx + 1
    if trigger_msg.get("role") != "assistant":
        # 如果触发消息不是 AI 发出的，向后找最近的 AI 消息
        for i in range(msg_idx + 1, len(src_msgs)):
            if src_msgs[i].get("role") == "assistant":
                branch_end = i + 1
                break
    branch_msgs = src_msgs[: branch_end]
    
    # 保存源会话
    from .session_manager import auto_save as auto_save_func
    try:
        src_save_path = getattr(src_session, '_session_save_path', None)
        auto_save_func(src_session, session_save_path=src_save_path)
    except Exception:
        pass
    
    # 创建新会话
    sid = _session_registry.create()
    _session_registry.set_active(sid)
    session = _session_registry.get(sid)
    session.set_status_update_callback(lambda: _update_status_cache(session.session_id))
    
    # 注入分支上下文
    if branch_msgs:
        session.msgs = [dict(m) for m in branch_msgs]
        session._display_msgs = [dict(m) for m in branch_msgs]
    
    # 复制元数据（原始输入记录 & 优化 Prompt 记录）
    src_original_inputs = getattr(src_session, 'original_user_inputs', {})
    src_optimized_prompts = getattr(src_session, 'optimized_prompts', {})
    # 只复制触发消息之前的记录（与截取的消息索引对应）
    src_original_inputs = {k: v for k, v in src_original_inputs.items() if k < msg_idx + 1}
    src_optimized_prompts = {k: v for k, v in src_optimized_prompts.items() if k < msg_idx + 1}
    session.original_user_inputs = src_original_inputs
    session.optimized_prompts = src_optimized_prompts
    
    # 设置分支元数据
    session.parent_session_id = req.session_id
    # trigger_message_index 指向分支中实际最后一条消息（AI 消息）的索引
    session.trigger_message_index = branch_end - 1
    # 更新预览文本为最后一条消息的内容
    last_msg = branch_msgs[-1] if branch_msgs else trigger_msg
    last_content = last_msg.get("content", "")
    trigger_preview = (last_content[:80] + "...") if len(last_content) > 80 else last_content
    session.trigger_message_preview = trigger_preview
    
    # 根据触发消息内容生成标题
    if trigger_msg.get("role") == "user":
        title_text = trigger_content[:50]
    else:
        title_text = trigger_content[:50]
    session.session_title = ("[分支] " + title_text)[:60]
    session._title_set = True
    
    # 自动保存新会话 - 确保 _session_save_path 绝对正确设置
    from .session_manager import save_session as direct_save
    from .config import SESSION_SAVE_DIR
    import os, datetime, re
    
    _title = getattr(session, "session_title", "") or "分支会话"
    _safe = re.sub(r'[\\/:*?"<>|\n\r\t]', '', _title).strip() or "分支会话"
    _ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    _filename = f"{_safe}_{_ts}.json"
    _path = os.path.join(SESSION_SAVE_DIR, _filename)
    
    # 直接 save_session 到明确路径，100% 确保文件被创建
    try:
        direct_save(session, path=_path)
        session._session_save_path = _path
        print(f"[DEBUG_BRANCH] direct_save SUCCESS to {_path}", flush=True)
    except Exception as e2:
        print(f"[DEBUG_BRANCH] direct_save FAILED: {e2}", flush=True)
        # traceback removed
        # auto_save 兜底
        try:
            save_path = auto_save_func(session)
            if save_path:
                session._session_save_path = save_path
                print(f"[DEBUG_BRANCH] auto_save SUCCESS to {save_path}", flush=True)
            else:
                print(f"[DEBUG_BRANCH] auto_save returned empty path!", flush=True)
        except Exception as e3:
            print(f"[DEBUG_BRANCH] auto_save FAILED: {e3}", flush=True)
            traceback.print_exc()
            # 最后尝试 save_session 到随机路径
            try:
                import uuid
                _fallback = os.path.join(SESSION_SAVE_DIR, f"branch_{uuid.uuid4().hex[:8]}.json")
                direct_save(session, path=_fallback)
                session._session_save_path = _fallback
                print(f"[DEBUG_BRANCH] fallback SUCCESS to {_fallback}", flush=True)
            except Exception as e4:
                print(f"[DEBUG_BRANCH] fallback ALL FAILED: {e4}", flush=True)
                traceback.print_exc()
                pass
    
    _update_status_cache()
    
    return {
        "session_id": sid,
        "status": "success",
        "parent_session_id": req.session_id,
        "trigger_message_index": branch_end - 1,
        "message_count": len(branch_msgs),
        "save_path": getattr(session, '_session_save_path', ''),
    }


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
            "parent_session_id": getattr(session, 'parent_session_id', ''),
            "trigger_message_index": getattr(session, 'trigger_message_index', -1),
            "trigger_message_preview": getattr(session, 'trigger_message_preview', ''),
        })

    return {
        "active_sessions": active_sessions,
        "saved_files": saved_files,
    }


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
    session.set_status_update_callback(lambda: _update_status_cache(session.session_id))
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
            return "[Wait] 当前有流式请求正在处理（等待超时 30 秒），请稍后再试。"

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
        help_text = "[Wait] 当前有请求正在处理，请稍后再试。"
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
        result = "[Wait] 当前有请求正在处理，请稍后再试。"
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
        micro_count=data.get("micro_count", 0),
        auto_count=data.get("auto_count", 0),
        manual_count=data.get("manual_count", 0),
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
            f"[Chart]合计: {total_tk:,} ({usage_pct:.1f}%)"
        )
    else:
        from .config import MAX_CTX_TOKENS as max_ctx
        status = (
            f"**模式**: {mode_name} | "
            f"**消息**: {msg_count} 条"
        )

    if notification:
        status += f"\n\n[Bell] **{notification}**"

    if is_streaming or from_cache:
        status += "\n\n[Wait] *AI 响应中...*"

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
    if req.session_id:
        # 指定 session_id 保存
        session = _session_registry.get(req.session_id)
        if session is None:
            return {"status": "error", "detail": "会话不存在"}
        lock = _session_registry.get_lock(req.session_id) or threading.Lock()
        with lock:
            if req.title and req.title.strip():
                session.set_title(req.title.strip())
            # 使用 _session_save_path 覆盖同一文件
            save_path = getattr(session, '_session_save_path', None)
            result = session.save(path=save_path)
        _update_status_cache()
        return {"message": result}
    else:
        # 默认：保存当前活跃会话
        session, lock = _get_session_and_lock()
        with lock:
            if req.title and req.title.strip():
                session.set_title(req.title.strip())
            # 使用 _session_save_path 覆盖同一文件
            save_path = getattr(session, '_session_save_path', None)
            result = session.save(path=save_path)
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

        # 逐条构建 rounds：每个 assistant 消息携带自己的 rounds 数据
        # pending 结构: {thinking, tool_calls:[{name,arguments,tool_call_id,result}]}
        pending = None  # 当前 round（最后一次 assistant 工具调用后创建）

        for idx, m in enumerate(msgs):
            role = m.get("role", "")
            if role == "system":
                continue

            if role == "assistant":
                content = m.get("content", "")
                tool_calls_raw = m.get("tool_calls", None)
                reasoning = m.get("reasoning_content", "")

                msg_item = {"role": "assistant", "content": content or "[工具调用]"}
                if reasoning:
                    msg_item["reasoning_content"] = reasoning

                if tool_calls_raw:
                    # 工具调用：创建一个新 round，挂载到本 msg_item
                    # 本 round 的 response 留空（后续的最终回复消息会创建独立的新 round，
                    # 不通过对象引用修改此 round）
                    tc_list = []
                    tool_list = []
                    for tc in tool_calls_raw:
                        tc_info = {
                            "name": tc.get("function", {}).get("name", ""),
                            "arguments": tc.get("function", {}).get("arguments", ""),
                            "tool_call_id": tc.get("id", ""),
                        }
                        tc_list.append(tc_info)
                        tool_list.append({**tc_info, "result": ""})
                    msg_item["tool_calls"] = tc_list
                    pending = {
                        "thinking": reasoning or "",
                        "tool_calls": tool_list,
                        "response": ""
                    }
                    # 当前 round 挂载到本 assistant 消息
                    msg_item["rounds"] = [pending]
                else:
                    # 最终回复：创建独立的新 round，不修改之前的 pending 对象
                    # （前台知悉每个 assistant 消息独立渲染，工具调用消息不含回复内容）
                    current_round = {
                        "thinking": reasoning or "",
                        "tool_calls": [],
                        "response": content
                    }
                    if reasoning or content:
                        msg_item["rounds"] = [current_round]
                    pending = None
                display_msgs.append(msg_item)

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
                # 新用户消息 => 重置 pending 和 assistant_rounds
                pending = None
                assistant_rounds = None

            elif role == "tool":
                tool_call_id = m.get("tool_call_id", "")
                result = m.get("content", "")[:10000]
                if pending:
                    for rt in pending["tool_calls"]:
                        if rt.get("tool_call_id") == tool_call_id:
                            rt["result"] = result
                            break
                display_msgs.append({
                    "role": "tool",
                    "content": result,
                    "tool_call_id": tool_call_id
                })

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
    if result.startswith("[X]"):
        raise HTTPException(status_code=400, detail=result.replace("[X] ", ""))
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
    if result.startswith("[X]"):
        raise HTTPException(status_code=400, detail=result.replace("[X] ", ""))
    models = session.get_available_models()
    current = session.current_model
    return {"message": result, "models": models, "current": current}


@app.delete("/api/models/{code}")
async def delete_model(code: str):
    """删除自定义模型"""
    session, lock = _get_session_and_lock()
    with lock:
        result = session.delete_custom_model(code.strip())
    if result.startswith("[X]"):
        raise HTTPException(status_code=400, detail=result.replace("[X] ", ""))
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
    return {"message": f"[OK] 已更新模型 API 配置", "current": session.current_model}


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
    if result.startswith("[X]"):
        raise HTTPException(status_code=400, detail=result.replace("[X] ", ""))
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
    if result.startswith("[X]"):
        raise HTTPException(status_code=400, detail=result.replace("[X] ", ""))
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
        return {"message": "[OK] 已选择: 继续探索"}
    elif req.action == "modify":
        _plan_selected = 1
        return {"message": "[OK] 已选择: 修改计划"}
    elif req.action == "reset":
        _plan_selected = None
        return {"message": "[Refresh] 已重置，请重新选择操作"}

    # ---- 需要锁的操作 ----
    session, lock = _get_session_and_lock()

    if req.action == "execute":
        _plan_selected = 2
        acquired = lock.acquire(timeout=10.0)
        if acquired:
            try:
                session.switch_mode(MODE_SMART)
                result = {"message": "[OK] 已选择: [Rocket] 切换 Smart 执行\n\n[U+1F4D5] 已切换为 Smart 模式，开始执行计划。"}
            finally:
                lock.release()
        else:
            result = {"message": "[Wait] 当前有流式请求正在处理，请稍后再试。"}
        _update_status_cache()
        return result

    elif req.action == "confirm":
        if _plan_selected is None:
            return {"message": "[Warn]️ 请先选择一个操作"}

        acquired = lock.acquire(timeout=10.0)
        if acquired:
            try:
                if _plan_selected == 0:
                    result_text = "[OK] 已选择: 继续探索\n\n[U+1F4D5] 请在对话框继续输入消息。"
                elif _plan_selected == 1:
                    session.switch_mode(MODE_SMART)
                    result_text = "[OK] 已选择: 修改计划\n\n[U+1F4D5] 已切换为 Smart 模式，请直接发送修改指令。"
                elif _plan_selected == 2:
                    session.switch_mode(MODE_SMART)
                    result_text = "[OK] 已选择: [Rocket] 切换 Smart 执行\n\n[U+1F4D5] 已切换为 Smart 模式，开始执行计划。"
                else:
                    result_text = "[Warn]️ 未知选择"
            finally:
                lock.release()
        else:
            result_text = "[Wait] 当前有流式请求正在处理，请稍后再试。"

        _plan_selected = None
        _update_status_cache()
        return {"message": result_text}

    else:
        return {"message": f"[Warn]️ 未知操作: {req.action}"}


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
                print(f"[OK] 端口 {start_port} 被占用，已自动切换到端口 {port}")
            return port
        port += 1
    raise RuntimeError(f"无法找到可用端口（尝试范围：{start_port}-{port-1}）")



# ============================================================
# Skill & Personality API
# ============================================================

class SkillPersonalityResponse(BaseModel):
    success: bool = True
    message: str = ""
    data: dict = {}


def _get_skill_personality_data(session):
    """Get skill and personality data from session"""
    data = {}
    try:
        engine = getattr(session, 'skill_engine', None)
        if engine:
            skills_data = []
            for sk_id, sk in engine.skill_tree.skills.items():
                sk_dict = sk.to_dict()
                sk_dict["is_owned"] = sk_id in engine._owned_skill_ids
                sk_dict["is_active"] = sk_id in engine._active_skill_ids
                skills_data.append(sk_dict)
            data["skills"] = skills_data
            data["skill_stats"] = engine.get_skill_stats()
            data["available_combos"] = [
                c.to_dict() for c in engine.get_available_combos()
            ]
            data["unlockable_skills"] = [
                s.to_dict() for s in engine.get_unlockable_skills()
            ]
    except Exception as e:
        data["skills_error"] = str(e)

    try:
        pe = getattr(session, 'personality_engine', None)
        if pe:
            data["personality"] = pe.get_stats()
            data["personality_guide"] = pe.get_response_style_guide()
            data["important_memories"] = [
                m.to_dict() for m in pe.get_important_memories(0.6)
            ]
    except Exception as e:
        data["personality_error"] = str(e)

    return data


@app.get("/api/skills", response_model=SkillPersonalityResponse)
async def get_skills(session_id: str = None):
    """获取所有技能及其状态"""
    session, _ = _get_session_and_lock(session_id)
    data = _get_skill_personality_data(session)
    return SkillPersonalityResponse(
        success=True,
        message=f"共 {len(data.get('skills', []))} 个技能",
        data={"skills": data.get("skills", []), "stats": data.get("skill_stats", {})},
    )


@app.get("/api/skills/available", response_model=SkillPersonalityResponse)
async def get_available_skills(session_id: str = None):
    """获取当前可用技能列表"""
    session, _ = _get_session_and_lock(session_id)
    try:
        skills = getattr(session, 'skill_engine', None)
        if skills:
            available = skills.get_available_skills()
            return SkillPersonalityResponse(
                success=True,
                data={"skills": [s.to_dict() for s in available]},
            )
    except Exception as e:
        return SkillPersonalityResponse(success=False, message=str(e))
    return SkillPersonalityResponse(success=False, message="技能引擎未初始化")


@app.post("/api/skills/{skill_id}/activate")
async def activate_skill(skill_id: str, session_id: str = None):
    """激活/停用技能"""
    session, lock = _get_session_and_lock(session_id)
    acquired = lock.acquire(timeout=10.0)
    if not acquired:
        raise HTTPException(status_code=423, detail="会话忙，请稍后重试")
    try:
        engine = getattr(session, 'skill_engine', None)
        if not engine:
            return SkillPersonalityResponse(success=False, message="技能引擎未初始化")
        skill = engine.skill_tree.get_skill(skill_id)
        if not skill:
            return SkillPersonalityResponse(success=False, message=f"技能 {skill_id} 不存在")
        is_active = engine.is_skill_active(skill_id)
        if is_active:
            engine.deactivate_skill(skill_id)
            return SkillPersonalityResponse(message=f"已停用: {skill.name}")
        else:
            engine.activate_skill(skill_id)
            return SkillPersonalityResponse(message=f"已激活: {skill.name}")
    finally:
        lock.release()


@app.get("/api/personality", response_model=SkillPersonalityResponse)
async def get_personality(session_id: str = None):
    """获取人格档案"""
    session, _ = _get_session_and_lock(session_id)
    data = _get_skill_personality_data(session)
    return SkillPersonalityResponse(
        success=True,
        data={
            "personality": data.get("personality", {}),
            "guide": data.get("personality_guide", ""),
            "memories": data.get("important_memories", []),
        },
    )


@app.post("/api/personality/template")
async def apply_personality_template(data: dict, session_id: str = None):
    """应用人格模板（支持JSON body）"""
    template_name = data.get("name", "").strip()
    if not template_name:
        raise HTTPException(status_code=400, detail="缺少模板名称")
    session, lock = _get_session_and_lock(session_id)
    acquired = lock.acquire(timeout=10.0)
    if not acquired:
        raise HTTPException(status_code=423, detail="会话忙，请稍后重试")
    try:
        pe = getattr(session, 'personality_engine', None)
        if not pe:
            return SkillPersonalityResponse(success=False, message="人格引擎未初始化")
        from .personality_models import list_personality_templates, load_custom_templates
        all_templates = list_personality_templates()
        if template_name not in all_templates:
            return SkillPersonalityResponse(
                success=False,
                message=f"模板不存在，可用: {all_templates}",
            )
        print(f"[apply_personality_template] Applying template: {template_name}", flush=True)
        if not pe.apply_template(template_name):
            print(f"[apply_personality_template] [Warn]️ Failed to apply template: {template_name}", flush=True)
            return SkillPersonalityResponse(
                success=False, 
                message=f"应用人格模板「{template_name}」失败，请检查角色定义文件"
            )
        print(f"[apply_personality_template] Template applied successfully", flush=True)
        # Refresh system prompt with new personality context
        if hasattr(session, 'refresh_personality_in_system_prompt'):
            session.refresh_personality_in_system_prompt()
        # 如果自定义模板有预置技能，一并装备
        pub_tmpl = load_custom_templates().get(template_name, {})
        equipped_ids = []
        if pub_tmpl:
            equipped_ids = pub_tmpl.get("equipped_skill_ids", [])
            soul_md = pub_tmpl.get("soul_md", "")
            if soul_md:
                try:
                    import os
                    personas_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "personas")
                    role_dir = os.path.join(personas_dir, template_name)
                    os.makedirs(role_dir, exist_ok=True)
                    with open(os.path.join(role_dir, "soul.md"), "w", encoding="utf-8") as f:
                        f.write(soul_md)
                except Exception as e:
                    logger.warning(f"写入 soul.md 失败: {e}")
        else:
            # Try personas directory
            try:
                import os, json
                personas_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "personas")
                def_file = os.path.join(personas_dir, template_name, "definition.json")
                if os.path.isfile(def_file):
                    with open(def_file, 'r', encoding='utf-8') as f:
                        def_data = json.load(f)
                    equipped_ids = def_data.get("equipped_skill_ids", [])
            except Exception:
                pass
        if equipped_ids:
            pe.profile.equipped_skill_ids = list(equipped_ids)
        pe.save_profile()
        # 同步更新技能注册表的 used_by_personas
        from .skill_models import add_persona_to_skill
        for sid in equipped_ids:
            add_persona_to_skill(sid, template_name)
        return SkillPersonalityResponse(
            success=True,
            message=f"已应用人格模板: {template_name}",
            data={"equipped_skills": list(pe.profile.equipped_skill_ids)},
        )
    except Exception as e:
        return SkillPersonalityResponse(success=False, message=str(e))
    finally:
        lock.release()


@app.get("/api/personality/templates")
async def list_templates():
    """列出所有可用人格模板"""
    from .personality_models import list_personality_templates
    return {"templates": list_personality_templates()}


@app.get("/api/skills/combos", response_model=SkillPersonalityResponse)
async def get_skill_combos(session_id: str = None):
    """获取可用技能组合"""
    session, _ = _get_session_and_lock(session_id)
    try:
        engine = getattr(session, 'skill_engine', None)
        if engine:
            combos = engine.get_available_combos()
            return SkillPersonalityResponse(
                success=True,
                data={"combos": [c.to_dict() for c in combos]},
            )
    except Exception as e:
        return SkillPersonalityResponse(success=False, message=str(e))
    return SkillPersonalityResponse(success=False, message="技能引擎未初始化")


@app.get("/api/status/extended")
async def get_extended_status(session_id: str = None):
    """获取扩展状态（包含技能和人格信息）"""
    session, _ = _get_session_and_lock(session_id)
    data = _get_skill_personality_data(session)
    return {
        "skill_stats": data.get("skill_stats", {}),
        "personality_name": data.get("personality", {}).get("profile_name", ""),
        "personality_traits": data.get("personality", {}).get("traits", {}),
        "memories_count": data.get("personality", {}).get("memories_count", 0),
    }



# ============================================================
# 人格管理 API（新增）
# ============================================================

@app.put("/api/personality/traits")
async def update_personality_traits(data: dict, session_id: str = None):
    """更新性格特征（OCEAN 五维）"""
    session, lock = _get_session_and_lock(session_id)
    acquired = lock.acquire(timeout=10.0)
    if not acquired:
        raise HTTPException(status_code=423, detail="会话忙，请稍后重试")
    try:
        pe = getattr(session, 'personality_engine', None)
        if not pe:
            return SkillPersonalityResponse(success=False, message="人格引擎未初始化")
        # data格式: {"openness": 80, "conscientiousness": 70, ...}
        for dim, val in data.items():
            if hasattr(pe.profile.traits, dim):
                current = getattr(pe.profile.traits, dim)
                delta = val - current
                pe.update_trait(dim, delta)
        pe.save_profile()
        # Refresh system prompt with updated traits
        if hasattr(session, 'refresh_personality_in_system_prompt'):
            session.refresh_personality_in_system_prompt()
        return SkillPersonalityResponse(
            success=True,
            message="性格特征已更新",
            data={"traits": pe.profile.traits.to_dict()},
        )
    finally:
        lock.release()


@app.put("/api/personality/style")
async def update_language_style(data: dict, session_id: str = None):
    """更新语言风格"""
    session, lock = _get_session_and_lock(session_id)
    acquired = lock.acquire(timeout=10.0)
    if not acquired:
        raise HTTPException(status_code=423, detail="会话忙，请稍后重试")
    try:
        pe = getattr(session, 'personality_engine', None)
        if not pe:
            return SkillPersonalityResponse(success=False, message="人格引擎未初始化")
        for dim, val in data.items():
            if hasattr(pe.profile.language_style, dim):
                current = getattr(pe.profile.language_style, dim)
                pe.profile.language_style.adjust(dim, val - current)
        pe.save_profile()
        # Refresh system prompt with updated style
        if hasattr(session, 'refresh_personality_in_system_prompt'):
            session.refresh_personality_in_system_prompt()
        return SkillPersonalityResponse(
            success=True,
            message="语言风格已更新",
            data={"style": pe.profile.language_style.to_dict(), "tags": pe.profile.language_style.get_style_tags()},
        )
    finally:
        lock.release()


@app.put("/api/personality/preferences")
async def update_behavior_preferences(data: dict, session_id: str = None):
    """更新行为偏好"""
    session, lock = _get_session_and_lock(session_id)
    acquired = lock.acquire(timeout=10.0)
    if not acquired:
        raise HTTPException(status_code=423, detail="会话忙，请稍后重试")
    try:
        pe = getattr(session, 'personality_engine', None)
        if not pe:
            return SkillPersonalityResponse(success=False, message="人格引擎未初始化")
        prefs = pe.profile.behavior_prefs
        for key, val in data.items():
            if hasattr(prefs, key):
                setattr(prefs, key, val)
        pe.save_profile()
        return SkillPersonalityResponse(
            success=True,
            message="行为偏好已更新",
            data={"preferences": prefs.to_dict()},
        )
    finally:
        lock.release()


@app.get("/api/personality/memories")
async def get_memories(keyword: str = "", session_id: str = None):
    """获取记忆列表（支持关键词搜索）"""
    session, _ = _get_session_and_lock(session_id)
    pe = getattr(session, 'personality_engine', None)
    if not pe:
        return SkillPersonalityResponse(success=False, message="人格引擎未初始化")
    if keyword:
        memories = pe.search_memories(keyword)
    else:
        memories = sorted(
            pe.profile.memories,
            key=lambda m: m.importance,
            reverse=True,
        )
    return SkillPersonalityResponse(
        success=True,
        data={"memories": [m.to_dict() for m in memories]},
    )


@app.delete("/api/personality/memory/{memory_id}")
async def delete_memory(memory_id: str, session_id: str = None):
    """删除指定记忆"""
    session, lock = _get_session_and_lock(session_id)
    acquired = lock.acquire(timeout=10.0)
    if not acquired:
        raise HTTPException(status_code=423, detail="会话忙，请稍后重试")
    try:
        pe = getattr(session, 'personality_engine', None)
        if not pe:
            return SkillPersonalityResponse(success=False, message="人格引擎未初始化")
        before = len(pe.profile.memories)
        pe.profile.memories = [m for m in pe.profile.memories if m.id != memory_id]
        if len(pe.profile.memories) < before:
            pe.save_profile()
            return SkillPersonalityResponse(success=True, message="记忆已删除")
        return SkillPersonalityResponse(success=False, message="未找到该记忆")
    finally:
        lock.release()


@app.post("/api/personality/reset")
async def reset_personality(session_id: str = None):
    """重置人格为默认配置"""
    session, lock = _get_session_and_lock(session_id)
    acquired = lock.acquire(timeout=10.0)
    if not acquired:
        raise HTTPException(status_code=423, detail="会话忙，请稍后重试")
    try:
        pe = getattr(session, 'personality_engine', None)
        if not pe:
            return SkillPersonalityResponse(success=False, message="人格引擎未初始化")
        from .personality_models import PersonalityProfile
        old_id = pe.profile.profile_id
        pe.profile = PersonalityProfile(profile_id=old_id)
        pe.save_profile()
        # Refresh system prompt after personality reset
        if hasattr(session, 'refresh_personality_in_system_prompt'):
            session.refresh_personality_in_system_prompt()
        return SkillPersonalityResponse(
            success=True,
            message="人格已重置为默认配置",
            data={"profile": pe.get_stats()},
        )
    finally:
        lock.release()


@app.get("/api/personality/style/tags")
async def get_style_tags(session_id: str = None):
    """获取当前语言风格标签"""
    session, _ = _get_session_and_lock(session_id)
    pe = getattr(session, 'personality_engine', None)
    if not pe:
        return SkillPersonalityResponse(success=False, message="人格引擎未初始化")
    return SkillPersonalityResponse(
        success=True,
        data={
            "tags": pe.profile.language_style.get_style_tags(),
            "style": pe.profile.language_style.to_dict(),
        },
    )


# ============================================================
# 全局技能库 API（新增）
# ============================================================

@app.get("/api/skills/registry")
async def get_skill_registry(include_detail: bool = False, session_id: str = None):
    """获取全局技能库列表"""
    try:
        from .skill_models import get_registry_skills_list
        skills = get_registry_skills_list(include_detail=include_detail)
        return {"success": True, "data": skills}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/skills/registry/{skill_id}/detail")
async def get_skill_detail(skill_id: str, session_id: str = None):
    """获取单个技能的详细内容（含description和guide）"""
    try:
        from .skill_models import get_skill_detail
        detail = get_skill_detail(skill_id)
        if detail.get("description") or detail.get("guide"):
            return {"success": True, "description": detail.get("description", ""), "guide": detail.get("guide", "")}
        return {"success": False, "description": "", "guide": ""}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/personality/equipped-skills")
async def get_equipped_skills(session_id: str = None):
    """获取当前人格已装备的技能"""
    session, _ = _get_session_and_lock(session_id)
    pe = getattr(session, 'personality_engine', None)
    if not pe:
        raise HTTPException(status_code=404, detail="人格引擎未初始化")
    try:
        from .skill_models import load_global_skill_registry
        registry = load_global_skill_registry()
        equipped_ids = pe.profile.equipped_skill_ids
        equipped_skills = []
        for sk_id in equipped_ids:
            if sk_id in registry:
                equipped_skills.append(registry[sk_id])
        return {"success": True, "data": equipped_skills, "equipped_ids": equipped_ids}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/personality/equip-skill/{skill_id}")
async def equip_skill(skill_id: str, session_id: str = None):
    """装备技能到当前人格"""
    session, lock = _get_session_and_lock(session_id)
    acquired = lock.acquire(timeout=10.0)
    if not acquired:
        raise HTTPException(status_code=423, detail="会话忙，请稍后重试")
    try:
        pe = getattr(session, 'personality_engine', None)
        if not pe:
            raise HTTPException(status_code=404, detail="人格引擎未初始化")
        if skill_id not in pe.profile.equipped_skill_ids:
            pe.profile.equipped_skill_ids.append(skill_id)
            pe.save_profile()
        return {"success": True, "message": f"已装备技能 {skill_id}"}
    finally:
        lock.release()


@app.delete("/api/personality/equip-skill/{skill_id}")
async def unequip_skill(skill_id: str, session_id: str = None):
    """从当前人格卸下技能"""
    session, lock = _get_session_and_lock(session_id)
    acquired = lock.acquire(timeout=10.0)
    if not acquired:
        raise HTTPException(status_code=423, detail="会话忙，请稍后重试")
    try:
        pe = getattr(session, 'personality_engine', None)
        if not pe:
            raise HTTPException(status_code=404, detail="人格引擎未初始化")
        if skill_id in pe.profile.equipped_skill_ids:
            pe.profile.equipped_skill_ids.remove(skill_id)
            pe.save_profile()
        return {"success": True, "message": f"已卸下技能 {skill_id}"}
    finally:
        lock.release()


# ============================================================
# 自定义人格模板 API（新增）


# ============================================================
# Session Role API (预留扩展接口)
# ============================================================

@app.get("/api/session/{session_id}/role")
async def get_session_role(session_id: str = None):
    """获取当前会话绑定的角色卡
    
    Note: 当前版本角色卡在新建会话时选定，不支持会话中切换。
    此接口为预留，后续用于主/子 agent 多角色支持。
    """
    session, _ = _get_session_and_lock(session_id)
    
    # Get personality engine for current session
    pe = getattr(session, 'personality_engine', None)
    if pe:
        role_name = pe.profile.name or '默认助手'
        return {
            "success": True,
            "data": {
                "role_id": pe.profile_id,
                "role_name": role_name,
            }
        }
    
    return {
        "success": True,
        "data": {
            "role_id": "default",
            "role_name": "默认助手",
        }
    }


@app.put("/api/session/{session_id}/role")
async def set_session_role(session_id: str = None, data: dict = None):
    """切换会话的角色卡（预留接口）
    
    当前版本不支持会话中切换角色。
    此接口为预留，后续用于主/子 agent 嵌套调用场景。
    
    Returns:
        固定返回"功能开发中"提示
    """
    return {
        "success": False,
        "message": "会话中切换角色功能开发中，敬请期待",
        "future_use": "此接口预留用于主/子 agent 多角色支持"
    }
# ============================================================

@app.get("/api/personality/templates/all")
async def get_all_templates(session_id: str = None):
    """获取所有模板（内置+自定义）"""
    try:
        from .personality_models import get_all_templates_with_custom
        templates = get_all_templates_with_custom()
        return {"success": True, "data": templates}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/api/personality/templates/{name}/soul")
async def get_template_soul(name: str):
    """获取角色 soul.md 内容（用于前端悬停预览）"""
    try:
        from urllib.parse import unquote
        import os
        role_name = unquote(name)
        personas_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "personas")
        soul_path = os.path.join(personas_dir, role_name, "soul.md")
        if os.path.isfile(soul_path):
            with open(soul_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
            return {"success": True, "content": content}
        else:
            from .personality_models import load_custom_templates
            custom = load_custom_templates()
            if role_name in custom:
                soul_md = custom[role_name].get("soul_md", "")
                if soul_md:
                    return {"success": True, "content": soul_md}
            return {"success": False, "content": "", "error": "soul.md not found"}
    except Exception as e:
        return {"success": False, "content": "", "error": str(e)}

@app.post("/api/personality/templates/custom")
async def create_custom_template(data: dict, session_id: str = None):
    """创建自定义人格模板"""
    try:
        from .personality_models import add_custom_template
        result = add_custom_template(data)
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        return {"success": True, "data": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/personality/templates/custom/{name}")
async def update_custom_template(name: str, data: dict, session_id: str = None):
    """更新自定义人格模板"""
    try:
        from .personality_models import update_custom_template
        result = update_custom_template(name, data)
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/personality/templates/custom/{name}")
async def delete_custom_template(name: str, session_id: str = None):
    """删除自定义人格模板"""
    try:
        from .personality_models import delete_custom_template
        result = delete_custom_template(name)
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def start_web_api(host="127.0.0.1", port=None):
    """启动 FastAPI Web API 服务器，端口被占用时自动递增"""
    if port is None:
        port = GRADIO_PORT

    # 自动检测并分配可用端口
    try:
        port = find_available_port(host, port)
    except RuntimeError as e:
        print(f"[X] {e}")
        return

    print(f"{'='*50}")
    print(f"[Desktop] TennineClaw v{__version__} - Web API")
    print(f"{'='*50}")
    print(f"[U+1F4CD] 服务器地址: http://{host}:{port}")
    print(f"[U+1F4C9] API 文档:   http://{host}:{port}/docs")
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


