# Agentic Workflow: End-to-End Reference

This document describes the complete autonomous agent system used to develop
Clawssistant. It is written as a handoff document — any model or developer
reading this should be able to understand how the system works, what each
agent does, how context flows between them, and how to extend or modify the
pipeline.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Core Architecture](#core-architecture)
3. [Agent Roles](#agent-roles)
4. [Ticket Lifecycle (State Machine)](#ticket-lifecycle)
5. [End-to-End Walkthrough](#end-to-end-walkthrough)
6. [Context Handoff Protocol](#context-handoff-protocol)
7. [Dispatch Mechanism](#dispatch-mechanism)
8. [The Agentic Loop](#the-agentic-loop)
9. [Tool System](#tool-system)
10. [Security Model](#security-model)
11. [Configuration](#configuration)
12. [How to Extend](#how-to-extend)
13. [Key Files Reference](#key-files-reference)

---

## System Overview

Clawssistant uses a multi-agent autonomous development system where Claude
instances operate as specialized team members — an orchestrator, product
manager, triage coordinator, engineering triad, code reviewer, security
pair, QA engineer, codebase auditor, and blog writer. These agents
communicate asynchronously through GitHub (issues, PRs, labels, comments)
and are dispatched via GitHub Actions workflows.

**Key properties:**

- **Fully autonomous** — agents run on cron schedules and event triggers,
  no human in the loop required (though humans can intervene at any point)
- **Asynchronous** — agents communicate via GitHub artifacts (comments,
  labels, structured context blocks), not direct messages
- **Stateless execution** — each agent invocation is a fresh process; all
  persistent state lives in GitHub issues/comments
- **Context-preserving** — structured JSON context blocks in issue comments
  ensure lossless handoffs between agents
- **Safety-gated** — mandatory code review, dual security review, and QA
  gates prevent bad code from deploying

### What This System Is NOT

This is the *development infrastructure* — the agents that build Clawssistant
itself. It is separate from the Clawssistant home assistant runtime (the voice
pipeline, Claude brain, memory system, connectors, etc.), which is what these
agents are building.

---

## Core Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    GitHub Actions (Scheduler)                    │
│  Cron triggers, webhook triggers, workflow_dispatch triggers     │
└───────────────┬─────────────────────────────────┬───────────────┘
                │                                 │
                ▼                                 ▼
┌───────────────────────┐         ┌───────────────────────────────┐
│   Orchestrator Agent  │────────►│     Dispatch Layer            │
│   (every 15 min)      │         │     dispatch.py               │
│                       │         │                               │
│   Scans board state,  │         │   Maps AgentRole → workflow   │
│   dispatches agents,  │         │   Triggers GitHub Actions     │
│   resolves blocks     │         │   Passes trigger context      │
└───────────────────────┘         └──────────────┬────────────────┘
                                                 │
                    ┌────────────────────────────┬┴──────────────────┐
                    ▼                            ▼                   ▼
          ┌─────────────────┐          ┌──────────────────┐  ┌────────────┐
          │  Triage Agent   │          │  Engineer/Triad  │  │  Reviewer  │
          │                 │          │                  │  │            │
          │  Multi-lens     │          │  Design Eng +    │  │  Sr. Eng   │
          │  evaluation     │          │  Software Eng +  │  │  code      │
          │  (researcher,   │          │  UX Eng as one   │  │  review    │
          │   data sci,     │          │  Claude context  │  │            │
          │   engineer)     │          │                  │  │            │
          └────────┬────────┘          └────────┬─────────┘  └─────┬──────┘
                   │                            │                  │
                   ▼                            ▼                  ▼
          ┌─────────────────┐          ┌──────────────────┐  ┌──────────────────┐
          │  PM Agent       │          │  Security Pair   │  │  QA Agent        │
          │                 │          │                  │  │                  │
          │  Writes epics,  │          │  Security Eng +  │  │  Runs tests,     │
          │  features,      │          │  InfoSec Agent   │  │  validates       │
          │  stories        │          │  (both must      │  │  acceptance      │
          │                 │          │   approve)       │  │  criteria        │
          └─────────────────┘          └──────────────────┘  └──────────────────┘

          ┌─────────────────┐          ┌──────────────────┐
          │  Wildcard Agent │          │  Blog Agent      │
          │                 │          │                  │
          │  Periodic       │          │  Writes release  │
          │  codebase       │          │  notes, roadmap  │
          │  auditor        │          │  updates         │
          └─────────────────┘          └──────────────────┘
```

### Execution Model

Each agent is a Python class that inherits from `Agent` (defined in
`agents/base.py`). When triggered:

1. A GitHub Actions workflow starts
2. The workflow runs `python -m agents.scripts.run_agent --role <role> ...`
3. The agent class is instantiated, which creates an Anthropic API client
   and a GitHub operations client
4. The agent's `run()` method is called with a trigger dict
5. `run()` gathers context, builds messages, and enters the **agentic loop**
6. The agentic loop calls Claude repeatedly until Claude stops making tool
   calls (or hits the iteration limit of 10)
7. The agent posts results, updates labels/state, writes a context block
   for the next agent, and exits

---

## Agent Roles

### Orchestrator (`agents/roles/orchestrator.py`)

**Role:** Root coordinator of the entire system.

**Triggered by:** Cron (every 15 minutes) or escalation events.

**What it does:**
- Scans the GitHub board for tickets in every state
- Dispatches agents to tickets that need attention:
  - `state:ready` → dispatches Engineer (Triad Squad)
  - `state:code-review` → dispatches Sr. Engineer (Reviewer)
  - `state:security-review` → dispatches Security + InfoSec pair
  - `state:qa` → dispatches QA Agent
  - `state:blocked` → attempts to resolve or re-scope
- Detects stale tickets (no movement in 24+ hours)
- Handles escalations from blocked agents
- Rate-limited: max 10 dispatches per cycle

**Unique tools:** `dispatch_engineer`, `dispatch_review`, `dispatch_security`,
`dispatch_qa`, `dispatch_deploy`, `dispatch_wildcard`, `dispatch_blog`,
`escalate_blocked`

**Safety:** Never deploys without dual security approval. Never skips QA.
Never force-merges.

---

### Product Manager (`agents/roles/pm.py`)

**Role:** Product voice — bridges user needs with engineering capacity.

**Triggered by:** New issues, new discussions, or backlog grooming schedule.

**What it does:**
- Reviews new issues and discussions
- Collaborates with users via @-tagging
- Writes structured epics, features, and user stories with acceptance
  criteria detailed enough for an agent to implement autonomously
- Manages board priorities and timeline
- Requests blog posts for milestones

**Unique tools:** `create_epic` (creates parent + child feature tickets),
`reply_to_discussion`, `request_blog_post`

**Ticket writing standards:** Every ticket includes user story, acceptance
criteria, technical notes, scope boundaries, priority, and effort estimate.

---

### Triage Coordinator (`agents/roles/triage.py`)

**Role:** Multi-perspective issue evaluation.

**Triggered by:** New issues arriving in `state:new`.

**What it does:** Evaluates every new issue from three simultaneous
perspectives within a single Claude conversation:

1. **Senior User Researcher** — user need, usability, market fit,
   competitive analysis
2. **Data Scientist** — scope estimate (XS-XL), effort hours, priority
   score (Impact x Urgency / Effort), risk assessment
3. **Engineer** — technical feasibility, architecture impact, security
   implications, estimated LOC

**Output:** A structured triage report with a verdict:
- `ACCEPTED` → ticket gets priority/type/scope labels, moves to `scoped`
- `REJECTED` → detailed reasoning posted, issue closed
- `NEEDS-INFO` → specific questions asked, author tagged

**Unique tools:** `post_triage_report` (posts report + updates labels +
saves handoff context)

---

### Engineering Triad (`agents/roles/triad.py`)

**Role:** The executing development task force — three engineering
perspectives in one Claude context.

**Triggered by:** Orchestrator dispatching to a `state:ready` ticket.

**The three perspectives:**
- **Design Engineer (DE)** — architecture, system design, API contracts,
  data models, scalability
- **Software Engineer (SE)** — implementation, tests, security, performance,
  code quality
- **UX Engineer (UXE)** — user experience, CLI ergonomics, error messages,
  documentation, accessibility

**Workflow:**
1. All three perspectives plan together (architecture → implementation → UX)
2. Reach consensus before coding
3. Implement with all three lenses active
4. Self-review from all three perspectives before opening PR
5. PR description includes architecture, implementation, and UX sections

**Unique tools:** `read_file`, `write_file`, `list_files`, `search_code`,
`run_command` (allowlisted: pytest, ruff, mypy), `git_create_branch`,
`git_commit_and_push`, `create_pr`, `signal_block`

**Persistence:** Owns the ticket until deployed or archived. Addresses
all review feedback through the full review cycle.

**Security:** Path traversal protection on file ops. Secret file write
prevention. Command allowlist enforcement.

---

### Standalone Engineer (`agents/roles/engineer.py`)

**Role:** Simpler single-perspective development agent.

**Note:** In the current configuration, the `engineer` role maps to the
Triad Squad by default (see `run_agent.py` line 45). The standalone
engineer exists as a lighter alternative for simpler tickets.

**Same tools as Triad** but without the three-perspective system prompt.

---

### Senior Engineer / Reviewer (`agents/roles/reviewer.py`)

**Role:** Code quality gate — nothing ships without approval.

**Triggered by:** Ticket entering `state:code-review` (orchestrator
dispatches).

**Review criteria (7 dimensions):**
1. **Correctness** — does it work, edge cases, error paths, races
2. **Architecture** — fits system design, clean boundaries
3. **Code quality** — PEP 8, type hints, DRY, no smells
4. **Testing** — coverage, edge case tests, deterministic
5. **Security** — input validation, no eval/exec, no secrets
6. **Performance** — no N+1, efficient queries, appropriate caching
7. **UX** — helpful errors, clean API shapes, intuitive config

**Verdicts:**
- `APPROVE` → ticket moves to `security-review`
- `REQUEST CHANGES` → ticket moves back to `in-progress`, engineer
  is re-dispatched with feedback
- `COMMENT` → suggestions only, not blocking

**Unique tools:** `get_pr_details`, `get_pr_diff`, `submit_review`,
`request_security_review`

---

### Security Pair (`agents/roles/security.py`)

Two separate agents review every PR in parallel. **Both must approve**
before deployment.

#### Security Engineer (`SecurityAgent`)

**Focus:** Code-level vulnerability scanning.

**Scans for:**
- OWASP Top 10 adapted for home automation (injection, broken auth,
  data exposure, access control, misconfig, XSS, deserialization, CVEs)
- Path traversal in file ops and skill loading
- Voice command injection vectors
- MCP server sandbox escapes
- Token exposure

**Verdicts:**
- `APPROVED` — no critical/high findings
- `BLOCKED` — any critical finding, or 2+ high findings
- `CONDITIONALLY APPROVED` — 1 high finding trackable in follow-up

#### InfoSec Agent (`InfoSecAgent`)

**Focus:** Threat modeling, compliance, systemic security.

**Evaluates:**
- Trust boundary violations (does this change weaken any boundary?)
- Data flow analysis (where does user data go?)
- Privacy/GDPR compliance (data minimization, deletability)
- Attack surface changes (new endpoints, file access, subprocesses)
- Defense in depth (multiple protection layers, least privilege)

**When both approve:** Ticket moves to `state:qa`. If either blocks,
ticket goes back to `state:in-progress` with `security:blocked` label.

**Unique tools:** `get_pr_diff`, `submit_security_review` /
`submit_infosec_review`

---

### QA Engineer (`agents/roles/qa.py`)

**Role:** Final quality gate before deployment.

**Triggered by:** Both security + infosec approving (ticket enters
`state:qa`).

**QA process:**
1. Run full test suite (`pytest tests/ -v --tb=short`)
2. Verify each acceptance criterion from the original ticket
3. Regression check on affected areas
4. Exploratory testing for edge cases
5. Documentation check (outdated docs, config examples)

**Verdicts:**
- `PASSED` → ticket moves to `state:deploying`
- `FAILED` → ticket moves back to `state:in-progress`
- `PARTIAL` → tests pass but acceptance criteria unclear

**Unique tools:** `run_tests`, `get_pr_details`, `submit_qa_result`,
`file_bug` (creates regression bug issues)

---

### Wildcard Auditor (`agents/roles/wildcard.py`)

**Role:** Independent periodic codebase scanner.

**Triggered by:** Weekly cron schedule or orchestrator dispatch.

**Scans for:** Security issues, tech debt, dead code, architecture drift,
testing gaps, documentation staleness, performance anti-patterns,
dependency vulnerabilities.

**Output:** Creates GitHub issues for findings (max 10 per scan) with
category, severity, file references, and fix recommendations. Checks
for duplicate issues before filing.

**Tools:** `scan_directory`, `read_file`, `search_pattern`, `run_linter`
(ruff, mypy, pip-audit), `file_finding`

---

### Blog Writer (`agents/roles/blog.py`)

**Role:** Project communication — writes and publishes blog posts.

**Triggered by:** PM requesting a post or orchestrator dispatching for
milestones.

**Post types:** Release notes, architecture deep dives, roadmap updates,
community spotlights, dev logs.

**Tools:** `write_blog_post`, `list_recent_changes`, `list_recent_prs`,
`commit_and_push_blog`

---

## Ticket Lifecycle

Every ticket follows a strict state machine. Invalid transitions are
rejected by `agents/state.py`.

```
                                    ┌──────────┐
                                    │   new    │
                                    └────┬─────┘
                                         │
                                         ▼
                                    ┌──────────┐
                          ┌────────►│ triaging │──────────────┐
                          │         └────┬─────┘              │
                          │              │                    │
                          │              ▼                    ▼
                          │    ┌────────────────────┐   ┌──────────┐
                          │    │ feasibility-review │   │ archived │
                          │    └────────┬───────────┘   └──────────┘
                          │             │                    ▲
                          │             ▼                    │
                          │       ┌──────────┐              │
                          │       │  scoped  │              │
                          │       └────┬─────┘              │
                          │            │                    │
                          │            ▼                    │
                          │       ┌──────────┐              │
                          │       │ backlog  │──────────────┤
                          │       └────┬─────┘              │
                          │            │                    │
                          │            ▼                    │
                          │       ┌──────────┐              │
                          │       │  ready   │              │
                          │       └────┬─────┘              │
                          │            │                    │
                          │            ▼                    │
                          │     ┌─────────────┐             │
          ┌───────────────┼────►│ in-progress │─────────────┤
          │               │     └──────┬──────┘             │
          │               │            │   │                │
          │               │            │   └──►┌─────────┐  │
          │               │            │       │ blocked │──┘
          │               │            ▼       └─────────┘
          │               │     ┌─────────────┐
          │    ◄──────────┼─────│ code-review │
          │  (changes     │     └──────┬──────┘
          │   requested)  │            │
          │               │            ▼ (approved)
          │               │  ┌──────────────────┐
          │    ◄──────────┼──│ security-review  │
          │  (blocked)    │  └────────┬─────────┘
          │               │           │
          │               │           ▼ (both approved)
          │               │       ┌────────┐
          │    ◄──────────┼───────│   qa   │
          │  (failed)     │       └───┬────┘
                          │           │
                          │           ▼ (passed)
                          │     ┌───────────┐
                          │     │ deploying │
                          │     └─────┬─────┘
                          │           │
                          │           ▼
                          │     ┌──────────┐
                          │     │ deployed │
                          │     └────┬─────┘
                          │          │
                          │          ▼
                          │     ┌──────────┐
                          └─────│ archived │
                                └──────────┘
```

### State-to-Agent Mapping

| State | Acting Agent(s) | What Happens |
|-------|----------------|--------------|
| `new` | Triage, PM | Issue evaluated, triaged |
| `triaging` | Triage | Multi-perspective assessment |
| `feasibility-review` | Triage | Technical feasibility deep dive |
| `scoped` | PM | PM writes tickets, sets priority |
| `backlog` | PM, Orchestrator | Groomed, prioritized |
| `ready` | Orchestrator | Dispatches Triad Squad |
| `in-progress` | Engineer/Triad | Code is being written |
| `code-review` | Sr. Engineer | PR reviewed for quality |
| `security-review` | Security + InfoSec | Dual security review |
| `qa` | QA | Test suite + acceptance validation |
| `deploying` | Orchestrator | Merge + deploy triggered |
| `deployed` | — | Live in production |
| `blocked` | Orchestrator | Resolves or re-scopes |
| `archived` | — | Terminal state |

### Label Scheme

Every state, priority, type, and agent assignment maps to a GitHub label:

- **State labels:** `state:new`, `state:in-progress`, `state:code-review`, etc.
- **Priority labels:** `priority:P0-critical` through `priority:P4-backlog`
- **Type labels:** `type:epic`, `type:feature`, `type:bug`, `type:chore`, etc.
- **Agent labels:** `agent:engineer`, `agent:security`, `agent:qa`, etc.

Labels are the source of truth for board queries. The orchestrator scans
by label to find work.

---

## End-to-End Walkthrough

Here is a complete lifecycle of a feature request, from user filing an
issue to deployed code.

### Phase 1: Issue Arrives

1. A user opens a GitHub issue: *"Add MQTT connector for direct device
   control without Home Assistant"*
2. GitHub webhook triggers the triage workflow
3. The **Triage Agent** is dispatched

### Phase 2: Triage

4. Triage agent reads the issue (title, body, author, existing labels,
   comments)
5. Labels the issue `state:triaging`, removes `state:new`
6. Evaluates from three perspectives in a single Claude conversation:
   - **Researcher:** High user need (privacy users want HA-free option),
     aligned with "platform-independent" principle
   - **Data Scientist:** Scope M, effort ~16h, priority P2-medium,
     risk medium (MQTT protocol complexity)
   - **Engineer:** Feasible, affects `connectors/` layer, needs
     `aiomqtt` dependency, no security concerns beyond input validation
7. Posts a structured triage report as a comment
8. Calls `post_triage_report` tool with verdict `accepted`
9. Labels updated: `state:scoped`, `priority:P2-medium`, `type:feature`,
   `scope:M`
10. **Writes a TicketContext** JSON block to the issue as a comment:
    ```json
    {
      "ticket_id": 42,
      "triage_decision": "accepted",
      "priority": "P2-medium",
      "scope_estimate": "M",
      "estimated_effort_hours": 16,
      "ticket_type": "feature",
      "state": "scoped"
    }
    ```

### Phase 3: Product Management

11. **PM Agent** picks up the scoped ticket
12. Writes detailed acceptance criteria, technical notes, scope boundaries
13. Moves ticket to `state:backlog`
14. During next grooming cycle, promotes to `state:ready`

### Phase 4: Development (Triad Squad)

15. **Orchestrator** (on its 15-minute cron) sees ticket #42 in
    `state:ready`
16. Dispatches the engineer workflow via `dispatch_engineer_for_ticket()`
17. The **Triad Squad Agent** starts:
    - Reads the issue and any existing TicketContext
    - Labels: `state:in-progress`, `agent:engineer`, `triad-squad`
    - **DE plans:** Connector interface (discover, read_state, execute,
      subscribe), aiomqtt integration, topic mapping
    - **SE plans:** Implementation files, test strategy, async patterns
    - **UXE plans:** Config YAML ergonomics, error messages, logging
    - All three reach consensus
18. Creates branch `feature/42-mqtt-connector`
19. Writes code: `connectors/mqtt.py`, `tests/test_mqtt.py`
20. Runs `pytest tests/ -v` — all pass
21. Runs `ruff check .` — clean
22. Commits and pushes
23. Opens PR with triad-structured description (architecture, implementation,
    UX sections), linking `Closes #42`
24. Labels PR `state:code-review`
25. **Writes updated TicketContext** with `pr_number`, `branch_name`,
    `implementation_notes`

### Phase 5: Code Review

26. **Orchestrator** sees ticket in `state:code-review`
27. Dispatches **Sr. Engineer (Reviewer)**
28. Reviewer fetches PR details and full diff
29. Reviews against 7 dimensions (correctness, architecture, security,
    testing, performance, code quality, UX)
30. If issues found: `REQUEST CHANGES` → ticket back to `in-progress`,
    triad re-dispatched with feedback. Go to step 17.
31. If clean: `APPROVE` → ticket transitions to `state:security-review`

### Phase 6: Security Review (Dual)

32. **Orchestrator** dispatches both **Security** and **InfoSec** agents
    (via `dispatch_security_review()`, which triggers both workflows)

33. **Security Engineer** (in parallel):
    - Scans diff for OWASP Top 10
    - Checks subprocess calls, input validation, path traversal
    - Checks for MQTT-specific concerns (topic injection, auth)
    - Posts security review with verdict + findings

34. **InfoSec Agent** (in parallel):
    - Evaluates trust boundary impact (MQTT broker = new trust boundary)
    - Data flow analysis (device commands over MQTT)
    - Attack surface assessment (new network listener)
    - Posts infosec review with verdict

35. Both write `SecurityReviewEntry` objects to the TicketContext
36. **Both must approve.** The InfoSec agent checks
    `context.security_approved()` which requires both `security` and
    `infosec` verdicts to be `approved`
37. If either blocks: ticket goes to `in-progress` with
    `security:blocked` label. Engineer addresses findings. Go to step 17.
38. If both approve: ticket moves to `state:qa`

### Phase 7: QA

39. **Orchestrator** dispatches **QA Agent**
40. QA runs full test suite
41. Checks each acceptance criterion from the original ticket
42. Regression checks affected areas
43. Exploratory testing for edge cases
44. If failures: `FAILED` → ticket back to `in-progress`. May file
    regression bugs via `file_bug` tool
45. If clean: `PASSED` → ticket moves to `state:deploying`

### Phase 8: Deployment

46. **Orchestrator** triggers deployment via `dispatch_deploy()`
47. PR is merged
48. Ticket moves to `state:deployed`, then eventually `state:archived`

### Total Agents Involved: 7+

Triage → PM → Orchestrator → Triad (DE+SE+UXE) → Reviewer → Security
→ InfoSec → QA → Orchestrator (deploy)

Each handoff preserves full context via structured JSON blocks in issue
comments.

---

## Context Handoff Protocol

The most critical piece of the system. Agents are stateless — they don't
share memory. All context flows through **TicketContext** objects
serialized as JSON in GitHub issue comments.

### TicketContext Structure

Defined in `agents/context.py`:

```python
@dataclass
class TicketContext:
    # Identity
    ticket_id: int
    title: str
    description: str

    # Classification (set by triage)
    ticket_type: str          # "epic", "feature", "bug", "chore"
    epic_ref: int | None      # parent epic issue number
    user_story: str
    acceptance_criteria: list[str]

    # Triage results
    feasibility_assessment: str
    scope_estimate: str       # "XS", "S", "M", "L", "XL"
    priority: str             # "P0-critical" through "P4-backlog"
    estimated_effort_hours: float
    triage_decision: str      # "accepted", "rejected", "needs-info"
    triage_reasoning: str

    # Development (set by engineer)
    assigned_engineer: str
    branch_name: str
    pr_number: int | None
    implementation_notes: str
    blocked: bool
    block_reason: str

    # Reviews (appended by reviewer, security, QA)
    reviews: list[dict]
    security_reviews: list[dict]
    qa_results: list[dict]

    # Lifecycle
    state: str
    state_history: list[dict]   # every state transition with timestamp
    handoffs: list[dict]        # every agent-to-agent handoff
    created_at: float
    updated_at: float
```

### How Context Blocks Look in GitHub

When an agent writes context, it posts a comment like:

```html
<!-- AGENT_CONTEXT_START -->
```json
{
  "ticket_id": 42,
  "state": "in-progress",
  "priority": "P2-medium",
  "pr_number": 7,
  "branch_name": "feature/42-mqtt-connector",
  "reviews": [...],
  "security_reviews": [...],
  "handoffs": [
    {"from_role": "triage", "to_role": "engineer", "reason": "accepted", "timestamp": 1709312400},
    {"from_role": "engineer", "to_role": "reviewer", "reason": "PR ready", "timestamp": 1709315000}
  ]
}
```
<!-- AGENT_CONTEXT_END -->

*Context updated by `engineer` agent at 2026-03-01 12:30 UTC*
```

### Reading Context

When an agent starts, it calls `self.read_context(issue_number)`:

1. Fetches all comments on the issue via GitHub API
2. Scans comments in **reverse order** (most recent first)
3. Finds the first comment containing `<!-- AGENT_CONTEXT_START -->` and
   `<!-- AGENT_CONTEXT_END -->` markers
4. Parses the JSON between the markers
5. Returns a `TicketContext` dataclass

This ensures agents always read the most recent context, even if multiple
agents have written context blocks.

### Writing Context

After completing work, agents call `self.post_context(issue_number, ctx)`:

1. Serializes the TicketContext to JSON
2. Wraps it in the marker comments
3. Posts as a new issue comment
4. The next agent to read this issue gets the updated context

### What Gets Preserved Across Handoffs

| From Agent | What It Writes | Used By |
|------------|---------------|---------|
| Triage | priority, scope, effort, type, decision | PM, Engineer |
| PM | acceptance criteria, user story | Engineer, QA |
| Engineer | branch_name, pr_number, implementation_notes | Reviewer, Security, QA |
| Reviewer | review verdict, feedback details | Engineer (if changes needed) |
| Security | findings, severity, verdict | InfoSec (for dual check), Engineer |
| InfoSec | threat model impact, verdict | QA (proceed gate) |
| QA | test results, failures, verdict | Orchestrator (deploy gate) |

---

## Dispatch Mechanism

Agents don't call each other directly. The **Orchestrator** dispatches
agents by triggering GitHub Actions workflows.

### How Dispatch Works

```
Orchestrator calls dispatch_engineer_for_ticket(github, issue_number=42)
    │
    ▼
dispatch.py maps AgentRole.ENGINEER → "agent-develop.yml"
    │
    ▼
github.dispatch_workflow("agent-develop.yml", inputs={"issue_number": "42", "action": "develop"})
    │
    ▼
`gh workflow run agent-develop.yml -f issue_number=42 -f action=develop`
    │
    ▼
GitHub Actions starts the workflow
    │
    ▼
Workflow runs: python -m agents.scripts.run_agent --role engineer --action develop --issue-number 42
    │
    ▼
run_agent.py instantiates TriadSquadAgent and calls .run({"action": "develop", "issue_number": "42"})
```

### Workflow-to-Agent Mapping

| Workflow File | Agent Role(s) | Trigger |
|---------------|--------------|---------|
| `agent-orchestrator.yml` | Orchestrator | Cron (15 min) or escalation |
| `agent-triage.yml` | Triage, PM | New issue webhook or dispatch |
| `agent-develop.yml` | Engineer/Triad | Orchestrator dispatch |
| `agent-review.yml` | Sr. Engineer | Orchestrator dispatch |
| `agent-security.yml` | Security, InfoSec | Orchestrator dispatch |
| `agent-qa.yml` | QA | Orchestrator dispatch |
| `agent-wildcard.yml` | Wildcard | Weekly cron or dispatch |
| `agent-blog.yml` | Blog | PM request or dispatch |
| `agent-deploy.yml` | (deployment) | Orchestrator dispatch |

### Escalation Path

When an engineer is blocked:

1. Engineer calls `signal_block(issue_number, reason)`
2. This transitions the ticket to `state:blocked`
3. Dispatches `agent-orchestrator.yml` with action `escalate`
4. Orchestrator receives the escalation, reads the block reason
5. Decides: dispatch another engineer, re-scope, or archive

---

## The Agentic Loop

Every agent's core execution follows the same pattern, implemented in
`Agent.agentic_loop()` (`agents/base.py:130`):

```
┌──────────────────────────────────────────────────────┐
│                    agentic_loop()                     │
│                                                      │
│  messages = [initial user message with context]      │
│                                                      │
│  for iteration in range(MAX_THINK_ITERATIONS=10):    │
│      │                                               │
│      ▼                                               │
│  ┌────────────┐                                      │
│  │   THINK    │  Call Claude API with:               │
│  │            │  - system prompt (role-specific)      │
│  │            │  - messages (conversation so far)     │
│  │            │  - tools (role-specific tool defs)    │
│  └─────┬──────┘                                      │
│        │                                             │
│        ▼                                             │
│  ┌─────────────────────────────┐                     │
│  │  Parse response             │                     │
│  │  - Extract text blocks      │                     │
│  │  - Extract tool_use blocks  │                     │
│  └─────┬───────────────────────┘                     │
│        │                                             │
│        ├── No tool calls? ──► Return final text      │
│        │                       (loop ends)           │
│        │                                             │
│        ▼                                             │
│  ┌────────────┐                                      │
│  │    ACT     │  For each tool call:                 │
│  │            │  - Dispatch to handle_tool_call()     │
│  │            │  - Get result (GitHub API, file I/O,  │
│  │            │    git ops, subprocess, etc.)         │
│  └─────┬──────┘                                      │
│        │                                             │
│        ▼                                             │
│  ┌────────────────────────┐                          │
│  │  Append to messages:   │                          │
│  │  - assistant message   │                          │
│  │    (with tool_use)     │                          │
│  │  - user message        │                          │
│  │    (with tool_results) │                          │
│  └────────────────────────┘                          │
│        │                                             │
│        └──── Loop back to THINK ─────────────────────┘
│                                                      │
└──────────────────────────────────────────────────────┘
```

**Key details:**
- Max 10 iterations prevents runaway loops
- Text from the final response is returned as the agent's output
- Tool results are JSON-serialized and fed back as `tool_result` blocks
- The conversation grows with each iteration — Claude sees the full
  history of its own tool calls and their results

---

## Tool System

Tools are defined per-agent as JSON schemas matching the Anthropic tool
use specification.

### Common Tools (all agents)

Every agent inherits these from `Agent._common_tools()`:

| Tool | Description | GitHub Operation |
|------|-------------|-----------------|
| `comment_on_issue` | Post a markdown comment | `gh issue comment` |
| `add_labels` | Add labels to an issue | `gh issue edit --add-label` |
| `remove_labels` | Remove labels from an issue | `gh issue edit --remove-label` |
| `get_issue` | Get issue details + comments | `gh issue view --json` |
| `list_issues` | List issues with filters | `gh issue list --label` |
| `update_ticket_state` | Transition state (validates via state machine) | Label swap |
| `create_issue` | Create a new issue | `gh issue create` |
| `close_issue` | Close an issue | `gh issue close` |

### Role-Specific Tools

Each role adds specialized tools. Examples:

- **Orchestrator:** `dispatch_*` tools for triggering agent workflows
- **Engineer/Triad:** `read_file`, `write_file`, `run_command`,
  `git_create_branch`, `git_commit_and_push`, `create_pr`, `signal_block`
- **Reviewer:** `get_pr_details`, `get_pr_diff`, `submit_review`
- **Security:** `get_pr_diff`, `submit_security_review`
- **QA:** `run_tests`, `submit_qa_result`, `file_bug`
- **Wildcard:** `scan_directory`, `search_pattern`, `run_linter`,
  `file_finding`

### Tool Execution Safety

- **Command allowlist** (engineer): Only `pytest`, `ruff`, `mypy` can be
  executed via `run_command`
- **Path traversal prevention**: File read/write operations normalize
  paths and reject `..` or absolute paths
- **Secret file protection**: Refuses to write to `.env`, `secrets.yaml`,
  or files containing `credentials`
- **Subprocess timeout**: All commands have 120s timeout
- **Output truncation**: Long outputs are truncated to prevent context
  overflow (3000-5000 chars)

---

## Security Model

### Agent Capabilities Matrix

Capabilities are declared in `agents/config.py` and enforced by tool
availability:

| Capability | Orchestrator | PM | Triage | Engineer | Reviewer | Security | QA | Wildcard |
|-----------|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| can_dispatch | x | x | | | | | | |
| can_create_issues | x | x | x | | | | x | x |
| can_manage_board | x | x | | | | | | |
| can_close_issues | x | x | | | | | | |
| can_write_code | | | | x | | | | |
| can_create_prs | | | | x | | | | |
| can_review_prs | | | | | x | x | | |
| can_approve_prs | | | | | x | | | |
| can_block_deploy | | | | | | x | | |
| can_run_tests | | | | | | | x | |
| can_scan_codebase | | | | | | | | x |

### Deployment Safety Chain

```
Code written by Engineer
    │
    ▼ (must pass)
Reviewed by Sr. Engineer ──► Changes requested? → Back to Engineer
    │
    ▼ (must pass BOTH)
Security Engineer approves ──┐
                             ├──► Either blocks? → Back to Engineer
InfoSec Agent approves ──────┘
    │
    ▼ (must pass)
QA validates ──► Tests fail? → Back to Engineer
    │
    ▼
Deploy (orchestrator)
```

No code can skip any gate. The state machine enforces the order.

---

## Configuration

All agent configuration lives in `agents/agents.yaml`.

### Key Configuration Options

```yaml
system:
  max_dispatches_per_cycle: 10    # Prevent runaway costs
  stale_ticket_days: 7            # Flag stale tickets
  archive_inactive_days: 30       # Auto-archive old tickets
  max_tokens_per_cycle: 50000     # Global token budget
  model_default: "claude-sonnet-4-6"

agents:
  orchestrator:
    response_delay_minutes: 15    # Cron interval
    model: "claude-sonnet-4-6"
    max_tokens: 8192

  engineer:
    triad_mode: true              # Use triad squad (DE+SE+UXE)
    model: "claude-sonnet-4-6"
    max_tokens: 8192

  wildcard:
    scan_schedule: "weekly"
    max_tokens: 8192

security:
  required_approvals: [security, infosec]  # Both must approve
  auto_block_severity: [critical, high]    # Auto-block on these

lifecycle:
  state_agents:                   # Who acts at each state
    ready: [orchestrator]
    in-progress: [engineer]
    code-review: [sr-engineer]
    security-review: [security, infosec]
    qa: [qa]
```

### Environment Variables

| Variable | Required | Used By |
|----------|---------|---------|
| `ANTHROPIC_API_KEY` | Yes | All agents (Claude API) |
| `GITHUB_TOKEN` | Yes | All agents (GitHub operations) |
| `GITHUB_REPOSITORY` | Yes | All agents (repo identifier) |
| `GITHUB_WORKSPACE` | Optional | Engineer/QA (working directory) |

---

## How to Extend

### Adding a New Agent Role

1. **Define the role** in `agents/config.py`:
   ```python
   class AgentRole(Enum):
       MY_AGENT = "my-agent"
   ```

2. **Add capabilities** in `AGENT_CAPABILITIES`:
   ```python
   AgentRole.MY_AGENT: {
       "model": "claude-sonnet-4-6",
       "max_tokens": 4096,
       "can_do_something": True,
       "description": "What this agent does",
   }
   ```

3. **Create the agent class** in `agents/roles/my_agent.py`:
   ```python
   class MyAgent(Agent):
       role = AgentRole.MY_AGENT

       @property
       def system_prompt(self) -> str:
           return "..."

       def get_tools(self) -> list[dict]:
           tools = self._common_tools()
           tools.append({...})  # your custom tools
           return tools

       def handle_tool_call(self, name, params):
           match name:
               case "my_tool":
                   return self._do_something(params)
               case _:
                   return self._handle_common_tool(name, params)

       def run(self, trigger):
           # gather context, build messages, call self.agentic_loop()
   ```

4. **Register** in `agents/scripts/run_agent.py`:
   ```python
   from agents.roles.my_agent import MyAgent
   AGENT_REGISTRY["my-agent"] = MyAgent
   ```

5. **Map to a workflow** in `agents/dispatch.py`:
   ```python
   WORKFLOW_MAP[AgentRole.MY_AGENT] = "agent-my-agent.yml"
   ```

6. **Create the GitHub Actions workflow** (`.github/workflows/agent-my-agent.yml`)

7. **Add to `agents.yaml`** with configuration

### Adding a New Tool to an Existing Agent

1. Add the tool definition in the agent's `get_tools()` method
2. Add the handler in `handle_tool_call()` (via match/case)
3. Implement the actual tool logic as a private method

### Adding a New State

1. Add to `TicketState` enum in `agents/state.py`
2. Add valid transitions in `TRANSITIONS` dict
3. Add label definition in `STATE_LABELS`
4. Update `state_agents` in `agents.yaml`

---

## Key Files Reference

| File | Lines | Purpose |
|------|-------|---------|
| `agents/base.py` | 418 | Base Agent class, agentic loop, common tools |
| `agents/context.py` | 189 | TicketContext dataclass, handoff serialization |
| `agents/state.py` | 139 | State machine, valid transitions, label scheme |
| `agents/dispatch.py` | 199 | Workflow dispatch functions |
| `agents/config.py` | 215 | Role definitions, capabilities, YAML config loader |
| `agents/github_ops.py` | 304 | GitHub REST/GraphQL API via `gh` CLI |
| `agents/agents.yaml` | 161 | Agent configuration |
| `agents/roles/orchestrator.py` | 323 | Root coordinator |
| `agents/roles/pm.py` | 287 | Product manager |
| `agents/roles/triage.py` | 217 | Multi-perspective triage |
| `agents/roles/triad.py` | 475 | Engineering triad (DE+SE+UXE) |
| `agents/roles/engineer.py` | 402 | Standalone engineer |
| `agents/roles/reviewer.py` | 252 | Sr. engineer code review |
| `agents/roles/security.py` | 406 | Security + InfoSec pair |
| `agents/roles/qa.py` | 256 | QA validation |
| `agents/roles/wildcard.py` | 262 | Codebase auditor |
| `agents/roles/blog.py` | 203 | Blog writer |
| `agents/scripts/run_agent.py` | 101 | CLI entry point |

---

## Handoff Checklist for Receiving Model

If you are a model receiving this document as context for continuing
development, here is what you need to know:

1. **The agent system is production-ready** — 4,500+ lines of tested
   Python. The framework works.

2. **The home assistant runtime does not exist yet** — the agents are
   building toward Phase 1 of Clawssistant (see CLAUDE.md). The actual
   voice pipeline, memory system, connectors, skills, and API server are
   planned but unimplemented.

3. **To run an agent locally:**
   ```bash
   export ANTHROPIC_API_KEY="sk-..."
   export GITHUB_TOKEN="ghp_..."
   export GITHUB_REPOSITORY="owner/repo"

   python -m agents.scripts.run_agent --role engineer --action develop --issue-number 42
   ```

4. **To add a ticket to the pipeline:** Create a GitHub issue with
   `state:new` label. The triage agent will pick it up.

5. **The Orchestrator is the entry point** — if you're confused about
   what to do, read `orchestrator.py`. It's the root that dispatches
   everything else.

6. **Context is everything** — always read and write TicketContext blocks.
   Without them, the next agent in the chain has no idea what happened.

7. **Never skip security review** — the dual-gate (Security + InfoSec)
   exists for a reason. This project controls physical devices in homes.

8. **State transitions are enforced** — you cannot jump from `new` to
   `deployed`. Follow the state machine.

9. **All GitHub operations use `gh` CLI** — not raw HTTP. This is
   intentional for auth simplicity and consistency.

10. **The triad is the default engineer** — when `engineer` is dispatched,
    it actually runs `TriadSquadAgent` (three perspectives in one context),
    not the simpler `EngineerAgent`.
