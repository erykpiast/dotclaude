---
description: Apply open PR review feedback (human + agent threads) — auto-implement what the PR author already approved, evaluate and confirm the rest, then commit in chunks
allowed-tools: Bash(gh:*), Bash(git:*), Bash(jq:*), Read, Grep, Glob, Edit, MultiEdit, Write, Task, AskUserQuestion, TodoWrite
argument-hint: "[loose natural-language decisions for ambiguous suggestions]"
category: workflow
---

# Address PR Feedback

Resolve the open review threads on this branch's PR. The code is **already committed and pushed**, so this skill commits the fixes — keep commits in sensible logical groups alongside the parallelized work.

The core distinction: **threads the PR author already approved get implemented and committed without re-asking**; everything else (agent reviews, un-answered threads) is evaluated for feasibility and confirmed before implementing.

**Decisions passed in `$ARGUMENTS`:** $ARGUMENTS

`$ARGUMENTS` supplies **decisions for specific items only** — it is never an authoritative list of what to fix. Items not mentioned in `$ARGUMENTS` are still processed; they simply have no pre-resolved decision and will be evaluated and confirmed per Step 5. The only exception: if `$ARGUMENTS` contains explicit scope-limiting language ("only the approved threads", "skip agent reviews"), honor that scope restriction.

## Step 1: Find the PR

Run in parallel:
- `git branch --show-current` — current branch
- `gh pr view --json number,state,url,baseRefName,headRefName,author` — the open PR and its **author** (the creator whose approvals we trust)

If no open PR exists for this branch, stop and tell the user:

> No open PR found for `<branch>`. Push the branch and open a PR first, or use `/review:address-feedback` to act on `/code-review` or `/spec:validate` output in this conversation.

Do not auto-open a PR.

## Step 2: Fetch unresolved threads, reactions, and reviews

Get the repo's owner/name (`gh repo view --json owner,name`) and the PR number. Then fetch threads **with reactions and author types** so we can tell humans from bots and detect the author's approvals:

```bash
gh api graphql -F owner=<owner> -F repo=<repo> -F pr=<pr-num> -f query='
  query($owner:String!, $repo:String!, $pr:Int!) {
    repository(owner:$owner, name:$repo) {
      pullRequest(number:$pr) {
        author { login }
        reviewThreads(first:100) {
          nodes {
            id isResolved isOutdated
            comments(first:50) {
              nodes {
                author { login __typename }
                body path line databaseId
                reactions(first:20) { nodes { content user { login } } }
              }
            }
          }
        }
      }
    }
  }'
```

Filter out `isResolved: true`. Flag `isOutdated: true` threads but still include them (the underlying concern often still applies).

Also fetch review summary bodies (top-level review comments not on a line):
```bash
gh api repos/<owner>/<repo>/pulls/<pr>/reviews
```
Include any review body that contains actionable suggestions; treat it as its own thread with no author response.

## Step 3: Classify each thread by the PR author's stance

For each unresolved thread, the **first comment** is the suggestion. Identify the suggester and the author's response.

**Is the suggester an agent (agentic review)?** True if the first comment's `author.__typename` is `Bot`, or the login matches a known reviewer bot (`*[bot]`, `coderabbitai`, `claude`, `cursor`, `greptile`, `codium`, `sonarcloud`, `copilot-pull-request-reviewer`, etc.). Otherwise it's a human.

**Did the PR author (from Step 1) approve?** Look for, by the author's login:
- A 👍 reaction (`THUMBS_UP`, also `HEART` / `ROCKET` / `+1`) on the suggestion comment, **or**
- A later reply in the thread that affirms: "yes", "sure", "ok", "agreed", "good/great idea", "good/great point", "makes sense", "will do", "done", "fixed", "sounds good", "lgtm", "+1", "👍", "✅", or similar.

**Did the PR author decline?** A `THUMBS_DOWN` reaction, or a reply like "no", "won't fix", "disagree", "out of scope", "not now", "later", "skip". → **Skip** the thread (record the reason).

Bucket each thread:

- **Approved** — the author approved (reaction or affirmative reply). Implement and commit, **no further confirmation needed**.
- **Declined** — the author declined. Skip.
- **Needs evaluation** — everything else: agent-review threads with no author approval, and any human thread with no author response.

## Step 4: Build the item list

Produce a flat list. Each item has:

