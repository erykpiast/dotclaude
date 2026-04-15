# dotclaude

My [Claude Code](https://docs.anthropic.com/en/docs/claude-code) configuration.

## What's inside

The base for my configuration is [ClaudeKit](https://github.com/carlrannaberg/claudekit).

- **`agents/`** — 25 domain expert subagents (TypeScript, React, PostgreSQL, Docker, accessibility, and more). Installed via [ClaudeKit](https://github.com/carlrannaberg/claudekit).
- **`commands/`** — 24 slash commands for git workflows, specs, code review, research, and more. Most installed via [ClaudeKit](https://github.com/carlrannaberg/claudekit).

On top of that I have:

- **`statusline.py`** — Custom status line rendering three sparkline charts (context window %, input tokens, output tokens) with color-coded bars, y-axis labels, and a turn counter.
  <img width="1510" height="278" alt="CleanShot 2026-03-10 at 18 00 26@2x" src="https://github.com/user-attachments/assets/60a9c14f-517d-49e6-8df6-0c128d7960e0" />
- **`hooks/`** — SessionStart hook that surfaces project memory, and a Stop hook that reminds to run `/reflect` after substantive work.
- **`skills/ship/`** — Custom skill that guides branch naming, commit messages, and PR creation through a structured interactive workflow.

The general configuration:

- **`settings.json`** — Global Claude Code settings (dangerous mode prompt skip, Swift LSP plugin enabled, status line command, SessionStart and Stop hooks).

## Memory system

Three commands for managing per-project persistent memory:

| Command | Purpose |
|---------|---------|
| `/remember <insight>` | Save a specific insight to project memory |
| `/recall <query>` | Search project memory (no query = list all) |
| `/reflect` | Review the session for insights, confirm each before saving |

Memory is stored at `.claude/memory/` inside each project. Each project decides independently whether to commit or gitignore its memory directory. Cross-project knowledge that applies everywhere should be graduated to `CLAUDE.md` or `.claude/rules/`.

### Memory entry format

Each entry is a markdown file with YAML frontmatter:

```yaml
---
name: Short title
description: One-line summary
type: feedback | pattern | decision | reference
created: 2026-04-15
updated: 2026-04-15
---

Concise, actionable body.
```

### How it works

- **SessionStart hook** reads `.claude/memory/index.md` and surfaces it at the beginning of each session. Silent if no memory exists.
- **Stop hook** reminds to run `/reflect` after sessions with code changes.
- **`templates/memory-index.md`** is used to bootstrap `.claude/memory/` in new projects.

## Install ClaudeKit

```bash
npm i -g claudekit && claudekit setup
```

See the [ClaudeKit repo](https://github.com/carlrannaberg/claudekit) for details.
