# Global Instructions

## Prefer read-only wrappers for `gcloud` and `gigs`

When **reading/inspecting** data from Google Cloud or Gigs (listing, describing, retrieving, getting config, etc.), use the read-only wrapper scripts instead of the bare CLI:

- `gcloud` → `~/bin/gcloud-read-only`
- `gigs` → `~/bin/gigs-read-only`

These wrappers allow only read verbs and block anything that mutates state or exposes credentials (e.g. `gcloud auth print-access-token`, `gigs token`, `gigs *-credentials retrieve`).

```bash
# WRONG — bare command for a read
gcloud compute instances list
gigs subscriptions retrieve sub_123

# CORRECT — read-only wrapper
~/bin/gcloud-read-only compute instances list
~/bin/gigs-read-only subscriptions retrieve sub_123
```

`~/bin` is not on `PATH`, so invoke the wrappers by their full `~/bin/...` path. For a mutating operation the wrapper will refuse; only then fall back to the bare command, and confirm first.

## Prefer the `gg` CLI for supported GCP operations

`gg` is Gigs' internal CLI wrapper around common `gcloud` tasks. When a task matches one of its subcommands, use `gg` instead of the raw `gcloud` command — it handles the correct flags, prompts, and defaults. Run `gg <command> --help` to see options.

| Task | Use `gg` | Instead of raw `gcloud` |
| --- | --- | --- |
| Authenticate / refresh application default credentials | `gg gcp-login` | `gcloud auth login --update-adc` |
| Temporarily elevate GCP permissions (request a PAM grant) | `gg elevate-permissions` | `gcloud pam grants create ...` |
| Pin all Cloud Run traffic to a specific revision | `gg pin-revision --project <id> --service <name>` | `gcloud run services update-traffic ...` |

```bash
# WRONG — raw gcloud for a task gg covers
gcloud auth login --update-adc
gcloud run services update-traffic api-production --to-revisions=api-production-3b0edf4-0098-1=100 --region europe-west1

# CORRECT — use gg
gg gcp-login
gg pin-revision --project gigs-backbone --service api-production --revision api-production-3b0edf4-0098-1
```

These are **mutating/auth** operations, so they are out of scope for the read-only wrappers above and require confirmation before running. For read-only inspection, keep using `~/bin/gcloud-read-only`. Fall back to raw `gcloud` only when no `gg` subcommand fits (confirm the current subcommand list with `gg --help`, since it may gain commands over time).

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

## User-invocable-only skills exist but are hidden from your skills listing

These skills live in `~/.agents/skills` (symlinked into `~/.claude/skills`) and carry
`disable-model-invocation: true`, which **deliberately removes them from the model-facing
skills listing**. They are real and installed. You will not see them listed:

`ask-matt`, `grill-me`, `grill-with-docs`, `handoff`, `implement`,
`improve-codebase-architecture`, `setup-matt-pocock-skills`, `teach`, `to-spec`,
`to-tickets`, `triage`, `wayfinder`, `writing-great-skills`

Never tell the user one of these "doesn't exist", and never substitute a similarly-named
listed skill (e.g. reaching for `/spec:create` when asked for `/to-spec` — different
skills, different outputs). When the user names one:

1. Read `~/.agents/skills/<name>/SKILL.md` and follow its process directly. The flag blocks
   *autonomous* invocation, not the user asking for it by name.
2. Re-derive this list when in doubt:
   ```bash
   grep -rl '^disable-model-invocation:[[:space:]]*true' ~/.claude/skills/*/SKILL.md
   ```

Only act on one of these when the user names it. Do not reach for them on your own.

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
