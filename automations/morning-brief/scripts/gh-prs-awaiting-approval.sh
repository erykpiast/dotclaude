#!/bin/bash
#
# 3b — My open PRs NOT yet approved that have unresolved review threads (org: gigs).
# Emits a JSON array: [{ number, title, url, repository, reviewDecision, unresolvedThreads }]
#
set -euo pipefail
ORG="${GIGS_ORG:-gigs}"

unresolved_count() {  # owner repo pr -> integer
  gh api graphql -f query='
    query($owner:String!, $repo:String!, $pr:Int!) {
      repository(owner:$owner, name:$repo) {
        pullRequest(number:$pr) {
          reviewThreads(first:100) { nodes { isResolved } }
        }
      }
    }' -F owner="$1" -F repo="$2" -F pr="$3" \
    --jq '[.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved == false)] | length'
}

gh search prs --author=@me --state=open --owner="$ORG" --limit 100 \
  --json number,title,url,repository \
| jq -c '.[]' \
| while read -r pr; do
    url=$(jq -r '.url' <<<"$pr")
    nwo=$(jq -r '.repository.nameWithOwner' <<<"$pr")
    num=$(jq -r '.number' <<<"$pr")
    detail=$(gh pr view "$url" --json reviewDecision,isDraft 2>/dev/null) || continue
    [[ "$(jq -r '.isDraft' <<<"$detail")" == "true" ]] && continue
    decision=$(jq -r '.reviewDecision // ""' <<<"$detail")
    [[ "$decision" == "APPROVED" ]] && continue   # ready-to-merge handled by 3a
    owner="${nwo%%/*}"; repo="${nwo##*/}"
    count=$(unresolved_count "$owner" "$repo" "$num")
    [[ "$count" -gt 0 ]] || continue
    jq -c --arg dec "$decision" --argjson c "$count" \
      '{number, title, url, repository: .repository.nameWithOwner, reviewDecision: $dec, unresolvedThreads: $c}' <<<"$pr"
  done \
| jq -s '.'
