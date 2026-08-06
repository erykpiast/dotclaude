---
description: Apply agentic review feedback (/code-review or /spec:validate output in context) by severity — break down, parallelize across subagents, and edit the uncommitted working tree
allowed-tools: Read, Grep, Glob, Edit, MultiEdit, Write, Task, AskUserQuestion, TodoWrite
argument-hint: "[loose natural-language decisions for ambiguous suggestions]"
category: workflow
---

# Address Review Feedback

Apply feedback from an **agentic review that just ran in this conversation** — `/code-review`'s consolidated report or `/spec:validate`'s findings, organized by CRITICAL / HIGH / MEDIUM / LOW severity.

The reviewed code (or spec) is **not committed yet**: this skill only edits the working tree. It does **not** commit, stage, or group commits — that's the user's next step (`/git:commit`, `/ship`). It still parallelizes independent work across subagents.

**Decisions passed in `$ARGUMENTS`:** $ARGUMENTS

`$ARGUMENTS` supplies **decisions for specific items only** — it is never an authoritative list of what to fix. Items not mentioned in `$ARGUMENTS` are still addressed; they simply have no pre-resolved decision and will be asked about if they are ambiguous. The only exception: if `$ARGUMENTS` contains explicit scope-limiting language ("only the critical ones", "skip LOW", "just the SQL fix"), honor that scope restriction.

## Step 1: Locate the review output in context

Scan recent conversation turns for either source:

1. **`/code-review`** — the "🗂 Consolidated Code Review Report" header, with `🔴 CRITICAL` / `🟠 HIGH` / `🟡 MEDIUM` (and any LOW) sections.
2. **`/spec:validate`** — headers like "Critical Gaps", "Missing Details", "Reference Validation Report", "Overengineering Analysis", "Features to Cut", "Context Consistency".

If neither is present, stop and tell the user:

> No `/code-review` or `/spec:validate` output found in this conversation. Run one of those first, or use `/pr:address-feedback` to act on open PR review threads.

Do not auto-trigger a review.

## Step 2: Extract items by severity

Produce a flat list. Each item has:

- **id** — `cr-<short-slug>` (code review) or `sv-<short-slug>` (spec validate)
- **source** — `code-review` | `spec-validate`
- **severity** — `critical` | `high` | `medium` | `low` (map spec-validate findings: Critical Gaps → critical; broken refs / content mismatches → critical; Missing Details → high; overengineering / features-to-cut → medium unless flagged otherwise)
- **type** — `missing-test`, `bug-fix`, `refactor`, `security`, `perf`, `docs`, `style`, `naming`, `architecture`, `unclear-requirement`, `overengineering`, `other`
- **location** — file path + line range when available
- **summary** — one sentence
- **detail** — verbatim quote of the reviewer text (ground truth for subagents)
- **options** — alternatives the reviewer offered, recommended one marked
- **ambiguous** — true iff `options` is non-empty AND `$ARGUMENTS` doesn't resolve it

Briefly check each item against the current code/spec (Read/Grep) — drop anything already addressed and note it in the final report.

## Step 3: Resolve ambiguities upfront

Parse `$ARGUMENTS` as loose natural language and match statements to item ids or rough descriptions ("the auth one", "the critical security gap"). Reasonable matching is fine. Matched items have their ambiguity resolved; **unmatched items remain in scope** — they are not dropped.

For items still ambiguous after parsing, gather decisions with **`AskUserQuestion`**:
- One question per ambiguous item (group only if truly identical).
- Reviewer's recommendation first, labeled `(Recommended)`.
- Always include a `Skip` option.
- Batch into a single call where possible (≤4 questions per call).

All questions must be resolved before implementation begins. Don't interleave questions with execution.

## Step 4: Choose severities and plan parallel groups

Recommend addressing **CRITICAL + HIGH** now; present MEDIUM/LOW as optional. If `$ARGUMENTS` contains explicit scope-limiting language ("just the critical ones", "everything", "skip MEDIUM"), honor it. Do NOT infer scope restriction from item-specific decisions — the presence of decisions for only some items does not mean the others are excluded.

Then plan **parallel groups** — what can run concurrently. Items are independent if they touch disjoint files (or non-overlapping regions of the same file) and neither's output feeds the other. When in doubt, separate — cheap to over-split, expensive to merge-conflict. (There are no commit groups here; nothing gets committed.)

Present the plan:

```
Addressing: CRITICAL + HIGH (4 items). Deferred: 3 MEDIUM, 1 LOW.

Parallel groups (concurrent subagents):
  [A] cr-sql-injection, cr-authz       — security fixes in api layer   → general-purpose
  [B] cr-missing-tests-1               — coverage for payment module   → testing-expert
  [C] sv-missing-error-handling        — fill spec gap: failure modes  → general-purpose

Skipped: cr-style-3 (deferred MEDIUM), cr-naming-2 (already addressed)
```

Confirm the plan. A short "looks good" is enough.

## Step 5: Execute in parallel

Launch a specialist subagent per parallel group via **Task**, all in a **single message** so they run concurrently.

**Always pass `model: "sonnet"`** on every implementation subagent, regardless of the session's model. The items are already extracted, verified, and disambiguated by this point — the subagents are executing a decided change, not deciding what to do — so a Sonnet-class model is the right tier. Do not inherit the parent model and do not upgrade individual groups.

Match `subagent_type` to the work: tests → `testing-expert` (or the repo's `vitest`/`jest` variant); refactors → `refactoring-expert`; TS types → `typescript-type-expert`; React → `react-expert`; perf → `react-performance-expert` / `database-expert`; a11y → `accessibility-expert`; spec/doc edits → `documentation-expert` or `general-purpose`; anything else → `general-purpose`.

Each subagent prompt must contain:
- The verbatim feedback items it owns (id + severity + detail quote)
- The exact file paths and line ranges to change
- Any user-resolved decisions for ambiguous items
- The instruction: **do not commit and do not stage** — leave all changes in the working tree
- A short report-back: items addressed, files changed, anything surprising

Track progress with `TodoWrite`.

## Step 6: Report

After all subagents finish:

- **Addressed** — item ids (with severity) and the files changed for each
- **Skipped** — item ids + reason (deferred severity, already addressed, user skipped, blocked)
- **Follow-ups** — anything larger than expected, newly surfaced questions, or deferred MEDIUM/LOW items worth revisiting

End by noting the changes are **uncommitted in the working tree**, ready for re-review (re-run `/code-review`) and then commit via `/git:commit` or `/ship`.
