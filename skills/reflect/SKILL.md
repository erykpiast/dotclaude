Review the current session for insights worth preserving. This command replaces `/learn`.

## Process

### Step 1: Review the session

Scan the full conversation context for:

- **Corrections you received** — the user said "no, not that", "don't do X", or redirected your approach
- **Surprising behaviors** — a framework, library, or tool behaved unexpectedly
- **Failed approaches** — something you tried that didn't work before finding the right solution
- **User preferences** — code style, workflow choices, or patterns the user preferred over your initial suggestion
- **Architectural decisions** — choices made about structure, dependencies, or trade-offs, with the reasoning behind them
- **Environment/setup quirks** — CLI aliases, config requirements, or tooling details specific to this project

### Step 2: Identify candidates

For each potential insight, draft a memory entry:
- Classify its type: `feedback`, `pattern`, `decision`, or `reference`
- Write a short title (2-6 words)
- Write a one-line description
- Write a concise body (2-4 sentences)

Skip anything that is:
- Already documented in CLAUDE.md or `.claude/rules/`
- Already captured in `.claude/memory/` (check the index)
- Trivially obvious or project-specific ephemera (temporary state, in-progress work)
- Only relevant within this single session

### Step 3: Present candidates for confirmation

For each candidate, use AskUserQuestion to present it and ask whether to save it. Show the proposed type, title, and a brief summary in the question description so the user can make an informed decision without extra back-and-forth.

If there are multiple candidates, present them all in a single AskUserQuestion with `multiSelect: true` so the user can approve several at once.

If no candidates are found, say so briefly: "Nothing noteworthy to capture from this session." Do not force entries.

### Step 4: Save confirmed entries

For each confirmed candidate, follow the same process as `/remember`:
1. Bootstrap `.claude/memory/` if it doesn't exist (copy template from `~/.claude/templates/memory-index.md`)
2. Write the memory file at `.claude/memory/{type}_{slug}.md` with YAML frontmatter
3. Update `.claude/memory/index.md`

### Step 5: Evaluate graduation

If any confirmed insight applies beyond this project (framework behavior, general tool preference, universal debugging technique), ask the user whether to graduate it to `~/.claude/CLAUDE.md` or `~/.claude/rules/`.
