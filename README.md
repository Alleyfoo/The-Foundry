# 🔥 The Foundry

**Turning incoming business chaos into trusted, structured change.**

Most business systems describe a company through job titles and departments. But
day-to-day reality is messier than an org chart: requests arrive by email, PDF,
Excel, and chat; things get stuck; nobody is sure who owns what. The Foundry is a
governance layer that takes that incoming chaos and forges it into trusted,
structured, *owned* change before it is allowed to become truth.

> Org charts show hierarchy. The Foundry shows the organisation through **access** —
> who can act on what, as objects flow from chaos toward trusted truth.

> *Users see tools. The system sees governed change.*

---

## The idea

A job title says what someone is **called**. Access shows what they can **affect**.
The Foundry models a company not as a tree of titles, but as **objects in motion**,
each carrying an **owner, a state, and a lifecycle** — and it makes the access
behind that motion explicit.

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

- **Approval without authority** — a change routed to someone not authorised to control it.
- **Ownership without flow** — an owner is accountable, but the object is blocked.
- **Editable without an approver** — a change that can touch truth with nobody to sign off.
- **Low-confidence truth** — something committed as truth that triage was unsure about.

These are detected for real by the pipeline, not just described — see
[`runtime/foundry.py`](runtime/foundry.py) and [`docs/access_model.md`](docs/access_model.md).

---

## Repo layout

```
/schema
    object_schema.json   — the governed object (world, box, owner, state, commitment, lifecycle)
    boxes.json           — the five governed action families
    roles.json           — org-chart-through-access: role gravity over the boxes
    definition_of_definition.json — the meta-schema (the five definition questions)
/data
    objects.json         — sample in-flight objects across customer / item / supplier streams
/runtime
    foundry.py           — the pipeline: triage, impact, approval, access checks, lenses
    schema_validator.py  — typed-box validation
    shadow.py            — the invisible eye (audit trail)
    artifact_store.py    — run artifacts + JSONL shadow log
/artifacts               — run outputs (gitignored)
streamlit_app.py         — the web frontend
```

The runtime is pure Python standard library. The Streamlit frontend is a thin
shell over it — *the user does not need to see the Foundry; the Foundry makes the
process trustworthy.*

## Running it

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Press **🔥 Run the Foundry** in the sidebar. The pipeline is self-contained — no
Ollama or cloud LLM is needed.

## Deploying the demo (Streamlit Community Cloud)

1. Push to GitHub (public).
2. At [share.streamlit.io](https://share.streamlit.io), point an app at this repo,
   branch `master`, main file `streamlit_app.py`.
3. `requirements.txt` is picked up automatically; no secrets required.

## License

MIT — see [LICENSE](LICENSE).

---

*Documents are inputs, not the truth. The truth is the structured record.*
*Every important object has an owner, a state, and a lifecycle.*
*Fast enough for the business. Structured enough for shared truth.*
