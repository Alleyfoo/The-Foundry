# The Access Model

How The Spring models a company as an access/responsibility graph, and the
mismatches it is built to expose.

This document is the conceptual reference. The contract it describes lives in
[`schema/definition_of_definition.json`](../schema/definition_of_definition.json)
— the meta-schema every field must answer.

---

## Why access-first

A job title says what someone is *called*. It does not tell you what they can
*affect*. Two people with the same title often have very different access, and
two people with very different titles often touch the same field. If you want to
know how data actually gets created, changed, and broken, follow the access — not
the org chart.

So The Spring describes the company as a graph:

- **Actors** (person, team, system, agent) hold
- **Permissions** over
- **Objects** (product, field, schema, workflow, view, file), and are expected to
  carry
- **Responsibilities**, which **Evidence** can confirm or contradict.

## Access as a claim, not a guarantee

The central rule:

> Access should be treated as a claim about responsibility. If access and
> responsibility do not match, the system should expose the mismatch.

We deliberately do **not** say "access equals responsibility." Access is cheap to
grant and easy to forget. Responsibility has to be declared. The value of the
model is in the *delta* between the two — and surfacing that delta instead of
hiding it.

---

## The five primitives

| Primitive | Schema home | Notes |
|---|---|---|
| **Actor** | `who_has_access.access_rules[].role`, `who_responsible.*` | role / team / system / agent |
| **Object** | the field itself, plus `where.owning_system` | what is being acted on |
| **Permission** | `who_has_access.access_rules[].permissions` | view, edit, approve, export, delete, override |
| **Responsibility** | `who_responsible.responsibility_assignments[]` | owns, maintains, reviews, validates, approves |
| **Evidence** | `shadow.jsonl` audit trail | logs, changes, approvals, exceptions, comments |

`who_has_access` (Permission) and `who_responsible` (Responsibility) are separate
blocks **on purpose**. Keeping them separate is what makes a mismatch detectable.

---

## The mismatches

Each mismatch below names the schema fields it compares. (Detection logic is out
of scope for this pass — this is the specification a detector would implement.)

### 1. Access without responsibility
An actor appears in `access_rules` with `edit`/`approve`/`override`/`delete`, but
holds no entry in `responsibility_assignments`.
**Reading:** someone can change it; no one has claimed they keep it right.

### 2. Responsibility without access
An actor is listed in `responsibility_assignments` (e.g. `maintains`) but has no
corresponding `access_rules` entry granting the permission that responsibility
implies.
**Reading:** someone is accountable but cannot act.

### 3. Approval without evidence
A field's lifecycle shows an approval, but `shadow.jsonl` holds no logged event
backing it.
**Reading:** a sign-off with nothing behind it.

### 4. Ownership without visibility
An actor holds `owns` in `responsibility_assignments` but lacks `view` on the
object.
**Reading:** an owner who cannot see the state of what they own.

### 5. Editable fields without a declared owner
Some actor has `edit` in `access_rules`, but no actor holds `owns` in
`responsibility_assignments`.
**Reading:** change is possible; ownership is blank.

### 6. High-risk fields without review rules
`why_exists.impact_if_wrong` is `safety_critical` or `financial_loss`, but
`who_responsible.review_cycle` is `never` (or no actor holds `reviews`).
**Reading:** the field can cause real harm and nothing schedules a look at it.

---

## What this is *not*

This is a practical product-data governance model. It is not an ideological or
political statement about organizations. The claim is narrow and operational:
*when a field is wrong, you should be able to find who was responsible, check it
against what they could actually do, and see the evidence.* Everything here
serves that.

> Org charts show hierarchy. Access maps show how work actually happens.
