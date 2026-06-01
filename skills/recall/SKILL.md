Search persistent memory for relevant knowledge in the current project.

If the user provides a query (e.g., `/recall vitest`), search for matching entries. If no query is provided, list all memory entries grouped by type.

## Process

### With a query

Search across two locations for entries matching the query:

1. **Project memory** at `.claude/memory/` — read all `.md` files and match against the query (check filenames, frontmatter `name`/`description` fields, and body content)
2. **Native auto memory** at `~/.claude/projects/*/memory/` for the current project — determine the project hash from the git root path and search that directory

For each match, display:
- Type (from frontmatter)
- Name and description
- Date (created/updated)
- A brief excerpt of the body (first 2-3 lines)

Sort results by relevance (title/name matches first, then body matches).

### Without a query

Read `.claude/memory/index.md` and display it. If it doesn't exist, check native auto memory and display that instead. If neither exists, report that no memory has been captured for this project yet and suggest using `/remember` or `/reflect`.
