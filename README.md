# The Spring

**An access-first model for product data responsibility.**

Most business systems describe people through job titles and departments, but
day-to-day data work happens through access: who can see a field, who can change
it, who can approve it, who maintains it, and who is accountable when it becomes
wrong.

> Org charts show hierarchy. Access maps show how work actually happens.

---

## The idea in three lines

- A job title says what someone is **called**.
- Access shows what they can **affect**.
- Responsibility should be **explicit** wherever access exists.

A company is not really a tree of titles. It is a graph of actors who can touch
objects, and of responsibilities that are supposed to sit behind that access.
The Spring models the graph, not the org chart.

## The one distinction that matters

Access does **not** automatically equal responsibility. Treating them as the
same thing is how accountability quietly disappears.

Instead, The Spring treats **access as a claim about responsibility**. If someone
can edit a field, that is an implicit claim that someone is responsible for it
being right. When access and responsibility do not match, the system does not
paper over it — **it exposes the mismatch.**

---

## The model

Five primitives describe everything in the system.

| Primitive | What it is | Examples |
|---|---|---|
| **Actor** | Who is acting | person, team, system, agent |
| **Object** | What is acted on | product, field, schema, workflow, view, file |
| **Permission** | What the actor can do | view, edit, approve, export, delete, override |
| **Responsibility** | What the actor is accountable for | owns, maintains, reviews, validates, approves |
| **Evidence** | What actually happened | logs, changes, approvals, exceptions, comments |

Permission and Responsibility are recorded **separately** — see
[`schema/definition_of_definition.json`](schema/definition_of_definition.json),
where `who_has_access` and `who_responsible` are two distinct questions. Because
they are separate, they can disagree. Evidence (the `shadow.jsonl` audit trail)
is what lets us check whether the claims hold up.

## What the system exposes

The point of separating access from responsibility is to surface the gaps that
title-first systems hide. The Spring is designed to flag:

- **Access without responsibility** — someone can change it, but no one owns it.
- **Responsibility without access** — someone is accountable but cannot act.
- **Approval without evidence** — a sign-off with no record behind it.
- **Ownership without visibility** — an owner who cannot see the object's state.
- **Editable fields without a declared owner** — change is possible, ownership is blank.
- **High-risk fields without review rules** — `impact_if_wrong` is high, review cycle is `never`.

See [`docs/access_model.md`](docs/access_model.md) for the full definition of
each mismatch and the schema fields it reads.

---

## Why this is a product-data tool, not a theory

The business value is concrete. When a price, a tolerance, or a safety grade is
wrong, the first question is always *"who was supposed to be keeping this right?"*
Title-first systems answer with a department. Access maps answer with a name, a
permission, and a responsibility claim you can check against the evidence.

The same source data drives four maps drawn for four travellers — customer,
sales, engineer, management — each showing only what that traveller needs to act.
The maps differ; the source of truth does not.

---

## Repo layout

```
/schema           source schema + four view schemas + the meta-schema (definition of definition)
/data             the product dataset (industrial fasteners)
/runtime          orchestrator (puhemies), validator, transforms, janitor, judge, shadow
/gui              four-panel Tkinter overview, each panel expandable to full detail
/artifacts        run outputs — view exports, validation reports, shadow logs
streamlit_app.py  web frontend — a thin shell over the same runtime
main.py           desktop frontend (Tkinter)
```

The runtime is pure Python standard library. The frontends are thin shells over
it — swapping a UI requires zero runtime changes.

## Running it

Install dependencies (only needed for the web frontend; the runtime itself needs none):

```bash
pip install -r requirements.txt
```

**Web app (recommended):**

```bash
streamlit run streamlit_app.py
```

Press **▶ Run pipeline** in the sidebar. The pipeline is fully self-contained —
schema-driven transforms and a rule-based judge — so it needs no Ollama or cloud
LLM to produce the four maps.

**Desktop app (Tkinter):**

```bash
python main.py
```

## Deploying the demo (Streamlit Community Cloud)

1. Push this repo to GitHub (public).
2. At [share.streamlit.io](https://share.streamlit.io), create an app pointing at
   this repo, branch `master`, main file `streamlit_app.py`.
3. `requirements.txt` is picked up automatically; no secrets are required.

The app writes run artifacts to `artifacts/` (gitignored, ephemeral on the cloud
host) — nothing persistent or sensitive leaves the box.

---

*Data is not reality. But it is all we have.*
*Every schema is a map. Maps are drawn for travellers — they all need a different map.*
*Define it in the schema or it does not exist.*
