---
allowed-tools: Read, Write, Edit, Glob, Grep, Bash(mv:*), Bash(ls:*)
description: Distill a detailed spec into a concise reviewer-facing decision document
category: validation
argument-hint: "<path-to-spec-file>"
---

# Distill Specification

Distill the detailed specification at `$ARGUMENTS` into a concise, reviewer-facing decision document.

## Context

In the age of LLM-generated code, reviewers skim diffs and trust agents to get implementation right. What they actually review is: **Is this the right thing to build? Were the right tradeoffs made? What could go wrong?**

The distilled spec is a **decision surface** — committed alongside code, it enables meaningful review without reading every line. Every section should present a reviewable opinion, not just state facts.

Critically, the distilled spec must match the **actual implementation**, not the original plan. During implementation, follow-up prompts, testing feedback, and course corrections often change assumptions and decisions. The conversation history is the source of truth — the original spec is just the starting point.

## Source-of-truth split

The PR diff is authoritative for **what changed**. The distilled spec is authoritative for **why**.

If the reviewer can read it off the diff, it does not belong in the distilled spec:
- Function, method, type, file, route, and column names
- Type signatures, result shapes, predicates (`x !== 'foo'`)
- Log/event slug strings, status codes, error codes
- Field counts ("six columns", "all four fields") — say "the X"
- Implementation phases or step-by-step task breakdowns

When tempted to name a symbol, replace it with the conceptual role it plays: `findOrCreateRecordForUser` → "the record resolver"; `AccountRepo.delete` → "delete the account row"; `/items/new` → "the item-creation form".

Exception: a symbol is fine when it is the *subject* of a decision the reviewer is being asked to weigh in on, and naming it adds precision the prose cannot. Default to omitting.

## Process

1. **Read** the input spec at `$ARGUMENTS`
2. **Review the full conversation context** — scan all follow-up prompts, feedback, corrections, and implementation changes that happened after the original spec. The conversation is the ground truth for what was actually built. **Resolved questions disappear from the spec entirely** — they become a Decision (if the rationale matters) or vanish (if the answer is now obvious from the diff). Never leave a header called "Open questions" in a distilled spec; if a genuine unknown remains, attach it as one inline sentence to the Decision it qualifies.
3. **Identify divergences** between the original spec and what was actually implemented. Categorize each:
   - **Trivial/mistake corrections** (typos in approach, obvious bugs caught during implementation) → omit from the distilled spec entirely, just reflect the final correct decision
   - **Meaningful pivots with clear rationale** (user explained why, or the reason is obvious from context) → document as a decision with the alternative framed naturally (see Decisions section below)
   - **Meaningful pivots with unclear rationale** → **stop and ask the user** why this changed before writing the distilled spec. Frame it as: "The original spec called for X but the implementation does Y. What was the reasoning? I want to capture this for reviewers."
4. **Read** 1-2 other specs in the same directory for tone calibration: `!ls -la $(dirname $ARGUMENTS)/*.md 2>/dev/null | head -5`
5. **Move** the original to `{basename}.plan.md` (the implementation plan, not committed)
6. **Write** the distilled version to the original path — reflecting the **actual implementation**, not the original plan

## Distilled Spec Format

Produce a markdown document with these sections. **Not every section is required** — aggressively skip sections that don't add value. The spec should be proportional to the complexity of the change. A tiny feature needs a tiny spec.

**Always include:** Summary, Decisions, and Acceptance Criteria.
**Include when they add value:** Motivation, Usage, What doesn't change, Observability, References.
**Only include for complex changes:** Architecture diagram, Goals/Non-Goals, Deployment notes.

### Summary
What and why, 2-3 sentences. Keep from original if already concise.

### Motivation
The problem being solved, with observed impact if available. Keep from original if already concise. Skip if the Summary already covers it adequately.

When the conversation names a specific customer, incident, ticket, or metric, **use the concrete name** ("Northwind reports..."), not the category ("outbound-heavy customers report..."). Concrete references ground reviewer trust and survive the spec longer than vague stand-ins.

### Goals / Non-Goals
Scope boundaries **with reasoning for each non-goal**. Not just "X is out of scope" but "X is out of scope because Y." This invites reviewers to push back on scope decisions.

**One sentence per non-goal.** If you find yourself writing a paragraph, the reasoning belongs in a Decision instead. Skip the section entirely for small features where the scope is obvious from the Summary.

### Architecture
A **mermaid diagram** showing data flow and module boundaries — **only when the change involves multiple interacting modules or non-obvious data flow**. A single component wired to an existing hook does not need a diagram.

**Use conceptual node labels, not function names.** `findOrCreateRecordForUser` → "record resolver"; `clearStoredRecords, mode: 'all'` → "purge all upstream records"; `AccountRepo.delete` → "delete account row". The diagram should be readable by someone who has never opened the repo. If the reviewer can understand the architecture from the Usage example alone, skip the diagram entirely.

Do NOT include file trees — the PR diff shows which files changed.

### Decisions
**The highest-value section.** Format each decision as:

> **Chose X** over Y — because Z.

This structure invites disagreement. A reviewer who sees the alternative was already considered either agrees or can argue with the specific reasoning.

**Important framing rules:**
- Write from the **reviewer's perspective**. The reviewer sees the PR diff and this document — they don't know what was "originally planned" or "cut." Don't use phrases like "originally planned," "cut from the spec," or "deferred." Instead, frame alternatives naturally: "**Chose X** over Y — because Z."
- Don't make claims about existing codebase patterns unless you've verified them. Saying "the app already uses X everywhere" when it doesn't undermines trust.
- Keep reasoning concise. One sentence for the "because" is usually enough.

