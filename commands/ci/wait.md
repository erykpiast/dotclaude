---
description: Wait for CI on the current PR to finish (all green, or first failure)
allowed-tools: Bash(gh:*), Bash(git:*), Bash(jq:*), Bash(sleep:*), Bash(echo:*), Bash(bash:*), Bash(printf:*), Bash(tr:*)
category: workflow
argument-hint: "[check name substring, e.g. tests | preview deployment]"
---

# Wait for CI

Block until CI on the current PR reaches a terminal state, then report.

Modes:
- **No argument** — wait for the entire CI suite. Returns on either all-green or the first check failure.
- **With argument** (`$ARGUMENTS`) — wait only for checks whose names contain the argument (case-insensitive substring). Returns when every matching check is done (pass or fail).

The argument is interpolated into a shell command, so it must not contain shell metacharacters (quotes, `$`, backticks, `\`). Plain words and spaces are fine: `tests`, `preview deployment`, `e2e`.

## Step 1 — Confirm there is a PR

Run:

```
gh pr view --json number,headRefName,url 2>/dev/null
```

If this errors or returns nothing, report `No PR for the current branch.` and stop.

## Step 2 — Dispatch by argument

CI runs can take >10 minutes, so always launch the wait command with `run_in_background: true` and let the runtime notify you when it exits. Then read the output and proceed.

### Case A — `$ARGUMENTS` is empty

Run in background:

```
gh pr checks --watch --fail-fast --interval 30
```

Exit codes from `gh pr checks`:
- `0` — all checks passed.
- `1` — at least one check failed (or `--fail-fast` short-circuited).
- `8` — still pending (shouldn't happen with `--watch`, but treat as inconclusive).

When the background task completes, read its output. Then run `gh pr checks` once more (without `--watch`) to grab the final summary table for the report.

### Case B — `$ARGUMENTS` is non-empty

Launch this script in the background. Pass the argument via the env var `WAIT_CI_QUERY` so quoting stays sane:

```bash
WAIT_CI_QUERY="$ARGUMENTS" bash -c '
  q=$(printf %s "$WAIT_CI_QUERY" | tr "[:upper:]" "[:lower:]")
  max_iters=120   # 60 minutes at 30s intervals
  empty_grace=1   # tolerate one empty poll before giving up (CI may not have triggered yet)
  i=0
  while [ "$i" -lt "$max_iters" ]; do
    i=$((i + 1))
    out=$(gh pr checks --json name,bucket,link,state 2>/dev/null) || { echo "gh pr checks failed"; exit 2; }
    total_all=$(echo "$out" | jq "length")
    if [ "$total_all" -eq 0 ]; then
      if [ "$empty_grace" -gt 0 ]; then
        empty_grace=$((empty_grace - 1))
        sleep 30
        continue
      fi
      echo "No CI checks reported for this PR."
      exit 2
    fi
    matches=$(echo "$out" | jq --arg q "$q" "[.[] | select(.name | ascii_downcase | contains(\$q))]")
    total=$(echo "$matches" | jq "length")
    if [ "$total" -eq 0 ]; then
      echo "No checks match: $WAIT_CI_QUERY"
      echo "Available checks:"
      echo "$out" | jq -r ".[].name"
      exit 2
    fi
    failed=$(echo "$matches" | jq "[.[] | select(.bucket == \"fail\" or .bucket == \"cancel\")] | length")
    # Anything not in the known terminal set is treated as still pending,
    # so unknown future bucket values do not silently exit 0.
    pending=$(echo "$matches" | jq "[.[] | select(.bucket != \"pass\" and .bucket != \"fail\" and .bucket != \"cancel\" and .bucket != \"skipping\")] | length")
    if [ "$failed" -gt 0 ]; then
      echo "$matches" | jq -r ".[] | \"\(.bucket | ascii_upcase)\t\(.name)\t\(.link)\""
      exit 1
    fi
    if [ "$pending" -eq 0 ]; then
      echo "$matches" | jq -r ".[] | \"\(.bucket | ascii_upcase)\t\(.name)\t\(.link)\""
      exit 0
    fi
    sleep 30
  done
  echo "Timed out after 60 minutes. Last state:"
  echo "$matches" | jq -r ".[] | \"\(.bucket | ascii_upcase)\t\(.name)\t\(.link)\""
  exit 3
'
```

Exit codes from the script:
- `0` — all matching checks completed without failure.
- `1` — at least one matching check failed or was cancelled.
- `2` — no checks reported on the PR after one grace poll, no checks matched the query, or the `gh` call failed.
- `3` — timed out after 60 minutes; partial state is printed.

## Step 3 — Report

Keep the report tight:

- ✅ Green: list each completed check with its bucket and link.
- ❌ Failed: list the failing check(s) with link(s) and suggest `/ci:fix`.
- ⚠️ No match (Case B only): show the list of available check names so the user can retry.

Do not summarize what was just done beyond that.
