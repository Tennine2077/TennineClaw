# 🤖 多 Agent 协同架构设计文档 — 主子 Agent 模式

> **语言**: 中文 | [🌏 English](MULTI_AGENT_ARCHITECTURE_DESIGN.en.md)
> **项目**: TennineClaw  
> **版本**: v1.1.0（依赖已就绪）  
> **设计目标**: 构建主子 Agent 协同架构，实现任务智能分配、并行拆分、结果汇总、异常容错  
> **前置依赖**: Skill 技能系统 + 人格化持久性系统（SKILL_PERSONALITY_DESIGN.md）  
> **设计原则**: 高内聚低耦合、异步优先、优雅降级、可观测

---

## 📖 目录

1. [系统概述](#1-系统概述)
2. [架构总览](#2-架构总览)
3. [核心数据结构](#3-核心数据结构)
4. [Orchestrator — 主 Agent 引擎](#4-orchestrator--主-agent-引擎)
5. [WorkerAgent — 子 Agent 实现](#5-workeragent--子-agent-实现)
6. [TaskDispatcher — 任务调度器](#6-taskdispatcher--任务调度器)
7. [TaskSplitter — 任务拆分引擎](#7-tasksplitter--任务拆分引擎)
8. [ResultMerger — 结果合并引擎](#8-resultmerger--结果合并引擎)
9. [RegistryCenter — 子 Agent 注册中心](#9-registrycenter--子-agent-注册中心)
10. [负载均衡与容错](#10-负载均衡与容错)
11. [扩展场景设计](#11-扩展场景设计)
12. [与现有系统的集成](#12-与现有系统的集成)
13. [交互流程详图](#13-交互流程详图)
14. [存储与配置规划](#14-存储与配置规划)
15. [变更清单](#15-变更清单)

---

## 1. 系统概述

### 1.1 为什么需要多 Agent 协同？

| 当前单 Agent 痛点 | 多 Agent 架构解决方式 |
|-------------------|----------------------|
| ❌ 一个 Agent 串行处理所有工具调用，大任务耗时极长 | ✅ 主 Agent 将子任务并行分发给多个子 Agent，大幅缩短耗时 |
| ❌ 所有能力耦合在同一个 System Prompt 中，上下文膨胀严重 | ✅ 子 Agent 专注单一领域，System Prompt 精简高效 |
| ❌ 单个 Agent 出错导致整个对话失败，无容错能力 | ✅ 子 Agent 独立运行，单个失败不影响整体，支持重试/降级 |
| ❌ 无法同时处理多个独立请求（如查文件+查Git状态） | ✅ 多个子 Agent 可完全并行执行不相关的任务 |
| ❌ Agent 能力无法水平扩展 | ✅ 子 Agent 可动态注册/注销，系统能力可横向扩展 |

### 1.2 核心概念

| 概念 | 说明 |
|------|------|
| **Orchestrator** (主 Agent) | 接收用户请求，负责任务分析、拆分、分配、汇总的大脑 |
| **WorkerAgent** (子 Agent) | 负责执行具体任务的"工人"，专注单一领域，拥有独立会话 |
| **Task** (任务) | 最小的可执行单元，包含任务定义、参数、状态、结果 |
| **TaskGroup** (任务组) | 一组可并行执行的 Task 集合，有共同的 parent_task_id |
| **Dispatcher** (调度器) | 负责任务排队、分配、并发控制、负载均衡 |
| **Splitter** (拆分器) | 分析任务特性，决定是否拆分以及如何拆分成子任务 |
| **Merger** (合并器) | 收集子任务结果，按策略合并为最终结果 |

---

## 2. 架构总览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         TennineClaw 多 Agent 协同架构                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                     Orchestrator (主 Agent)                          │   │
│  │  ┌─────────────┐  ┌──────────────┐  ┌────────────┐  ┌───────────┐  │   │
│  │  │ TaskAnalyzer│  │ TaskSplitter │  │ ResultMerge│  │ Strategy  │  │   │
│  │  │ (任务分析器)  │  │ (任务拆分器)  │  │ (结果合并器) │  │ (策略引擎) │  │   │
│  │  └─────────────┘  └──────────────┘  └────────────┘  └───────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                                    ▼                                         │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                     TaskDispatcher (任务调度器)                       │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐  ┌──────────┐ │   │
│  │  │ TaskQueue    │  │ RouteTable   │  │ LoadBalance │  │ RetryMgr │ │   │
│  │  │ (任务队列)    │  │ (路由表)      │  │ (负载均衡)   │  │ (重试管理) │ │   │
│  │  └──────────────┘  └──────────────┘  └─────────────┘  └──────────┘ │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│         ┌──────────────────────────┼──────────────────────────┐              │
│         ▼                          ▼                          ▼              │
│  ┌──────────────┐          ┌──────────────┐          ┌──────────────┐       │
│  │  WorkerAgent │          │  WorkerAgent │          │  WorkerAgent │       │
│  │  (子Agent A)  │          │  (子Agent B)  │   ...    │  (子Agent N)  │       │
│  │  ┌──────────┐│          │  ┌──────────┐│          │  ┌──────────┐│       │
│  │  │ 专长:    ││          │  │ 专长:    ││          │  │ 专长:    ││       │
│  │  │ 文件操作  ││          │  │ Git操作  ││          │  │ 代码分析  ││       │
│  │  │ 命令执行  ││          │  │ 搜索     ││          │  │ 重构     ││       │
│  │  └──────────┘│          │  └──────────┘│          │  └──────────┘│       │
│  └──────────────┘          └──────────────┘          └──────────────┘       │
│                                    │                                         │
│                                    ▼                                         │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                  RegistryCenter (注册中心)                            │   │
│  │  管理所有 WorkerAgent 的注册信息、健康状态、能力声明                     │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    Monitor & Observer (监控观测)                      │   │
│  │  任务执行追踪 / 性能指标 / 调用链 / 日志审计                           │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.1 核心设计思路

```
用户请求
    │
    ▼
┌────────────────────────────────────────────────────┐
│ Orchestrator 主 Agent                              │
│                                                    │
│  ① analyze_task()   → 分析任务类型、复杂度、依赖     │
│  ② should_split()   → 判断是否需要拆分              │
│      ├── 不需要拆分 → 直接分配 dispatch()            │
│      └── 需要拆分   → split_task() → 生成 TaskGroup │
│  ③ dispatch_all()   → 将任务/任务组发给 Dispatcher  │
│  ④ wait_for_results() → 等待所有子任务完成           │
│  ⑤ merge_results()  → 策略性合并结果                 │
│  ⑥ 返回最终结果                                     │
└────────────────────────────────────────────────────┘
```

---

## 3. 核心数据结构

### 3.1 任务相关

```python
# ──── 任务状态枚举 ────
class TaskStatus(str, Enum):
    PENDING = "pending"           # 等待调度
    QUEUED = "queued"             # 已入队
    DISPATCHED = "dispatched"     # 已分派给子 Agent
    RUNNING = "running"           # 子 Agent 正在执行
    SUCCEEDED = "succeeded"       # 执行成功
    FAILED = "failed"             # 执行失败
    RETRYING = "retrying"         # 正在重试
    TIMEOUT = "timeout"           # 超时
    CANCELLED = "cancelled"       # 已取消
    MERGED = "merged"             # 已合并至父任务


class TaskPriority(int, Enum):
    LOW = 0
    MEDIUM = 1
    HIGH = 2
    CRITICAL = 3


# ──── 任务定义 ────
@dataclass
class Task:
    """
    任务：多 Agent 系统中的最小可执行单元。
    包含从创建到完成的全生命周期信息。
    """
    task_id: str                         # 全局唯一任务 ID (uuid)
    parent_task_id: Optional[str]        # 父任务 ID（子任务指向拆分它的父任务）
    group_id: Optional[str]              # 所属 TaskGroup ID
    name: str                            # 任务名称（简短描述）
    description: str                     # 任务详细描述

    # ── 执行信息 ──
    agent_type: str                      # 目标子 Agent 类型（如 "file_ops", "git_ops"）
    agent_id: Optional[str]              # 已分配的具体子 Agent ID
    payload: Dict[str, Any]              # 任务载荷（工具名、参数等）

    # ── 控制信息 ──
    priority: TaskPriority = TaskPriority.MEDIUM
    timeout_seconds: int = 60            # 超时时间
    max_retries: int = 2                 # 最大重试次数
    retry_delay_seconds: int = 2         # 重试间隔
    depends_on: List[str] = field(default_factory=list)  # 依赖的任务 ID 列表

    # ── 状态信息 ──
    status: TaskStatus = TaskStatus.PENDING
    retry_count: int = 0
    created_at: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_ms: Optional[int] = None    # 执行耗时

    # ── 结果信息 ──
    result: Optional[Any] = None         # 执行结果
    error: Optional[str] = None          # 错误信息
    result_summary: Optional[str] = None # 结果摘要（给 Merger 用）

    # ── 元信息 ──
    tags: Dict[str, str] = field(default_factory=dict)  # 标签（用于统计、过滤）
    metadata: Dict[str, Any] = field(default_factory=dict)  # 扩展元数据


@dataclass
class TaskGroup:
    """
    任务组：一组可并行执行的子任务集合。
    由 TaskSplitter 拆分产生，由 ResultMerger 合并消费。
    """
    group_id: str                        # 组唯一 ID
    parent_task_id: str                  # 产生该组的父任务 ID
    name: str                            # 组名称
    strategy: str                        # 合并策略: "all" | "first" | "majority" | "custom"
    tasks: List[Task]                    # 组内子任务列表
    status: str = "pending"              # "pending" | "running" | "partial" | "completed" | "failed"
    created_at: str = ""
    completed_at: Optional[str] = None

    # 合并控制
    merge_config: Dict[str, Any] = field(default_factory=lambda: {
        "require_all": True,             # 是否要求所有子任务都完成才合并
        "timeout_fallback": "partial",   # 超时后的降级策略: "partial" | "skip" | "error"
        "conflict_resolution": "latest", # 冲突解决: "latest" | "majority" | "priority"
    })
```

### 3.2 Agent 相关

```python
# ──── 子 Agent 能力声明 ────
@dataclass
class AgentCapability:
    """
    子 Agent 的能力声明：描述它能做什么、擅长什么。
    注册时声明，供 Orchestrator 的任务分配决策使用。
    """
    agent_type: str                      # Agent 类型标识（唯一）
    display_name: str                    # 显示名，如 "文件操作专家"
    description: str                     # 能力描述

    # 能力列表
    tools: List[str]                     # 支持的工具列表，如 ["read_file", "write_file"]
    skill_ids: List[str]                 # 关联的技能 ID 列表
    max_concurrency: int = 3             # 最大并发任务数
    supported_task_types: List[str]      # 支持的任务类型标签

    # 性能指标（动态更新）
    avg_duration_ms: float = 0.0         # 平均执行耗时
    success_rate: float = 1.0            # 成功率
    current_load: int = 0                # 当前任务数
    total_tasks_completed: int = 0       # 累计完成任务数

    # 配置
    system_prompt_template: str = ""     # System Prompt 模板
    model: str = ""                      # 使用的模型
    config_overrides: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentInstance:
    """
    子 Agent 运行时实例。
    每个实例对应一个独立的 AgentSession（拥有独立的 msgs、client、context）。
    """
    agent_id: str                        # 实例唯一 ID
    agent_type: str                      # 关联的 AgentCapability.agent_type
    status: str = "idle"                 # "idle" | "busy" | "error" | "offline"
    session: Any = None                  # AgentSession 实例（实际运行时）
    created_at: str = ""
    last_heartbeat: str = ""
    current_tasks: List[str] = field(default_factory=list)  # 正在执行的任务 ID
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### 3.3 调度相关

```python
@dataclass
class DispatchResult:
    """
    任务调度结果。
    """
    task_id: str
    status: str                          # "dispatched" | "queued" | "failed"
    agent_id: Optional[str] = None       # 分配到的子 Agent ID
    queue_position: Optional[int] = None # 队列位置（如已入队）
    estimated_wait_ms: Optional[int] = None  # 预计等待时间
    error: Optional[str] = None


@dataclass
class OrchestratorContext:
    """
    主 Agent 的一次执行上下文。
    记录一次用户请求的处理全链路。
    """
    context_id: str                      # 上下文 ID
    user_request: str                    # 原始用户请求
    root_task_id: str                    # 根任务 ID
    task_groups: Dict[str, TaskGroup] = field(default_factory=dict)  # 所有任务组
    all_tasks: Dict[str, Task] = field(default_factory=dict)        # 所有任务
    start_time: str = ""
    end_time: Optional[str] = None
    total_duration_ms: Optional[int] = None
    final_result: Optional[Any] = None
    trace_log: List[Dict] = field(default_factory=list)  # 调用链日志
```

---

## 4. Orchestrator — 主 Agent 引擎

### 4.1 主类设计

```python
class Orchestrator:
    """
    🧠 主 Agent 引擎 — 多 Agent 协同的大脑。
    
    职责：
    1. 分析用户请求，决定处理策略（直派/拆分/转交）
    2. 将任务/任务组交给 TaskDispatcher 调度
    3. 等待子任务完成，调用 ResultMerger 合并
    4. 管理 OrchestratorContext（一次请求的全生命周期）
    
    挂载在 AgentSession 上，作为 AgentSession.orchestrator 使用。
    """

    def __init__(self, session_id: str,
                 dispatcher: TaskDispatcher = None,
                 splitter: TaskSplitter = None,
                 merger: ResultMerger = None,
                 registry: RegistryCenter = None):
        """
        初始化主 Agent 引擎。

        Args:
            session_id: 当前会话 ID（用于关联日志）
            dispatcher: TaskDispatcher 实例（不传则自动创建默认实例）
            splitter:   TaskSplitter 实例（不传则自动创建）
            merger:     ResultMerger 实例（不传则自动创建）
            registry:   RegistryCenter 实例（不传则自动创建）

        初始化逻辑：
            1. 创建或接收各子模块实例
            2. 初始化任务上下文缓存 _contexts: Dict[str, OrchestratorContext]
            3. 初始化统计计数器
        """
        pass

    # ════════════════════════════════════════════
    # 核心入口
    # ════════════════════════════════════════════

    async def process_request(self, 
                              user_request: str,
                              context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        处理用户请求（核心入口方法）。

        Args:
            user_request: 用户原始请求文本
            context:      额外上下文（历史记录、当前会话状态等）

        Returns:
            Dict: {
                "final_result": Any,            # 最终结果
                "strategy": str,                # 使用的策略: "direct" | "parallel" | "mixed"
                "task_count": int,              # 总任务数
                "sub_agent_count": int,         # 参与的子 Agent 数
                "total_duration_ms": int,       # 总耗时
                "trace_id": str,                # 追踪 ID
                "summary": str,                 # 简要说明
                "details": Dict,                # 详细结果（可选）
            }

        完整执行流程：
            1. 创建 OrchestratorContext
            2. 调用 analyze_request() 分析请求
            3. 调用 decide_strategy() 决策策略
            4. 根据策略分支:
               ├─ "direct"    → 直接 dispatch_single_task()
               ├─ "parallel"  → split_task() → dispatch_group() → merge_results()
               └─ "mixed"     → 混合模式
            5. 记录追踪日志
            6. 返回最终结果
        """
        pass

    async def process_multi_request(self,
                                    requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        批量处理多个独立请求（每个请求可独立分配子 Agent）。

        Args:
            requests: 请求列表，每项: { "request": str, "context": dict }

        Returns:
            List[Dict]: 每个请求的处理结果列表
        """
        pass

    # ════════════════════════════════════════════
    # 任务分析
    # ════════════════════════════════════════════

    def analyze_request(self, 
                        user_request: str,
                        context: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析用户请求，提取任务特征。

        Args:
            user_request: 用户请求文本
            context:      额外上下文

        Returns:
            Dict: {
                "task_type": str,               # 任务类型: "file_ops" | "git_ops" | "code_analysis" | "mixed"
                "complexity": float,            # 复杂度评分 0.0~1.0
                "estimated_difficulty": str,    # "easy" | "medium" | "hard"
                "required_tools": List[str],    # 需要的工具列表
                "required_skills": List[str],   # 需要的技能列表
                "subtasks_hint": List[str],     # 潜在的子任务提示
                "parallelizable": bool,         # 是否可并行
                "estimated_steps": int,         # 预估执行步骤数
                "dependencies": List[str],      # 依赖的外部资源
            }

        分析策略：
            - 关键词匹配 + 语义分析（调用 LLM 做意图识别）
            - 统计历史类似任务的执行数据
            - 参考 Skill 技能系统的技能等级（高等级技能对应低复杂度）
        """
        pass

    def decide_strategy(self, 
                        analysis: Dict[str, Any]) -> str:
        """
        根据任务分析结果决策执行策略。

        Args:
            analysis: analyze_request() 的分析结果

        Returns:
            str: 策略名称
                "direct"   — 直接分配（简单任务，单 Agent 即可）
                "parallel" — 并行拆分（可拆分为 n 个并行子任务）
                "pipeline" — 流水线（子任务有依赖关系，串行执行）
                "mixed"    — 混合模式（部分并行 + 部分串行）
                "delegate" — 全权委托（完整交给一个子 Agent）

        决策规则：
            - 只有一个工具调用 → "direct"
            - 多工具调用且无依赖 → "parallel"
            - 多工具调用且有依赖链 → "pipeline"
            - 复杂度 > 0.7 且涉及多个领域 → "mixed"
            - 已有高度匹配的子 Agent → "delegate"
        """
        pass

    # ════════════════════════════════════════════
    # 任务拆分
    # ════════════════════════════════════════════

    def should_split(self, 
                     analysis: Dict[str, Any],
                     strategy: str) -> bool:
        """
        判断是否需要将任务拆分为子任务。

        Args:
            analysis: 任务分析结果
            strategy: 选定的策略

        Returns:
            bool: True 表示需要拆分

        判断条件（满足任一即可）：
            1. strategy 为 "parallel" 或 "pipeline" 或 "mixed"
            2. estimated_steps > 3
            3. 涉及 2 个以上不同类型的工具
            4. 复杂度 > 0.6
            5. 存在可识别的子任务提示
        """
        pass

    async def split_task(self, 
                         task: Task,
                         analysis: Dict[str, Any]) -> TaskGroup:
        """
        将任务拆分为多个子任务（调用 TaskSplitter）。

        Args:
            task:     要拆分的父任务
            analysis: 任务分析结果

        Returns:
            TaskGroup: 包含多个子任务的任务组
        """
        pass

    # ════════════════════════════════════════════
    # 任务分发
    # ════════════════════════════════════════════

    async def dispatch_task(self, 
                            task: Task) -> DispatchResult:
        """
        分发单个任务给子 Agent（调用 TaskDispatcher）。

        Args:
            task: 要分发的任务

        Returns:
            DispatchResult: 分发结果
        """
        pass

    async def dispatch_group(self, 
                             group: TaskGroup) -> List[Dict[str, Any]]:
        """
        分发整个任务组（所有子任务并行下发）。

        Args:
            group: 任务组

        Returns:
            List[Dict]: 每个子任务的分发结果列表

        说明：
            - 组内无依赖的任务同时下发
            - 组内有依赖的任务按依赖顺序分批下发
        """
        pass

    # ════════════════════════════════════════════
    # 结果收集与合并
    # ════════════════════════════════════════════

    async def wait_for_task(self, 
                            task_id: str,
                            timeout: int = None) -> Task:
        """
        等待单个任务完成（阻塞/异步等待）。

        Args:
            task_id: 任务 ID
            timeout: 超时秒数，默认使用 Task.timeout_seconds

        Returns:
            Task: 已完成的任务（含 result 或 error）

        说明：
            - 通过事件/回调机制等待，非轮询
            - 超时后任务状态变为 TIMEOUT
        """
        pass

    async def wait_for_group(self, 
                             group: TaskGroup,
                             timeout: int = None) -> TaskGroup:
        """
        等待任务组中所有子任务完成。

        Args:
            group:   任务组
            timeout: 整体超时

        Returns:
            TaskGroup: 所有子任务已完成（或超时/失败的）任务组
        """
        pass

    async def merge_results(self, 
                            group: TaskGroup,
                            parent_task: Task) -> Any:
        """
        合并任务组中的子任务结果（调用 ResultMerger）。

        Args:
            group:       已完成的任务组
            parent_task: 父任务（原始请求）

        Returns:
            Any: 合并后的最终结果

        说明：
            - 根据 TaskGroup.strategy 选择合并策略
            - 支持 partial 降级（部分子任务失败时仍可汇总）
        """
        pass

    # ════════════════════════════════════════════
    # 上下文管理
    # ════════════════════════════════════════════

    def create_context(self, 
                       user_request: str) -> OrchestratorContext:
        """
        创建一个新的执行上下文。

        Args:
            user_request: 用户请求

        Returns:
            OrchestratorContext
        """
        pass

    def get_context(self, 
                    context_id: str) -> Optional[OrchestratorContext]:
        """
        获取执行上下文。

        Args:
            context_id: 上下文 ID

        Returns:
            OrchestratorContext | None
        """
        pass

    def close_context(self, 
                      context_id: str) -> Dict:
        """
        关闭执行上下文，生成总结报告。

        Args:
            context_id: 上下文 ID

        Returns:
            Dict: 上下文总结报告（含耗时、任务数、成功/失败统计）
        """
        pass

    # ════════════════════════════════════════════
    # 追踪与日志
    # ════════════════════════════════════════════

    def log_event(self, 
                  context_id: str,
                  event_type: str,
                  data: Dict[str, Any]):
        """
        记录追踪事件。

        Args:
            context_id: 上下文 ID
            event_type: 事件类型: "task_created" | "task_dispatched" | 
                        "task_completed" | "task_failed" | "merge_start" | "merge_done"
            data:       事件数据
        """
        pass

    def get_trace(self, 
                  context_id: str) -> List[Dict]:
        """
        获取完整的调用链追踪记录。

        Args:
            context_id: 上下文 ID

        Returns:
            List[Dict]: 按时间排序的事件列表
        """
        pass

    # ════════════════════════════════════════════
    # 统计与监控
    # ════════════════════════════════════════════

    def get_stats(self) -> Dict[str, Any]:
        """
        获取主 Agent 的统计信息。

        Returns:
            Dict: {
                "total_requests": int,
                "avg_duration_ms": int,
                "strategy_distribution": Dict[str, int],  # 各策略使用次数
                "success_rate": float,
                "avg_sub_agents_per_request": float,
                "avg_tasks_per_request": float,
            }
        """
        pass
```

### 4.2 策略决策引擎

```python
class StrategyEngine:
    """
    策略决策引擎：根据任务分析结果、系统负载、子 Agent 状态，
    智能决定最优执行策略。
    """

    def __init__(self, registry: RegistryCenter):
        """
        Args:
            registry: 注册中心（用于获取子 Agent 信息）
        """
        pass

    def decide(self, 
               analysis: Dict[str, Any],
               system_load: Dict[str, Any]) -> str:
        """
        决策执行策略。

        Args:
            analysis:    任务分析结果
            system_load: 系统负载信息（当前排队任务数、子 Agent 空闲率等）

        Returns:
            str: 策略名称

        决策树：
            1. 只有一个工具调用 → "direct"
            2. 存在匹配的子 Agent 且 analysis['parallelizable']=True → "parallel"
            3. 存在依赖链 → "pipeline"
            4. 涉及 3+ 个不同领域 → "mixed"
            5. 子 Agent 负载 > 0.8 → 减少并行度或排队
            6. 兜底 → "direct"
        """
        pass

    def estimate_parallelism(self, 
                             analysis: Dict[str, Any],
                             available_agents: int) -> int:
        """
        估算最优并行度。

        Args:
            analysis:         任务分析结果
            available_agents: 可用子 Agent 数

        Returns:
            int: 建议的并行任务数（1 ~ available_agents）

        估算公式：
            parallelism = min(
                available_agents,
                analysis['estimated_steps'],
                max(1, int(analysis['complexity'] * 5))
            )
        """
        pass

    def estimate_duration(self, 
                          task: Task,
                          strategy: str) -> int:
        """
        预估任务执行耗时（用于超时设置和进度提示）。

        Args:
            task:     任务
            strategy: 执行策略

        Returns:
            int: 预估毫秒数
        """
        pass
```

---

## 5. WorkerAgent — 子 Agent 实现

### 5.1 子 Agent 基类

```python
class WorkerAgent:
    """
    👷 子 Agent 基类 — 所有子 Agent 的抽象基类。
    
    职责：
    1. 接收 Task，在独立的 AgentSession 中执行
    2. 将执行结果封装返回
    3. 上报心跳和健康状态
    4. 支持取消和超时
    """

    def __init__(self, 
                 agent_id: str,
                 capability: AgentCapability,
                 parent_session_id: str = None):
        """
        初始化子 Agent。

        Args:
            agent_id:          Agent 实例 ID
            capability:        能力声明
            parent_session_id: 关联的主会话 ID（用于日志关联）
        """
        pass

    # ════════════════════════════════════════════
    # 核心执行流程
    # ════════════════════════════════════════════

    async def execute_task(self, task: Task) -> Task:
        """
        执行一个任务（核心方法）。

        Args:
            task: 待执行的任务（含 payload）

        Returns:
            Task: 执行完成后的任务（含 result 或 error）

        执行流程：
            1. 更新 task.status = RUNNING
            2. 根据 task.payload 解析执行方案
            3. 调用 AgentSession 中的工具执行
            4. 若执行成功 → task.status = SUCCEEDED, task.result = ...
            5. 若执行失败 → task.status = FAILED, task.error = ...
            6. 计算耗时 task.duration_ms
            7. 回调通知 Orchestrator
            8. 返回更新后的 task
        """
        pass

    async def execute_tool_call(self, 
                                tool_name: str,
                                tool_params: Dict[str, Any]) -> Any:
        """
        在子 Agent 的会话中执行一个工具调用。

        Args:
            tool_name:   工具名
            tool_params: 工具参数

        Returns:
            Any: 工具执行结果
        """
        pass

    async def execute_multi_tool(self, 
                                 tool_calls: List[Dict[str, Any]]) -> List[Any]:
        """
        按顺序执行多个工具调用（串行）。

        Args:
            tool_calls: 工具调用列表
                [{ "tool_name": str, "params": dict }]

        Returns:
            List[Any]: 每个工具的执行结果列表
        """
        pass

    # ════════════════════════════════════════════
    # 生命周期管理
    # ════════════════════════════════════════════

    async def start(self):
        """
        启动子 Agent（初始化 AgentSession，建立连接）。
        """
        pass

    async def shutdown(self):
        """
        关闭子 Agent（释放资源，保存状态）。
        """
        pass

    async def cancel_task(self, task_id: str) -> bool:
        """
        取消正在执行的任务。

        Args:
            task_id: 任务 ID

        Returns:
            bool: 是否成功取消
        """
        pass

    def is_busy(self) -> bool:
        """
        判断子 Agent 是否忙碌。

        Returns:
            bool: True 表示正在执行任务
        """
        pass

    def current_load(self) -> int:
        """
        获取当前负载（正在执行的任务数）。

        Returns:
            int: 当前任务数
        """
        pass

    # ════════════════════════════════════════════
    # 心跳与健康检查
    # ════════════════════════════════════════════

    async def heartbeat(self) -> Dict[str, Any]:
        """
        上报心跳信息。

        Returns:
            Dict: {
                "agent_id": str,
                "status": str,
                "current_load": int,
                "memory_usage": float,
                "uptime_seconds": int,
                "timestamp": str,
            }
        """
        pass

    def health_check(self) -> Dict[str, Any]:
        """
        健康自检。

        Returns:
            Dict: {
                "healthy": bool,
                "status": str,
                "last_error": str | None,
                "consecutive_failures": int,
            }
        """
        pass

    # ════════════════════════════════════════════
    # 结果回调
    # ════════════════════════════════════════════

    async def on_task_completed(self, task: Task):
        """
        任务完成时的回调（通知 Orchestrator）。

        Args:
            task: 已完成的任务
        """
        pass

    async def on_task_failed(self, task: Task, error: Exception):
        """
        任务失败时的回调。

        Args:
            task:  失败的任务
            error: 异常信息
        """
        pass
```

### 5.2 内置子 Agent 类型

```python
# ──── 内置子 Agent 注册定义 ────

# ═══ 文件操作子 Agent ═══
WORKER_FILE_OPS = AgentCapability(
    agent_type="file_ops",
    display_name="📁 文件操作专家",
    description="专门负责文件的读取、写入、搜索、替换等操作",
    tools=["read_file", "write_file", "delete_file", "search_files", 
           "list_files", "create_directory", "find_files", "grep", "replace"],
    skill_ids=["skill_file_ops", "skill_search_ops"],
    max_concurrency=3,
    supported_task_types=["file_read", "file_write", "file_search", "file_grep"],
    system_prompt_template="""
你是一个专注于文件操作的子 Agent。
你的职责是高效、准确地执行文件操作任务。
请直接执行，不需要额外解释。
当前任务: {task_description}
    """,
)

# ═══ Git 操作子 Agent ═══
WORKER_GIT_OPS = AgentCapability(
    agent_type="git_ops",
    display_name="🔀 Git 操作专家",
    description="专门负责 Git 仓库的状态查询、日志查看、差异比较等",
    tools=["git_status", "git_log", "git_diff", "git_commit_stats"],
    skill_ids=["skill_git_ops"],
    max_concurrency=2,
    supported_task_types=["git_status", "git_log", "git_diff", "git_stats"],
    system_prompt_template="""
你是一个专注于 Git 版本控制的子 Agent。
你的职责是执行 Git 相关操作并返回结构化结果。
当前任务: {task_description}
    """,
)

# ═══ 命令执行子 Agent ═══
WORKER_CMD_EXEC = AgentCapability(
    agent_type="cmd_exec",
    display_name="⚡ 命令执行专家",
    description="专门负责执行系统命令、运行脚本、环境管理",
    tools=["run_cmd"],
    skill_ids=["skill_cmd_exec"],
    max_concurrency=3,
    supported_task_types=["cmd_exec", "script_run", "env_query"],
    system_prompt_template="""
你是一个专注于系统命令执行的子 Agent。
请安全、高效地执行命令任务。
注意：始终检查命令安全性。
当前任务: {task_description}
    """,
)

# ═══ 代码分析子 Agent ═══
WORKER_CODE_ANALYSIS = AgentCapability(
    agent_type="code_analysis",
    display_name="🔍 代码分析专家",
    description="专门负责代码分析、Bug 检测、重构建议",
    tools=["read_file", "grep", "count_lines", "find_files", "diff"],
    skill_ids=["skill_code_analysis", "skill_debug_detection", "skill_project_insight"],
    max_concurrency=2,
    supported_task_types=["code_analysis", "bug_detection", "code_review", "refactor_plan"],
    system_prompt_template="""
你是一个专注于代码分析的专业子 Agent。
你可以阅读代码、分析结构、发现潜在问题。
请提供结构化的分析结果。
当前任务: {task_description}
    """,
)

# ═══ 信息查询子 Agent ═══
WORKER_INFO_QUERY = AgentCapability(
    agent_type="info_query",
    display_name="ℹ️ 信息查询专家",
    description="专门负责系统信息、时间查询、配置查看等",
    tools=["get_system_info", "get_current_time", "read_file"],
    skill_ids=[],
    max_concurrency=5,
    supported_task_types=["system_info", "time_query", "config_query"],
    system_prompt_template="""
你是一个专注于信息查询的子 Agent。
请快速、准确地返回查询结果。
当前任务: {task_description}
    """,
)


# ─── 所有内置子 Agent 的注册表 ───
BUILTIN_WORKER_AGENTS: Dict[str, AgentCapability] = {
    "file_ops":       WORKER_FILE_OPS,
    "git_ops":        WORKER_GIT_OPS,
    "cmd_exec":       WORKER_CMD_EXEC,
    "code_analysis":  WORKER_CODE_ANALYSIS,
    "info_query":     WORKER_INFO_QUERY,
}
```

---

## 6. TaskDispatcher — 任务调度器

### 6.1 调度器设计

```python
class TaskDispatcher:
    """
    📤 任务调度器 — 负责任务的排队、分发、并发控制、负载均衡。
    
    职责：
    1. 维护任务队列（按优先级排序）
    2. 根据子 Agent 负载智能分配任务
    3. 管理并发上限（全局 + 每 Agent）
    4. 支持任务取消和重新排队
    """

    def __init__(self, 
                 registry: RegistryCenter,
                 max_global_concurrency: int = 10,
                 queue_timeout: int = 300):
        """
        Args:
            registry:               注册中心
            max_global_concurrency: 全局最大并发数
            queue_timeout:          队列超时（超过此时间未调度则失败）
        """
        self._queue = TaskQueue()          # 优先级队列
        self._active_tasks: Dict[str, Task] = {}  # 正在执行的任务
        self._max_global_concurrency = max_global_concurrency
        self._queue_timeout = queue_timeout
        pass

    # ════════════════════════════════════════════
    # 核心调度
    # ════════════════════════════════════════════

    async def dispatch(self, task: Task) -> DispatchResult:
        """
        调度一个任务（核心入口）。

        Args:
            task: 待调度任务

        Returns:
            DispatchResult

        调度流程：
            1. 检查全局并发是否已满
            2. 通过 RegistryCenter 查找匹配的子 Agent
            3. 通过 LoadBalancer 选择最优的子 Agent
            4. 如果目标 Agent 有空闲槽位 → 立即分发
            5. 如果没有空闲槽位 → 入队等待
            6. 设置超时定时器
        """
        pass

    async def dispatch_batch(self, 
                             tasks: List[Task]) -> List[DispatchResult]:
        """
        批量调度多个任务（无依赖的任务可同时分发）。

        Args:
            tasks: 任务列表

        Returns:
            List[DispatchResult]: 每个任务的分发结果
        """
        pass

    async def dispatch_group(self, 
                             group: TaskGroup) -> Dict[str, DispatchResult]:
        """
        调度一个任务组（按依赖关系分批分发）。

        Args:
            group: 任务组

        Returns:
            Dict[str, DispatchResult]: task_id → DispatchResult
        """
        pass

    # ════════════════════════════════════════════
    # 队列管理
    # ════════════════════════════════════════════

    def enqueue(self, task: Task) -> bool:
        """
        将任务加入等待队列。

        Args:
            task: 待入队任务

        Returns:
            bool: 入队是否成功
        """
        pass

    def dequeue(self) -> Optional[Task]:
        """
        从队列中取出优先级最高的任务。

        Returns:
            Task | None: 队列为空返回 None
        """
        pass

    def cancel(self, task_id: str) -> bool:
        """
        取消队列中的任务。

        Args:
            task_id: 任务 ID

        Returns:
            bool: 是否成功取消
        """
        pass

    def get_queue_length(self) -> int:
        """
        获取当前队列长度。

        Returns:
            int
        """
        pass

    def get_queue_status(self) -> Dict[str, Any]:
        """
        获取队列状态信息。

        Returns:
            Dict: {
                "queued_count": int,
                "active_count": int,
                "estimated_wait_ms": int,
                "oldest_task_waiting_ms": int,
            }
        """
        pass

    # ════════════════════════════════════════════
    # 任务状态管理
    # ════════════════════════════════════════════

    def mark_completed(self, task_id: str):
        """
        标记任务完成（从活跃列表中移除）。

        Args:
            task_id: 任务 ID
        """
        pass

    def mark_failed(self, task_id: str, error: str):
        """
        标记任务失败。

        Args:
            task_id: 任务 ID
            error:   错误信息
        """
        pass

    def get_active_tasks(self) -> List[Task]:
        """
        获取所有正在执行的任务。

        Returns:
            List[Task]
        """
        pass

    # ════════════════════════════════════════════
    # 并发控制
    # ════════════════════════════════════════════

    def can_dispatch(self) -> bool:
        """
        检查是否还可以分发新任务（全局并发限制）。

        Returns:
            bool
        """
        pass

    def get_available_slots(self) -> int:
        """
        获取剩余可用并发槽位。

        Returns:
            int: max_global_concurrency - len(active_tasks)
        """
        pass
```

### 6.2 负载均衡器

```python
class LoadBalancer:
    """
    ⚖️ 负载均衡器 — 从可用的子 Agent 中选出最优的一个。
    
    支持的策略：
    - "round_robin":    轮询
    - "least_load":     最少负载优先
    - "fastest":        最快响应优先
    - "highest_success":最高成功率优先
    - "affinity":       亲和性（优先分配给上次处理过同类任务的 Agent）
    """

    def __init__(self, registry: RegistryCenter, strategy: str = "least_load"):
        """
        Args:
            registry: 注册中心
            strategy: 负载均衡策略
        """
        pass

    def select(self, 
               task: Task,
               candidates: List[AgentInstance]) -> Optional[AgentInstance]:
        """
        从候选子 Agent 中选择最优的一个。

        Args:
            task:       待分配任务
            candidates: 候选子 Agent 列表（同类型）

        Returns:
            AgentInstance | None: 选中的子 Agent，无可用返回 None
        """
        pass

    def select_by_least_load(self, 
                             candidates: List[AgentInstance]) -> AgentInstance:
        """
        最少负载策略。

        Args:
            candidates: 候选列表

        Returns:
            AgentInstance: current_load 最小的
        """
        pass

    def select_by_fastest(self, 
                          candidates: List[AgentInstance]) -> AgentInstance:
        """
        最快响应策略。

        Args:
            candidates: 候选列表

        Returns:
            AgentInstance: avg_duration_ms 最小的
        """
        pass

    def select_by_round_robin(self, 
                              candidates: List[AgentInstance]) -> AgentInstance:
        """
        轮询策略。
        """
        pass

    def select_by_affinity(self, 
                           task: Task,
                           candidates: List[AgentInstance]) -> AgentInstance:
        """
        亲和性策略（优先选上次处理过同类任务的 Agent）。

        Args:
            task:        任务
            candidates:  候选列表

        Returns:
            AgentInstance
        """
        pass

    def set_strategy(self, strategy: str):
        """
        切换负载均衡策略。

        Args:
            strategy: 策略名
        """
        pass
```

### 6.3 任务队列

```python
class TaskQueue:
    """
    📋 优先级任务队列 — 支持优先级排序、超时检测、取消。
    内部基于 heapq 实现，优先级高的任务先出队。
    """

    def __init__(self):
        pass

    def push(self, task: Task):
        """
        将任务入队（按优先级插入）。

        Args:
            task: 待入队任务
        """
        pass

    def pop(self) -> Optional[Task]:
        """
        取出优先级最高的任务。

        Returns:
            Task | None
        """
        pass

    def peek(self) -> Optional[Task]:
        """
        查看优先级最高的任务（不移除）。

        Returns:
            Task | None
        """
        pass

    def remove(self, task_id: str) -> bool:
        """
        从队列中移除指定任务。

        Args:
            task_id: 任务 ID

        Returns:
            bool: 是否找到并移除
        """
        pass

    def get_all(self) -> List[Task]:
        """
        获取队列中所有任务（按优先级排序）。

        Returns:
            List[Task]
        """
        pass

    def size(self) -> int:
        """
        获取队列长度。

        Returns:
            int
        """
        pass

    def is_empty(self) -> bool:
        """
        队列是否为空。

        Returns:
            bool
        """
        pass
```

---

## 7. TaskSplitter — 任务拆分引擎

```python
class TaskSplitter:
    """
    🔪 任务拆分引擎 — 将复杂任务拆分为可并行/可串行的子任务集合。
    
    拆分策略：
    - "by_tool":       按工具类型拆分（read_file + git_status → 2个子任务）
    - "by_file":       按文件拆分（分析多个文件 → 每个文件一个子任务）
    - "by_step":       按执行步骤拆分（先查后改 → 2个阶段子任务）
    - "by_domain":     按领域拆分（代码分析 + Git提交 → 分配到不同 Agent）
    - "llm_guided":    LLM 引导拆分（调用 LLM 分析最佳拆分方案）
    """

    def __init__(self, registry: RegistryCenter, llm_client=None):
        """
        Args:
            registry:   注册中心（用于识别可用的 Agent 类型）
            llm_client: LLM 客户端（用于 llm_guided 策略）
        """
        pass

    # ════════════════════════════════════════════
    # 核心方法
    # ════════════════════════════════════════════

    async def split(self, 
                    task: Task,
                    analysis: Dict[str, Any],
                    strategy: str = "auto") -> TaskGroup:
        """
        将任务拆分为子任务组（核心方法）。

        Args:
            task:     父任务
            analysis: 任务分析结果
            strategy: 拆分策略: "auto" | "by_tool" | "by_file" | "by_step" | "by_domain" | "llm_guided"

        Returns:
            TaskGroup: 拆分后的任务组

        流程：
            1. 根据 strategy 选择具体的拆分方法
            2. 生成多个子 Task
            3. 设置子任务的 parent_task_id、group_id
            4. 分析子任务之间的依赖关系
            5. 返回 TaskGroup
        """
        pass

    async def split_by_tool(self, 
                            task: Task,
                            analysis: Dict[str, Any]) -> TaskGroup:
        """
        按工具类型拆分：每个工具调用拆成一个子任务。

        示例：
            用户请求 "查一下 Git 状态，再看看当前目录结构"
            → 子任务1: { tool: "git_status" } → git_ops Agent
            → 子任务2: { tool: "list_files" } → file_ops Agent
        """
        pass

    async def split_by_file(self, 
                            task: Task,
                            files: List[str]) -> TaskGroup:
        """
        按文件拆分：处理多个文件时，每个文件拆成一个子任务。

        示例：
            用户请求 "分析 src/ 下所有 Python 文件"
            → 子任务1: 分析 a.py → code_analysis Agent
            → 子任务2: 分析 b.py → code_analysis Agent
            → 子任务3: 分析 c.py → code_analysis Agent
            三个子任务并行执行！
        """
        pass

    async def split_by_step(self, 
                            task: Task,
                            steps: List[Dict]) -> TaskGroup:
        """
        按执行步骤拆分：具有先后依赖关系的步骤拆分。

        示例：
            用户请求 "找出代码中的 Bug 并修复"
            → 阶段1（子任务1）: 检测 Bug → code_analysis Agent
            → 阶段2（子任务2，依赖阶段1）: 修复 Bug → file_ops Agent
            阶段1 完成后才执行阶段2
        """
        pass

    async def split_by_domain(self, 
                              task: Task,
                              analysis: Dict[str, Any]) -> TaskGroup:
        """
        按领域拆分：跨领域任务按专业领域拆分。

        示例：
            用户请求 "检查项目健康度"
            → 子任务1: Git 提交分析 → git_ops Agent
            → 子任务2: 代码质量分析 → code_analysis Agent
            → 子任务3: 项目结构分析 → file_ops Agent
            三个子任务完全并行！
        """
        pass

    async def split_by_llm(self, 
                           task: Task,
                           analysis: Dict[str, Any]) -> TaskGroup:
        """
        LLM 引导拆分：让 LLM 分析最佳拆分方案。

        流程：
            1. 将任务描述 + 可用子 Agent 列表发给 LLM
            2. LLM 返回拆分子任务的 JSON 方案
            3. 解析 JSON 并生成 TaskGroup
        """
        pass

    # ════════════════════════════════════════════
    # 辅助方法
    # ════════════════════════════════════════════

    def detect_parallelizable_patterns(self, 
                                       task: Task,
                                       analysis: Dict[str, Any]) -> List[Dict]:
        """
        检测任务中可并行的模式。

        Args:
            task:     父任务
            analysis: 分析结果

        Returns:
            List[Dict]: 检测到的并行模式列表
                [{ "pattern_type": str, "confidence": float, "suggested_split": ... }]
        """
        pass

    def detect_dependencies(self, 
                            subtasks: List[Task]) -> List[Tuple[str, str]]:
        """
        检测子任务之间的依赖关系。

        Args:
            subtasks: 子任务列表

        Returns:
            List[Tuple[str, str]]: 依赖边列表 [(依赖方task_id, 被依赖方task_id)]

        检测逻辑：
            - 如果子任务A的输出是子任务B的输入 → A→B 依赖
            - 如果子任务B需要在子任务A之后执行 → A→B 依赖（如先读后写）
        """
        pass

    def estimate_speedup(self, 
                         original_task: Task,
                         group: TaskGroup) -> float:
        """
        估算拆分后的加速比。

        Args:
            original_task: 原始任务
            group:         拆分后的任务组

        Returns:
            float: 预估加速比（如 2.5 表示预估快 2.5 倍）
        """
        pass

    def generate_task_name(self, 
                           index: int,
                           tool_name: str,
                           description: str) -> str:
        """
        生成子任务的名称。

        Args:
            index:       序号
            tool_name:   工具名
            description: 描述

        Returns:
            str: 如 "子任务#2 — git_status 查询仓库状态"
        """
        pass
```

---

## 8. ResultMerger — 结果合并引擎

```python
class ResultMerger:
    """
    🧩 结果合并引擎 — 将多个子任务的结果按策略合并为最终结果。
    
    合并策略：
    - "concatenate":  直接拼接（适用于无冲突的信息收集）
    - "summarize":    智能摘要（适用于大量信息的浓缩）
    - "vote":         投票（适用于多个 Agent 对同一问题的判断）
    - "priority":     优先级（按 Agent 优先级取结果）
    - "latest":       最新覆盖（相同 key 取最新）
    - "structured":   结构化合并（按 JSON Schema 合并）
    - "llm_merge":    LLM 引导合并（让 LLM 做最终汇总）
    """

    def __init__(self, llm_client=None):
        """
        Args:
            llm_client: LLM 客户端（用于 llm_merge 策略）
        """
        pass

    # ════════════════════════════════════════════
    # 核心方法
    # ════════════════════════════════════════════

    async def merge(self, 
                    group: TaskGroup,
                    parent_task: Task,
                    strategy: str = None) -> Any:
        """
        合并任务组中的所有子任务结果（核心方法）。

        Args:
            group:       已完成的任务组
            parent_task: 父任务（原始请求）
            strategy:    合并策略，默认使用 group.strategy

        Returns:
            Any: 合并后的结果

        流程：
            1. 收集所有子任务的结果
            2. 过滤失败的任务（根据降级策略决定是否包含）
            3. 按 strategy 选择合并方法
            4. 执行合并
            5. 返回合并结果
        """
        pass

    async def merge_concatenate(self, 
                                tasks: List[Task]) -> str:
        """
        拼接合并：将所有子任务结果按顺序拼接。

        Args:
            tasks: 子任务列表（按 task_id 或优先级排序）

        Returns:
            str: 拼接后的完整文本
        """
        pass

    async def merge_summarize(self, 
                              tasks: List[Task],
                              max_length: int = 2000) -> str:
        """
        摘要合并：对大量信息进行智能摘要。

        Args:
            tasks:      子任务列表
            max_length: 摘要最大长度

        Returns:
            str: 摘要文本
        """
        pass

    async def merge_vote(self, 
                         tasks: List[Task]) -> Any:
        """
        投票合并：多个 Agent 对同一问题的结果投票。

        Args:
            tasks: 子任务列表（每个子任务是对同一问题的判断）

        Returns:
            Any: 投票结果（多数一致的结论）
        """
        pass

    async def merge_priority(self, 
                             tasks: List[Task],
                             priority_map: Dict[str, int]) -> Any:
        """
        优先级合并：按 Agent 优先级取最高优先级的结果。

        Args:
            tasks:        子任务列表
            priority_map: Agent 类型→优先级的映射

        Returns:
            Any: 最高优先级的 Agent 结果
        """
        pass

    async def merge_structured(self, 
                               tasks: List[Task],
                               schema: Dict) -> Dict:
        """
        结构化合并：按照预定义的 JSON Schema 合并。

        Args:
            tasks:  子任务列表
            schema: JSON Schema 定义

        Returns:
            Dict: 符合 Schema 的合并结果
        """
        pass

    async def merge_by_llm(self, 
                           tasks: List[Task],
                           parent_task: Task) -> str:
        """
        LLM 引导合并：让 LLM 阅读所有子任务结果，生成最终汇总。

        Args:
            tasks:       子任务列表
            parent_task: 父任务（原始请求作为上下文）

        Returns:
            str: LLM 生成的汇总结果
        """
        pass

    # ════════════════════════════════════════════
    # 辅助方法
    # ════════════════════════════════════════════

    def filter_successful(self, 
                          tasks: List[Task]) -> List[Task]:
        """
        筛选出执行成功的任务。

        Args:
            tasks: 任务列表

        Returns:
            List[Task]: status == SUCCEEDED 的任务
        """
        pass

    def detect_conflicts(self, 
                         tasks: List[Task]) -> List[Dict]:
        """
        检测子任务结果之间的冲突。

        Args:
            tasks: 任务列表

        Returns:
            List[Dict]: 冲突描述列表
                [{ "key": str, "values": List, "severity": str }]
        """
        pass

    def resolve_conflicts(self, 
                          conflicts: List[Dict],
                          resolution: str = "latest") -> Dict:
        """
        解决结果冲突。

        Args:
            conflicts:  冲突列表
            resolution: 解决策略: "latest" | "majority" | "trust"

        Returns:
            Dict: 解决后的结果
        """
        pass
```

---

## 9. RegistryCenter — 子 Agent 注册中心

```python
class RegistryCenter:
    """
    📚 子 Agent 注册中心 — 管理所有子 Agent 的注册、发现、健康监控。
    
    职责：
    1. 子 Agent 的注册与注销
    2. 按类型/能力查找子 Agent
    3. 健康状态监控与心跳检测
    4. 能力匹配（任务 → Agent）
    """

    def __init__(self, heartbeat_interval: int = 30):
        """
        Args:
            heartbeat_interval: 心跳检测间隔（秒）
        """
        self._capabilities: Dict[str, AgentCapability] = {}     # agent_type → 能力
        self._instances: Dict[str, AgentInstance] = {}          # agent_id → 实例
        self._type_to_instances: Dict[str, List[str]] = {}      # agent_type → [agent_id]
        pass

    # ════════════════════════════════════════════
    # 注册与注销
    # ════════════════════════════════════════════

    def register_capability(self, capability: AgentCapability) -> bool:
        """
        注册一种子 Agent 类型的能力声明。

        Args:
            capability: 能力声明

        Returns:
            bool: 是否成功（已存在的 agent_type 会失败）
        """
        pass

    def unregister_capability(self, agent_type: str) -> bool:
        """
        注销一种子 Agent 类型。

        Args:
            agent_type: Agent 类型

        Returns:
            bool: 是否成功
        """
        pass

    def register_instance(self, instance: AgentInstance) -> bool:
        """
        注册一个子 Agent 运行时实例。

        Args:
            instance: 子 Agent 实例

        Returns:
            bool: 是否成功
        """
        pass

    def unregister_instance(self, agent_id: str) -> bool:
        """
        注销一个子 Agent 实例。

        Args:
            agent_id: 实例 ID

        Returns:
            bool: 是否成功
        """
        pass

    # ════════════════════════════════════════════
    # 发现与查找
    # ════════════════════════════════════════════

    def find_agents_by_type(self, 
                            agent_type: str) -> List[AgentInstance]:
        """
        按类型查找所有可用的子 Agent 实例。

        Args:
            agent_type: Agent 类型

        Returns:
            List[AgentInstance]: 可用实例列表
        """
        pass

    def find_agents_by_tool(self, 
                            tool_name: str) -> List[AgentInstance]:
        """
        按工具名查找支持该工具的子 Agent。

        Args:
            tool_name: 工具名

        Returns:
            List[AgentInstance]: 支持该工具的 Agent 列表
        """
        pass

    def find_agents_by_task(self, 
                            task: Task) -> List[AgentInstance]:
        """
        根据任务匹配合适的子 Agent。

        Args:
            task: 任务

        Returns:
            List[AgentInstance]: 匹配的 Agent 列表（按匹配度排序）

        匹配逻辑：
            1. 优先 agent_type 精确匹配
            2. 其次 tools 包含任务所需工具
            3. 然后 skill_ids 包含任务所需技能
            4. 最后按 success_rate 降序
        """
        pass

    def find_best_agent(self, 
                        task: Task,
                        lb: LoadBalancer) -> Optional[AgentInstance]:
        """
        查找最适合执行该任务的子 Agent（含负载均衡）。

        Args:
            task: 任务
            lb:   负载均衡器

        Returns:
            AgentInstance | None: 最优 Agent
        """
        pass

    def get_all_agent_types(self) -> List[str]:
        """
        获取所有已注册的 Agent 类型。

        Returns:
            List[str]: Agent 类型列表
        """
        pass

    def get_all_instances(self) -> List[AgentInstance]:
        """
        获取所有已注册的 Agent 实例。

        Returns:
            List[AgentInstance]
        """
        pass

    def get_instance(self, agent_id: str) -> Optional[AgentInstance]:
        """
        获取指定 Agent 实例。

        Args:
            agent_id: 实例 ID

        Returns:
            AgentInstance | None
        """
        pass

    def get_capability(self, agent_type: str) -> Optional[AgentCapability]:
        """
        获取指定 Agent 类型的能力声明。

        Args:
            agent_type: Agent 类型

        Returns:
            AgentCapability | None
        """
        pass

    # ════════════════════════════════════════════
    # 健康监控
    # ════════════════════════════════════════════

    async def heartbeat_check(self):
        """
        心跳检测：定期检查所有子 Agent 的健康状态。
        超过 3 个心跳间隔未上报的标记为 offline。
        """
        pass

    def mark_offline(self, agent_id: str):
        """
        将子 Agent 标记为离线。

        Args:
            agent_id: 实例 ID
        """
        pass

    def mark_online(self, agent_id: str):
        """
        将子 Agent 标记为在线。

        Args:
            agent_id: 实例 ID
        """
        pass

    def get_healthy_agents(self) -> List[AgentInstance]:
        """
        获取所有健康的子 Agent。

        Returns:
            List[AgentInstance]: status == "idle" 或 "busy" 的实例
        """
        pass

    def get_overview(self) -> Dict[str, Any]:
        """
        获取注册中心总览信息。

        Returns:
            Dict: {
                "total_types": int,
                "total_instances": int,
                "healthy_count": int,
                "busy_count": int,
                "offline_count": int,
                "types": [{ "type": str, "instance_count": int, "load": float }]
            }
        """
        pass
```

---

## 10. 负载均衡与容错

### 10.1 重试管理器

```python
class RetryManager:
    """
    🔄 重试管理器 — 负责任务失败后的重试策略。
    
    重试策略：
    - "fixed":     固定间隔重试（如每隔 2s 重试一次）
    - "exponential": 指数退避（2s → 4s → 8s → ...）
    - "immediate": 立即重试
    """

    def __init__(self):
        pass

    async def retry(self, 
                    task: Task,
                    agent: WorkerAgent,
                    strategy: str = "exponential") -> Task:
        """
        执行任务重试。

        Args:
            task:     失败的任务
            agent:    子 Agent
            strategy: 重试策略

        Returns:
            Task: 重试后的任务结果

        流程：
            1. 检查 task.retry_count < task.max_retries
            2. 根据 strategy 计算等待时间
            3. 更新 task.status = RETRYING
            4. 等待后重新调用 agent.execute_task(task)
            5. 成功 → 更新状态；失败 → 继续重试或标记 FAILED
        """
        pass

    def calculate_backoff(self, 
                          retry_count: int,
                          base_delay: int = 2) -> int:
        """
        计算指数退避的等待时间。

        Args:
            retry_count: 已重试次数
            base_delay:  基础延迟（秒）

        Returns:
            int: 等待秒数

        公式：delay = base_delay * (2 ^ retry_count) + random(0, 1)
            重试0次 → 2s
            重试1次 → 4s
            重试2次 → 8s
        """
        pass

    def should_retry(self, task: Task, error: str) -> bool:
        """
        判断是否应该重试。

        Args:
            task:  任务
            error: 错误信息

        Returns:
            bool

        判断逻辑：
            - 可重试的错误类型：超时、网络错误、临时性错误
            - 不可重试的错误：权限不足、参数错误、文件不存在
        """
        pass

    def max_retry_reached(self, task: Task) -> bool:
        """
        是否已达到最大重试次数。

        Args:
            task: 任务

        Returns:
            bool
        """
        pass
```

### 10.2 优雅降级策略

```python
class DegradationManager:
    """
    📉 优雅降级管理器 — 在部分子任务失败时确保系统仍能返回可用结果。
    """

    def decide_degradation(self, 
                           group: TaskGroup,
                           failed_tasks: List[Task]) -> str:
        """
        决定降级策略。

        Args:
            group:        任务组
            failed_tasks: 失败的任务列表

        Returns:
            str: 降级策略
                "partial_merge"  — 仅合并成功的子任务结果
                "retry_critical" — 重试关键任务
                "fallback"       — 使用回退方案
                "report_error"   — 报告错误，终止合并

        决策规则：
            - 失败任务占比 < 30% → "partial_merge"
            - 失败任务包含关键路径 → "retry_critical"
            - 有 fallback 方案 → "fallback"
            - 否则 → "report_error"
        """
        pass

    def create_fallback_task(self, 
                             original_task: Task) -> Task:
        """
        创建回退任务（降级方案）。

        Args:
            original_task: 原始失败任务

        Returns:
            Task: 简化版的回退任务

        示例：
            原任务: "详细分析所有代码" → 耗时太长失败
            回退任务: "仅分析核心模块代码"
        """
        pass
```

### 10.3 超时管理器

```python
class TimeoutManager:
    """
    ⏱️ 超时管理器 — 管理任务的超时检测与超时处理。
    """

    def __init__(self):
        self._timers: Dict[str, asyncio.TimerHandle] = {}

    def set_timeout(self, 
                    task_id: str, 
                    timeout_seconds: int,
                    callback: Callable) -> bool:
        """
        设置任务超时定时器。

        Args:
            task_id:         任务 ID
            timeout_seconds: 超时秒数
            callback:        超时回调函数

        Returns:
            bool: 是否成功设置
        """
        pass

    def cancel_timeout(self, task_id: str) -> bool:
        """
        取消任务超时定时器。

        Args:
            task_id: 任务 ID

        Returns:
            bool: 是否成功取消
        """
        pass

    def on_timeout(self, task_id: str):
        """
        超时触发时的处理逻辑。

        Args:
            task_id: 超时的任务 ID
        """
        pass
```

---

## 11. 扩展场景设计

### 11.1 场景A：动态子 Agent 注册与热插拔

```
系统运行时，新增一个 "docker_ops" 子 Agent:

1. 开发者在 registry.py 定义 DockerAgentCapability
2. 调用 RegistryCenter.register_capability()
3. 创建 AgentInstance 并 register_instance()
4. RegistryCenter 广播通知 Orchestrator
5. Orchestrator 更新路由表
6. 下次遇到 docker 相关任务 → 自动路由到新 Agent

函数设计：

def register_agent_dynamically(agent_type: str,
                                capability: AgentCapability,
                                instance_count: int = 1) -> bool:
    """
    动态注册一个新的子 Agent 类型。

    Args:
        agent_type:     Agent 类型名
        capability:     能力声明
        instance_count: 创建实例数

    Returns:
        bool: 是否成功
    """
    pass

def unregister_agent_dynamically(agent_type: str) -> bool:
    """
    动态注销一个子 Agent 类型（热卸载）。

    Args:
        agent_type: Agent 类型名

    Returns:
        bool: 是否成功

    流程：
        1. 等待该类型所有正在执行的任务完成
        2. 通知 Dispatcher 停止分发新任务
        3. 注销所有实例
        4. 注销能力声明
    """
    pass

def list_registered_agents() -> List[Dict]:
    """
    列出所有已注册的子 Agent。

    Returns:
        List[Dict]: [{ agent_type, display_name, instance_count, status }]
    """
    pass
```

### 11.2 场景B：Agent 间通信与协作

某些场景下，子 Agent 之间需要直接交换数据，而不是全部经过主 Agent 中转。

```python
class AgentMessageBus:
    """
    📨 Agent 消息总线 — 子 Agent 之间的轻量级通信渠道。
    """

    def __init__(self):
        self._channels: Dict[str, List[Callable]] = {}

    def subscribe(self, channel: str, callback: Callable):
        """
        订阅消息频道。

        Args:
            channel:  频道名，如 "file_ops:file_written"
            callback: 回调函数 async def handler(data: Dict)
        """
        pass

    def publish(self, channel: str, data: Dict):
        """
        发布消息到频道。

        Args:
            channel: 频道名
            data:    消息数据
        """
        pass

    def create_channel_for_group(self, group_id: str) -> str:
        """
        为任务组创建临时通信频道。

        Args:
            group_id: 任务组 ID

        Returns:
            str: 频道名
        """
        pass

    async def request_reply(self, 
                            target_agent_type: str,
                            request: Dict,
                            timeout: int = 10) -> Optional[Dict]:
        """
        向指定类型的子 Agent 发送请求并等待回复（RPC 风格）。

        Args:
            target_agent_type: 目标子 Agent 类型
            request:           请求数据
            timeout:           超时

        Returns:
            Dict | None: 回复数据
        """
        pass
```

### 11.3 场景C：结果缓存与去重

```python
class ResultCache:
    """
    💾 结果缓存 — 缓存子任务的执行结果，避免重复执行相同任务。
    """

    def __init__(self, ttl_seconds: int = 300):
        """
        Args:
            ttl_seconds: 缓存有效期（秒）
        """
        pass

    def get_cached(self, task: Task) -> Optional[Any]:
        """
        获取缓存的结果。

        Args:
            task: 任务

        Returns:
            Any | None: 缓存命中返回结果，否则 None

        缓存 key 生成：
            key = hash(task.agent_type + json.dumps(task.payload, sort_keys=True))
        """
        pass

    def set_cached(self, task: Task, result: Any):
        """
        缓存任务结果。

        Args:
            task:   任务
            result: 结果
        """
        pass

    def invalidate_by_tool(self, tool_name: str):
        """
        使指定工具相关的缓存失效（如文件被修改后）。

        Args:
            tool_name: 工具名
        """
        pass

    def clear_expired(self):
        """
        清理过期缓存。
        """
        pass

    def get_stats(self) -> Dict:
        """
        获取缓存统计信息。

        Returns:
            Dict: { "hits": int, "misses": int, "hit_rate": float, "size": int }
        """
        pass
```

### 11.4 场景D：任务进度上报与流式输出

```python
class TaskProgressReporter:
    """
    📊 任务进度上报器 — 向用户实时展示多 Agent 任务的执行进度。
    """

    def report_group_progress(self, group: TaskGroup) -> Dict:
        """
        上报任务组的执行进度。

        Args:
            group: 任务组

        Returns:
            Dict: {
                "group_id": str,
                "total": int,
                "completed": int,
                "failed": int,
                "running": int,
                "progress_pct": float,
                "estimated_remaining_sec": int,
                "tasks": [
                    { "task_id": str, "name": str, "status": str, "agent_type": str }
                ]
            }
        """
        pass

    def format_progress_message(self, progress: Dict) -> str:
        """
        格式化进度信息为可读文本（供前端展示）。

        Args:
            progress: report_group_progress() 的结果

        Returns:
            str: 如 "⏳ 任务执行中... 3/5 已完成 (60%) | 🟢3 ✅2 ❌0 ⏳1"
        """
        pass

    async def stream_progress(self, 
                               group: TaskGroup,
                               stream_callback: Callable):
        """
        流式推送进度更新。

        Args:
            group:          任务组
            stream_callback: 回调函数 async def cb(progress_msg: str)
        """
        pass
```

### 11.5 场景E：审计日志与调用链追踪

```python
class AuditLogger:
    """
    📝 审计日志 — 记录多 Agent 调用的完整链路，用于调试、回溯、分析。
    """

    def __init__(self, log_dir: str = "logs/audit/"):
        pass

    def log_task_created(self, task: Task):
        """
        记录任务创建事件。
        """
        pass

    def log_task_dispatched(self, task: Task, agent_id: str):
        """
        记录任务分发事件。
        """
        pass

    def log_task_completed(self, task: Task):
        """
        记录任务完成事件。
        """
        pass

    def log_task_failed(self, task: Task, error: str):
        """
        记录任务失败事件。
        """
        pass

    def log_merge(self, group_id: str, strategy: str, result_summary: str):
        """
        记录结果合并事件。
        """
        pass

    def get_task_trace(self, task_id: str) -> List[Dict]:
        """
        获取单个任务的完整执行链路。

        Args:
            task_id: 任务 ID

        Returns:
            List[Dict]: 按时间排序的事件列表
        """
        pass

    def get_group_trace(self, group_id: str) -> Dict:
        """
        获取任务组的完整执行链路（含子任务）。

        Args:
            group_id: 任务组 ID

        Returns:
            Dict: 完整的调用链路树
        """
        pass

    def generate_report(self, 
                        context_id: str) -> str:
        """
        生成可读的执行报告。

        Args:
            context_id: 上下文 ID

        Returns:
            str: Markdown 格式的报告
        """
        pass
```

---

## 12. 与现有系统的集成

### 12.1 与 AgentSession 的集成

```python
# 在 AgentSession 中新增属性和方法

class AgentSession:
    """
    增强后的 AgentSession（集成多 Agent 协同能力）
    """

    def __init__(self, ...):
        # ... 原有初始化代码 ...

        # ── 新增：多 Agent 协同系统 ──
        self.orchestrator: Optional[Orchestrator] = None
        self.registry: Optional[RegistryCenter] = None
        self.dispatcher: Optional[TaskDispatcher] = None
        self._enable_multi_agent: bool = False  # 是否启用多 Agent（默认关闭，向后兼容）

    def enable_multi_agent(self):
        """
        启用多 Agent 协同模式。

        初始化所有子模块：
        1. 创建 RegistryCenter → 注册内置子 Agent
        2. 创建 LoadBalancer
        3. 创建 TaskDispatcher
        4. 创建 TaskSplitter
        5. 创建 ResultMerger
        6. 创建 Orchestrator
        7. 标记 _enable_multi_agent = True
        """
        pass

    def disable_multi_agent(self):
        """
        停用多 Agent 协同模式（回退到单 Agent 模式）。
        """
        pass

    async def chat_with_multi_agent(self, user_input: str) -> str:
        """
        使用多 Agent 协同处理用户输入。

        Args:
            user_input: 用户输入

        Returns:
            str: 最终回复

        流程：
            1. 判断是否启用多 Agent（未启用则走原有 chat 逻辑）
            2. 调用 Orchestrator.process_request()
            3. 获取合并后的最终结果
            4. 将结果注入到 msgs 中（保持对话连贯）
            5. 返回格式化后的回复
        """
        pass

    def get_multi_agent_status(self) -> Dict:
        """
        获取多 Agent 系统的状态信息。

        Returns:
            Dict: {
                "enabled": bool,
                "orchestrator_stats": Dict,
                "registry_overview": Dict,
                "queue_status": Dict,
                "active_task_count": int,
            }
        """
        pass
```

### 12.2 与 tools 系统的集成

```python
# 在 tools/__init__.py 中注册新的工具

# ── 新增工具 ──
TOOLS.extend([
    {
        "type": "function",
        "function": {
            "name": "multi_agent_execute",
            "description": "使用多 Agent 协同执行复杂任务（自动拆分、并行执行、合并结果）",
            "parameters": {
                "type": "object",
                "properties": {
                    "request": {
                        "type": "string",
                        "description": "任务描述"
                    },
                    "parallel": {
                        "type": "boolean",
                        "description": "是否允许并行执行",
                        "default": True
                    },
                    "strategy": {
                        "type": "string",
                        "enum": ["auto", "direct", "parallel", "pipeline"],
                        "description": "执行策略",
                        "default": "auto"
                    }
                },
                "required": ["request"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_agents",
            "description": "列出所有已注册的子 Agent 及其状态",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_agent_status",
            "description": "查看指定子 Agent 的详细状态",
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_type": {
                        "type": "string", 
                        "description": "Agent 类型"
                    }
                },
                "required": ["agent_type"]
            }
        }
    },
])


# ── 工具函数实现 ──

async def tool_multi_agent_execute(request: str, 
                                    parallel: bool = True,
                                    strategy: str = "auto",
                                    session=None) -> str:
    """
    多 Agent 协同执行任务的工具函数。

    Args:
        request:  任务描述
        parallel: 是否允许并行
        strategy: 执行策略
        session:  当前 AgentSession（由框架传入）

    Returns:
        str: 格式化后的执行结果
    """
    if not session or not session._enable_multi_agent:
        return "⚠️ 多 Agent 模式未启用，请先调用 enable_multi_agent()"
    
    result = await session.orchestrator.process_request(
        user_request=request,
        context={"parallel": parallel, "strategy": strategy}
    )
    return format_multi_agent_result(result)


def tool_list_agents(session=None) -> str:
    """
    列出所有已注册的子 Agent。
    """
    if not session or not session.registry:
        return "⚠️ 注册中心未初始化"
    
    overview = session.registry.get_overview()
    return json.dumps(overview, ensure_ascii=False, indent=2)


def tool_get_agent_status(agent_type: str, session=None) -> str:
    """
    查看指定子 Agent 的状态。
    """
    if not session or not session.registry:
        return "⚠️ 注册中心未初始化"
    
    capability = session.registry.get_capability(agent_type)
    instances = session.registry.find_agents_by_type(agent_type)
    return json.dumps({
        "capability": capability.__dict__ if capability else None,
        "instances": [i.__dict__ for i in instances]
    }, ensure_ascii=False, indent=2)


def format_multi_agent_result(result: Dict) -> str:
    """
    格式化多 Agent 执行结果。
    """
    lines = []
    lines.append(f"✅ 多 Agent 协同执行完成")
    lines.append(f"📊 策略: {result.get('strategy', 'unknown')}")
    lines.append(f"🔢 总任务数: {result.get('task_count', 0)}")
    lines.append(f"🤖 参与 Agent: {result.get('sub_agent_count', 0)} 个")
    lines.append(f"⏱️ 总耗时: {result.get('total_duration_ms', 0)}ms")
    lines.append("")
    lines.append("📋 结果:")
    lines.append(str(result.get("final_result", "")))
    return "\n".join(lines)
```

### 12.3 与 config.py 的集成

```python
# 在 config.py 中新增配置项

# ── 多 Agent 协同配置 ──
ENABLE_MULTI_AGENT = os.getenv("ENABLE_MULTI_AGENT", "false").lower() == "true"
MAX_GLOBAL_CONCURRENCY = int(os.getenv("MAX_GLOBAL_CONCURRENCY", "10"))
MAX_AGENT_QUEUE_SIZE = int(os.getenv("MAX_AGENT_QUEUE_SIZE", "50"))
AGENT_HEARTBEAT_INTERVAL = int(os.getenv("AGENT_HEARTBEAT_INTERVAL", "30"))
AGENT_DEFAULT_TIMEOUT = int(os.getenv("AGENT_DEFAULT_TIMEOUT", "60"))
AGENT_MAX_RETRIES = int(os.getenv("AGENT_MAX_RETRIES", "2"))
DEFAULT_LOAD_BALANCE_STRATEGY = os.getenv("DEFAULT_LOAD_BALANCE_STRATEGY", "least_load")
ENABLE_RESULT_CACHE = os.getenv("ENABLE_RESULT_CACHE", "true").lower() == "true"
RESULT_CACHE_TTL = int(os.getenv("RESULT_CACHE_TTL", "300"))
```

---

## 13. 交互流程详图

### 13.1 完整执行流程

```
┌──────────┐   ┌──────────────┐   ┌───────────┐   ┌────────────┐   ┌───────────┐
│  用户     │   │ Orchestrator │   │ Splitter  │   │ Dispatcher │   │ Worker    │
│          │   │ (主Agent)     │   │ (拆分器)   │   │ (调度器)    │   │ (子Agent) │
└────┬─────┘   └──────┬───────┘   └─────┬─────┘   └─────┬──────┘   └─────┬─────┘
     │                │                  │               │               │
     │  ① 发送请求     │                  │               │               │
     │───────────────►│                  │               │               │
     │                │                  │               │               │
     │         ② analyze_request()       │               │               │
     │                │──────────────────│               │               │
     │                │◄── 分析结果 ─────│               │               │
     │                │                  │               │               │
     │         ③ decide_strategy()       │               │               │
     │                │  (parallel)      │               │               │
     │                │                  │               │               │
     │         ④ should_split() → True   │               │               │
     │                │──────────────────│               │               │
     │         ⑤ split_task()           │               │               │
     │                │──────────────────│               │               │
     │                │◄── TaskGroup ────│               │               │
     │                │   (3个子任务)     │               │               │
     │                │                  │               │               │
     │         ⑥ dispatch_group()       │               │               │
     │                │────────────────────────────────►│               │
     │                │                  │               │               │
     │                │                  │         ⑦ 负载均衡选择 Agent │
     │                │                  │               │               │
     │                │                  │    ⑧ 分发子任务1 ───────────►│
     │                │                  │    ⑧ 分发子任务2 ───────────►│
     │                │                  │    ⑧ 分发子任务3 ───────────►│
     │                │                  │               │               │
     │                │                  │               │  ⑨ 并行执行   │
     │                │                  │               │  (各自独立)    │
     │                │                  │               │               │
     │                │                  │    ⑩ 返回结果1 ◄─────────────│
     │                │                  │    ⑩ 返回结果2 ◄─────────────│
     │                │                  │    ⑩ 返回结果3 ◄─────────────│
     │                │                  │               │               │
     │                │◄── 全部完成 ─────│───────────────│               │
     │                │                  │               │               │
     │         ⑪ merge_results()        │               │               │
     │                │  (concatenate)   │               │               │
     │                │                  │               │               │
     │  ⑫ 返回最终结果 │                  │               │               │
     │◄───────────────│                  │               │               │
     │                │                  │               │               │
```

### 13.2 并行拆分示例

```
用户请求: "帮我看看这个项目的健康状况——包括 Git 提交情况、代码行数统计、以及项目结构"

分析结果:
  - task_type: "mixed"
  - estimated_steps: 3
  - parallelizable: true
  - required_tools: ["git_log", "count_lines", "list_files"]

拆分决策 → 按领域拆分为 3 个并行子任务:

┌─ TaskGroup ─────────────────────────────────────────────────────┐
│                                                                 │
│  ┌─ 子任务#1 (git_ops) ─────────────────────────────────────┐  │
│  │  agent_type: "git_ops"                                   │  │
│  │  payload: { tool: "git_log", params: { count: 10 } }     │  │
│  │  查询最近 10 次提交记录                                     │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌─ 子任务#2 (file_ops) ─────────────────────────────────────┐  │
│  │  agent_type: "file_ops"                                   │  │
│  │  payload: { tool: "count_lines", params: {} }             │  │
│  │  统计项目总代码行数                                         │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌─ 子任务#3 (file_ops) ─────────────────────────────────────┐  │
│  │  agent_type: "file_ops"                                   │  │
│  │  payload: { tool: "list_files", params: { directory: "." }} │
│  │  列出项目目录结构                                           │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  合并策略: concatenate → 将3个结果拼接为完整报告                   │
└─────────────────────────────────────────────────────────────────┘

加速效果:
  - 串行执行: ~3s + 2s + 1s = 6s
  - 并行执行: max(3s, 2s, 1s) = 3s
  - 加速比: 2x 🎉
```

### 13.3 Pipeline 流水线示例

```
用户请求: "找到项目中所有 TODO 注释，然后统计每个文件有多少个 TODO，最后生成报告"

┌─ TaskGroup (pipeline) ──────────────────────────────────────┐
│                                                              │
│  阶段1 (无依赖):                                              │
│  ┌─ 子任务#1 (file_ops) ─────────────────────────────────┐  │
│  │  grep(pattern="TODO", glob="*.py") → 找到所有 TODO    │  │
│  └──────────────────────────────────────────────────────┘  │
│       │                                                    │
│       ▼  (依赖: 子任务#1 的结果是 子任务#2 的输入)            │
│                                                              │
│  阶段2 (依赖阶段1):                                          │
│  ┌─ 子任务#2 (code_analysis) ───────────────────────────┐  │
│  │  分析 grep 结果，按文件统计 TODO 数量                   │  │
│  └──────────────────────────────────────────────────────┘  │
│       │                                                    │
│       ▼  (依赖: 子任务#2 的结果是 子任务#3 的输入)            │
│                                                              │
│  阶段3 (依赖阶段2):                                          │
│  ┌─ 子任务#3 (info_query) ─────────────────────────────┐  │
│  │  将统计结果格式化为 Markdown 报告                      │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## 14. 存储与配置规划

### 14.1 文件结构

```
TennineClaw/
├── multi_agent/                      # [新] 多 Agent 协同模块包
│   ├── __init__.py                   # 导出 Orchestrator
│   ├── orchestrator.py               # Orchestrator 主类 + StrategyEngine
│   ├── worker_agent.py               # WorkerAgent 基类 + 内置子 Agent
│   ├── dispatcher.py                 # TaskDispatcher + TaskQueue + LoadBalancer
│   ├── splitter.py                   # TaskSplitter
│   ├── merger.py                     # ResultMerger
│   ├── registry.py                   # RegistryCenter
│   ├── retry.py                      # RetryManager
│   ├── degradation.py                # DegradationManager
│   ├── timeout.py                    # TimeoutManager
│   ├── cache.py                      # ResultCache
│   ├── message_bus.py                # AgentMessageBus
│   ├── progress.py                   # TaskProgressReporter
│   └── audit.py                      # AuditLogger
│
├── data/
│   ├── agent_registry.json           # [新] 子 Agent 注册信息持久化
│   └── agent_task_logs/              # [新] 任务执行日志目录
│
├── main.py                           # [修改] AgentSession 集成多 Agent
├── config.py                         # [修改] 新增多 Agent 配置项
├── tools/__init__.py                 # [修改] 注册多 Agent 相关工具
├── web_api.py                        # [修改] 新增多 Agent 状态 API
├── static/                           # [修改] 前端增加多 Agent 监控面板
│
├── SKILL_PERSONALITY_DESIGN.md       # 技能+人格设计文档（前置依赖）
└── MULTI_AGENT_ARCHITECTURE_DESIGN.md # [新] 本文档
```

### 14.2 agent_registry.json 存储格式

```json
{
  "version": "1.1.0",
  "last_updated": "2026-05-21 00:43:57",
  "registered_types": ["file_ops", "git_ops", "cmd_exec", "code_analysis", "info_query"],
  "instances": {
    "agent_file_ops_001": {
      "agent_id": "agent_file_ops_001",
      "agent_type": "file_ops",
      "status": "idle",
      "created_at": "2026-05-21 00:30:00",
      "last_heartbeat": "2026-05-21 00:43:50",
      "current_tasks": [],
      "metadata": {
        "total_tasks_completed": 47,
        "avg_duration_ms": 1230,
        "success_rate": 0.957
      }
    },
    "agent_git_ops_001": {
      "agent_id": "agent_git_ops_001",
      "agent_type": "git_ops",
      "status": "busy",
      "created_at": "2026-05-21 00:30:00",
      "last_heartbeat": "2026-05-21 00:43:48",
      "current_tasks": ["task_20260521_003"],
      "metadata": {
        "total_tasks_completed": 23,
        "avg_duration_ms": 890,
        "success_rate": 1.0
      }
    }
  },
  "load_balance_strategy": "least_load",
  "global_stats": {
    "total_tasks_dispatched": 156,
    "total_tasks_succeeded": 149,
    "total_tasks_failed": 5,
    "total_tasks_timeout": 2,
    "avg_dispatch_latency_ms": 45
  }
}
```

---

## 15. 变更清单

### 新增文件

| 文件 | 说明 |
|------|------|
| `multi_agent/__init__.py` | 多 Agent 协同模块包，导出 Orchestrator |
| `multi_agent/orchestrator.py` | Orchestrator 主类 + StrategyEngine |
| `multi_agent/worker_agent.py` | WorkerAgent 基类 + 5 个内置子 Agent |
| `multi_agent/dispatcher.py` | TaskDispatcher + TaskQueue + LoadBalancer |
| `multi_agent/splitter.py` | TaskSplitter（5种拆分策略） |
| `multi_agent/merger.py` | ResultMerger（7种合并策略） |
| `multi_agent/registry.py` | RegistryCenter（注册/发现/健康监控） |
| `multi_agent/retry.py` | RetryManager（3种重试策略） |
| `multi_agent/degradation.py` | DegradationManager（优雅降级） |
| `multi_agent/timeout.py` | TimeoutManager（超时管理） |
| `multi_agent/cache.py` | ResultCache（结果缓存） |
| `multi_agent/message_bus.py` | AgentMessageBus（Agent间通信） |
| `multi_agent/progress.py` | TaskProgressReporter（进度上报） |
| `multi_agent/audit.py` | AuditLogger（审计日志） |
| `data/agent_registry.json` | 注册信息持久化文件 |
| `data/agent_task_logs/` | 任务日志目录 |

### 修改文件

| 文件 | 改动内容 |
|------|----------|
| `main.py` | AgentSession 新增 `orchestrator`、`registry`、`dispatcher` 属性；新增 `enable_multi_agent()` / `disable_multi_agent()` / `chat_with_multi_agent()` 方法 |
| `config.py` | 新增 9 个多 Agent 配置项（并发数、超时、重试、缓存等） |
| `tools/__init__.py` | 新增 3 个工具注册：`multi_agent_execute`、`list_agents`、`get_agent_status` |
| `web_api.py` | 新增多 Agent 状态查询 API、注册信息 API、任务追踪 API |
| `static/` | 前端新增多 Agent 监控面板（任务队列、子 Agent 状态、调用链可视化） |

---

## 📋 附录：设计索引

### 核心类速查表

| 类名 | 文件 | 职责 | 关键方法数 |
|------|------|------|-----------|
| `Orchestrator` | `orchestrator.py` | 主 Agent 引擎 | 12 |
| `StrategyEngine` | `orchestrator.py` | 策略决策 | 4 |
| `WorkerAgent` | `worker_agent.py` | 子 Agent 基类 | 11 |
| `TaskDispatcher` | `dispatcher.py` | 任务调度 | 12 |
| `LoadBalancer` | `dispatcher.py` | 负载均衡 | 6 |
| `TaskQueue` | `dispatcher.py` | 优先级队列 | 8 |
| `TaskSplitter` | `splitter.py` | 任务拆分 | 8 |
| `ResultMerger` | `merger.py` | 结果合并 | 9 |
| `RegistryCenter` | `registry.py` | 注册中心 | 18 |
| `RetryManager` | `retry.py` | 重试管理 | 4 |
| `DegradationManager` | `degradation.py` | 降级管理 | 3 |
| `TimeoutManager` | `timeout.py` | 超时管理 | 3 |
| `ResultCache` | `cache.py` | 结果缓存 | 5 |
| `AgentMessageBus` | `message_bus.py` | Agent 通信 | 4 |
| `TaskProgressReporter` | `progress.py` | 进度上报 | 3 |
| `AuditLogger` | `audit.py` | 审计日志 | 8 |

### 数据类速查表

| 数据类 | 说明 | 字段数 |
|--------|------|--------|
| `Task` | 任务定义 | 18 |
| `TaskGroup` | 任务组 | 9 |
| `TaskStatus` | 任务状态枚举 | 10 |
| `TaskPriority` | 任务优先级枚举 | 4 |
| `AgentCapability` | 子 Agent 能力声明 | 11 |
| `AgentInstance` | 子 Agent 运行时实例 | 8 |
| `DispatchResult` | 调度结果 | 5 |
| `OrchestratorContext` | 执行上下文 | 10 |

### 并行拆分场景示例

| 场景 | 拆分策略 | 加速比预估 |
|------|---------|-----------|
| 查看项目健康度（Git+代码+结构） | `by_domain` | 2~3x |
| 分析多个文件 | `by_file` | N倍（N个文件） |
| 查找并修复 Bug | `by_step` (pipeline) | 减少等待时间 |
| 批量执行多个独立命令 | `by_tool` | 3~5x |
| 综合代码审查 | `llm_guided` | 2~4x |

---

> **文档版本**: v1.0 | **作者**: TennineClaw Team | **日期**: 2026-05-21  
> **前置依赖**: 建议先阅读 [SKILL_PERSONALITY_DESIGN.md](./SKILL_PERSONALITY_DESIGN.md)  
> **关联系统**: Skill 技能系统（提供子 Agent 技能等级）、Personality 人格系统（影响子 Agent 风格）
