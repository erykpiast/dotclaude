---
description: Wait for CI on the current PR to finish (all green, or first failure)
allowed-tools: Bash(gh:*), Bash(git:*), Bash(~/.claude/skills/ci:wait/wait-checks.sh:*)
category: workflow
argument-hint: "[check description, e.g. tests | staging deployment | e2e]"
---

# Wait for CI

Block until CI on the current PR reaches a terminal state, then report.

**Always launch the waiting command with `run_in_background: true`.** A foreground Bash call would freeze the conversation for the entire CI run; running in the background keeps the session interactive and the runtime will notify you when the process exits. This applies to both modes below — never run the wait in the foreground.

Modes:
- **No argument** — wait for the entire CI suite. Returns on either all-green or the first check failure.
- **With argument** (`$ARGUMENTS`) — interpret the argument as a natural-language description of which check(s) to wait for, resolve it to an actual check name (see Step 2), then wait only for matching checks.

## Step 1 — Confirm there is a PR

Run:

```
gh pr view --json number,headRefName,url 2>/dev/null
```

If this errors or returns nothing, report `No PR for the current branch.` and stop.

## Step 2 — Resolve the check name (only when $ARGUMENTS is provided)

Fetch the current check list:

```
gh pr checks --json name 2>/dev/null
```

Look at the returned names and pick the one(s) that best match the user's intent in `$ARGUMENTS`. Use semantic judgment — "staging deployment" should match `staging-deploy / build / build`, "tests" should match all `test (*/*)` checks, etc.

From the best match, derive the **shortest unambiguous substring** of the check name that uniquely identifies the intended check(s) and contains no shell metacharacters. Use that substring as `FILTER` in Step 3.

If no check is a plausible match, report the available check names and stop — do not launch the background poller.

If the check list is empty (checks haven't registered yet), skip resolution and pass an empty `FILTER` to wait for all checks, noting to the user that the specific filter couldn't be resolved yet.

## Step 3 — Wait

Run the polling helper in background (`run_in_background: true`). After kicking off the background task, return control to the user with a short note identifying which check(s) are being tracked. Do not poll, sleep, or block; the runtime will notify you when the background task exits, and only then proceed to Step 4.

```
~/.claude/skills/ci:wait/wait-checks.sh "FILTER"
```

- When `$ARGUMENTS` was provided, `FILTER` is the resolved substring from Step 2.
- When no argument was provided, `FILTER` is empty (matches every check).

Do **not** use `gh pr checks --watch` directly — it exits immediately when no checks have been registered yet, which is the common case right after a push.

The script polls every 30s and prints a tab-separated `BUCKET<TAB>NAME<TAB>LINK` line per tracked check on exit. Its exit codes:
- `0` — all tracked checks completed without failure.
- `1` — at least one tracked check failed or was cancelled.
- `2` — no checks reported on the PR after one grace poll, no checks matched the filter, or `gh pr checks` failed.
- `3` — timed out after 60 minutes; partial state is printed.

## Step 4 — Report

Keep the report tight:

- ✅ Green: list each completed check with its bucket and link.
- ❌ Failed: list the failing check(s) with link(s) and suggest `/ci:fix`.
- ⚠️ No match: show the list of available check names so the user can retry.

Do not summarize what was just done beyond that.
