# CodeSage — Multi-Agent Legacy Codebase Modernization Analyzer

A multi-agent system that ingests a legacy codebase, reasons about its structure, risk, and modernization path, and produces a structured "Modernization Readiness Report" — the same category of problem CloudHedge's OmniDeq/CHAI platform solves for enterprise clients.

---

## 1. Problem Statement

Enterprises sitting on legacy monoliths (old Java, .NET, or tightly-coupled service code) need to decide **what to modernize, in what order, and how risky each piece is** before committing engineering time to a rewrite or containerization effort. Today this is done manually: senior engineers spend weeks reading code, drawing dependency diagrams, and writing risk assessments by hand.

**Goal:** Build a multi-agent pipeline that takes a codebase (a GitHub repo or local folder) and automatically produces:

1. A **structural map** of the codebase (modules, dependencies, entry points)
2. A **modernization readiness score** per module (tightly-coupled legacy code = harder/riskier to modernize)
3. A **prioritized migration plan** (which modules to modernize first, and why)
4. A **human-readable report** (Markdown/PDF) a tech lead could actually hand to a client

This mirrors what CHAI DART (deep intelligence via "Trivector Assessment") and OmniDeq do — assess, then plan, then execute modernization — just at a smaller, learnable scale.

---

## 2. Why Multi-Agent (and not a single LLM call)

A single prompt can't hold an entire codebase in context, and different sub-tasks require genuinely different reasoning modes:

- **Parsing/structural analysis** is deterministic and code-heavy — better done with static analysis tools than an LLM guessing.
- **Risk assessment** requires judgment and synthesis across many files — good LLM use case.
- **Prioritization/planning** requires weighing trade-offs and producing a coherent narrative — another distinct reasoning task.
- **Report writing** is a different skill from analysis — formatting, tone, audience-awareness.

Splitting these into specialized agents means each agent gets a focused prompt, a narrow tool set, and its own context window — instead of one giant prompt trying to do everything (and hallucinating when it runs out of room).

---

## 3. Why LangGraph + CrewAI Together (not just one)

You're learning both, so this project is deliberately structured to use each where it's actually the better tool — not just to force both in:

| Framework | Used for | Why |
|---|---|---|
| **LangGraph** | The overall pipeline: parsing → analysis → prioritization → report, plus retry/error loops | LangGraph is a *graph*, not a *chat*. You need explicit control flow here: "if static analysis fails, retry with a smaller file batch," "if risk-scoring confidence is low, route back to analysis with more context." That's state-machine logic, which LangGraph is built for. |
| **CrewAI** | The Risk Assessment stage internally — a "crew" of 3 specialist agents (Security Reviewer, Complexity Reviewer, Dependency Reviewer) who each independently review the same module and then reconcile | CrewAI shines at *role-based collaboration* — several agents with distinct personas debating/converging on one artifact. That's a natural fit for "three reviewers give their opinion, then we synthesize," which is exactly how human code review works. |

**In short:** LangGraph owns the *pipeline* (deterministic control flow across stages). CrewAI owns *one node inside that pipeline* where you specifically want multiple agent personas collaborating. This also happens to mirror real systems — CHAI Universe (orchestration) coordinating CHAI DART (specialist assessment agents).

---

## 4. Architecture

```
                         ┌─────────────────────────┐
                         │      LangGraph State     │
                         │   (shared across nodes)  │
                         └─────────────────────────┘
                                     │
   ┌────────────┐      ┌────────────▼────────────┐      ┌──────────────────┐
   │   Ingest    │─────▶│   Static Analysis Node   │─────▶│  Dependency Graph  │
   │  (clone /   │      │  (AST parsing, imports,  │      │     Builder Node   │
   │   read repo)│      │   cyclomatic complexity) │      │  (networkx graph)  │
   └────────────┘      └──────────────────────────┘      └─────────┬─────────┘
                                                                     │
                                                                     ▼
                                                  ┌───────────────────────────────┐
                                                  │   Risk Assessment Node         │
                                                  │   (CrewAI crew, per module)    │
                                                  │  ┌───────────┐ ┌────────────┐  │
                                                  │  │ Security  │ │ Complexity │  │
                                                  │  │ Reviewer  │ │  Reviewer  │  │
                                                  │  └─────┬─────┘ └─────┬──────┘  │
                                                  │        │             │         │
                                                  │        ▼             ▼         │
                                                  │   ┌───────────────────────┐    │
                                                  │   │  Dependency Reviewer   │    │
                                                  │   └───────────┬───────────┘    │
                                                  │               ▼                │
                                                  │    Manager/Synthesizer Agent    │
                                                  │    (reconciles 3 opinions →     │
                                                  │     one readiness score)        │
                                                  └───────────────┬───────────────┘
                                                                  │
                                                                  ▼
                                                  ┌───────────────────────────────┐
                                                  │   Prioritization Node          │
                                                  │  (LangGraph + single LLM call: │
                                                  │   ranks modules, builds a      │
                                                  │   migration sequence)          │
                                                  └───────────────┬───────────────┘
                                                                  │
                                                                  ▼
                                                  ┌───────────────────────────────┐
                                                  │   Report Generation Node       │
                                                  │  (formats final Markdown/PDF   │
                                                  │   report for a human reader)   │
                                                  └───────────────────────────────┘

     ⤷ Conditional edge: if Static Analysis confidence < threshold,
       loop back to Ingest with a narrower file batch (LangGraph handles this retry)
```

---

## 5. Component Breakdown & Tech Choices

