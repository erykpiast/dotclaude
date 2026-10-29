# Morning Brief

Generates a weekday morning brief at 9am (Mon–Fri) and opens it in your browser.

## How it works

1. A `launchd` agent fires at 09:00 on weekdays.
2. It runs `morning-brief.sh`, which calls `claude -p "<prompt>"` (Claude Code CLI).
3. Claude gathers data from Slack (MCP), Linear (MCP), and GitHub (`gh` CLI) and writes a
   **strict JSON** file to `/tmp/morning-brief.json` (conforming to `brief.schema.json`).
   It produces no HTML.
4. The script renders that JSON into `/tmp/morning-brief.html` with `render-brief.jq` — a
   **static template**, so identical data always produces byte-identical HTML — then opens
   it with `open`.

Separating data (Claude) from presentation (static template) is what keeps the page
stable across runs: only the underlying data can change, never the layout/markup.

## Files

- `morning-brief.sh` — orchestrator: loads the prompt, runs Claude → JSON, renders → HTML, opens it.
- `morning-brief-prompt.md` — the Claude prompt (edit to change what data is gathered). The
  script substitutes `{{DATE}}`, `{{DATA_FILE}}`, `{{SCHEMA_FILE}}`, `{{SCRIPTS_DIR}}`,
  `{{PICKS_WINDOW}}`, `{{PICKS_CANDIDATES_FILE}}`, `{{PICKS_CANDIDATES_LINES}}`, and
  `{{LOOKBACK_DATE}}`.
- `morning-brief.env.example` — template for the personal values (Slack user ID, email).
  Copy it to `morning-brief.env`, which git ignores. The script stops if the file is missing.
- `brief.schema.json` — JSON Schema the generated data must conform to (the data contract).
- `render-brief.jq` — static `jq` template that renders the JSON into HTML (edit to change
  the look). Deterministic; escapes all dynamic text with `@html`.
- `scripts/` — deterministic data-fetching helpers the prompt invokes:
  - `gh-prs-ready-to-merge.sh` — my approved, open PRs (3a).
  - `gh-prs-awaiting-approval.sh` — my unapproved PRs with unresolved review threads (3b).
  - `gh-prs-needing-attention.sh` — PRs (mine or others') with a comment I have not answered (3c).
    Each card lists those comments. A comment counts when it is the newest human comment in its
    thread, I have not reacted to it, and the PR is mine or I posted in that thread. Bot comments
    and resolved threads are skipped. A PR where I am a requested reviewer also appears when it is
    not a draft and no reviewer's latest review is an approval. Reactions are read up to 50 per comment because of GitHub's
    query limits.
  - Each prints a JSON array. Override the org with `GIGS_ORG=...` (default `gigs`).
  - `slack-picks-candidates.py` — every thread in the picks window that I have not seen
    (section 4). `morning-brief.sh` runs it before Claude, not the prompt. Reads the Slack
    API with a user token, because the model stops paging early and misses threads.
- `com.eryk.morningbrief.plist` — the launchd agent.
- `/tmp/morning-brief.slack-candidates.json` — input for section 4, from `slack-picks-candidates.py`.
- `/tmp/morning-brief.json` — generated data (the contract between Claude and the renderer).
- `/tmp/morning-brief.html` — rendered output.
- `/tmp/morning-brief.log` — readable progress (each tool call, result, final summary).
- `/tmp/morning-brief.stream.jsonl` — raw Claude stream-json events, for debugging.

## Iterating

- Change **what data** appears → edit `morning-brief-prompt.md` (and `brief.schema.json` if
  you add/remove fields).
- Change **how it looks** → edit `render-brief.jq` only, then re-render without re-querying:
  ```bash
  jq -r -f render-brief.jq /tmp/morning-brief.json > /tmp/morning-brief.html && open /tmp/morning-brief.html
  ```

## Prerequisites

- `claude` CLI on PATH, authenticated, with the Slack and Linear MCP connectors enabled.
- `gh` CLI authenticated for the `gigs` org.
- `jq` on PATH (used by the PR scripts and to format the streaming log).
- `python3` on PATH, and a Slack user token in the Keychain item `morning-brief-slack`
  (or in `SLACK_USER_TOKEN`). Create a Slack app with these user token scopes:
  `channels:history`, `groups:history`, `channels:read`, `groups:read`, `search:read`,
  `users:read`. Install it, then store the `xoxp-` token:
  ```bash
  security add-generic-password -a "$USER" -s morning-brief-slack -w
  ```
  Without the token, section 4 is empty and the rest of the brief still works.
- Edit `morning-brief.sh` if your Homebrew/binary paths differ from `/opt/homebrew/bin`.
- A `morning-brief.env` file with your values:
  ```bash
  cp morning-brief.env.example morning-brief.env
  # then set SLACK_USER_ID (Slack profile → Copy member ID) and USER_EMAIL
  ```

## Install

```bash
# 1. Copy the plist into LaunchAgents.
cp com.eryk.morningbrief.plist ~/Library/LaunchAgents/

# 2. Load it.
launchctl load ~/Library/LaunchAgents/com.eryk.morningbrief.plist
```

On modern macOS you can also use the newer syntax:

```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.eryk.morningbrief.plist
```

## Test it now (without waiting for 9am)

```bash
# Run the script directly:
./morning-brief.sh

# Or trigger the loaded launchd job:
launchctl start com.eryk.morningbrief
```

## Manage

```bash
# Check status (look for the label):
launchctl list | grep morningbrief

# Unload (stop scheduling):
launchctl unload ~/Library/LaunchAgents/com.eryk.morningbrief.plist

# Reload after editing the plist:
launchctl unload ~/Library/LaunchAgents/com.eryk.morningbrief.plist
launchctl load   ~/Library/LaunchAgents/com.eryk.morningbrief.plist
```

## Brief sections

1. **Slack threads needing response** — threads from the last 48h where I participated
   (mentioned or replied), the latest message isn't mine, I haven't reacted, and it's not
   a bot. (Uses `SLACK_USER_ID` from `morning-brief.env`.)
2. **Linear issues** — assigned to `USER_EMAIL` from `morning-brief.env`, status In Progress or Todo, urgent/
   overdue flagged first.
3. **GitHub PRs** — my open PRs that are approved and ready to merge; my open PRs with
   unresolved threads; and PRs with a comment I have not answered, each card listing those
   comments.
4. **Slack picks you may have missed** — at most 3 threads from 09:00 on the previous
   working day (Friday on Mondays) to 09:00 today, in channels I am a member of, where I
   did not post, react, or get mentioned. Claude ranks them against my recent Slack
   messages, Linear issues, GitHub PRs, and Claude Code memory files. Shown below
   section 1.

## Notes

- launchd runs with a minimal environment, so the script sets `PATH` explicitly. If a
  tool isn't found, check the log and adjust `PATH` in `morning-brief.sh`.
- If the Mac is asleep at 9am, the job runs at the next wake. Set `RunAtLoad` to `true`
  in the plist if you also want it to run whenever you log in.
