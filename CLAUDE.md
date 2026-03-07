# CLAUDE.md — Product Schema Map System
## Session contract for Claude Code / Opus

---

## What we are building

A schema-driven product data system with a single source of truth and four distinct
frontend views — customer, sales, engineer, management. Each view is a map drawn for
a specific traveller making specific decisions. The source data does not change. The
maps do.

The system is built on the principle that **definitions are the hard problem, not the
code**. The schema is the governance mechanism. Agents are plumbers — they connect
pipes according to the schema. The schema tells them what to do. Update the schema,
the system adapts.

Core philosophy: data is not reality, but it is all we have. Every schema is a map,
not the territory. Maps are drawn for use cases, not for completeness.

---

## Coding standards

- Readable by a kindergartener. Explicit over clever.
- Security and readability first, performance second.
- Every decision that touches data must be logged (shadow pattern).
- Schema validation is not optional — it is the contract.
- Human-in-the-loop is a first class feature, not an escape hatch.
- No hidden state. No silent failures.
- If it cannot be expressed in a schema, it is not yet defined.

---

## What to harvest from existing projects

### 1. `C:\Users\pertt\Agentic-midi-generator`
**Take:** The Tkinter GUI architecture.
- The DAW-style layout — see everything at once, expand any panel for full detail
- Overview first, details on demand pattern
- Resizable paned windows
- Modern Tkinter design approach — proper spacing, fonts, color scheme
- The single screen that shows all four views at overview level simultaneously
- Each panel expandable to full detail on click

**Do not take:** Any MIDI, audio, or music-specific logic.

---

### 2. `C:\Users\pertt\Data-agents-demo`
**Take:** The full agent network and communication pattern.
- `runtime/excel_flow.py` — orchestration pattern, `puhemies_run_from_file`, `puhemies_continue`
- `runtime/data_janitor.py` — data cleaning and normalization
- Schema validation and human confirmation flow
- `shadow.jsonl` audit trail pattern — every event logged, nothing hidden
- `artifacts/` output structure — `schema_spec.json`, `evidence_packet.json`, `human_confirmation.json`
- Thin UI shells over a shared runtime core
- The `agent-base/` canonical agent definitions

**Key pattern to preserve:** Agents communicate through structured JSON contracts.
The orchestrator (puhemies) routes between agents. Human confirmation is requested
when confidence is low and the decision is recorded permanently.

---

### 3. `C:\Users\pertt\agent-learning`
**Evaluate and take if suitable:**
- SpeakerAgent orchestrator pattern — receives prompt, selects method circuit, fuses responses
- Verification/judging loops with revision gating — this is the judge agent pattern
- Shadow/monitoring layer — JSONL run histories and drift metrics
- Dataframe pipeline — header/schema inference, transforms, validation, save agents
- Filesystem allowlist pattern for safe writes
- Reusable template assets

**The judge/verification loop is particularly relevant** — agents that fail schema
validation should be given additional context and retried before escalating to human
confirmation. This is the healing-by-deepening pattern. More context, not restart.

---

### 4. `C:\Users\pertt\Support-triage-llm`
**Evaluate and take if suitable:**
- Copy `AGENT_GUIDE.md` → `agent.md` in new project root
- Closed-loop learning pattern — feedback improves future runs
- SQLite for local persistent state
- Ollama integration for local LLM inference
- The headless / local-first architecture — no cloud dependency for core function
- Read `AGENT_GUIDE.md`, `DESIGN.md`, `docs/overview_en.md` before deciding what to port

---

## System architecture

### Source of truth
One product dataset. Made up but realistic — fasteners/industrial products with:
- Product code as primary key (stable, short, dumb — just a reference)
- Full attribute set hanging off the key:
  - Physical specs (dimensions, material, coating, standard)
  - Commercial data (pricing tiers, lead times, supplier codes)
  - Logistics data (inventory, warehouse location, reorder point)
  - Classification (product family, application, approved uses)
  - Governance (who defined this, when, version, review date)

### The five definition questions (every attribute must answer these)
1. **Where does it live** — which system owns it, is this a copy
2. **What format** — type, length, units, allowed values, null handling
3. **Who is responsible** — who creates, who can change, who resolves conflicts
4. **Who has access** — read/write/delete/history per role
5. **Why does it exist** — what decision does this serve, what breaks if wrong

