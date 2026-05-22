---
description: Apply review feedback (PR threads, /code-review, or /spec:validate) by batching, parallelizing, and committing in chunks
allowed-tools: Bash(gh:*), Bash(git:*), Bash(jq:*), Read, Grep, Glob, Edit, MultiEdit, Write, Task, AskUserQuestion, TodoWrite
argument-hint: "[loose natural-language decisions for ambiguous suggestions]"
category: workflow
---

# Address Feedback

Apply review feedback systematically: gather → break down → resolve ambiguities → plan batches → execute in parallel → commit in chunks.

**Decisions passed in `$ARGUMENTS`:** $ARGUMENTS

## Step 1: Discover the feedback source

Run in parallel:
- `git branch --show-current` — current branch
- `gh pr view --json number,state,url,baseRefName,headRefName 2>/dev/null` — does an open PR exist for this branch?

Source precedence (use the first that yields items):

1. **Open PR review threads** — if a PR exists, fetch unresolved threads.

   Get the repo's owner/name (`gh repo view --json owner,name`) and the PR number from `gh pr view`. Then:

   ```bash
   gh api graphql -F owner=<owner> -F repo=<repo> -F pr=<pr-num> -f query='
     query($owner:String!, $repo:String!, $pr:Int!) {
       repository(owner:$owner, name:$repo) {
         pullRequest(number:$pr) {
           reviewThreads(first:100) {
             nodes {
               id isResolved isOutdated
               comments(first:50) {
                 nodes { author { login } body path line databaseId }
               }
             }
           }
         }
       }
     }'
   ```

   Filter out `isResolved: true`. Flag `isOutdated: true` threads but still include them (the underlying concern often still applies).

   Also fetch review summary bodies (the top-level review comment that isn't on a line):
   ```bash
   gh api repos/<owner>/<repo>/pulls/<pr>/reviews
   ```
   Include any review body that contains actionable suggestions.

2. **`/code-review` output in conversation context** — scan recent turns for the "🗂 Consolidated Code Review Report" header. Extract items from the CRITICAL / HIGH / MEDIUM sections.

3. **`/spec:validate` output in conversation context** — scan for headers like "Critical Gaps", "Missing Details", "Reference Validation Report", "Overengineering Analysis", "Features to Cut". Extract each gap/issue as an item.

**If none of the three sources yield items:** stop and tell the user:

> No PR found for `<branch>` and no recent `/code-review` or `/spec:validate` output in this conversation. Run `/code-review` first, or open a PR for this branch.

Do not auto-trigger anything.

## Step 2: Extract feedback items

Produce a flat list. Each item has:

- **id** — short stable label: `thread-<databaseId>`, `cr-<short-slug>`, `sv-<short-slug>`
- **source** — `pr-thread` | `code-review` | `spec-validate`
- **type** — one of: `missing-test`, `bug-fix`, `refactor`, `security`, `perf`, `docs`, `style`, `naming`, `architecture`, `unclear-requirement`, `other`
- **location** — file path and line range when available
- **summary** — one sentence
- **detail** — verbatim quote of the relevant reviewer text (so subagents have ground truth)
- **options** — when the reviewer offered alternatives (e.g. "do X or Y, X recommended"), list them with the recommended one marked
- **ambiguous** — true iff `options` is non-empty AND `$ARGUMENTS` does not clearly resolve it

Before finalizing the list, briefly check each item against the current code (Read/Grep) — drop items that look already addressed and note them in the final report.

## Step 3: Resolve ambiguities upfront

Parse `$ARGUMENTS` as loose natural language. Match user statements to item ids or rough descriptions (e.g. "the auth one", "thread 42"). Reasonable matching is fine; don't fail on imperfect phrasing.

For any item that is still ambiguous after parsing arguments, gather decisions using **`AskUserQuestion`**. Rules:

- One question per ambiguous item (group only if truly identical).
- Include the reviewer's recommendation as the first option, labeled `(Recommended)`.
- Always include a `Skip` option for items the user wants to defer.
- Collect **all** decisions in a single `AskUserQuestion` call when possible (the tool accepts up to 4 questions per call — batch in chunks of 4).

**Critical:** all questions must be resolved before any implementation begins. Do not interleave questions with execution.

## Step 4: Plan parallel groups and commit groups

Produce two independent groupings — they may not match.

**Parallel groups** — what can run concurrently in subagents. Items are independent if:
- They touch disjoint files (or non-overlapping regions of the same file), AND
- Neither's output is an input to the other.

When in doubt, separate. Cheap to over-split, expensive to merge-conflict.

**Commit groups** — what belongs in one logical commit. Group by intent, not by file. Examples:
- "test: increase coverage for X and Y" — even if X and Y are different modules implemented in parallel
- "refactor(auth): simplify middleware" — one focused change
- "fix: address security review" — multiple security items rolled together
- "docs: update API examples" — keep docs separate from code

One commit group can span multiple parallel groups (you wait for all to finish, then commit together). One parallel group can also span multiple commit groups (one subagent's work touches multiple intents — split the commit when staging).

Present the plan as:

```
Parallel groups (concurrent subagents):
  [A] thread-3, cr-test-1   — missing tests for module X      → testing-expert
  [B] thread-7              — missing tests for module Y      → testing-expert
  [C] cr-arch-2             — refactor auth middleware        → refactoring-expert

Commit groups (atomic commits, in order):
  1. test: increase coverage for X and Y     ← A + B
  2. refactor(auth): simplify middleware     ← C

Skipped: cr-docs-4 (user chose skip), sv-gap-2 (already addressed in main)
```

Confirm the plan with the user before executing. A short "looks good" is enough — don't require restating the plan.

## Step 5: Execute in parallel

For each parallel group, launch a specialist subagent via the **Task** tool. Send all parallel launches in a **single message** with multiple Task calls so they run concurrently.

Match `subagent_type` to the work:
- Missing tests → `testing-expert` (or `vitest-testing-expert` / `jest`-flavored variant if the repo uses one)
- Refactors / code smells → `refactoring-expert`
- TypeScript type issues → `typescript-type-expert` or `typescript-expert`
- React component issues → `react-expert`
- Performance → `react-performance-expert` or `database-expert` depending on domain
- Accessibility → `accessibility-expert`
- Anything that doesn't fit → `general-purpose`

Each subagent prompt must contain:
- The verbatim feedback items it owns (id + detail quote)
- The exact file paths and line ranges to change
- Any user-resolved decisions for ambiguous items in that group
- The instruction: **do not commit** — commits are batched after parallel work finishes
- A short report-back format: which items were addressed, which files changed, anything that surprised the subagent

Track parallel progress with `TodoWrite`.

## Step 6: Commit in batches

After all parallel subagents finish:

For each commit group, in order:
1. `git status` to see what's changed.
2. Stage only the files relevant to this group: `git add <specific files>`. Never `git add .` / `git add -A`.
3. Write a conventional-commit message reflecting the group's intent.
4. Commit.

If files staged for a group also contain unrelated changes (a subagent touched something out of scope), stop and ask the user how to resolve before committing.

Do not push. Do not open or update PRs. Do not reply on review threads. Leave those follow-ups to the user (or to a later `/ship` invocation).

## Step 7: Report

Summarize concisely:
- **Addressed** — list item ids and the commit sha each landed in
- **Skipped** — list item ids with the reason (user chose skip, already addressed, blocked)
- **Commits** — sha + subject for each new commit
- **Follow-ups** — anything that turned out to be larger than expected, surfaced new questions, or needs the user's attention

End with: branch is ready for re-review / next step (don't auto-push or auto-update the PR).
