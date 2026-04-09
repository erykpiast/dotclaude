# Global Instructions

## Vitest: always use `CI=true` to prevent watch mode

Claude Code's Bash tool runs commands in a pseudo-TTY, which makes vitest enter watch mode and hang indefinitely. **Always** prefix vitest/test commands with `CI=true`:

```bash
# WRONG — hangs in watch mode
pnpm test -- src/utils/foo.test.ts
npx vitest src/utils/foo.test.ts

# CORRECT
CI=true pnpm test -- src/utils/foo.test.ts
CI=true npx vitest src/utils/foo.test.ts
```

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
