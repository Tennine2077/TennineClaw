# 🎯 Skill System & Personality Persistence — Design Document

> **Language**: English | [🇨🇳 中文](SKILL_PERSONALITY_DESIGN.md)
> **Project**: TennineClaw
> **Version**: v1.0.0 → v1.1.0 (Planned)
> **Design Goal**: Empower the AI Agent with a growable, composable Skill system, and cross-session consistent personality memory and behavioral traits
> **Design Principles**: Modular, extensible, low-coupling, progressive rollout

---

## 📖 Table of Contents

1. [System Overview](#1-system-overview)
2. [Data Structure Design](#2-data-structure-design)
3. [Skill System](#3-skill-system)
4. [Personality Persistence System](#4-personality-persistence-system)
5. [Integration & Interaction Flow](#5-integration--interaction-flow)
6. [Configuration & Storage Planning](#6-configuration--storage-planning)
7. [Extensibility Design](#7-extensibility-design)

---

## 1. System Overview

### 1.1 Why Introduce These Systems?

| Current Pain Point | Solution |
|--------------------|----------|
| Agent starts from scratch every session, no sense of growth | Skill system with experience, leveling up based on usage frequency/success rate |
| Tool calls are "flat" with no priority or combination strategy | Skill tree, passive/active skills, skill combinations |
| No personality memory across sessions, feels like a "stranger" each time | Personality persistence system for traits, language habits, preferences |
| No behavioral differentiation, even with different models | Personality traits influence response style and decision preferences |

### 1.2 Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    TennineClaw Overall Architecture           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────┐    ┌───────────────────────────┐  │
│  │   AgentSession      │    │   PersonalityEngine       │  │
│  │   (Core Engine)     │◄──►│   - Trait Management     │  │
│  │                     │    │   - Language Style        │  │
│  │   - Mode Management │    │   - Memory Fragments      │  │
│  │   - Tool Dispatch   │    │   - Behavioral Preferences│  │
│  │   - Composer        │    └──────────┬────────────────┘  │
│  │   - Session Mgmt    │               │                   │
│  └────────┬────────────┘               │                   │
│           │                             │                   │
│           ▼                             ▼                   │
│  ┌──────────────────────────────────────────────┐          │
│  │            Skill Engine                       │          │
│  │   - Skill Registration & Discovery           │          │
│  │   - Skill Tree / Dependencies                │          │
│  │   - Experience & Level System                │          │
│  │   - Skill Execution & Combination            │          │
│  └──────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Data Structure Design

### 2.1 Skill Core Data Structures

```python
@dataclass
class SkillDefinition:
    """Skill definition template"""
    skill_id: str                        # Unique skill ID, e.g., "skill_git_ops"
    name: str                            # Display name, e.g., "Git Operations Mastery"
    category: str                        # Category: "tool" | "cognitive" | "communication" | "analysis"
    description: str                     # Functional description
    prerequisites: List[str]             # Prerequisite skill IDs
    max_level: int = 5                   # Maximum level
    base_experience: int = 100           # Base XP for leveling (incremental per level)
    skill_type: str = "active"           # "active" | "passive"
    cooldown_rounds: int = 0             # Cooldown rounds (0 = no cooldown)
    tags: List[str] = field(default_factory=list)

@dataclass
class SkillState:
    """Skill runtime state (per session/per agent)"""
    skill_id: str
    level: int = 1                       # Current level (starts at 1)
    experience: int = 0                  # Current XP
    total_uses: int = 0                  # Total uses
    success_count: int = 0               # Success count
    last_used_round: int = 0             # Last used round (for cooldown)
    is_unlocked: bool = True
    unlocked_at: str = ""
    context_tags: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SkillCombo:
    """Skill combination definition"""
    combo_id: str
    name: str
    skill_ids: List[str]                 # Skills to combine
    description: str                     # Combo effect description
    trigger_condition: str               # Trigger condition
    priority: int = 0                    # Priority (higher = more preferred)
```

### 2.2 Personality Core Data Structures

```python
@dataclass
class PersonalityProfile:
    """Personality profile (cross-session persistent)"""
    profile_id: str
    name: str = ""                       # Personality name, e.g., "Claw"

    # Big Five (simplified)
    traits: Dict[str, float] = field(default_factory=lambda: {
        "openness": 0.7,           # Willingness to try new tools
        "conscientiousness": 0.8,  # Carefulness in execution
        "extraversion": 0.5,       # Verbosity preference
        "agreeableness": 0.7,      # Willingness to follow user preferences
        "neuroticism": 0.3,        # Caution level
    })

    # Language style
    language_style: Dict[str, Any] = field(default_factory=lambda: {
        "formality": 0.5,          # Formal vs casual
        "emoji_frequency": 0.6,    # Emoji usage
        "verbosity": 0.5,          # Verbosity (brief vs detailed)
        "greeting_template": "",   # Custom greeting
    })

    # Behavioral preferences
    behavioral_preferences: Dict[str, Any] = field(default_factory=lambda: {
        "preferred_tools": [],     # Preferred tools (used more often)
        "avoided_tools": [],       # Avoided tools
        "auto_confirm": True,      # Auto-confirm before dangerous ops
        "show_reasoning": True,    # Show reasoning process
    })

    # Memory fragments
    memory_fragments: List[Dict] = field(default_factory=list)
    # Each fragment: {id, content, type, importance, created_at, last_accessed}
```

---

## 3. Skill System

### 3.1 SkillEngine

The core manager for the Skill system.

| Method | Description |
|--------|-------------|
| `register_skill(definition)` | Register a new skill |
| `unlock_skill(agent_id, skill_id)` | Unlock a skill for an agent |
| `get_skill_state(agent_id, skill_id)` | Get skill runtime state |
| `add_experience(agent_id, skill_id, xp)` | Add experience, trigger level-up if threshold met |
| `check_level_up(skill_state, definition)` | Check and perform level-up |
| `use_skill(agent_id, skill_id, success)` | Record skill usage and outcome |
| `get_available_skills(agent_id)` | Get all available skills for an agent |
| `find_combinations(agent_id, task_type)` | Find applicable skill combos |

### 3.2 Experience & Level System

```
Level 1: 0 XP    → Base capability
Level 2: 100 XP  → +10% efficiency
Level 3: 300 XP  → +20% efficiency, unlock sub-skills
Level 4: 600 XP  → +30% efficiency, reduced cooldown
Level 5: 1000 XP→ +50% efficiency, unlock expert features
```

| Concept | Description |
|---------|-------------|
| XP Gain | +10 XP per use, +20 XP on success, bonus for complex tasks |
| Level-Up | XP threshold = base_experience × level × 1.5 |
| Effects | Higher level = faster execution, better results, new capabilities |

### 3.3 Skill Categories

| Category | Type | Examples |
|----------|------|----------|
| Tool Skills | Active | Git operations, file operations, search, replace |
| Cognitive Skills | Passive | Code analysis, pattern recognition, dependency tracing |
| Communication Skills | Passive/Active | Explanation style, error reporting, suggestion making |
| Analysis Skills | Active | Code review, performance analysis, security audit |

### 3.4 Skill Combinations

| Combo | Skills Required | Effect |
|-------|----------------|--------|
| "Smart Refactor" | Search + Replace + Code Analysis | Context-aware batch refactoring |
| "Full Audit" | Git Log + Diff + Count Lines + Search | Comprehensive project audit |
| "Smart Debug" | Grep + Diff + Cmd Exec + Code Analysis | Intelligent debugging workflow |

---

## 4. Personality Persistence System

### 4.1 PersonalityEngine

| Method | Description |
|--------|-------------|
| `load_profile(profile_id)` | Load personality profile from storage |
| `save_profile(profile)` | Persist personality profile |
| `update_trait(profile_id, trait, value)` | Update a personality trait |
| `learn_preference(profile_id, context, action, outcome)` | Learn from user interaction |
| `get_personality_prompt(profile_id)` | Generate personality system prompt |
| `add_memory(profile_id, content, importance)` | Add a memory fragment |
| `recall_memories(profile_id, query, limit)` | Recall relevant memories |

### 4.2 Personality Traits (Big Five)

| Trait | Low Score | High Score |
|-------|-----------|------------|
| **Openness** | Prefers familiar tools, follows patterns | Eager to try new tools, innovative solutions |
| **Conscientiousness** | Quick execution, less verification | Meticulous, double-checks before acting |
| **Extraversion** | Brief, direct responses | Detailed explanations, proactive suggestions |
| **Agreeableness** | Sticks to own style | Adapts to user preferences, flexible |
| **Neuroticism** | Bold, takes risks | Cautious, warns about potential issues |

### 4.3 Memory System

| Memory Type | Description | Persistence |
|-------------|-------------|-------------|
| **Episodic** | Specific past interactions | Session-only or persistent (if important) |
| **Semantic** | Learned facts about user preferences | Cross-session persistent |
| **Procedural** | Learned workflows and patterns | Cross-session persistent |

Memory importance scoring: `importance = user_feedback × 0.4 + frequency × 0.3 + recency × 0.3`

### 4.4 Learning Mechanism

```
User Action → Observe Outcome → Update Traits & Preferences
                                      ↓
                              Update Memory Fragments
                                      ↓
                              Adjust Future Behavior
```

---

## 5. Integration & Interaction Flow

### 5.1 Full Interaction Flow

```
User Input
    ↓
PersonalityEngine: Load profile → Build personality prompt
    ↓
SkillEngine: Analyze task → Check available skills → Find combos
    ↓
AgentSession: Process message with personality + skill context
    ↓
Tool Execution: Record usage → Update skill XP → Learn preferences
    ↓
Response Generation: Apply language style → Format with personality
    ↓
Post-processing: Save personality profile → Persist memory fragments
```

### 5.2 System Prompt Integration

The personality and skill information is injected into the system prompt:

```
[Personality]
You are {name}, with the following traits: ...
Your language style: ...
User preferences: ...

[Available Skills]
- Git Operations (Lv.3): 320/600 XP
- File Search (Lv.5): MAX
...
```

---

## 6. Configuration & Storage Planning

### Storage Structure
```
personalities/
├── profiles/
│   └── {profile_id}.json      # Personality profile data
└── memories/
    └── {profile_id}/
        ├── episodic.json       # Episodic memories
        ├── semantic.json       # Semantic memories
        └── procedural.json     # Procedural memories

skills/
├── definitions/
│   └── {skill_id}.json        # Skill definitions
└── states/
    └── {agent_id}/
        └── {skill_id}.json    # Agent skill states
```

### Configuration
```json
{
  "skill_system": {
    "enabled": true,
    "xp_decay": false,
    "max_level": 10,
    "combo_enabled": true
  },
  "personality": {
    "enabled": true,
    "default_profile": "default",
    "learning_enabled": true,
    "memory_limit": 100,
    "auto_save_interval": 300
  }
}
```

---

## 7. Extensibility Design

### Plugin-like Skill Registration
```python
# Register custom skills easily
@skill_engine.register(
    skill_id="skill_custom_analyzer",
    name="Custom Code Analyzer",
    category="analysis",
    prerequisites=["skill_search"],
    max_level=3
)
class CustomAnalyzerSkill:
    async def execute(self, params, context):
        # Custom implementation
        pass
```

### Future Extensions

| Extension | Description |
|-----------|-------------|
| **Skill Marketplace** | Community-shared skill packages |
| **Personality Templates** | Pre-built personality profiles |
| **Cross-Agent Skill Sharing** | Skills learned by one agent shared with others |
| **Adaptive Difficulty** | Task difficulty auto-adjusts to skill level |
| **Emotional State** | Temporary mood affecting response style |

---

**Made with 💙**
