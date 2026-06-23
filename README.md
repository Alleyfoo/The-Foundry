# 🔥 The Foundry

**Authority-aware governance for business change.**

A supplier emails a new price list. Someone in pricing pushes it through. The new
number is now live in SAP — except the person who approved it was never authorised
to make pricing decisions. Nobody noticed, because the system only checked *that* an
approval happened, not *whether the approver had the authority to give it.*

That gap — between who touched a change and who was actually allowed to make it
true — is what the Foundry governs. It takes incoming chaos (email, PDF, Excel,
chat, forms) and forges each change into a structured, *owned* object, then refuses
to let it become truth unless the right authority, responsibility, and confidence
are all present.

> **This is not process mining.** Process tools (Celonis) ask *where work moves*.
> Automation tools (UiPath) ask *how to make it move faster*. Neither asks the
> governance question: do the people moving this change have the **authority,
> responsibility, and confidence** for it to become trusted truth? The Foundry does.

> *Users see tools. The system sees governed change.*

---

## The idea

A job title says what someone is **called**. Access shows what they can **affect**.
The Foundry models a company not as a tree of titles, but as **objects in motion**,
each carrying an **owner, a state, and a lifecycle** — and it makes the access
behind that motion explicit. The novel primitive is the gate at the end of the
spine: a change becomes *trusted truth* only when authority, responsibility, and
confidence line up. Where they don't, the change is held and the mismatch is shown.

**The spine** every change travels:

```
Inputs → Triage → Five Boxes → Impact → Approval → Commit
```

- **Inputs** — email, PDF, Excel, chat, form, API. *Documents are inputs, not the truth.*
- **Triage** — what is it, what does it affect, how sure are we? (confidence)
- **Five Boxes** — every change is sorted into one governed action family.
- **Impact** — bottlenecks, aging, downstream effects.
- **Approval** — routed by confidence, risk, and ownership.
- **Commit** — written to the system of record + an audit trail.

## The Five Boxes

The Foundry sorts incoming reality into a small number of governed action families.
A box is not a folder — it is a *governed route*.

| Box | Meaning | Examples |
|---|---|---|
| ➕ **Create** | Bring a new thing into the system | new item, new record, new request |
| ✏️ **Modify** | Change something that already exists | price update, lead time, attribute change |
| 📅 **Plan** | Prepare future work without touching live reality | roadmap, draft launch, future project |
| 🛡️ **Control** | Approve, reject, route, or govern a change | approval, escalation, exception, release |
| 📄 **Reference** | Store evidence or context without changing the system | spec sheet, certificate, email, attachment |

## Org chart, shown through access

The same company seen through *access* instead of titles. A role's level is not a
title — it is **which governed box it can act in.**

| Level | Role | Dominant box | Responsibility |
|---|---|---|---|
| 5 | CEO / Executive | Future Horizon | sets strategic direction |
| 4 | Director | Plan | coordinates priorities |
| 3 | Manager | Control | approves, escalates, handles exceptions |
| 2 | Specialist / Owner | Modify | maintains and improves existing reality |
| 1 | Data Entry / Ops | Create | adds new records and requests |

*Primary ownership is not exclusive permission. Most roles touch adjacent boxes.
Reference cuts across every level.*

## What it exposes

Because access and responsibility are recorded **separately**, they can disagree —
and the Foundry surfaces the gap instead of papering over it:

- **Approval without authority** — *any* truth-touching change (create, modify, or
  control) routed to someone not authorised to act in Control. The supplier price
  list above lands here.
- **Ownership without flow** — an owner is accountable, but the object is blocked.
- **Editable without an approver** — a change that can touch truth with nobody to sign off.
- **Low-confidence truth** — something committed as truth that triage was unsure about.

These are detected for real by the pipeline, not just described — see
[`runtime/foundry.py`](runtime/foundry.py) and [`docs/access_model.md`](docs/access_model.md).
The **Scenario** tab plays the supplier-price-change story end to end and stops at
the flag, running a live object through the same detection engine.

---

## Repo layout

```
/schema
    object_schema.json   — the governed object (world, box, owner, state, commitment, lifecycle)
    boxes.json           — the five governed action families
    roles.json           — org-chart-through-access: role gravity over the boxes
/data
    objects.json         — sample in-flight objects across customer / item / supplier streams
/runtime
    foundry.py           — the pipeline: triage, impact, approval, access checks, lenses
    schema_validator.py  — typed-box validation
    shadow.py            — the invisible eye (audit trail)
    artifact_store.py    — run artifacts + JSONL shadow log
/artifacts               — run outputs (gitignored)
streamlit_app.py         — the web frontend
PLAN.md                  — roadmap: what is left to build, and the visual plan
```

See [PLAN.md](PLAN.md) for the programside roadmap and the visual design plan.

The runtime is pure Python standard library. The Streamlit frontend is a thin
shell over it — *the user does not need to see the Foundry; the Foundry makes the
process trustworthy.*

## Running it

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

The pipeline runs automatically over the live system-of-record state; the sidebar
has **Re-run pipeline** and **Reset to seed**. Start on the **Scenario** tab to watch
a change travel the spine. The pipeline is self-contained — no Ollama or cloud LLM
is needed.

## Deploying the demo (Streamlit Community Cloud)

1. Push to GitHub (public).
2. At [share.streamlit.io](https://share.streamlit.io), point an app at this repo,
   branch `master`, main file `streamlit_app.py`.
3. `requirements.txt` is picked up automatically; no secrets required.

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest
```

24 tests cover schema validation, the system of record, the actions/state-machine
(including the access guard), and the pipeline (bottlenecks, the generalized
authority rule, mismatches, coverage, lenses), plus an AppTest render smoke test.

## License

MIT — see [LICENSE](LICENSE).

---

*Documents are inputs, not the truth. The truth is the structured record.*
*Every important object has an owner, a state, and a lifecycle.*
*Fast enough for the business. Structured enough for shared truth.*
