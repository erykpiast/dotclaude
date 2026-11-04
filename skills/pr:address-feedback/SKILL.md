---
description: Apply open PR review feedback (human + agent threads) without asking — fix every item verified real, commit in chunks, resolve the threads, push, wait for the next review round and repeat until only low-impact feedback is left, then report the learnings and how docs, AGENTS.md, and linters could catch them earlier
allowed-tools: Bash(gh:*), Bash(git:*), Bash(jq:*), Bash(date:*), Bash(~/.claude/skills/pr:address-feedback/wait-feedback.sh:*), Read, Grep, Glob, Edit, MultiEdit, Write, Task, TodoWrite
argument-hint: "[loose natural-language decisions for ambiguous suggestions]"
category: workflow
---

# Address PR Feedback

Resolve the open review threads on this branch's PR, then keep going round after round until the reviewers have nothing important left to say. The code is **already committed and pushed**, so this skill commits the fixes — keep commits in sensible logical groups alongside the parallelized work.

**This skill runs without questions.** It never asks which items to fix, never asks to confirm the plan, and never asks whether to commit or push. Every item that is verified real gets fixed, committed, and pushed.

**Order at the end of each round: commit, reply, resolve, then push.** Step 9 explains why the push comes last.

**Decisions passed in `$ARGUMENTS`:** $ARGUMENTS

`$ARGUMENTS` supplies **decisions for specific items only** — it is never an authoritative list of what to fix. Items not mentioned in `$ARGUMENTS` are still processed with the default rules in Step 5. The only exception: if `$ARGUMENTS` contains explicit scope-limiting language ("only the approved threads", "skip agent reviews", "one round only"), honor that scope restriction.

## The round loop

Step 1 runs once. Steps 2–11 are one **round**. Step 11 decides whether to wait for another round or stop. Step 12 runs once at the end.

Keep a **ledger** across rounds (in `TodoWrite` or in your notes): for each item, the round number, id, thread node id, type, impact, assessment, outcome (fixed / skipped + reason), and commit sha. Step 12 builds the learnings from this ledger.

## Step 1: Find the PR

Run in parallel:
- `git branch --show-current` — current branch
- `gh pr view --json number,state,url,baseRefName,headRefName,author` — the open PR and its **author** (the creator whose approvals we trust)
- `gh repo view --json owner,name` — the repo's owner and name

If no open PR exists for this branch, stop and tell the user:

> No open PR found for `<branch>`. Push the branch and open a PR first, or use `/review:address-feedback` to act on review output in this conversation (for example `/standards-spec-review`, `/code-review`, or `/spec:validate`).

Do not auto-open a PR.

## Step 2: Fetch unresolved threads, reactions, and reviews

Fetch threads **with reactions, author types, and timestamps** so we can tell humans from bots, detect the author's approvals, and spot new replies:

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
                body path line databaseId createdAt
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

**From round 2 on**, drop items that the ledger already records as handled. Re-open a handled thread only if it has a comment newer than our reply, posted by someone other than the PR author (for example, a human who answered our "not addressing" reply). Drop review summary bodies submitted before the previous push.

## Step 3: Classify each thread by the PR author's stance

For each unresolved thread, the **first comment** is the suggestion. Identify the suggester and the author's response.

**Is the suggester an agent (agentic review)?** True if the first comment's `author.__typename` is `Bot`, or the login matches a known reviewer bot (`*[bot]`, `coderabbitai`, `claude`, `cursor`, `greptile`, `codium`, `sonarcloud`, `copilot-pull-request-reviewer`, etc.). Otherwise it's a human.

**Did the PR author (from Step 1) approve?** Look for, by the author's login:
- A 👍 reaction (`THUMBS_UP`, also `HEART` / `ROCKET` / `+1`) on the suggestion comment, **or**
- A later reply in the thread that affirms: "yes", "sure", "ok", "agreed", "good/great idea", "good/great point", "makes sense", "will do", "done", "fixed", "sounds good", "lgtm", "+1", "👍", "✅", or similar.

