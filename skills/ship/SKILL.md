---
name: ship
description: This skill should be used when the user asks to "ship", "prepare a PR", "create a pull request", "commit and push", "finalize for review", "open a draft PR", or wants to prepare their code changes for review. Provides a structured workflow for branch naming, commit messages, and PR creation.
---

# Ship

Prepare code changes for a pull request using conversation context and current git state.

## Process

### Step 1: Assess State

Run these commands in parallel to understand the full context:

- `git status` and `git diff` — understand all staged/unstaged/untracked changes
- `gh pr view --json title,body,url,state 2>/dev/null` — check if a PR already exists for the current branch
- `git log --oneline main..HEAD` — understand all commits on this branch

Combine with conversation context about what was worked on.

### Step 2: Determine Flow

Based on the results from Step 1, follow one of two paths:

- **No existing PR** → follow the **New PR** flow (Steps 3–7)
- **Existing PR found** → follow the **Update PR** flow (Steps 8–10)

---

## New PR Flow

### Step 3: Propose Branch Name

Follow the format: `{PREFIX}/{SHORT_NAME}`

- `PREFIX` — the Linear ticket ID if available, otherwise a conventional commit type (`feat`, `fix`, `chore`)
- `SHORT_NAME` — three to five words separated with `_`, describing the scope

Skip this step if already on a well-named feature branch.

### Step 4: Draft Commit Message

Use conventional commits with the appropriate scope. Always use present tense verbs.

- The first line is a concise summary
- The body describes high-level changes in detail
- Avoid mentioning exact modules, files, or function names in the body

**Example:**
```
feat(user): add SSO login capability

Users can now sign in with their SSO provider, streamlining authentication
and improving security for enterprise accounts.

This change introduces backend logic to handle the SSO authentication
flow, updates the user model to support SSO identities, and adds a new UI
entry point for SSO login on the sign-in page.

Tested with Okta and AzureAD providers. User provisioning and session
handling confirmed.
```

Skip this step if there are no uncommitted changes.

### Step 5: Draft PR Title

Set the PR title to exactly match the commit message header (first line). If there are multiple commits and no new commit to make, summarize the branch's overall change.

### Step 6: Draft PR Description

**Do not wrap or cap line width.** PR descriptions render as Markdown on GitHub and must not have a hard column limit (no 80-column wrap, no soft-wrap). Write each paragraph as a single continuous line and let the renderer handle wrapping. This applies to the body passed to `gh pr create` / `gh pr edit` as well.

**Size the description to the changeset.** Before drafting, look at `git diff --stat main..HEAD`. The description should not dwarf the diff. If the rendered description is more than ~3× the meaningful changed lines, you are overwriting. A 3-line change to one file should produce a paragraph, not an essay — unless the change is genuinely subtle (a tricky concurrency bug, a non-obvious algorithmic choice, a security-sensitive carve-out with broad implications) and the reasoning is load-bearing for review.

**Default structure (non-trivial changes)** — three H2 headers:

- **Why** — The motivation for the change. If the reason is not clearly stated in the conversation context, the initial prompt, or a linked spec/ticket, **stop and ask the user** to provide the motivation before continuing. Do not guess or fabricate a "Why".
- **What** — The net change the branch makes, at branch altitude. For a single new commit this matches the commit message body. With multiple commits, write it independently: per-commit bodies are legitimately granular, and inheriting that granularity here is what turns a description into a changelog.
- **Testing** — Manual scenarios a reviewer can run to observe the change. Create an H3 header per scenario, with precise steps as checkbox bullets.

  Every scenario must pass all three of these gates:

  1. **Observable** — the step produces something a human can see: UI state, CLI output, a file's contents, an API response. "All tests pass", "types check", "no lint errors", "CI is green" fail this gate — they observe the toolchain, not the change.
  2. **Reachable by the reviewer** — someone with the branch checked out and no knowledge of the diff can follow the steps as written.
  3. **Would not run in CI** — if a machine already does it on every push, it is not a testing scenario. This is the sharpest filter; apply it to every bullet before writing it.

  Example:
  ### SSO Login
  - [ ] Go to the login page
  - [ ] Select the SSO option
  - [ ] Authenticate with SSO
  - [ ] Verify the dashboard is displayed

  **When the change has no product surface** (prompt/skill edits, docs, config, tooling), the scenario is exercising *that* surface: invoke the command, skill, or script and describe the behaviour that should differ — naming the old behaviour too, so the reviewer knows what "correct" looks like.

  If there is genuinely nothing a human can observe, write the section as a single line — "No runtime behaviour change — covered by CI." — and stop. Do not invent a scenario to fill the section, and do not fall back to running the test suite.

