---
description: Resolve merge conflicts automatically
allowed-tools: Task, Bash(git:*), Bash(pnpm:*), Read, Grep, Glob
category: workflow
---

# Resolve Merge Conflicts

## Current State
!`git status --short 2>/dev/null && echo "---" && git diff --name-only --diff-filter=U 2>/dev/null`

## Merge Context
!`git log --oneline -1 MERGE_HEAD 2>/dev/null; git log --oneline -1 HEAD 2>/dev/null`

## Instructions

The conflict resolution itself is **always** performed by a subagent running the **Haiku** model — never resolve conflicts inline. The orchestrator (you) gathers context, delegates the resolution, and verifies the result.

### Step 1: Gather context

From the Current State above, collect the list of conflicted files (`git diff --name-only --diff-filter=U`). If there are none, report that there is nothing to resolve and stop.

### Step 2: Delegate resolution to a Haiku subagent

Spawn a subagent via the **Task** tool with `subagent_type: general-purpose` and **`model: haiku`**. When there are many conflicted files that touch disjoint areas, split them across several Haiku subagents launched in a single message so they run concurrently; otherwise one subagent handles all files.

Each subagent's prompt must include the conflicted files it owns, the merge context (both commit headlines above), and these instructions verbatim:

> For each conflicted file:
> 1. Read the file and identify all conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`).
> 2. Analyze both sides of each conflict. Use `git log`, `git blame`, or surrounding code context to understand the intent behind each change.
> 3. Produce the correct merged result — not blindly picking one side, but combining changes when both sides contribute meaningful work (e.g., one side adds an import and the other adds a different import — keep both).
> 4. Remove all conflict markers and write the resolved content.
> 5. Stage the resolved file with `git add`.
>
> **Be decisive.** Most conflicts have a clear correct resolution. Resolve them without hesitation. If a conflict is genuinely ambiguous — e.g., two sides implement competing business logic and you cannot determine which is intended — do **not** guess: leave that file's markers in place and report it back as needing a human decision. This should be rare.
>
> Report which files you resolved, the key decisions you made, and any files left unresolved because they were ambiguous.

### Step 3: Handle ambiguity

If any subagent reports a file it could not resolve, surface the competing options to the user and ask which direction to take. Then dispatch the decision back to a Haiku subagent (or resolve that one file via a follow-up Task) — still never resolving inline.

## After Resolving

Run sanity checks:
- `git diff --check` to verify no conflict markers remain.
- If TypeScript files were resolved, run `pnpm tsc --noEmit` to catch type errors introduced by the merge.
- If test files were resolved, run the relevant tests.

Report what the subagent(s) resolved and any decisions that were made.
