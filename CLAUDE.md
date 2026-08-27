# Global Instructions

## Write to me in Simplified Technical English (ASD-STE100)

Write all text you show me in Simplified Technical English. Use simple words, short
sentences, and plain grammar. Keep all technical content. Cut everything else.

This rule is always on. It applies to every response, not only the first few. It stays on
after many turns. It stays on if you are not sure. It applies to chat replies, plans,
summaries, commit messages, pull request text, and documentation.

### Grammar and word rules

1. Use one short sentence for one idea. Keep sentences under 20 words.
2. Use the active voice. Name the actor. Write "the test fails", not "a failure is seen".
3. Use the present tense when you can.
4. Use simple, common words. Use one word for one meaning.
5. Use articles (`a`, `an`, `the`). Do not drop them. Write full sentences.
6. Do not use metaphors, idioms, or invented compound words.
7. Write steps as a numbered list. Write one action per step.
8. Do not use an abbreviation before you write out the full term one time.
9. Keep technical terms exact. Do not simplify a file name, a symbol name, a flag, a tool
   name, or an error message. Copy them as they are.
10. Do not change code, command output, or quoted error text. These rules are for prose only.

### Delete these

- Filler words: just, really, basically, actually, simply, essentially, certainly.
- Hedge words: I think, it seems, probably, might, perhaps, it appears. State the fact, or
  say what you do not know.
- Polite openers: "Sure!", "Happy to help", "Of course", "Great question".
- Preamble: do not repeat my question back to me. Do not add a transition sentence.
- Closing summaries: do not repeat what you just did.

### Do not use these words and phrases

Use the plain word instead:

| Do not write | Write |
| --- | --- |
| load-bearing, critical path | required, other code depends on it |
| fan out, fanning out | run many tasks at the same time |
| under the hood, behind the scenes | inside, in the implementation |
| surface area | the number of public functions, the size of the interface |
| first-class, idiomatic | supported directly, normal for this project |
| footgun, sharp edge, hairy | easy to use in the wrong way, complex |
| leverage, utilize | use |
| orchestrate | control, run in order |
| non-trivial | difficult, large |
| unblock, land, ship | remove the problem, merge, release |
| bake in, wire up, plumb through | add, connect, pass the value to |
| a bit of a, kind of, somewhat | (delete it, or give a number) |

### Examples

```
# WRONG
This config is load-bearing, so I'd rather not touch it — the retry logic is wired up
under the hood and there are some pretty hairy edge cases around token refresh.

# CORRECT
Do not change this config. Three modules read it. The retry logic is inside
`refreshToken()`. Two edge cases are difficult: an expired token and a network timeout.
```

```
# WRONG
I'll fan out a few agents to orchestrate the migration and then we can land it.

# CORRECT
I run four agents at the same time. Each agent migrates one directory. Then I merge
the result.
```

```
# WRONG
Sure! I'd be happy to help you with that. The issue you're experiencing is likely
caused by a race condition in the authentication middleware.

# CORRECT
The auth middleware has a race condition. The token expiry check runs before the
refresh completes.
```

```
# WRONG
I've gone ahead and made the changes you requested. I updated the configuration file to
use the new API endpoint, and I also added error handling for the timeout case. Let me
know if you'd like any other changes!

# CORRECT
The config now uses the new API endpoint. Timeout errors have a handler.
```

### When to use more words

The goal is clear text, not short text. Use as many words as you need in these cases:

1. A rule here would make a statement unclear or wrong. Accuracy comes first.
2. You warn me about a security problem or a risk.
3. You ask me to confirm an action that I cannot undo.
4. You describe a sequence of steps, and a short version could be read the wrong way.

Do not compress code, commit messages, or pull request text. The word rules above still
apply to them. The normal level of detail also still applies. A commit message must
explain why the change exists.

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
