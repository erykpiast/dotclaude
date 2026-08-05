---
description: Apply open PR review feedback (human + agent threads) — auto-implement what the PR author already approved, evaluate and confirm the rest, commit in chunks, then optionally push and resolve the threads
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

## Step 5: Verify and evaluate `needs-eval` items

Never ask the user about a `needs-eval` item before you've verified it yourself. For each item, check it against the **current code** (Read/Grep) and write a one-line **assessment**: is the reported issue real and still present, already addressed, or a false positive? For suggestions (refactors, alternatives) where "real" doesn't apply, judge whether it's worth doing and **dig deeper into why it does or does not make sense** — don't relay the reviewer's claim, evaluate it.

This assessment is mandatory and **must be included in every question you raise** (e.g. "issue verified real — null deref on empty input", "suggestion worth considering — would remove the duplicate parse", "claimed race condition not reproducible in current code").

How you handle each item then depends on the suggester:

- **Agent items** — if the issue is **not verified real** (false positive, already fixed, or the suggestion doesn't hold up), **skip without asking**; just note it and your reasoning in the final report. If it **is** verified real (or a worthwhile suggestion), ask the user to confirm implement vs. skip, leading with your assessment.
- **Human items** — **never discard without asking**, even when your assessment says the suggestion doesn't make sense. Always ask, leading with your assessment and the deeper reasoning behind it so the user can decide with full context.

For items you do ask about:
- For ambiguous items (`options` unresolved by `$ARGUMENTS`), include the reviewer's recommendation as the first `AskUserQuestion` option labeled `(Recommended)`.
- Always include a `Skip` option.
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

**Always pass `model: "sonnet"`** on every implementation subagent, regardless of the session's model. The items are already scoped, verified, and confirmed by this point — the subagents are executing a decided change, not deciding what to do — so a Sonnet-class model is the right tier. Do not inherit the parent model and do not upgrade individual groups.

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

Keep the commit SHA for each addressed item — you'll cite it when replying to that item's thread.

## Step 9: Offer to push

The commits are still local. Ask the user whether to push, with a single `AskUserQuestion` (Yes / No):

> Committed N fixes locally. Push to `<headRefName>` and update the PR?

- **No** — stop here. Go straight to the report (Step 11), noting the commits are local and the threads are untouched. Do **not** post replies or resolve threads: the "Fixed in …" links won't resolve until the branch is pushed.
- **Yes** — push the current branch (`git push`, or the repo's existing upstream), then continue to Step 10.

## Step 10: Reply to and resolve threads

Only after a successful push. For each thread-backed item (skip `review-<slug>` summary bodies — they aren't resolvable threads, just note them in the report), post one reply, then resolve the thread.

**Reply body:**
- **Addressed items** — `Fixed in <commit-url>`, where `<commit-url>` is `https://github.com/<owner>/<repo>/commit/<sha>` for the commit that item landed in (Step 8). Add a one-line note if the fix diverged from the suggestion.
- **Not-valid / skipped items** — a short, courteous reason: the assessment that justified dropping it (agent items auto-skipped as not verified real, or items the user chose to skip). Lead with the conclusion, then the reasoning — e.g. `Not addressing this — the claimed null deref can't occur because <reason>.`
- **Author-declined items** — already answered by the author; leave them alone (don't reply, don't resolve) unless the user asks.

Post the reply with the thread's GraphQL node **id** captured in Step 2:

```bash
gh api graphql -F threadId=<thread-node-id> -f body='<reply body>' -f query='
  mutation($threadId:ID!, $body:String!) {
    addPullRequestReviewThreadReply(input:{pullRequestReviewThreadId:$threadId, body:$body}) {
      comment { id url }
    }
  }'
```

Then resolve it:

```bash
gh api graphql -F threadId=<thread-node-id> -f query='
  mutation($threadId:ID!) {
    resolveReviewThread(input:{threadId:$threadId}) {
      thread { id isResolved }
    }
  }'
```

If a reply or resolve call fails (permissions, already resolved, stale id), don't abort the rest — note the failure for that thread in the report and move on.

## Step 11: Report

- **Addressed** — item ids + the commit sha each landed in, noting which were auto-applied (author-approved) vs. confirmed
- **Skipped** — item ids + reason (author declined, already addressed, agent item not verified real, user skipped, blocked); for auto-skipped agent items include the assessment that justified dropping it
- **Commits** — sha + subject for each new commit
- **Threads** — which were replied to and resolved, and any reply/resolve calls that failed (with the reason)
- **Follow-ups** — anything larger than expected or needing the user's attention

End with the push state:
- **Pushed** — the PR is updated; the addressed threads are answered and resolved.
- **Not pushed** — the new commits are local and the threads are untouched; the PR won't update until the user pushes.
