#!/bin/bash
#
# 3a — My open PRs that are approved and ready to merge (org: gigs).
# Emits a JSON array: [{ number, title, url, repository, mergeable }]
#
set -euo pipefail
ORG="${GIGS_ORG:-gigs}"

gh search prs --author=@me --state=open --owner="$ORG" --limit 100 \
  --json number,title,url,repository \
| jq -c '.[]' \
| while read -r pr; do
    url=$(jq -r '.url' <<<"$pr")
    detail=$(gh pr view "$url" --json reviewDecision,mergeable,isDraft 2>/dev/null) || continue
    [[ "$(jq -r '.isDraft' <<<"$detail")" == "true" ]] && continue
    [[ "$(jq -r '.reviewDecision // ""' <<<"$detail")" == "APPROVED" ]] || continue
    jq -c --argjson d "$detail" \
      '{number, title, url, repository: .repository.nameWithOwner, mergeable: $d.mergeable}' <<<"$pr"
  done \
| jq -s '.'
