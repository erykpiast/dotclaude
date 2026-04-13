# Spec-Driven Development

A workflow for turning feature requests into validated, decomposed, and autonomously executed implementations using Claude Code slash commands.

## The Pipeline
```text
CREATE → VALIDATE → [DECOMPOSE] → EXECUTE → TEST & ITERATE → DISTILL
```

Each stage gates the next. Don't skip validation — it catches fabricated references, overengineering, and scope creep before any code is written.

## Stage 1: Create (`/spec:create <description>`)

Generates a spec file in `specs/` from a feature or bugfix description.

**What it does:**
- Runs first-principles problem analysis (is this the right thing to build?)
- Searches the codebase for related features, conflicts, and existing patterns
- Optionally pulls library docs via Context7 MCP for accurate API references
- Maps end-to-end system impact: data flow, service dependencies, deployment
- Produces a structured markdown spec with 17 sections

**Output:** `specs/feat-{name}.md` or `specs/fix-{issue}-{name}.md`

**Key behavior:** If the request is vague or confidence is below 80%, it stops and asks clarifying questions rather than guessing.

## Stage 2: Validate (`/spec:validate [<path-to-spec>]`)

Analyzes the spec for completeness, coherence, and reference accuracy.

**What it does:**
- Fetches every URL in the spec to verify it resolves
- Greps the codebase to confirm referenced files, functions, and flags exist
- Checks that referenced docs actually support the spec's claims
- Evaluates WHY (intent), WHAT (scope), and HOW (implementation)
- Runs overengineering detection against YAGNI principles

**Output:** A readiness report with:
- **Reference Validation Report** — broken links, content mismatches, unsupported claims
- **Critical Gaps** — must-fix blockers
- **Features to Cut** — scope reduction recommendations
- **Essential Scope** — the minimum that solves the core problem

**Key behavior:** Any broken link or content mismatch is a Critical Gap that blocks implementation readiness. A spec citing non-existent documentation cannot be trusted.

## Stage 3: Decompose (`/spec:decompose [<path-to-spec>]`)

**For big scope tasks only**. Breaks a validated spec into actionable, self-contained tasks, which can be implemented one by one in separate Claude sessions or in a Ralph loop.

**What it does:**
- Extracts implementation phases and technical dependencies
- Creates tasks with single objectives, clear acceptance criteria, and dependency tracking
- Groups into foundation → feature → testing → documentation phases
- Identifies parallel execution opportunities
- Saves task breakdown to `specs/{name}-tasks.md`

**Output:** Task breakdown document + tasks created in STM (if installed) or TodoWrite.

**Critical rule:** Tasks must contain complete implementation details copied verbatim from the spec — no "as specified in spec" references. Each task is a self-contained mini-specification.

## Stage 4: Execute (`/spec:execute [<path-to-spec>]`)

Implements the validated spec or decomposed tasks using concurrent specialist agents.

**What it does:**
- Loads tasks from STM or creates them directly from the spec
- For each task, it follows a cycle:
  1. **Implement** — launches a domain-specialist agent matching the task
  2. **Test** — launches testing expert for comprehensive test coverage
  3. **Review** — launches code-review expert checking both completeness and quality
  4. **Fix** — addresses critical issues and incomplete requirements
  5. **Commit** — creates atomic commits per task

**Key behavior:** A task cannot be marked done without passing both completeness and quality review. If the review finds the implementation incomplete, it loops back to fix.

## Stage 5: Test & Iterate (manual)

Manually exercise the implementation, catch real-world issues, and drive follow-up prompts until it feels right. This is the stage where the implementation meets actual usage — agents can't replace it.

What to do:
- Review the code diff — check for anything that looks off, overly complex, or inconsistent with the codebase
- Run the feature end-to-end in a real environment
- Compare behavior against the acceptance criteria in the spec
- File follow-up prompts for anything that's wrong, missing, needs polish, or should be refactored
- Repeat until satisfied — each iteration may loop back to any earlier stage

The distil spec captures the final state after this stage, not the original plan, so don't skip it.

## Stage 6: Distil (`/spec:distil [<path-to-spec>]`)

Condenses the spec into a reviewer-facing decision document.

**What it does:**
- Compares the original spec against what was actually implemented (conversation context is ground truth)
- Moves the original to `{name}.plan.md`
- Writes a concise distilled spec focused on reviewable decisions
- Asks the user about any meaningful pivot with unclear rationale

**Output:** A decision document proportional to the change:
- Tiny feature (~40-60 lines): Summary + Decisions + Usage + Acceptance criteria
- Medium feature (~60-100 lines): adds Motivation, What doesn't change, Architecture
- Large feature (~up to 150 lines): all relevant sections

**Key format:** Decisions are framed as "**Chose X** over Y — because Z" to invite reviewer disagreement. No references to "the original plan" — the reviewer only sees the final result.

## Tips

- Run `/spec:validate` even on specs you wrote by hand — the reference validation alone catches broken links and outdated API references.
- The decompose stage's value scales with spec size. For a 20-line bugfix spec, you can skip straight to execute.
- The distil output is meant to be committed alongside the PR. It replaces the spec as the permanent record.
- If STM (Simple Task Manager) is installed, decompose and execute use it for persistent cross-session task tracking with dependency resolution. Otherwise they fall back to TodoWrite (session-only).