**Tiny changes (roughly ≤ ~10 changed lines, single file, single concern)** — collapse the structure:

- Drop the **What** section. The diff already shows what; restating it bloats the description.
- Use a single **Why** paragraph (2–4 sentences max) that explains the observed problem and the one-line nature of the fix. State the user-visible effect, not the implementation mechanics.
- Keep **Testing** to one H3 scenario unless the change genuinely has multiple distinct verification paths. Do not add a "verify nothing else regressed" section — that's the default expectation, not a scenario.

**Things to leave out unless they materially help the reviewer:**

- Prior commit hashes, ticket IDs of historical work, or "follow-up to #X" framing when the current change stands on its own. A link in the PR body to a Linear ticket is fine; archaeology is not.
- Production revision identifiers, deployment hashes, log entry IDs, or any string that will be stale within a week.
- Detailed mechanism analysis (which regex matches what, why a sibling key behaves differently) when one sentence captures the gist. Save the depth for the commit body or a code comment if it's truly needed.
- "Behavioural change is only visible after deploy" or similar boilerplate — assume the reviewer knows how deploys work.
- Mentions of typecheck/lint/test-count passing — that's CI's job.

### Step 7: Confirm and Execute

Present the proposed branch name (if changing), commit message (if there are uncommitted changes), PR title, and PR description to the user **before** executing any git commands.

Then ask: **"Create draft PR? (Yes / No)"** and wait for an explicit answer. Do not proceed until the user responds.

When creating the PR, always create it as a **draft**.

---

## Update PR Flow

### Step 8: Draft Commit Message

If there are uncommitted changes, draft a commit message following the same conventions as Step 4.

Skip this step if there are no uncommitted changes.

### Step 9: Regenerate, Then Apply the Minimal Edit

Fetch the existing PR title and body.

**Draft the What and Testing sections from scratch.** Work from the branch's final state — `git diff main...HEAD` and `git diff --stat main...HEAD` — not from the new commits, and not by appending to what is already there. Write it as if the whole branch had landed in a single commit and you were describing it for the first time. Follow Step 6 in full, including the size and altitude rules.

**Intra-branch churn is invisible to the reviewer.** A bug introduced and then fixed on this branch, a refactor of code this branch itself added, a fix applied in response to review feedback on unmerged code — none of these are changes worth describing. The reviewer sees only the net result, so describe only the net result. The path taken to get there is not part of the change.

**Then compare your fresh draft against the live body and apply the smallest edit that reconciles them:**

- If the fresh draft says the same thing as what's already there, leave the body untouched and tell the user so. This is the common outcome for follow-up commits.
- Preserve the existing **Why** verbatim unless the branch's motivation has actually changed.
- Preserve existing checkbox state in **Testing** — reviewers tick boxes. Add a scenario only for behaviour that is genuinely new; remove one only if it is now wrong.
- **Updated PR title** — only if the scope of the PR has materially changed.

Report the outcome as either "description unchanged" or a short list of the specific edits. Do not print a full side-by-side rewrite when a few words changed.

### Step 10: Confirm and Execute

Present the commit message (if applicable) and proposed PR description updates.

Then ask: **"Commit, push, and update PR? (Yes / No)"** and wait for an explicit answer. Do not proceed until the user responds.

Use `gh pr edit` to update the title and/or body.
