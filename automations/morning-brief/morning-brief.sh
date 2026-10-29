#!/bin/bash
#
# morning-brief.sh
# Generates a weekday morning brief via Claude Code CLI and opens it in the browser.
# Invoked by launchd (~/Library/LaunchAgents/com.eryk.morningbrief.plist) at 9am Mon–Fri.

set -uo pipefail

# launchd runs with a minimal environment. Make sure the tools Claude needs are on PATH.
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$HOME/.local/bin:$PATH"

OUTPUT="/tmp/morning-brief.html"
DATA_FILE="/tmp/morning-brief.json"
PICKS_CANDIDATES_FILE="/tmp/morning-brief.slack-candidates.json"
TODAY="$(date '+%A, %B %-d, %Y')"

# Slack picks window: 09:00 on the previous working day -> 09:00 today (Monday looks back
# to Friday), as Unix timestamps for slack-picks-candidates.py.
DAY_BACK=1
[[ "$(date +%u)" == 1 ]] && DAY_BACK=3
PICKS_LATEST="$(date -j -v9H -v0M -v0S +%s)"
PICKS_OLDEST="$(date -j -v-${DAY_BACK}d -v9H -v0M -v0S +%s)"
PICKS_WINDOW="$(date -j -r "$PICKS_OLDEST" '+%A %Y-%m-%d %H:%M') to $(date -j -r "$PICKS_LATEST" '+%A %Y-%m-%d %H:%M') $(date +%Z)"
LOOKBACK_DATE="$(date -j -v-14d +%Y-%m-%d)"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROMPT_FILE="$SCRIPT_DIR/morning-brief-prompt.md"
SCHEMA_FILE="$SCRIPT_DIR/brief.schema.json"
RENDERER="$SCRIPT_DIR/render-brief.jq"

# Personal values (Slack user ID, email) live in a local file that git ignores.
# Copy morning-brief.env.example to morning-brief.env and fill it in.
ENV_FILE="$SCRIPT_DIR/morning-brief.env"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "Config file not found: $ENV_FILE" >&2
  exit 1
fi
source "$ENV_FILE"
: "${SLACK_USER_ID:?set SLACK_USER_ID in morning-brief.env}"
: "${USER_EMAIL:?set USER_EMAIL in morning-brief.env}"

for f in "$PROMPT_FILE" "$SCHEMA_FILE" "$RENDERER"; do
  if [[ ! -f "$f" ]]; then
    echo "Required file not found: $f" >&2
    exit 1
  fi
done

# Start each run from a clean slate so a stale file can't be mistaken for success.
rm -f "$DATA_FILE" "$OUTPUT" "$PICKS_CANDIDATES_FILE"

# Load the prompt template and substitute placeholders.
PROMPT="$(cat "$PROMPT_FILE")"
PROMPT="${PROMPT//\{\{DATE\}\}/$TODAY}"
PROMPT="${PROMPT//\{\{DATA_FILE\}\}/$DATA_FILE}"
PROMPT="${PROMPT//\{\{SCHEMA_FILE\}\}/$SCHEMA_FILE}"
PROMPT="${PROMPT//\{\{SCRIPTS_DIR\}\}/$SCRIPT_DIR/scripts}"
PROMPT="${PROMPT//\{\{PICKS_WINDOW\}\}/$PICKS_WINDOW}"
PROMPT="${PROMPT//\{\{PICKS_CANDIDATES_FILE\}\}/$PICKS_CANDIDATES_FILE}"
PROMPT="${PROMPT//\{\{LOOKBACK_DATE\}\}/$LOOKBACK_DATE}"
PROMPT="${PROMPT//\{\{SLACK_USER_ID\}\}/$SLACK_USER_ID}"
PROMPT="${PROMPT//\{\{USER_EMAIL\}\}/$USER_EMAIL}"

RAW_STREAM="/tmp/morning-brief.stream.jsonl"

echo "=== $(date '+%Y-%m-%d %H:%M:%S') starting morning brief ==="

