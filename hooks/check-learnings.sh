#!/bin/bash
# Stop hook: remind to run /reflect after substantive work.
# Only triggers when there are uncommitted changes (i.e., work was done).

if git diff --quiet HEAD 2>/dev/null && git diff --cached --quiet HEAD 2>/dev/null; then
  # No changes — nothing to reflect on
  exit 0
fi

# Count changed files for context
changed=$(git diff --stat HEAD 2>/dev/null | tail -1)

# Check if memory was already updated this session
memory_note=""
if [ -d ".claude/memory" ]; then
  recent=$(find .claude/memory -name "*.md" -newer .claude/memory/index.md 2>/dev/null | head -1)
  if [ -n "$recent" ]; then
    memory_note=" Memory was updated this session."
  fi
fi

echo "Session summary: ${changed}.${memory_note} Run /reflect to review this session for insights worth remembering."
