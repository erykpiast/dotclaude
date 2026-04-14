# Development Workflow

End-to-end guide for going from idea to merged PR using the commands in this config.

---

## 1. Explore the idea: `/brainstorm`

Before writing a spec, use `/brainstorm <idea>` to think through the problem space. This is a conversational mode — no files are created, no implementation details discussed.

The brainstorm session will:
- Reframe the problem at a higher level, stripping away assumed solutions
- Propose 3–5 alternative approaches with their tradeoffs
- Drive a back-and-forth to narrow down scope and constraints

It ends with a summary: the problem, the chosen approach, key decisions, open questions, and a suggested next step.

**When to use:** Any time a feature is non-trivial or the right approach isn't obvious. Even a 10-minute brainstorm prevents a lot of spec rewrites.

---

## 2. Build and implement: spec-driven development

Once the direction is clear, follow the spec-driven development pipeline to go from idea to implemented code. See [spec-driven-development.md](./spec-driven-development.md) for the full pipeline.

The short version:
1. `/spec:create` — generate a structured spec from the idea
2. `/spec:validate` — verify references, catch overengineering, identify gaps
3. `/spec:decompose` — *(big tasks only)* break the spec into self-contained tasks
4. `/spec:execute` — implement using concurrent specialist agents
5. **Test & iterate** — manually review the code and test the feature; follow up with prompts
6. `/spec:distil` — condense the spec into a reviewer-facing decision document

---

## 3. Ship: `/ship`

When the implementation is ready, `/ship` handles the full PR workflow:

- If there's no PR yet: proposes a branch name, drafts a commit message, PR title, and description — then waits for confirmation before executing anything
- If a PR already exists: drafts a new commit and proposes updates to the PR title and description

Always creates **draft PRs**. Commit messages follow conventional commits.

---

## Utilities

### `/fix:ci`

When CI fails on a PR, `/fix:ci` fetches the error logs, identifies the root cause, applies fixes, and amends the responsible commit. Uses `--force-with-lease` to push the updated history. If the failure is flaky or environment-related (missing secrets, base drift), it reports to you instead of guessing.

### `/learn`

Reviews the current session for non-obvious insights worth preserving — surprising framework behaviors, failed approaches, debugging dead ends, or user corrections. Captures them in `docs/learnings.md` so future sessions don't repeat the same mistakes. A Stop hook also reminds Claude to consider running this after substantive work.

### `/merge`

Resolves merge conflicts automatically. For each conflicted file, it analyzes both sides using git history and context, produces the correct merged result, and stages it. Runs sanity checks (type errors, tests) after resolving. Stops and asks only when a conflict is genuinely ambiguous — competing business logic with no clear winner.
