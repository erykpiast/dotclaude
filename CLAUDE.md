@AGENTS.md

# Claude Code Instructions

## claudekit-hooks: `test-changed` and paths with special characters

The `claudekit-hooks run test-changed` PostToolUse hook may fail with a shell syntax error when file paths contain parentheses (e.g., Next.js route groups like `(workspace)`). The hook passes unquoted paths to `/bin/sh -c`, which interprets `(` as subshell syntax.

When this hook fails with `syntax error near unexpected token '('`:

1. The failure is a hook bug, **not** a code problem.
2. Run the tests manually with a **quoted** path to verify:
   ```bash
   pnpm test -- "src/app/(workspace)/billing/CountryPlansSection.test.tsx"
   ```
3. If the tests pass when run manually, safely continue.

**Always quote file paths** containing parentheses in any shell command (test, lint, typecheck, etc.):

```bash
# WRONG
pnpm test -- src/app/(workspace)/billing/file.test.tsx

# CORRECT
pnpm test -- "src/app/(workspace)/billing/file.test.tsx"
```

## You *do* have access to previous conversations

Every session is on disk at `~/.claude/projects/<encoded-cwd>/<session-id>.jsonl`, including
sessions from other worktrees of the same repo and the parts of the current session that
compaction dropped from your context.

So never say "I don't have access to previous conversations" or "I have no memory of that".
The moment the user refers to something as already discussed — "we talked about this before",
"as I mentioned", "in the previous convo", "you said last time", "in the other worktree",
"the plan we agreed on" — **invoke the `prior-conversations` skill and search before
answering**. Only after the search comes up empty may you say you cannot find it, and then
say what you searched for and in what scope.
