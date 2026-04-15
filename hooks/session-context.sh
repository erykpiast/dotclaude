#!/bin/bash
# SessionStart hook: surface project memory at the beginning of a session.
# Silent if no memory exists (no noise for projects without memory).

MEMORY_INDEX=".claude/memory/index.md"

if [ ! -f "$MEMORY_INDEX" ]; then
  exit 0
fi

# Output the memory index so Claude has project context
echo "=== Project Memory ==="
head -40 "$MEMORY_INDEX"
echo ""
echo "Use /recall <query> to search memory. Use /remember to capture new insights."
