#!/usr/bin/env bash
# Poll `gh pr checks` until every check whose name contains $1 (case-insensitive
# substring) reaches a terminal state, or any of them fails.
#
# Usage: wait-checks.sh [substring]
#   - empty substring matches every check
#
# Exit codes:
#   0 — all matching checks completed without failure
#   1 — at least one matching check failed or was cancelled
#   2 — no checks reported on the PR (after one grace poll), no checks matched
#       the query, or `gh pr checks` failed
#   3 — timed out after 60 minutes; partial state is printed

set -u

query=$(printf %s "${1:-}" | tr '[:upper:]' '[:lower:]')
max_iters=120     # 60 minutes at 30s intervals
empty_grace=4     # tolerate ~2 minutes of empty polls before giving up
                  # (workflows can take a minute or two to register after push)
i=0

while [ "$i" -lt "$max_iters" ]; do
  i=$((i + 1))

  out=$(gh pr checks --json name,bucket,link,state 2>/dev/null) || {
    echo "gh pr checks failed"
    exit 2
  }

  total_all=$(echo "$out" | jq 'length')
  if [ "$total_all" -eq 0 ]; then
    if [ "$empty_grace" -gt 0 ]; then
      empty_grace=$((empty_grace - 1))
      sleep 30
      continue
    fi
    echo "No CI checks reported for this PR."
    pr_state=$(gh pr view --json isDraft,mergeable,mergeStateStatus 2>/dev/null) || pr_state=""
    if [ -n "$pr_state" ]; then
      is_draft=$(echo "$pr_state" | jq -r '.isDraft')
      mergeable=$(echo "$pr_state" | jq -r '.mergeable')
      merge_status=$(echo "$pr_state" | jq -r '.mergeStateStatus')
      if [ "$mergeable" = "CONFLICTING" ]; then
        echo "Likely cause: branch has merge conflicts (required checks are gated on conflict resolution)."
      elif [ "$is_draft" = "true" ]; then
        echo "PR is a draft. If your CI is gated on non-draft state, mark it ready: gh pr ready"
      else
        echo "PR state: isDraft=$is_draft, mergeable=$mergeable, mergeStateStatus=$merge_status"
      fi
    fi
    exit 2
  fi

  matches=$(echo "$out" | jq --arg q "$query" '[.[] | select(.name | ascii_downcase | contains($q))]')
  total=$(echo "$matches" | jq 'length')
  if [ "$total" -eq 0 ]; then
    echo "No checks match: ${1:-}"
    echo "Available checks:"
    echo "$out" | jq -r '.[].name'
    exit 2
  fi

  failed=$(echo "$matches" | jq '[.[] | select(.bucket == "fail" or .bucket == "cancel")] | length')
  # Anything outside the known terminal set is treated as still pending, so
  # unknown future bucket values do not silently exit 0.
  pending=$(echo "$matches" | jq '[.[] | select(.bucket != "pass" and .bucket != "fail" and .bucket != "cancel" and .bucket != "skipping")] | length')

  if [ "$failed" -gt 0 ]; then
    echo "$matches" | jq -r '.[] | "\(.bucket | ascii_upcase)\t\(.name)\t\(.link)"'
    exit 1
  fi
  if [ "$pending" -eq 0 ]; then
    echo "$matches" | jq -r '.[] | "\(.bucket | ascii_upcase)\t\(.name)\t\(.link)"'
    exit 0
  fi

  sleep 30
done

echo "Timed out after 60 minutes. Last state:"
echo "$matches" | jq -r '.[] | "\(.bucket | ascii_upcase)\t\(.name)\t\(.link)"'
exit 3
