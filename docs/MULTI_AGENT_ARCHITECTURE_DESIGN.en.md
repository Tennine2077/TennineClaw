# 🤖 Multi-Agent Collaborative Architecture Design — Master/Worker Pattern

> **Language**: English | [🇨🇳 中文](MULTI_AGENT_ARCHITECTURE_DESIGN.md)
> **Project**: TennineClaw
> **Version**: v1.1.0 (Planned)
> **Design Goal**: Build a master-worker collaborative architecture enabling intelligent task distribution, parallel split, result aggregation, and fault tolerance
> **Prerequisites**: Skill System + Personality Persistence System (see [SKILL_PERSONALITY_DESIGN.md](SKILL_PERSONALITY_DESIGN.en.md))
> **Design Principles**: High cohesion, low coupling, async-first, graceful degradation, observable

---

## 📖 Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture Overview](#2-architecture-overview)
3. [Core Data Structures](#3-core-data-structures)
4. [Orchestrator — Master Agent Engine](#4-orchestrator--master-agent-engine)
5. [WorkerAgent — Worker Implementation](#5-workeragent--worker-implementation)
6. [TaskDispatcher — Task Scheduler](#6-taskdispatcher--task-scheduler)
7. [TaskSplitter — Task Splitting Engine](#7-tasksplitter--task-splitting-engine)
8. [ResultMerger — Result Merging Engine](#8-resultmerger--result-merging-engine)
9. [RegistryCenter — Worker Registration](#9-registrycenter--worker-registration)
10. [Load Balancing & Fault Tolerance](#10-load-balancing--fault-tolerance)
11. [Extension Scenarios](#11-extension-scenarios)
12. [Integration with Existing System](#12-integration-with-existing-system)
13. [Interaction Flow Diagrams](#13-interaction-flow-diagrams)
14. [Storage & Configuration Planning](#14-storage--configuration-planning)
15. [Change List](#15-change-list)

---

## 1. System Overview

### 1.1 Why Multi-Agent Collaboration?

| Current Single-Agent Pain Point | Multi-Agent Solution |
|---------------------------------|---------------------|
| ❌ Serial tool calls, very slow for large tasks | ✅ Master distributes subtasks in parallel to workers, drastically reducing time |
| ❌ All capabilities coupled in one System Prompt → context bloat | ✅ Workers focus on single domains with lean, efficient prompts |
| ❌ Single failure crashes entire conversation, no tolerance | ✅ Workers run independently, single failure doesn't affect overall flow |
| ❌ Cannot handle multiple independent requests simultaneously | ✅ Multiple workers can execute unrelated tasks in parallel |
| ❌ Agent capability cannot scale horizontally | ✅ Workers can be dynamically registered/deregistered |

### 1.2 Core Concepts

| Concept | Description |
|---------|-------------|
| **Orchestrator** (Master Agent) | Receives user requests, handles analysis, splitting, assignment, and aggregation |
| **WorkerAgent** (Worker) | Executes specific tasks, focused on a single domain with independent session |
| **Task** | Smallest executable unit with definition, parameters, status, and results |
| **TaskGroup** | A set of parallel-executable tasks sharing a common parent_task_id |
| **Dispatcher** | Handles task queuing, assignment, concurrency control, load balancing |
| **Splitter** | Analyzes tasks to decide whether and how to split into subtasks |
| **Merger** | Collects subtask results and merges them into final output |

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    TennineClaw Multi-Agent Architecture                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  User Request → ┌──────────────┐                                            │
│                 │ Orchestrator │  Master Agent Engine                       │
│                 │ (Master)     │  Analysis → Split → Dispatch → Merge      │
│                 └──────┬───────┘                                            │
│                        │                                                    │
│         ┌──────────────┼──────────────────────────┐                        │
│         ▼              ▼                          ▼                        │
│  ┌──────────────┐ ┌──────────────┐       ┌──────────────┐                 │
│  │ WorkerAgent │ │ WorkerAgent │  ...  │ WorkerAgent │                 │
│  │ (Worker A)  │ │ (Worker B)  │       │ (Worker N)  │                 │
│  │ File Ops    │ │ Git Ops     │       │ Code Analysis│                 │
│  │ Cmd Exec    │ │ Search      │       │ Refactor     │                 │
│  └──────────────┘ └──────────────┘       └──────────────┘                 │
│                        │                                                    │
│                        ▼                                                    │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    RegistryCenter                                     │  │
│  │   Manages all WorkerAgent registrations, health status, capabilities  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    Monitor & Observer                                  │  │
│  │   Task execution tracing / Performance metrics / Call chain / Audit   │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.1 Core Design Flow

```
User Request
    │
    ▼
┌────────────────────────────────────────────────────┐
│ Orchestrator (Master Agent)                        │
│                                                    │
│  1. Parse → Understand user intent                 │
│  2. Split → Break into subtasks (TaskSplitter)     │
│  3. Assign → Match workers (RegistryCenter)        │
│  4. Dispatch → Parallel execution (TaskDispatcher) │
│  5. Merge → Aggregate results (ResultMerger)       │
│  6. Respond → Final answer to user                 │
└────────────────────────────────────────────────────┘
```

**Key Workflow**:
- Orchestrator acts as the "brain" — it doesn't execute tools directly; it manages the process
- Each WorkerAgent has its own independent `AgentSession` with dedicated system prompt
- TaskDispatcher handles parallel execution, concurrency limits, and timeouts
- ResultMerger uses configurable strategies (all, first, majority, custom)

---

## 3. Core Data Structures

### 3.1 Task & TaskGroup

```python
@dataclass
class Task:
    """Smallest executable unit"""
    task_id: str                    # Unique task ID
    parent_task_id: str             # Parent task ID
    group_id: str                   # Task group ID
    task_type: str                  # Task type label
    name: str                       # Task name
    description: str                # Task description
    params: Dict[str, Any]          # Execution parameters
    status: str = "pending"         # pending → assigned → running → completed/failed
    assigned_to: Optional[str] = None  # Assigned worker agent ID
    result: Optional[Any] = None    # Execution result
    error: Optional[str] = None     # Error message
    created_at: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    retry_count: int = 0            # Retry count
    max_retries: int = 2            # Max retries
    timeout: int = 60               # Timeout in seconds
    dependencies: List[str] = field(default_factory=list)  # Dependent task IDs

@dataclass
class TaskGroup:
    """A set of parallel-executable tasks"""
    group_id: str
    parent_task_id: str
    name: str
    strategy: str                    # Merge strategy: "all" | "first" | "majority" | "custom"
    tasks: List[Task]
    status: str = "pending"          # pending | running | partial | completed | failed
    created_at: str = ""
    completed_at: Optional[str] = None
    merge_config: Dict[str, Any] = field(default_factory=lambda: {
        "require_all": True,
        "timeout_fallback": "partial",
        "conflict_resolution": "latest",
    })
```

### 3.2 Agent-Related Structures

```python
@dataclass
class AgentCapability:
    """Worker capability declaration"""
    agent_type: str                  # Unique agent type ID
    display_name: str                # Display name
    description: str                 # Description
    tools: List[str]                 # Supported tools
    skill_ids: List[str]             # Associated skill IDs
    max_concurrency: int = 3         # Max concurrent tasks
    supported_task_types: List[str]  # Supported task types
    avg_duration_ms: float = 0.0     # Average duration
    success_rate: float = 1.0        # Success rate
    current_load: int = 0            # Current task count
    total_tasks_completed: int = 0   # Total completed tasks

@dataclass
class AgentInstance:
    """Worker runtime instance with independent AgentSession"""
    agent_id: str
    agent_type: str
    capability: AgentCapability
    session: Any                     # AgentSession instance
    status: str = "idle"             # idle | busy | error | offline
    created_at: str = ""
    last_heartbeat: Optional[str] = None
```

---

## 4. Orchestrator — Master Agent Engine

The Orchestrator is the core "brain" of the multi-agent system. It orchestrates the entire workflow.

### Key Methods

| Method | Description |
|--------|-------------|
| `process_request(user_input)` | Main entry point: analyze → split → dispatch → merge → respond |
| `analyze_intent(user_input)` | Analyze user intent to determine task type and complexity |
| `split_task(task)` | Use TaskSplitter to break tasks into subtasks |
| `dispatch_tasks(task_group)` | Use TaskDispatcher to assign and execute tasks |
| `merge_results(task_group)` | Use ResultMerger to aggregate subtask results |
| `handle_error(task, error)` | Handle task failures with retry or graceful degradation |
| `get_progress()` | Get current execution progress for frontend display |

### Orchestrator Workflow

```
1. User sends request
2. Orchestrator analyzes intent → determines if splitting is needed
3. If simple → execute directly via existing tool system
4. If complex → activate multi-agent workflow:
   a. TaskSplitter breaks down into subtasks
   b. RegistryCenter finds capable workers
   c. TaskDispatcher assigns & executes in parallel
   d. ResultMerger collects & aggregates results
   e. Orchestrator formats final response
5. Return response to user
```

---

## 5. WorkerAgent — Worker Implementation

Each WorkerAgent is a focused, independent agent with its own session.

### Key Characteristics

| Feature | Description |
|---------|-------------|
| **Single Responsibility** | Each worker focuses on one domain (file ops, git, search, etc.) |
| **Independent Session** | Each has its own `AgentSession`, message list, and context |
| **Dedicated System Prompt** | Lean prompt specialized for its domain |
| **Result Reporting** | Returns structured results with status, data, and metadata |
| **Health Check** | Sends periodic heartbeats to RegistryCenter |

### Worker Lifecycle

```
Register → Idle → Assigned → Executing → Completed → Idle
                              ↓ (on error)
                            Failed → Retry → Executing
                                    → Fallback → Report error
```

---

## 6. TaskDispatcher — Task Scheduler

Responsible for task queuing, assignment, concurrency control, and load balancing.

| Method | Description |
|--------|-------------|
| `dispatch(group)` | Dispatch all tasks in a TaskGroup |
| `assign_task(task, workers)` | Assign a task to the most suitable worker |
| `execute_task(task, worker)` | Execute task on assigned worker |
| `get_worker_load(worker_id)` | Get current load of a worker |
| `cancel_group(group_id)` | Cancel all tasks in a group |

### Dispatch Strategies

| Strategy | Description |
|----------|-------------|
| `load_balanced` | Assign to least loaded worker |
| `capability_first` | Assign to most capable worker (highest success rate) |
| `round_robin` | Simple round-robin assignment |
| `priority` | Assign by task priority level |

### Concurrency Control

- Global max concurrency limit (configurable)
- Per-worker max concurrency (from AgentCapability)
- Task-level timeout (configurable per task)
- Graceful cancellation

---

## 7. TaskSplitter — Task Splitting Engine

Analyzes tasks to decide whether and how to split them into subtasks.

| Method | Description |
|--------|-------------|
| `should_split(task)` | Decide if a task needs splitting |
| `split(task)` | Split task into subtasks TaskGroup |
| `merge_plan(task)` | Plan how results should be merged |

### Split Strategies

| Strategy | Description |
|----------|-------------|
| `by_file` | Split by file (e.g., "analyze all Python files") |
| `by_type` | Split by task type (e.g., "check git + count lines") |
| `by_dependency` | Split by dependency chain |
| `custom` | Custom splitting via Orchestrator analysis |

---

## 8. ResultMerger — Result Merging Engine

Collects subtask results and merges them according to strategy.

| Method | Description |
|--------|-------------|
| `merge(group)` | Merge all task results in a group |
| `collect_results(group)` | Collect completed task results |
| `resolve_conflicts(results)` | Resolve conflicts between results |
| `handle_timeout(group)` | Handle timeout for incomplete tasks |

### Merge Strategies

| Strategy | Description |
|----------|-------------|
| `all` | Wait for all subtasks, merge all results |
| `first` | Return first successful result |
| `majority` | Return majority consensus result |
| `custom` | Custom merge logic via callback |

---

## 9. RegistryCenter — Worker Registration

Manages all WorkerAgent registrations, health status, and capability declarations.

| Method | Description |
|--------|-------------|
| `register(capability)` | Register a new worker type |
| `deregister(agent_type)` | Remove a worker type |
| `find_workers(task_type)` | Find workers capable of handling a task type |
| `get_worker(agent_id)` | Get specific worker instance |
| `list_workers(status=None)` | List all workers, optionally filtered |
| `heartbeat(agent_id)` | Receive heartbeat from worker |

### Registration Flow

```
1. Worker starts → creates AgentInstance
2. Worker sends registration request with AgentCapability
3. RegistryCenter validates and stores registration
4. Worker enters idle state, sends periodic heartbeats
5. On shutdown → deregister
```

---

## 10. Load Balancing & Fault Tolerance

### Load Balancing

| Strategy | Description |
|----------|-------------|
| Least Connections | Assign to worker with fewest active tasks |
| Weighted Distribution | Weight by capability score & success rate |
| Adaptive | Adjust weights based on historical performance |

### Fault Tolerance

| Mechanism | Description |
|-----------|-------------|
| **Retry** | Auto-retry on failure (configurable count) |
| **Fallback** | Route to alternative worker if primary fails |
| **Timeout** | Task-level timeout with configurable fallback |
| **Degradation** | Partial results returned if some workers fail |
| **Graceful Shutdown** | Complete current tasks before deregistering |

---

## 11. Extension Scenarios

| Scenario | Implementation |
|----------|---------------|
| **Code Review** | Orchestrator splits by file → workers analyze in parallel |
| **Project Analysis** | Split by type (structure + dependencies + tests) |
| **Batch Refactoring** | Split by file pattern, workers execute in parallel |
| **Multi-Repo Git Audit** | Each repo assigned to a dedicated worker |
| **Document Generation** | Split by section, workers generate in parallel |

---

## 12. Integration with Existing System

The multi-agent system is designed as a **layer above** the current single-agent architecture.

```
Current: User → AgentSession (single agent)
Future:  User → Orchestrator → [WorkerAgent × N] (each with AgentSession)
```

### Integration Points

| Module | Integration |
|--------|-------------|
| `main.py` | Orchestrator creates/manages WorkerAgent sessions |
| `tools/` | Workers reuse existing tool implementations |
| `session_manager.py` | Extended to manage worker sessions |
| `web_api.py` | New API routes for multi-agent status |
| `static/` | Frontend displays multi-agent progress |

---

## 13. Interaction Flow Diagrams

### Sequential Task Flow

```
User: "Analyze this project structure"

Orchestrator: Parse intent → "project analysis"
  ├─ TaskSplitter: Split into 3 subtasks
  │  ├─ Task A: List directory structure
  │  ├─ Task B: Count lines of code
  │  └─ Task C: Git commit stats
  │
  ├─ RegistryCenter: Find capable workers
  │  ├─ Worker Alpha: file_ops, dir_ops
  │  ├─ Worker Beta: search_ops, count_lines
  │  └─ Worker Gamma: git_ops
  │
  ├─ TaskDispatcher: Dispatch in parallel
  │  ├─ Task A → Worker Alpha
  │  ├─ Task B → Worker Beta
  │  └─ Task C → Worker Gamma
  │
  ├─ [Parallel Execution]
  │
  └─ ResultMerger: Combine results
     └─ Orchestrator: Format final response
```

---

## 14. Storage & Configuration Planning

### Storage Structure
```
sessions/
├── orchestrator_{id}.json     # Orchestrator session
├── worker_{agent_id}_{id}.json  # Worker sessions
└── multi_agent_registry.json  # Registry data
```

### Configuration
```json
{
  "multi_agent": {
    "enabled": true,
    "max_concurrent_workers": 10,
    "default_task_timeout": 60,
    "heartbeat_interval": 30,
    "worker_auto_scale": true,
    "min_workers": 3,
    "max_workers": 20
  }
}
```

---

## 15. Change List

| Module | Change | Status |
|--------|--------|--------|
| `multi_agent/` | New directory for multi-agent system | Planned |
| `multi_agent/orchestrator.py` | Orchestrator engine | Planned |
| `multi_agent/worker.py` | WorkerAgent implementation | Planned |
| `multi_agent/dispatcher.py` | TaskDispatcher | Planned |
| `multi_agent/splitter.py` | TaskSplitter | Planned |
| `multi_agent/merger.py` | ResultMerger | Planned |
| `multi_agent/registry.py` | RegistryCenter | Planned |
| `config.py` | Add multi-agent config items | Planned |
| `web_api.py` | Add multi-agent API routes | Planned |
| `static/js/app.js` | Multi-agent progress UI | Planned |

---

**Made with 💙**
