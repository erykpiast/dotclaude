---
name: prior-conversations
description: Find what was said in an earlier Claude Code conversation — in this session before compaction, or in another session/worktree of the same repo. Use whenever the user refers to something as already discussed ("we talked about this", "as I mentioned", "in the previous convo", "you said last time", "in the other worktree", "the plan we agreed on").
---

# Prior Conversations

The user's past conversations are on disk and searchable. **You have access to them.**
Never answer "I don't have access to previous conversations" or "I have no memory of
that" — search first, then answer from what you find.

## When to use this

Any time the user refers to something as already established but it is not in your
current context:

- "we talked about this before", "as I mentioned earlier", "in the previous convo"
- "you already looked into that", "you said last time", "we decided X"
- "in the other worktree", "in the central repo session", "the plan from yesterday"
- a bare reference to a decision, name, or artifact you have no record of

Also use it when the reference is probably *in this session but compacted away* — the
session transcript on disk is complete, including everything dropped from your context.

## Where the conversations live

`~/.claude/projects/<encoded-cwd>/<session-id>.jsonl` — one directory per working
directory, one JSONL file per session. Because every git worktree and every Conductor
workspace is its own working directory, conversations about one repo are spread across
many directories. Subagent transcripts sit under
`<session-id>/subagents/…/agent-*.jsonl`.

Use the helper script rather than grepping by hand — it groups directories by repo (via
git origin, so differently-named worktrees still match), strips system-reminder and
tool-result noise, and prints session ids, dates, worktrees, and branches.

```bash
SCRIPT=~/.claude/skills/prior-conversations/scripts/convo-search.py
```

## Process

### 1. Search

Start scoped to the current repo — that covers every worktree of it, which is the usual
case:

```bash
python3 "$SCRIPT" search "keyword" "another keyword"
```

Terms are case-insensitive regexes and **all** must appear in the same message. Use two
or three distinctive terms (a filename, an error string, a proper noun) rather than one
generic one.

Widen only if that comes up empty:

| Situation | Flag |
| --- | --- |
| Reference is to a different project | `--scope all` |
| Only this worktree matters | `--scope current` |
| A specific directory | `--scope dir:/path/to/worktree` |
| The finding came from a subagent or workflow | `--subagents` |
| It was in a tool call or its output | `--include-tools` |
| Recent only, to cut noise | `--days 7` |

If you cannot guess the keywords, list sessions and match on titles and dates instead:

```bash
python3 "$SCRIPT" sessions --limit 20          # this repo, all worktrees, newest first
python3 "$SCRIPT" repos                        # which repos have history at all
```

### 2. Read the surrounding conversation

A snippet is rarely enough — read the exchange around it before drawing conclusions:

```bash
python3 "$SCRIPT" show <session-id> --grep "keyword" --context 3
```

`<session-id>` accepts the short prefix printed by `search`. Add `--include-tools` to see
what was actually run, `--max-chars 6000` for long turns, `--tail 30` to read how a
session ended.

If the transcript is large and you only need the gist, delegate the reading to a
subagent and ask it to report the decision plus the evidence.

### 3. Answer, with the receipts

Tell the user *where* it came from, so they can verify or resume:

> Yes — you decided this on 2026-08-05 in the `central/rome` worktree
> (branch `feat/pubsub-filter`, session `ef00e1d4`): the malformed-message handler parks
> rather than retries, because …

Offer the resume command when the earlier session is worth continuing:
`claude --resume <full-session-id>` (from that session's working directory).

## Rules

- **Quote the transcript, do not reconstruct it.** If the search finds nothing, say so
  plainly and say what you searched for and in what scope — do not fill the gap with a
  plausible-sounding memory.
- **Check the date and the branch.** An old decision may have been superseded; if two
  sessions disagree, prefer the newer one and flag the conflict.
- **Confirm before acting on something big.** If the recovered conversation implies real
  work, restate what you found and let the user confirm it is the thing they meant.
- **Keep it brief.** Report the conclusion and its provenance, not a transcript dump.