**Did the PR author decline?** A `THUMBS_DOWN` reaction, or a reply like "no", "won't fix", "disagree", "out of scope", "not now", "later", "skip". → **Skip** the thread (record the reason).

Bucket each thread:

- **Approved** — the author approved (reaction or affirmative reply). Implement without verification.
- **Declined** — the author declined. Skip.
- **Needs evaluation** — everything else: agent-review threads with no author approval, and any human thread with no author response.

## Step 4: Build the item list

Produce a flat list. Each item has:

- **id** — `thread-<databaseId>` (or `review-<short-slug>` for summary bodies)
- **suggester** — `human` | `agent`
- **stance** — `approved` | `needs-eval` (declined items are already dropped)
- **type** — `missing-test`, `bug-fix`, `refactor`, `security`, `perf`, `docs`, `style`, `naming`, `architecture`, `unclear-requirement`, `other`
- **impact** — `high` or `low` (see below)
- **location** — file path + line range when available
- **summary** — one sentence
- **detail** — verbatim quote of the reviewer text (ground truth for subagents)
- **options** — alternatives the reviewer offered, recommended one marked

**Impact.** An item is `high` if ignoring it would leave a defect or a real risk: wrong behavior, a crash, a security hole, data loss, a measurable performance problem, a missing test for changed behavior, a broken contract or API, or a design problem that makes the next change harder. An item is `low` if the code works the same with or without it: style, formatting, naming, wording of comments or docs, a typo, a small readability refactor, or a reviewer's preference ("nit", "consider", "optional"). When unsure, choose `high`.

## Step 5: Verify and decide — no questions

Never ask the user about an item. Decide every item yourself with the rules below.

For each `needs-eval` item, check it against the **current code** (Read/Grep) and write a one-line **assessment**: is the reported issue real and still present, already addressed, or a false positive? For suggestions (refactors, alternatives) where "real" doesn't apply, judge whether it's worth doing and **dig deeper into why it does or does not make sense** — don't relay the reviewer's claim, evaluate it. Re-check the impact from Step 4 against what you found.

Decide:

