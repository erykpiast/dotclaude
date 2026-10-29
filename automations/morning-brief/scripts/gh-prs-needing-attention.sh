#!/bin/bash
#
# 3c — PRs (org: gigs) with a comment I have not answered. Covers my own PRs and PRs I
# commented on. A comment is unresponded when ALL of these are true:
#   - It is the newest non-bot comment in its review thread (or in the PR conversation).
#   - Its author is not me.
#   - I have not reacted to it.
#   - The PR is mine, or I posted in that thread.
# Resolved review threads and bot comments are skipped.
# A PR is also listed when I am a requested reviewer, the PR is not a draft, and no reviewer's
# latest review is an approval. The author waits for me in that case, even with no comment.
# The reason tags (review-requested, mentioned) are extra context.
# Emits a JSON array: [{ number, title, url, repository, author, reasons: [..],
#   unresponded: [{ kind, author, createdAt, url, excerpt }] }]
#
set -euo pipefail
ORG="${GIGS_ORG:-gigs}"
ME="$(gh api user --jq .login)"
TSV="$(mktemp)"
trap 'rm -f "$TSV"' EXIT

# --- Gather candidate PRs with their reason tags --------------------------------------
# Each line: <url>\t<reason>. An empty reason keeps the PR as a candidate without a tag.
{
  gh search prs --review-requested=@me --state=open --owner="$ORG" --limit 100 \
    --json url --jq '.[].url' | sed 's/$/\treview-requested/'

  gh search prs --mentions=@me --state=open --owner="$ORG" --limit 100 \
    --json url --jq '.[].url' | sed 's/$/\tmentioned/'

  # PRs I authored or commented on. Their comments decide whether they are listed.
  gh search prs --involves=@me --state=open --owner="$ORG" --limit 100 \
    --json url --jq '.[].url' | sed 's/$/\t/'
} > "$TSV"

# --- Per-PR comment check ---------------------------------------------------------------
QUERY='
  query($owner:String!, $repo:String!, $pr:Int!) {
    repository(owner:$owner, name:$repo) {
      pullRequest(number:$pr) {
        isDraft
        reviews(last:100) { nodes { state author { login } } }
        reviewThreads(first:100) {
          nodes {
            isResolved
            comments(first:50) {
              nodes { author { __typename login } body createdAt url reactions(first:50) { nodes { user { login } } } }
            }
          }
        }
        comments(last:100) {
          nodes { author { __typename login } body createdAt url reactions(first:50) { nodes { user { login } } } }
        }
      }
    }
  }'

# Input: the GraphQL response. Output: a JSON array of unresponded comments.
UNRESPONDED_JQ='
  def unresponded($cs; $mine; $kind):
    [ $cs[] | select((.author.__typename // "") != "Bot" and ((.author.login // "") | endswith("[bot]") | not)) ] as $human
    | select($human | length > 0)
    | $human[-1] as $last
    | select(($last.author.login // "") != $me)
    | select([ $last.reactions.nodes[].user.login ] | index($me) | not)
    | select($mine or any($human[]; (.author.login // "") == $me))
    | { kind: $kind,
        author: ($last.author.login // "ghost"),
        createdAt: $last.createdAt,
        url: $last.url,
        excerpt: ($last.body | gsub("\\s+"; " ") | .[0:140]) };
  .data.repository.pullRequest as $pr
  | ($author == $me) as $mine
  # Not a draft, and no reviewer has an approval as their latest review: the author waits for me.
  | (([ $pr.reviews.nodes | group_by(.author.login // "ghost")[] | last.state ] | index("APPROVED") | not)
     and ($pr.isDraft | not)) as $awaitingReview
  | {
      unresponded: [ ( $pr.reviewThreads.nodes[] | select(.isResolved | not)
                       | unresponded(.comments.nodes; $mine; "review-thread") ),
                     unresponded($pr.comments.nodes; $mine; "comment") ],
      awaitingReview: $awaitingReview
    }'

{
  while read -r url; do
    [[ -z "$url" ]] && continue
    # url like https://github.com/gigs/central/pull/783
    nwo=$(sed -E 's#https://github.com/([^/]+/[^/]+)/pull/[0-9]+#\1#' <<<"$url")
    num=$(sed -E 's#.*/pull/([0-9]+)#\1#' <<<"$url")
    owner="${nwo%%/*}"; repo="${nwo##*/}"
    reasons=$(awk -F'\t' -v u="$url" '$1 == u && $2 != "" { print $2 }' "$TSV" | sort -u | jq -R . | jq -s -c .)

    detail=$(gh pr view "$url" --json title,author) || { echo "skipped $url: gh pr view failed" >&2; continue; }
    author=$(jq -r '.author.login' <<<"$detail")
    title=$(jq -r '.title' <<<"$detail")

    raw=$(gh api graphql -f query="$QUERY" -F owner="$owner" -F repo="$repo" -F pr="$num") \
      || { echo "skipped $url: GraphQL query failed" >&2; continue; }
    result=$(jq -c --arg me "$ME" --arg author "$author" "$UNRESPONDED_JQ" <<<"$raw") \
      || { echo "skipped $url: unexpected GraphQL response" >&2; continue; }
    items=$(jq -c '.unresponded' <<<"$result")
    # Listed when a comment waits for my answer, or when I am a requested reviewer and the
    # author still waits for an approval.
    if [[ "$(jq length <<<"$items")" -eq 0 ]]; then
      [[ "$(jq -r '.awaitingReview' <<<"$result")" == true && "$reasons" == *review-requested* ]] || continue
    fi

    jq -c -n --argjson number "$num" --arg title "$title" --arg url "$url" \
      --arg repository "$nwo" --arg author "$author" --argjson reasons "$reasons" \
      --argjson unresponded "$items" \
      '{number: $number, title: $title, url: $url, repository: $repository, author: $author, reasons: $reasons, unresponded: $unresponded}'
  done < <(cut -f1 "$TSV" | sort -u)
} | jq -s '.'
