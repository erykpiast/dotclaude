You are gathering the data for my morning brief for {{DATE}}. Your ONLY output is a single
JSON file written to {{DATA_FILE}}. Do NOT produce HTML — a separate renderer turns the
JSON into the page. Do not print the JSON to stdout; write it to that path with your
file-writing tools.

The JSON MUST conform exactly to the schema in {{SCHEMA_FILE}} (read it first). Use the
exact field names and the exact structure shown in the TARGET SHAPE below. Include EVERY
matching item — never truncate, sample, or summarize the list down. Empty sections are
represented by an empty array [], never omitted. If a source errors, use an empty array
for that section and continue.

You have access to: the gh CLI (GitHub), the Slack MCP connector, and the Linear MCP
connector.

========================================================================
SECTION 1 — Slack threads needing a response  ->  "slack": [ ... ]
========================================================================
My Slack user ID is {{SLACK_USER_ID}}.
Find threads from the last 48 hours where I participated — I was either @-mentioned or
I replied in the thread — that now need my attention. A thread qualifies when ALL of
these are true:
  - I participated (mentioned or replied) within the last 48h.
  - The latest message in the thread is NOT from me ({{SLACK_USER_ID}}).
  - I have NOT reacted to that latest message.
  - The latest message is NOT from a bot (skip bot_id messages / bot users).
Be exhaustive: check every candidate thread against the four conditions and include all
that pass. For each, emit an object: { channel, from, summary, timestamp, permalink }.
- channel: channel name, e.g. "#eng-web".
- from: display name of the person who sent the latest message.
- summary: one sentence on what they're asking/saying.
- timestamp: time of the latest message (ISO-8601 or "YYYY-MM-DD HH:MM").
- permalink: URL to the latest message.
Order most-recent first.

========================================================================
SECTION 2 — Linear issues  ->  "linear": [ ... ]
========================================================================
Using the Linear MCP, list ALL issues assigned to me ({{USER_EMAIL}}) whose status is
exactly "In Progress" or "Todo". Do not filter by anything else and do not drop any —
return every such issue. For each, emit an object:
  { identifier, title, status, priority, dueDate, url, flagged }
- identifier: e.g. "ENG-123".
- status: "In Progress" or "Todo" (verbatim).
- priority: "Urgent" | "High" | "Medium" | "Low" | "No priority".
- dueDate: ISO date string, or null if none.
- url: the linear.app URL.
- flagged: true if priority is Urgent or High, OR the issue is overdue (dueDate before
  {{DATE}}), OR it is due today; otherwise false.
(The renderer sorts flagged issues first — you just set the boolean.)

========================================================================
SECTION 3 — GitHub PRs  ->  "github": { ... }   (org: gigs)
========================================================================
Run the three helper scripts in {{SCRIPTS_DIR}}. Each prints a JSON array to stdout
(empty array [] if nothing matches). Do NOT reimplement their logic and do NOT alter
their output — copy each script's JSON array VERBATIM into the matching key:
  bash {{SCRIPTS_DIR}}/gh-prs-ready-to-merge.sh      ->  github.readyToMerge
  bash {{SCRIPTS_DIR}}/gh-prs-awaiting-approval.sh   ->  github.awaitingApproval
  bash {{SCRIPTS_DIR}}/gh-prs-needing-attention.sh   ->  github.needingAttention
These scripts can take a couple of minutes (per-PR GraphQL calls) — wait for each to
finish. If a script fails, use [] for its key.

========================================================================
SECTION 4 — Slack top picks I may have missed  ->  "slackPicks": [ ... ]
========================================================================
This section is the ONE exception to "include every matching item": pick AT MOST 3.

Window: {{PICKS_WINDOW}}.

A script has already read every channel I am a member of. Read {{PICKS_CANDIDATES_FILE}}.
The file has {{PICKS_CANDIDATES_LINES}} lines. One Read call returns only part of it: call Read
again with offset=<next line> until you have read line {{PICKS_CANDIDATES_LINES}}. Do not rank
before you have read the whole file.
Do NOT search or read Slack for this section; the file is the complete input.
  - "candidates": every thread with activity in the window that I have NOT seen: I did not
    post in it, react in it, or get @-mentioned in it, and its root is not from a bot.
    "root_in_window" is false for an older thread with new replies; for those, "replies"
    holds only the replies inside the window.
  - "my_recent_messages": my own Slack messages since {{LOOKBACK_DATE}}.
