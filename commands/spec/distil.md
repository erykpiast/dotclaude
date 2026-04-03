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

## Process

1. **Read** the input spec at `$ARGUMENTS`
2. **Read** 1-2 other specs in the same directory for tone calibration: `!ls -la $(dirname $ARGUMENTS)/*.md 2>/dev/null | head -5`
3. **Move** the original to `{basename}.plan.md` (the implementation plan, not committed)
4. **Write** the distilled version to the original path

## Distilled Spec Format

Produce a markdown document with these sections. Not every section is required — skip sections that don't apply or add no value for the specific spec. But always include: Summary, Decisions, Architecture, and Acceptance Criteria.

### Summary
What and why, 2-3 sentences. Keep from original if already concise.

### Motivation
The problem being solved, with observed impact if available. Keep from original if already concise.

### Goals / Non-Goals
Scope boundaries **with reasoning for each non-goal**. Not just "X is out of scope" but "X is out of scope because Y." This invites reviewers to push back on scope decisions.

### Architecture
A **mermaid diagram** showing data flow and module boundaries. Worth more than paragraphs of prose. A reviewer should build a mental model in seconds.

Include a top-level file tree (just new/modified modules, not every file).

### Decisions
**The highest-value section.** Format each decision as:

> **Chose X** over Y — because Z. Accepting: W.

This structure invites disagreement. A reviewer who sees the alternative was already considered either agrees or can argue with the specific reasoning.

### What doesn't change
Explicitly list untouched areas so reviewers know what NOT to look at. Also prompts: "should X also change?"

### Key interfaces
Code snippets **only where they're clearer than prose**. Show type signatures and contracts, not implementations. The code IS the implementation — the spec shouldn't duplicate it.

### How to extend
For pattern-establishing code, show the 3-5 step recipe for the most common extension point. Lets the reviewer assess whether the pattern is ergonomic.

### Risks & failure modes
What could go wrong, what the consequence is, and whether that's accepted. Include observability: how do you know it's working in production? (Sentry, logs, dashboards)

### Acceptance criteria
Concrete, verifiable statements that define "done." A reviewer can check these against the PR diff.

### Test coverage intent
What cases are covered and **why those cases matter**. Not mocking details, file paths, or test mechanics.

### Deployment notes
Migration order, rollback implications, blast radius. Reviewers who approve PRs often own the deploy.

### References
Links to Notion, PRs, discussions, external docs.

## What to aggressively cut

- Full code listings — show only key interfaces/signatures
- Implementation phases and step-by-step task breakdowns
- Granular file trees — top-level modules only
- Test mechanics — mocking strategies, setup, file paths
- Performance/security boilerplate unless there's a non-obvious decision
- Repo/wrapper/component implementations — the code IS the implementation
- Separate "Open questions" sections — resolved questions become decisions with context; unresolved questions are flagged inline at the decision they block
- Anything a reviewer would never disagree with or have an opinion on

## Tone

- Written for a code reviewer reading the PR diff alongside this document
- Prefer "We chose X over Y because Z" over "X is used"
- Be honest about tradeoffs and risks — don't oversell
- Keep it scannable in under 2 minutes

## Quality check

Before writing, verify:
- [ ] Every decision has an alternative and a tradeoff
- [ ] The architecture diagram captures the key boundaries
- [ ] Acceptance criteria are concrete enough to verify against the PR
- [ ] Nothing in the document is purely informational with no reviewable opinion (except Summary/Motivation/References)
- [ ] The document is under ~150 lines