# Collect the Slack picks candidates with a script, not the model: the model stops paging
# early and misses threads. On failure the prompt sees an "error" key and skips Section 4.
echo "=== $(date '+%H:%M:%S') collecting Slack candidates -> $PICKS_CANDIDATES_FILE ==="
if ! python3 "$SCRIPT_DIR/scripts/slack-picks-candidates.py" \
    --oldest "$PICKS_OLDEST" --latest "$PICKS_LATEST" --lookback "$LOOKBACK_DATE" \
    > "$PICKS_CANDIDATES_FILE"; then
  echo '{"error": "Slack candidate collection failed; see /tmp/morning-brief.log"}' > "$PICKS_CANDIDATES_FILE"
fi
PICKS_CANDIDATES_LINES="$(wc -l < "$PICKS_CANDIDATES_FILE" | tr -d ' ')"
PROMPT="${PROMPT//\{\{PICKS_CANDIDATES_LINES\}\}/$PICKS_CANDIDATES_LINES}"

# Run Claude Code headless with a streaming JSON event log. It writes the data to
# $DATA_FILE (JSON conforming to brief.schema.json), which is rendered to HTML below.
# Raw events are tee'd to $RAW_STREAM; a jq filter renders readable progress to the log.
claude -p "$PROMPT" \
  --model claude-sonnet-4-6 \
  --permission-mode acceptEdits \
  --allowedTools "Bash,Read,Write,Edit,mcp__claude_ai_Slack,mcp__claude_ai_Linear" \
  --verbose --output-format stream-json \
| tee "$RAW_STREAM" \
| jq --unbuffered -rj 'def t: (now | strftime("%H:%M:%S"));
    if .type == "system" and .subtype == "init" then
      "\(t) ▶ session start — model \(.model // "?"), tools: \((.tools // []) | length)\n"
    elif .type == "assistant" then
      ( .message.content[]? |
        if .type == "text" and (.text | length > 0) then "\(t) 💬 \(.text)\n"
        elif .type == "tool_use" then "\(t) 🔧 \(.name): \((.input // {}) | tostring | .[0:200])\n"
        else empty end )
    elif .type == "user" then
      ( .message.content[]? |
        if .type == "tool_result" then
          ( (.content // "") | if type == "array" then (map(.text // "") | join(" ")) else tostring end
            | gsub("\\s+"; " ") | .[0:240] ) as $r
          | "\(t) ↩  \($r)\n"
        else empty end )
    elif .type == "result" then
      "\(t) ✅ done (\(.subtype // "?")) — \(.num_turns // 0) turns, \(((.duration_ms // 0) / 1000) | floor)s, cost $\(.total_cost_usd // 0)\n"
    else empty end' \
  || echo "(claude stream ended with non-zero status — see $RAW_STREAM)"

# Render the JSON deterministically into HTML. The template is static, so identical data
# always yields identical output.
if [[ -s "$DATA_FILE" ]] && jq empty "$DATA_FILE" 2>/dev/null; then
  echo "=== $(date '+%H:%M:%S') rendering $DATA_FILE -> $OUTPUT ==="
  if jq -r -f "$RENDERER" "$DATA_FILE" > "$OUTPUT" 2>>/tmp/morning-brief.log; then
    open "$OUTPUT"
  else
    echo "Renderer failed; see log." >&2
  fi
else
  echo "No valid JSON at $DATA_FILE — generation failed." >&2
  # Fallback page so something opens.
  cat >"$OUTPUT" <<'FALLBACK_EOF'
<!doctype html><meta charset="utf-8"><title>Morning Brief</title>
<style>body{font-family:system-ui,sans-serif;max-width:40rem;margin:4rem auto;padding:0 1rem;color:#333}</style>
<h1>Morning Brief</h1>
<p>Brief generation failed — no valid data file. Check the log at <code>/tmp/morning-brief.log</code>.</p>
FALLBACK_EOF
  open "$OUTPUT"
fi