If the file has an "error" key, or is missing or not valid JSON, set "slackPicks": [].

Step 1 — Build my interest profile. Use these sources:
  - "my_recent_messages" from the file: topics, channels, projects, and people I talk with.
  - My Linear issues (Section 2) and my open GitHub PRs (Section 3).
  - My GitHub PRs merged since {{LOOKBACK_DATE}}. Run:
      gh search prs --author @me --owner gigs --merged --merged-at ">={{LOOKBACK_DATE}}" \
        --limit 50 --json title,url,repository,closedAt
    Read the titles to learn which features and systems I built or changed.
  - My Claude Code memory files: ~/.claude/projects/*/memory/*.md (skip MEMORY.md).
Give the most weight to the systems I changed in my recent PRs and open issues. A thread
about a system I just built or changed is the strongest signal.
Keep the profile to yourself. Do not write it to the output.

Step 2 — Read EVERY candidate in the file. A long thread can hold several topics. Judge
each candidate by its root AND by EACH of its replies, not only by its newest reply. One
relevant reply is enough to make the thread relevant.

Step 3 — Remove news I already know. The script removes threads I posted or reacted in,
but I can know the same news from another thread or channel. Remove a candidate when
"my_recent_messages" show that I already know its SPECIFIC news: I wrote about the same
event, deadline, announcement, decision, or incident. Example: the thread announces a
poster deadline, and I already discussed that poster with my team.
Do NOT remove a candidate only because I work in the same area. A thread that adds NEW
information to a topic I work on (a new requirement, a new decision, a new bug) is a GOOD
pick. If you are not sure that I know the news, keep the candidate.

Step 4 — Rank. Score each candidate by how useful it is to me, based on the
profile: a decision that affects my work, a change in a system I changed, a question I can
answer, an announcement I must act on, or a discussion about my projects or Linear issues.
Rank lower: social chat, routine updates, and threads with no outcome.
Return the top 3, best first. Return fewer if fewer are relevant. Do not pad the list.

For each, emit an object: { channel, from, summary, why, timestamp, permalink }.
- channel: channel name, e.g. "#eng-web".
- from: display name of the person who started the thread or sent the message.
- summary: two sentences at most — what the thread says, and its outcome if any. For an
  older thread ("root_in_window": false), summarize the relevant reply, not the whole thread.
- why: one sentence on why it matters to ME, citing the specific link to my work
  (an issue, a PR, a project, a system, or a topic I discussed). Only claim a link that
  the profile shows. Do not say I own something unless the profile shows it.
- timestamp: time of the message that the permalink points to ("YYYY-MM-DD HH:MM").
- permalink: URL to the root message if the root is inside the window. For an older
  thread with new replies ("root_in_window": false), URL to the relevant reply inside the window.

========================================================================
TARGET SHAPE (write exactly this structure to {{DATA_FILE}})
========================================================================
{
  "date": "{{DATE}}",
  "generatedAt": "<current ISO-8601 timestamp>",
  "slack": [ { "channel": "...", "from": "...", "summary": "...", "timestamp": "...", "permalink": "..." } ],
  "linear": [ { "identifier": "...", "title": "...", "status": "...", "priority": "...", "dueDate": null, "url": "...", "flagged": false } ],
  "github": {
    "readyToMerge":     [ /* verbatim from gh-prs-ready-to-merge.sh */ ],
    "awaitingApproval": [ /* verbatim from gh-prs-awaiting-approval.sh */ ],
    "needingAttention": [ /* verbatim from gh-prs-needing-attention.sh */ ]
  },
  "slackPicks": [ { "channel": "...", "from": "...", "summary": "...", "why": "...", "timestamp": "...", "permalink": "..." } ]
}

After writing the file, validate it parses as JSON (e.g. `jq empty {{DATA_FILE}}`) and
that the top-level keys date, slack, linear, github, slackPicks are all present. Output
nothing else.
