#!/usr/bin/env bash
# Poll a PR for review feedback posted after a timestamp by anyone except the
# PR author. Return once feedback has arrived and the count has stayed the same
# for a settle period, so a reviewer that posts many comments is read as one
# round.
#
# Usage: wait-feedback.sh <owner/repo> <pr-number> <since-iso8601>
#   - <since-iso8601> must be UTC with a `Z` suffix, e.g. 2026-11-04T10:00:00Z,
#     because the script compares it to GitHub timestamps as strings
#
# Exit codes:
#   0 — new feedback arrived; one KIND<TAB>AUTHOR<TAB>URL line per item is printed
#   2 — bad arguments, or `gh api` failed 3 polls in a row
#   3 — timed out after 30 minutes with no new feedback

set -u
set -o pipefail

repo=${1:-}
pr=${2:-}
since=${3:-}
if [ -z "$repo" ] || [ -z "$pr" ] || [ -z "$since" ]; then
  echo "Usage: wait-feedback.sh <owner/repo> <pr-number> <since-iso8601>"
  exit 2
fi

interval=30
max_iters=60      # 30 minutes at 30s intervals
settle_polls=4    # the count must stay the same for ~2 minutes
max_failures=3

author=$(gh api "repos/$repo/pulls/$pr" --jq .user.login 2>/dev/null) || {
  echo "Cannot read PR $repo#$pr."
  exit 2
}

# Print one KIND<TAB>AUTHOR<TAB>URL line per item newer than $since that the PR
# author did not post. `--paginate` emits one JSON array per page, so `jq -s`
# merges the pages before filtering.
list_new() {
  local kind=$1 endpoint=$2 time_key=$3
  gh api --paginate "$endpoint" 2>/dev/null \
    | jq -rs --arg s "$since" --arg a "$author" --arg kind "$kind" --arg k "$time_key" '
        (add // [])[]
        | select(.[$k] != null and .[$k] > $s and .user.login != $a)
        | "\($kind)\t\(.user.login)\t\(.html_url)"'
}

poll() {
  list_new inline "repos/$repo/pulls/$pr/comments" created_at &&
    list_new review "repos/$repo/pulls/$pr/reviews" submitted_at &&
    list_new comment "repos/$repo/issues/$pr/comments" created_at
}

i=0
failures=0
last=-1
stable=0
items=""

while [ "$i" -lt "$max_iters" ]; do
  i=$((i + 1))

  if ! items=$(poll); then
    failures=$((failures + 1))
    if [ "$failures" -ge "$max_failures" ]; then
      echo "gh api failed $max_failures polls in a row."
      exit 2
    fi
    sleep "$interval"
    continue
  fi
  failures=0

  count=$(printf '%s' "$items" | grep -c .)
  if [ "$count" -gt 0 ]; then
    if [ "$count" -eq "$last" ]; then
      stable=$((stable + 1))
    else
      stable=0
    fi
    if [ "$stable" -ge "$settle_polls" ]; then
      printf '%s\n' "$items"
      exit 0
    fi
  fi
  last=$count

  sleep "$interval"
done

# Feedback that arrived near the timeout but did not settle is still a round.
if [ -n "$items" ]; then
  printf '%s\n' "$items"
  exit 0
fi

echo "No new feedback after 30 minutes."
exit 3