- **Verified real** (or a worthwhile suggestion), from any suggester → **fix it**.
- **Not verified real** (false positive, already fixed, or the suggestion doesn't hold up) from an **agent** → **skip**. Step 9 replies with the assessment and resolves the thread.
- **Not verified real** from a **human** → **do not fix**. Step 9 replies with the assessment but **leaves the thread open**, so that the human decides whether to resolve it.
- **Ambiguous** (the reviewer offered options and `$ARGUMENTS` doesn't pick one) → use the reviewer's recommended option. If the reviewer recommended none, pick the option that best fits the code and note the choice in the reply.
- **Approved** items skip verification — the author already greenlit them.

Do NOT drop items simply because they were not mentioned in `$ARGUMENTS` — their absence means "no pre-resolved decision," not "skip."

## Step 6: Plan parallel groups and commit groups

The code is already pushed, so you keep **both** groupings.

**Parallel groups** — what can run concurrently in subagents. Items are independent if they touch disjoint files (or non-overlapping regions) and neither's output feeds the other. When in doubt, separate — cheap to over-split, expensive to merge-conflict.

**Commit groups** — what belongs in one logical commit, grouped by intent not by file (e.g. "test: cover X and Y", "fix: address security review", "docs: update API examples"). A commit group can span multiple parallel groups (wait for all, then commit together); a parallel group can span multiple commit groups (split at staging time).

Print the plan for the user to read, then continue at once. Do not wait for confirmation.

```
Round 2 — parallel groups (concurrent subagents):
  [A] thread-3 (approved), thread-9 (needs-eval → real, high)  — missing tests for module X   → testing-expert
  [B] thread-7 (needs-eval → real, low)                        — rename helper                → refactoring-expert

Commit groups (atomic commits, in order):
  1. test: cover module X        ← A
  2. refactor: rename helper     ← B

Not fixed: thread-12 (author declined), thread-5 (agent, false positive), thread-6 (human, not verified — thread stays open)
```

If no item needs a fix, skip Steps 7, 8, and 10. Still run Step 9 for the replies.

## Step 7: Execute in parallel

Launch a specialist subagent per parallel group via **Task**, all in a **single message** so they run concurrently.

**Always pass `model: "sonnet"`** on every implementation subagent, regardless of the session's model. The items are already scoped and verified by this point — the subagents are executing a decided change, not deciding what to do — so a Sonnet-class model is the right tier. Do not inherit the parent model and do not upgrade individual groups.

Match `subagent_type` to the work: tests → `testing-expert` (or the repo's `vitest`/`jest` variant); refactors → `refactoring-expert`; TS types → `typescript-type-expert`; React → `react-expert`; perf → `react-performance-expert` / `database-expert`; a11y → `accessibility-expert`; otherwise `general-purpose`.

Each subagent prompt must contain:
- The verbatim feedback items it owns (id + detail quote)
- The exact file paths and line ranges to change
- The decisions for ambiguous items (from `$ARGUMENTS` or Step 5)
- The instruction: **do not commit** — commits are batched after parallel work finishes
- A short report-back: items addressed, files changed, anything surprising

Track progress with `TodoWrite`.

## Step 8: Commit in batches

After all subagents finish, for each commit group in order:
1. `git status` to see what changed.
2. Stage only this group's files: `git add <specific files>`. Never `git add .` / `git add -A`.
3. Write a conventional-commit message reflecting the group's intent.
4. Commit.

If a subagent changed files outside its scope, do not stage those changes. Leave them in the working tree and list them under **Follow-ups** in the report.

Record the commit SHA for each addressed item in the ledger — you'll cite it when replying to that item's thread.

## Step 9: Reply to and resolve threads — before the push

Reply and resolve **first**, then push in Step 10. Do not reverse this order.

**Why:** a push can hide an unanswered inline comment. Some repos run an in-house AI reviewer that reacts to the new head commit within seconds. It marks its own open inline comments as outdated or removes them, and their thread ids go stale. Then the reply and resolve calls fail, and the thread looks unanswered in the PR. The commit SHA from Step 8 is final, so the `Fixed in <commit-url>` link is correct before the push. The link is dead for the few seconds between the reply and the push. That is the accepted trade-off.

For each thread-backed item (skip `review-<slug>` summary bodies — they aren't resolvable threads, just note them in the report), post one reply, then resolve the thread unless the rule below says to leave it open.

**Reply body:**
- **Addressed items** — `Fixed in <commit-url>`, where `<commit-url>` is `https://github.com/<owner>/<repo>/commit/<sha>` for the commit that item went into (Step 8). Add a one-line note if the fix diverged from the suggestion or if you picked one of several options. Resolve the thread.
- **Agent items not verified real** — a short, courteous reason. Lead with the conclusion, then the reasoning — e.g. `Not addressing this — the claimed null deref can't occur because <reason>.` Resolve the thread.
- **Human items not verified real** — the same kind of reply. **Do not resolve** the thread; the human reviewer decides.
- **Author-declined items** — already answered by the author; leave them alone (don't reply, don't resolve).

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

If a reply or resolve call fails (permissions, already resolved, stale id), don't abort the rest — note the failure for that thread in the report and move on. A failure here does not block Step 10.

## Step 10: Push

First record the round's start time for Step 11, in UTC with a `Z` suffix:

```bash
date -u +%Y-%m-%dT%H:%M:%SZ
```

Then push the current branch (`git push`, or the repo's existing upstream). Do not ask first.

If the push fails, do not retry with a force flag. Stop the loop and go to Step 12. Report the error, and state that the threads are answered and resolved but the commit links stay dead until the branch reaches the remote. Give the user the exact command to finish the push.

## Step 11: Decide whether to wait for another round

Look at the items of **this round** only. Stop the loop and go to Step 12 if any of these is true:

1. **Only low-impact feedback.** No item in this round is both verified real (or approved) and `impact: high`. This includes a round where every item was a false positive.
2. **Nothing was pushed** in this round.
3. **Round 5 is done.** Five rounds is the cap. Note in the report that the cap stopped the loop.
4. `$ARGUMENTS` limits the run to one round.

Otherwise, wait for the next round. Launch the wait script with `run_in_background: true`, using the timestamp from Step 10:

```
~/.claude/skills/pr:address-feedback/wait-feedback.sh <owner>/<repo> <pr-num> <since>
```

Tell the user in one line that round N is pushed and you wait for reviews. Do not poll, sleep, or block; the runtime notifies you when the script exits.

The script polls every 30s for new inline comments, reviews, and PR comments by anyone except the PR author. It returns after the new feedback stops growing for about 2 minutes, so a reviewer that posts many comments counts as one round. Exit codes:
- `0` — new feedback arrived. Start the next round at Step 2.
- `2` — bad arguments, or `gh api` failed 3 polls in a row. Go to Step 12 and report the error.
- `3` — no new feedback in 30 minutes. Go to Step 12.

A new review that only says "no issues found" or "LGTM" has no actionable items. Treat that round as low-impact and stop.

## Step 12: Learnings and report

### 12a. Learnings

From the ledger, take the items that were **fixed and `impact: high`** across all rounds. Group items that share a root cause (for example, three threads about unchecked `null` from the same API). Rank the groups by severity, then by count. Keep the top five.

For each group, check whether the project already has a rule that should have caught it. Read:

1. `AGENTS.md` and `CLAUDE.md` at the repo root and in the directories the items touched.
2. The contributor docs: `README.md`, `CONTRIBUTING.md`, `docs/`, and any coding-standards file.
3. The linter and type-checker config: for example `eslint.config.*`, `.eslintrc*`, `biome.json`, `tsconfig.json`, `.golangci.yml`, `ruff.toml`, `pyproject.toml`, `.editorconfig`, and the `lint` script in `package.json` or `Makefile`.

Then propose one concrete prevention per group. Prefer the strongest mechanism that works:

1. **A linter or type-checker rule** — when a tool can detect the pattern mechanically. Name the exact rule and the config file, and show the config change. Say whether the rule is built in or needs a plugin.
2. **An `AGENTS.md` instruction** — when the pattern needs judgment. Give the exact text to add and the file and section where it goes. If an existing rule already covers the pattern but agents missed it, propose a rewrite that makes it clearer, not a duplicate.
3. **A docs change** — when the gap is missing project knowledge (a contract, an invariant, a domain rule). Name the file and give the text.

**Do not apply these changes.** Only propose them.

### 12b. Report

Write the report in this order:

1. **Learnings** — for each group from 12a: the issue in one sentence, the thread ids, why the existing docs/rules did not prevent it, and the proposed change.
2. **Rounds** — one line per round: number of items, fixed, skipped, and why the loop stopped (low-impact only, no new feedback, cap, push failed, nothing pushed).
3. **Addressed** — item ids + the commit sha each went into, noting which were author-approved vs. verified by you.
4. **Not fixed** — item ids + reason (author declined, already addressed, false positive, blocked). For human items left open, say so.
5. **Threads** — any reply/resolve calls that failed, with the reason.
6. **Follow-ups** — out-of-scope changes left in the working tree, items larger than expected, and low-impact items from the last round that you fixed but nobody re-reviewed.

End with the push state:
- **Pushed** — the PR is updated; the addressed threads are answered and resolved.
- **Push failed** — the threads are answered and resolved, but the commits are local. The commit links do not work until the push succeeds. Give the command to retry.

End with `Next:` and the one learning that is cheapest to apply.
