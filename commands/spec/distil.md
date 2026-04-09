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

## Process

1. **Read** the input spec at `$ARGUMENTS`
2. **Review the full conversation context** — scan all follow-up prompts, feedback, corrections, and implementation changes that happened after the original spec. The conversation is the ground truth for what was actually built.
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
**Include when they add value:** Motivation, Usage, What doesn't change, References.
**Only include for complex changes:** Architecture diagram, Goals/Non-Goals, Deployment notes.

### Summary
What and why, 2-3 sentences. Keep from original if already concise.

### Motivation
The problem being solved, with observed impact if available. Keep from original if already concise. Skip if the Summary already covers it adequately.

### Goals / Non-Goals
Scope boundaries **with reasoning for each non-goal**. Not just "X is out of scope" but "X is out of scope because Y." This invites reviewers to push back on scope decisions.

Skip for small features where the scope is obvious from the Summary.

### Architecture
A **mermaid diagram** showing data flow and module boundaries — **only when the change involves multiple interacting modules or non-obvious data flow**. A single component wired to an existing hook does not need a diagram. If the reviewer can understand the architecture from the Usage example alone, skip this section.

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

### Acceptance criteria
Concrete, verifiable statements that define "done." A reviewer can check these against the PR diff.

### Deployment notes
Migration order, rollback implications, blast radius. Only include when the change has non-trivial deployment considerations. Reviewers who approve PRs often own the deploy.

### References
Links to Linear tickets, related specs, external docs.

## What to aggressively cut

- **File trees and changed files lists** — the PR diff shows this
- **Architecture diagrams for simple changes** — a single component doesn't need a flowchart
- **Full code listings** — the code IS the implementation; show usage examples, not internals
- **Abstract type signatures** — a usage example with comments is almost always clearer than `type Props = { ... }`
- **"How to extend" when it duplicates Usage** — if the usage example shows the pattern, don't repeat it as numbered steps
- **Risks & failure modes for low-risk changes** — if the worst case is "link doesn't render," it doesn't need a risk table
- **Test coverage intent** — unless there's a non-obvious testing decision worth calling out
- **Performance/security boilerplate** — unless there's a genuine non-obvious concern
- **Implementation phases and step-by-step task breakdowns**
- **Separate "Open questions" sections** — resolved questions become decisions; unresolved questions are flagged inline
- **Anything a reviewer would never disagree with or have an opinion on**
- **Overly specific implementation details in non-goals** — say "Easy to add later" not "Adding `window.Pylon('showNewMessage', text)` is ~3 lines"

## Proportionality

**The spec should be proportional to the change.** A 30-line component doesn't need a 150-line spec. Before writing, ask: "Would a reviewer read all of this, or would they skip to the Decisions section?" If the answer is skip, you have too much text.

Rules of thumb:
- **Tiny feature** (1-2 files, single component): Summary + Decisions + Usage + Acceptance criteria. ~40-60 lines.
- **Medium feature** (3-10 files, multiple components): Add Motivation, What doesn't change, Architecture if needed. ~60-100 lines.
- **Large feature** (10+ files, new patterns, migrations): Use all relevant sections. Up to ~150 lines.

## Tone

- Written for a code reviewer reading the PR diff alongside this document
- Prefer "We chose X over Y because Z" over "X is used"
- Be honest about tradeoffs — don't oversell
- Keep it scannable in under 2 minutes

## Quality check

Before writing, verify:
- [ ] Every decision has an alternative and a reason
- [ ] Acceptance criteria are concrete enough to verify against the PR
- [ ] Nothing in the document is purely informational with no reviewable opinion (except Summary/Motivation/References)
- [ ] The document is proportional to the change — no section exists just to fill a template
- [ ] No claims about codebase patterns that haven't been verified
- [ ] No references to "the original plan" or "what was cut" — the reviewer only sees the final result