### 5.1 Ingest Node
- **What:** Clones/reads the target repo, filters to relevant source files (skip node_modules, vendor dirs, etc.)
- **Tools:** `GitPython`, simple filesystem walk
- **Why not an LLM here:** This is pure I/O and filtering — deterministic, no reasoning needed. Don't burn tokens on it.

### 5.2 Static Analysis Node
- **What:** Parses each file's AST to extract imports, function/class definitions, cyclomatic complexity, and lines of code
- **Tools:** `ast` (Python's built-in parser) for Python codebases, or `tree-sitter` if you want multi-language support (recommended — tree-sitter has grammars for Java, C#, JS, etc., which matters since enterprise legacy code is rarely Python)
- **Why:** Structural facts (imports, complexity) should come from real parsing, not LLM guesses — LLMs are unreliable at exact structural extraction and it's wasteful to use them for something a parser does deterministically and instantly.

### 5.3 Dependency Graph Builder
- **What:** Turns the parsed imports into a directed graph (which modules depend on which)
- **Tools:** `networkx`
- **Why it matters for modernization:** A module with many incoming dependencies is riskier to touch first (breaking it breaks everything downstream). This graph is what makes your "prioritization" step *evidence-based* rather than the LLM just guessing at importance.

### 5.4 Risk Assessment Node (CrewAI)
- **What:** For each module, three agents independently assess it, then a manager agent reconciles their views into one score + rationale
  - **Security Reviewer** — flags risky patterns (hardcoded secrets, unsafe deserialization, outdated crypto calls)
  - **Complexity Reviewer** — uses the cyclomatic complexity + LOC data from static analysis to judge "how hard would this be to safely refactor"
  - **Dependency Reviewer** — uses the dependency graph to judge blast radius if this module changes
  - **Manager/Synthesizer Agent** — takes all three opinions and produces one final `ModernizationRisk` object (score 1–10 + written justification)
- **Why CrewAI specifically:** This is a genuine multi-perspective task where you *want* disagreement surfaced and reconciled, not averaged silently. CrewAI's role/goal/backstory pattern forces each agent to stay in its lane (the Security Reviewer shouldn't start commenting on complexity), which keeps the outputs cleanly separable before synthesis.

### 5.5 Prioritization Node (back in LangGraph)
- **What:** Takes all modules' risk scores + dependency graph and produces an ordered migration plan (e.g., "start with low-risk, high-centrality modules to build confidence before tackling the risky core")
- **Why a plain LLM call here, not another crew:** This is a single coherent planning task over already-structured data — no need for multiple personas, just good reasoning over a clean input. Using CrewAI here would be over-engineering.

### 5.6 Report Generation Node
- **What:** Formats everything into a client-readable Markdown (or PDF) report: executive summary, module-by-module risk table, recommended migration order, rationale
- **Why separate from prioritization:** Writing *for a specific audience* (a non-technical stakeholder vs. an engineer) is a distinct skill from doing the analysis. Keeping it separate also means you can swap output formats (Markdown for engineers, a slide-style summary for execs) without touching the analysis logic.

---

## 6. State Schema (LangGraph)

```python
from typing import TypedDict, List, Dict
from langgraph.graph import StateGraph, END

class ModuleInfo(TypedDict):
    path: str
    imports: List[str]
    loc: int
    cyclomatic_complexity: float

class RiskAssessment(TypedDict):
    module_path: str
    security_notes: str
    complexity_notes: str
    dependency_notes: str
    final_score: int          # 1-10, synthesized
    rationale: str

class PipelineState(TypedDict):
    repo_path: str
    modules: List[ModuleInfo]
    dependency_graph: Dict[str, List[str]]   # adjacency list
    risk_assessments: List[RiskAssessment]
    migration_plan: List[str]                # ordered module paths
    final_report: str
    retry_count: int                         # for the conditional retry loop
```

---

## 7. Why This Project Maps Well to CHAI/OmniDeq-Style Work

| This project | CHAI / OmniDeq equivalent |
|---|---|
| Static analysis + dependency graph | "Trivector Assessment" (CHAI DART) — deep structural intelligence before touching code |
| CrewAI risk-assessment crew | Multiple specialist AI agents reasoning over the same legacy application |
| Prioritization node | Modernization sequencing / migration blueprinting |
| Report generation | Client-facing modernization readiness output |
| Conditional retry edges in LangGraph | Real production pipelines need self-correction, not just a happy path |

Being able to explain *why* you split work this way (not just that you used two frameworks) is what will actually land in an interview — anyone can call `crewai.Crew().kickoff()`, but explaining why static analysis shouldn't go through an LLM, or why risk assessment specifically benefits from multiple personas, shows you understand the design trade-offs CloudHedge's own engineers make daily.

---

## 8. Suggested Build Order (so it's demoable incrementally)

1. Ingest + static analysis + dependency graph (get real structural output first — no LLM needed yet)
2. Wire up LangGraph skeleton with stub nodes that just pass data through
3. Build the CrewAI risk-assessment crew on 2-3 real modules, tune prompts
4. Plug the crew in as a LangGraph node
5. Add prioritization node
6. Add report generation
7. **Last:** add the conditional retry edge (this is the part that shows you understand LangGraph beyond a linear chain — save it for once the happy path works)

---

## 9. Stretch Goals (if you have time before interviews)

- Swap `ast` for `tree-sitter` to support a real enterprise language (Java/C#) instead of just Python — this directly addresses the "legacy enterprise codebase" gap
- Add a RAGAS-style evaluation step scoring how consistent the risk assessments are across repeated runs (ties back to your existing RAG project's "roadmap" item)
- Add a simple Terraform snippet generator as a bonus output ("here's the containerization scaffold for the top-priority module") — touches the Infrastructure-as-Code gap