- **id** — `thread-<databaseId>` (or `review-<short-slug>` for summary bodies)
- **suggester** — `human` | `agent`
- **stance** — `approved` | `needs-eval` (declined items are already dropped)
- **type** — `missing-test`, `bug-fix`, `refactor`, `security`, `perf`, `docs`, `style`, `naming`, `architecture`, `unclear-requirement`, `other`
- **location** — file path + line range when available
- **summary** — one sentence
- **detail** — verbatim quote of the reviewer text (ground truth for subagents)
- **options** — alternatives the reviewer offered, recommended one marked
- **ambiguous** — true iff `options` is non-empty AND `$ARGUMENTS` doesn't resolve it

## Step 5: Evaluate feasibility of `needs-eval` items

For each `needs-eval` item, check it against the **current code** (Read/Grep): is the reported issue real and still present, or already addressed / a false positive? Write a one-line assessment per item.

Then resolve in one batched pass before any implementation:

- Drop items already fixed in the code (note them in the final report).
- For ambiguous items (`options` unresolved by `$ARGUMENTS`), include the reviewer's recommendation as the first `AskUserQuestion` option labeled `(Recommended)`.
- For each remaining `needs-eval` item, ask the user to **confirm implement vs. skip**, surfacing your feasibility assessment. Always include a `Skip` option.
- Do NOT drop `needs-eval` items simply because they were not mentioned in `$ARGUMENTS` — their absence from `$ARGUMENTS` means "no pre-resolved decision," not "skip."

Batch with `AskUserQuestion` (≤4 questions per call). **Approved items skip this step entirely** — they're already greenlit. All questions must be resolved before implementation starts; don't interleave questions with execution.

## Step 6: Plan parallel groups and commit groups

The code is already pushed, so you keep **both** groupings.

**Parallel groups** — what can run concurrently in subagents. Items are independent if they touch disjoint files (or non-overlapping regions) and neither's output feeds the other. When in doubt, separate — cheap to over-split, expensive to merge-conflict.

**Commit groups** — what belongs in one logical commit, grouped by intent not by file (e.g. "test: cover X and Y", "fix: address security review", "docs: update API examples"). A commit group can span multiple parallel groups (wait for all, then commit together); a parallel group can span multiple commit groups (split at staging time).

Present the plan:

```
Parallel groups (concurrent subagents):
  [A] thread-3 (approved), thread-9 (approved)  — missing tests for module X   → testing-expert
  [B] thread-7 (needs-eval → confirmed)         — refactor auth middleware     → refactoring-expert

Commit groups (atomic commits, in order):
  1. test: cover module X        ← A
  2. refactor(auth): simplify    ← B

Skipped: thread-12 (author declined), thread-5 (already addressed)
```

Confirm the plan. A short "looks good" is enough.

## Step 7: Execute in parallel

Launch a specialist subagent per parallel group via **Task**, all in a **single message** so they run concurrently.

Match `subagent_type` to the work: tests → `testing-expert` (or the repo's `vitest`/`jest` variant); refactors → `refactoring-expert`; TS types → `typescript-type-expert`; React → `react-expert`; perf → `react-performance-expert` / `database-expert`; a11y → `accessibility-expert`; otherwise `general-purpose`.

Each subagent prompt must contain:
- The verbatim feedback items it owns (id + detail quote)
- The exact file paths and line ranges to change
- Any user-resolved decisions for ambiguous items
- The instruction: **do not commit** — commits are batched after parallel work finishes
- A short report-back: items addressed, files changed, anything surprising

Track progress with `TodoWrite`.

## Step 8: Commit in batches

After all subagents finish, for each commit group in order:
1. `git status` to see what changed.
2. Stage only this group's files: `git add <specific files>`. Never `git add .` / `git add -A`.
3. Write a conventional-commit message reflecting the group's intent.
4. Commit.

If a group's files also contain unrelated changes (a subagent strayed out of scope), stop and ask before committing.

Do not push, do not resolve threads, do not reply on the PR — leave those to the user (or a later `/git:push` / `/ship`).

## Step 9: Report

- **Addressed** — item ids + the commit sha each landed in, noting which were auto-applied (author-approved) vs. confirmed
- **Skipped** — item ids + reason (author declined, already addressed, user skipped, blocked)
- **Commits** — sha + subject for each new commit
- **Follow-ups** — anything larger than expected or needing the user's attention

End by noting the new commits are local: the PR won't update until the user pushes.
