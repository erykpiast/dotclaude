# dotclaude

My [Claude Code](https://docs.anthropic.com/en/docs/claude-code) configuration.

## What's inside

The base for my configuration is [ClaudeKit](https://github.com/carlrannaberg/claudekit).

- **`agents/`** — 25 domain expert subagents (TypeScript, React, PostgreSQL, Docker, accessibility, and more). Installed via [ClaudeKit](https://github.com/carlrannaberg/claudekit).
- **`commands/`** — 24 slash commands for git workflows, specs, code review, research, and more. Most installed via [ClaudeKit](https://github.com/carlrannaberg/claudekit).

On top of that I have:

- **`statusline.py`** — Custom status line rendering three sparkline charts (context window %, input tokens, output tokens) with color-coded bars, y-axis labels, and a turn counter.
- **`hooks/`** — Git-aware Stop hook that reminds Claude to capture learnings after substantive work.
- **`templates/`** — Project template for `docs/learnings.md` — a structured log of debugging insights and development patterns.
- **`skills/ship/`** — Custom skill that guides branch naming, commit messages, and PR creation through a structured interactive workflow.

The general configuration:

- **`settings.json`** — Global Claude Code settings (dangerous mode prompt skip, Swift LSP plugin enabled, status line command).

## Install ClaudeKit

```bash
npm i -g claudekit && claudekit setup
```

See the [ClaudeKit repo](https://github.com/carlrannaberg/claudekit) for details.