### Schema layer
- Source schema — full attribute set, owned by engineer role
- Customer view schema — filterable specs, plain language, no internal codes, no pricing
- Sales view schema — inventory, lead times, pricing tiers, margin, customer history
- Engineer view schema — full precision, standards references, version history, tolerances
- Management view schema — aggregates, coverage gaps, exception flags, trends

### Agent network
- **Puhemies (orchestrator)** — receives requests, routes to correct agent circuit,
  fuses responses, requests human confirmation when confidence is low
- **Schema validation agent** — validates all input against source schema,
  dead-letters failures with reason codes
- **Transform agents** — one per view, converts source schema to view schema
- **Janitor agent** — cleans and normalizes incoming data
- **Judge agent** — reviews transform outputs, gates revision if output fails
  view schema contract, increases context budget for struggling agents before
  escalating to human
- **Shadow agent (invisible eye)** — logs everything to JSONL, no opinions,
  never intervenes, pure observer. Cannot be influenced by other agents.
- **Learning agent** — tracks confirmed human decisions, updates confidence
  scores for future similar cases

### Frontend (Tkinter)
Single window. Four resizable panels — customer, sales, engineer, management.
Each panel shows overview data at rest. Click any panel to expand to full detail.
Collapse returns to overview. All four maps visible simultaneously.

The UI is a thin shell. All logic lives in runtime. Swapping UI should require
zero changes to runtime.

---

## Repo structure

```
/schema
    source_schema.json          — full product attribute definitions
    customer_view.json          — customer map definition
    sales_view.json             — sales map definition  
    engineer_view.json          — engineer map definition
    management_view.json        — management map definition
    definition_of_definition.json — the meta-schema

/data
    products.json               — made up product dataset
    samples/                    — smaller test sets

/runtime
    orchestrator.py             — puhemies, routing, fusion
    schema_validator.py         — validation against any schema
    transform_agents.py         — one transform function per view
    janitor.py                  — cleaning and normalization
    judge.py                    — review, revision gating
    shadow.py                   — invisible eye, JSONL logger
    learning.py                 — confidence tracking

/frontends
    tkinter_app.py              — four panel DAW-style main window
    panels/
        customer_panel.py
        sales_panel.py
        engineer_panel.py
        management_panel.py

/artifacts
    (runtime outputs — schema specs, evidence packets, shadow logs)

/tests
    test_schema_validation.py
    test_transforms.py
    test_orchestrator.py

/agent-base
    (canonical agent definitions, mirrored from Data-agents-demo)

/docs
    overview.md
    schema_guide.md

agent.md                        — copied from Support-triage-llm AGENT_GUIDE.md
CLAUDE.md                       — this file
README.md
```

---

## First session tasks

1. Read `agent.md` (copied from Support-triage-llm) and note reusable patterns
2. Scan the four source repos and identify exact files to port
3. Create `/schema/definition_of_definition.json` — the meta-schema answering
   all five definition questions for every field
4. Create `/data/products.json` — realistic made up fastener/industrial dataset,
   minimum 20 products, enough variance to test all view transforms
5. Create `/schema/source_schema.json` from the product dataset
6. Derive the four view schemas from the source
7. Port runtime core from Data-agents-demo
8. Build the judge/healing layer from agent-learning
9. Build the four Tkinter panels from Agentic-midi-generator DAW pattern
10. Wire everything together in orchestrator

---

## Definition of done for first working version

- One product dataset loads from JSON
- All four view schemas validate against source schema
- Each view transform produces correct output for all 20 products
- Shadow log captures every transform event
- Human confirmation requested for any product failing view schema
- Tkinter window shows all four panels at overview
- Any panel expands to full detail on click
- README explains the map philosophy in plain language

---

## Notes

- Local first. No cloud dependency for core function.
- Ollama for any LLM inference (RTX 4070, 12GB VRAM)
- SQLite for persistent state if needed
- Streamlit demo can come later — Tkinter is the primary interface
- The invisible eye (shadow agent) logs to JSONL always, no exceptions
- Puhemies is the orchestrator. The name stays.

---

*Data is not reality. But it is all we have.*
*Every schema is a map. Maps are drawn for travellers, they are drawn for navigators, they are drawn for explorers. They all need a different map*
*Define it in the schema or it does not exist.*
