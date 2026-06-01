---
description: Resolve merge conflicts automatically
allowed-tools: Bash(git:*), Bash(pnpm:*), Read, Edit, Grep, Glob
category: workflow
---

# Resolve Merge Conflicts

## Current State
!`git status --short 2>/dev/null && echo "---" && git diff --name-only --diff-filter=U 2>/dev/null`

## Merge Context
!`git log --oneline -1 MERGE_HEAD 2>/dev/null; git log --oneline -1 HEAD 2>/dev/null`

## Instructions

Resolve all merge conflicts in the working tree. For each conflicted file:

1. Read the file and identify all conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`).
2. Analyze both sides of each conflict. Use `git log`, `git blame`, or surrounding code context to understand the intent behind each change.
3. Produce the correct merged result — not blindly picking one side, but combining changes when both sides contribute meaningful work (e.g., one side adds an import and the other adds a different import — keep both).
4. Remove all conflict markers and write the resolved content.
5. Stage the resolved file with `git add`.

## Decision Confidence

Be decisive. Most conflicts have a clear correct resolution. Resolve them without hesitation.

If a conflict is genuinely ambiguous — e.g., two sides implement competing business logic and you cannot determine which is intended — stop and ask the user which direction to take rather than guessing. This should be rare.

## After Resolving

Run sanity checks:
- `git diff --check` to verify no conflict markers remain.
- If TypeScript files were resolved, run `pnpm tsc --noEmit` to catch type errors introduced by the merge.
- If test files were resolved, run the relevant tests.

Report what you resolved and any decisions you made.