### What doesn't change
Explicitly list untouched areas so reviewers know what NOT to look at. Also prompts: "should X also change?"

### Usage
Show a concrete usage example with brief comments explaining the props/API. This is more useful than abstract type signatures — the reviewer sees real code and immediately understands how it works. If the usage example is self-explanatory, this replaces both "Key interfaces" and "How to extend" sections.

### Observability
Include only when the change adds non-trivial structured logging or metrics that operators will rely on.

**Frame as operator questions, not slug tables.** A list of slug strings paired with their meanings duplicates the code. Instead, list the questions the logs are designed to answer. For example:

> - What share of operations take the primary path vs the fallback?
> - Which tenants still rely on the fallback, and why (missing input / incomplete input / wrong category)?
> - Did the upstream provider reject any requests?
> - For a deleted account, was upstream PII purged successfully?

If the change includes a deliberate "what we never log" decision (e.g. PII redaction), state it once in plain prose.

### Acceptance criteria
Concrete, verifiable statements that define "done." A reviewer can check these against the PR diff.

**Each criterion must be checkable from observable behaviour or user-visible state, not internal symbols.** "Emits a provider-rejection event" beats "emits `record_rejected_by_provider` at error level". "The account row is NOT deleted" beats "`AccountRepo.delete` is NOT called". "Save still succeeds" beats "returns `{ ok: true }`".

### Deployment notes
Migration order, rollback implications, blast radius. Only include when the change has non-trivial deployment considerations. Reviewers who approve PRs often own the deploy.

### References
Links to Linear tickets, related specs, external docs.

## What to aggressively cut

Each of these has been seen leaking into a distilled spec — cut on sight:

- **Symbol names** — function, method, type, file, route, column names. The diff has them. Use the conceptual role instead.
- **Type signatures and result shapes** — `{ ok: true, recordId } | { ok: false, error }` belongs in the code; "no result shapes change" belongs here.
- **Log slug strings, error codes, HTTP status codes** — `record_rejected_by_provider` → "a provider-rejection event"; `422` → "rejected"; `404` → "not found".
- **Field counts** — "the six X columns" / "all four fields" / "any of the six columns" — say "the X". Counts rot when the schema changes.
- **File trees and changed-files lists** — the diff shows this.
- **Architecture diagrams for simple changes** — a single component does not need a flowchart.
- **Full code listings and abstract type definitions** — the code IS the implementation; show usage examples, not internals.
- **"How to extend" sections that duplicate Usage** — if the example shows the pattern, do not repeat it as numbered steps.
- **Risks & failure modes for low-risk changes** — if the worst case is "link does not render", no risk table.
- **Test coverage intent** — unless there is a non-obvious testing decision worth calling out.
- **Performance/security boilerplate** — unless there is a genuine non-obvious concern.
- **Implementation phases and step-by-step task breakdowns.**
- **Separate "Open questions" sections** — resolved questions become decisions; unresolved questions attach inline to the Decision they qualify.
- **Anything purely informational with no reviewable opinion** (except Summary/Motivation/References).
- **Overly specific implementation details in non-goals** — say "Easy to add later" not "Adding `someApi.someMethod(arg)` is ~3 lines".

## Proportionality

**The spec should be proportional to the change.** A 30-line component doesn't need a 150-line spec. Before writing, ask: "Would a reviewer read all of this, or would they skip to the Decisions section?" If the answer is skip, you have too much text.

Rules of thumb:
- **Tiny feature** (1-2 files, single component): Summary + Decisions + Usage + Acceptance criteria. ~40-60 lines.
- **Medium feature** (3-10 files, multiple components): Add Motivation, What doesn't change, Architecture if needed. ~60-100 lines.
- **Large feature** (10+ files, new patterns, migrations): Use all relevant sections. Up to ~150 lines.

## Tone and language

- Written for a code reviewer reading the PR diff alongside this document
- Prefer "We chose X over Y because Z" over "X is used"
- Be honest about tradeoffs — don't oversell
- Keep it scannable in under 2 minutes

**Plain language over domain jargon.** A reviewer who has not lived in the codebase should be able to parse every sentence. When you reach for a technical-sounding shorthand, expand it:

- "tuple-aware idempotency" → "match the existing record by its content, not by ID alone"
- "legacy heuristic" → "the previous behaviour (matching on ID only)"
- "normalize the tuple" → "trim and uppercase the values before comparing"
- "the X input" → name the actual thing ("the user's record")

**Write decisions directly, not abstractly.** "Chose the user's record over the tenant default" beats "Chose user-stored record as the resolver input". The first sentence of a decision should make the choice intelligible without any prior context.

## Quality check

Before writing, verify:
- [ ] Every decision has an alternative and a reason
- [ ] Acceptance criteria check observable behaviour, not internal symbols (function names, slug strings, result shapes)
- [ ] No symbol names, type signatures, file paths, slug strings, or HTTP/error codes in prose. The PR diff has those.
- [ ] No field-count references ("six columns", "all four fields") — say "the X"
- [ ] No domain jargon a non-domain reader cannot parse on first read
- [ ] No "Open questions" header. Resolved questions are gone; unresolved ones are attached inline to the relevant Decision
- [ ] No deployment-notes section unless the deploy genuinely has non-trivial steps the reviewer-as-deployer needs to know
- [ ] Non-goals are one sentence each
- [ ] Concrete customer/ticket/incident names are used where the conversation provided them
- [ ] No claims about codebase patterns that haven't been verified
- [ ] No references to "the original plan" or "what was cut" — the reviewer only sees the final result
- [ ] The document is proportional to the change — no section exists just to fill a template
