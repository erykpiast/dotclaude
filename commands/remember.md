Save an insight, preference, or decision to the current project's persistent memory.

The user provides what to remember as arguments (e.g., `/remember Always use pnpm, not npm`). If no arguments are given, ask what they want to remember.

## Process

1. **Classify** the insight into one of four types:
   - `feedback` — corrections, things that went wrong, approaches to avoid
   - `pattern` — recurring solutions, framework idioms, debugging techniques
   - `decision` — architectural choices with rationale (why X over Y)
   - `reference` — factual knowledge (CLI aliases, API quirks, env setup)

2. **Check for duplicates.** Read `.claude/memory/index.md` if it exists and grep existing memory files for overlapping content. If a duplicate is found, update the existing entry instead of creating a new one (merge content, update the `updated` date).

3. **Bootstrap if needed.** If `.claude/memory/` does not exist, create it by copying the template from `~/.claude/templates/memory-index.md` to `.claude/memory/index.md`.

4. **Write the memory file** at `.claude/memory/{type}_{slug}.md` using this format:

   ```yaml
   ---
   name: Short descriptive title
   description: One-line summary for the index
   type: feedback | pattern | decision | reference
   created: YYYY-MM-DD
   updated: YYYY-MM-DD
   ---

   Concise, actionable body explaining the insight.
   Includes context about when and why it was learned.
   ```

   The slug should be 2-4 words in snake_case derived from the title.

5. **Update the index.** Add a line to `.claude/memory/index.md` under the appropriate type heading:
   ```
   - [{type}_{slug}.md]({type}_{slug}.md) — One-line description
   ```
   Replace the `_(No entries yet.)_` placeholder if this is the first entry in that section.

6. **Evaluate scope.** If the insight applies beyond this specific project (e.g., it's about a framework behavior, a general tool preference, or a universal debugging technique), suggest graduating it to `~/.claude/CLAUDE.md` or `~/.claude/rules/`. Ask the user before doing so.
