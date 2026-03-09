#!/bin/bash
# Stop hook: remind Claude to consider updating learnings after substantive work.
# Only triggers when there are uncommitted changes (i.e., work was done).

if git diff --quiet HEAD 2>/dev/null && git diff --cached --quiet HEAD 2>/dev/null; then
  # No changes — nothing to reflect on
  exit 0
fi

echo "If this session involved debugging a non-obvious issue, a surprising framework behavior, a failed approach that was later corrected, a UX/design correction from the user, or a refactoring request on code you produced, consider running /learn to capture the insight in docs/learnings.md."
