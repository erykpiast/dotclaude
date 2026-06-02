---
allowed-tools: Read, Write, Grep, Glob, TodoWrite, Task, AskUserQuestion, mcp__context7__resolve-library-id, mcp__context7__get-library-docs, Bash(ls:*), Bash(echo:*), Bash(command:*), Bash(npm:*), Bash(claude:*)
description: Generate a spec file for a new feature or bugfix
category: validation
argument-hint: "<feature-or-bugfix-description>"
---

## Context
- Existing specs: !`ls -la specs/ 2>/dev/null || echo "No specs directory found"`
- Project context map: !`cat CONTEXT.md 2>/dev/null || echo "NO_CONTEXT_FILE"`

## CONTEXT.md Protocol

**Read `CONTEXT.md` (shown above) before research.** If it printed `NO_CONTEXT_FILE`, create it from the skeleton at the end of this section — `CONTEXT.md` must always exist.

`CONTEXT.md` is a *map*. Its `## Format` section declares where this project keeps its glossary and decisions: inline, or pointing to files like `docs/glossary.md` or `docs/adr/`. Read whatever it points to, and write new terms/decisions in that same layout. Stay in single-file (inline) mode unless `## Format` says otherwise — never split files on your own.

Use the glossary while writing the spec: use its terms verbatim, and when the request introduces a term the glossary doesn't define, define it precisely and append it. When the request uses a term loosely, pin it to the glossary's meaning rather than inventing a synonym.

**Decisions are opt-in.** Only if `CONTEXT.md`'s `## Format` declares a decisions/ADR location, record qualifying decisions there — and only those that clear the **ADR bar**: hard to reverse, surprising, *and* a genuine trade-off between alternatives. If the project tracks no decisions, leave all decisions in the spec body. Never create a decisions section on your own.

**Answer from the repo and glossary before asking the user** (reinforces the Clarification Batch rule below): never ask what the code or glossary already settles.

<details>
<summary>CONTEXT.md skeleton (single-file mode)</summary>

```markdown
# Context

> Entry point for this project's domain language.
> Read this first. It is a map + glossary — not a spec, plan, or scratchpad.

## Format

<!-- How this project organizes context. Edit to match reality.
     Switch a line to a path when the project grows, e.g. `see docs/glossary.md`.
     Skills follow whatever this section declares; they never split files on their own. -->
- **Glossary:** inline below (single-file mode)
<!-- Optional: if this project tracks decisions/ADRs, add a line pointing to them, e.g.
     `- **Decisions:** see docs/adr/`  — skills only read/write decisions when this exists. -->

## Glossary

<!-- One term per entry, alphabetical. Precise and project-specific.
     State what a term is NOT when there's a common confusion. -->

_None yet._
```
</details>

## Optional: Enhanced Library Documentation Support

Context7 MCP server provides up-to-date library documentation for better spec creation.

Check if Context7 is available: !`command -v context7-mcp || echo "NOT_INSTALLED"`

If NOT_INSTALLED and the feature involves external libraries, offer to enable Context7:
```
████ Optional: Enable Context7 for Enhanced Documentation ████

Context7 provides up-to-date library documentation to improve spec quality.
This is optional but recommended when working with external libraries.

Would you like me to install Context7 for you? I can:
  1. Install globally: npm install -g @upstash/context7-mcp
  2. Add to Claude Code: claude mcp add context7 context7-mcp

Or you can install it manually later if you prefer.
```

If user agrees to installation:
- Run: `npm install -g @upstash/context7-mcp`
- Then run: `claude mcp add context7 context7-mcp`
- Verify installation and proceed with enhanced documentation support

If user declines or wants to continue without it:
- Proceed with spec creation using existing knowledge

## FIRST PRINCIPLES PROBLEM ANALYSIS

Before defining any solution, validate the problem from first principles:

### Core Problem Investigation
- **Strip Away Solution Assumptions**: What is the core problem, completely separate from any proposed solution?
- **Root Cause Analysis**: Why does this problem exist? What created this need?
- **Goal Decomposition**: What are we fundamentally trying to achieve for users/business?
- **Success Definition**: What would success look like if we had unlimited resources and no constraints?
- **Alternative Approaches**: Could we achieve the underlying goal without building anything? Are there simpler approaches?

### Problem Validation Questions
- **Real vs. Perceived**: Is this solving a real problem that users actually have?
- **Assumption Audit**: What assumptions about user needs, technical constraints, or business requirements might be wrong?
- **Value Proposition**: What is the minimum viable solution that delivers core value?
- **Scope Validation**: Are we solving the right problem, or treating symptoms of a deeper issue?

**CRITICAL: Only proceed if the core problem is clearly defined and validated. If uncertain, request additional context.**

## MANDATORY PRE-CREATION VERIFICATION

After validating the problem from first principles, complete these technical checks:

### 1. Context Discovery Phase
- Search existing codebase for similar features/specs using AgentTool
- **Use specialized subagents** when research involves specific domains (TypeScript, React, testing, databases, etc.)
- Run `claudekit list agents` to see available specialized experts
- Match research requirements to expert domains for optimal analysis
- Use general-purpose approach only when no specialized expert fits
- Identify potential conflicts or duplicates
- Verify feature request is technically feasible
- Document any missing prerequisites

### 2. Request Validation
- Confirm request is well-defined and actionable
- Note any vague areas or scope ambiguities — collect them for the **Clarification Batch** (see below) instead of interrupting research with one-off questions
- Validate scope is appropriate (not too broad/narrow)

### 3. Quality Gate
- Only proceed past research when you either have 80%+ confidence in the implementation approach **or** have a concrete list of decisions to batch-ask the user about
- Document any assumptions being made

**CRITICAL: If any validation fails, do not improvise. Add the unresolved item to the Clarification Batch and ask the user once, in batch, after research completes.**

## Your task

Create a comprehensive specification document in the `specs/` folder for the following feature/bugfix: $ARGUMENTS

First, analyze the request to understand:
1. Whether this is a feature or bugfix
2. The scope and complexity
3. Related existing code/features
4. External libraries/frameworks involved

If the feature involves external libraries or frameworks AND Context7 is available:
- Use `mcp__context7__resolve-library-id` to find the library
- Use `mcp__context7__get-library-docs` to get up-to-date documentation
- Reference official patterns and best practices from the docs

## END-TO-END INTEGRATION ANALYSIS

Before writing the detailed specification, map the complete system impact:

### System Integration Mapping
- **Data Flow Tracing**: Trace data flow from user action → processing → storage → response
- **Service Dependencies**: Identify all affected services, APIs, databases, and external systems
- **Integration Points**: Map every place this feature touches existing functionality
- **Cross-System Impact**: How does this change affect other teams, services, or user workflows?

### Complete User Journey Analysis
- **Entry Points**: How do users discover and access this feature?
- **Step-by-Step Flow**: What is the complete sequence from start to finish?
- **Error Scenarios**: What happens when things go wrong at each step?
- **Exit Points**: How does this connect to what users do next?

### Deployment and Rollback Considerations
- **Migration Path**: How do we get from current state to new state?
- **Rollback Strategy**: What if we need to undo this feature?
- **Deployment Dependencies**: What must be deployed together vs. independently?
- **Data Migration**: How do we handle existing data during the transition?

**VERIFICATION: Ensure you can trace the complete end-to-end flow before proceeding to detailed specification.**

## CLARIFICATION BATCH

After problem analysis, context discovery, and integration mapping are complete — and **before** writing any section of the spec — collect every remaining ambiguity into one batched prompt using `AskUserQuestion`. Research first, then ask once.

### When to skip this step entirely

If the request entered with high clarity, do not invoke `AskUserQuestion` at all. Proceed directly to spec creation. Bothering the user with no-op confirmation questions is worse than silently proceeding.

Skip when:
- The spec is being created after a brainstorming or design conversation that already resolved the open decisions
- The user's prompt is detailed enough that every material decision has a clear answer
- All remaining gaps are implementation-detail choices that belong in the diff, not the spec

### What counts as a question worth asking

Ask only when a decision **materially shapes the spec** and you cannot pick the right answer from context. Examples:

- Scope ambiguity: "Does this need to handle X, or is X out of scope?"
- Architectural fork: approach A vs. approach B with different trade-offs
- External integration choice: library X vs. library Y vs. roll our own
- Data model decision: flat field vs. nested object, denormalize vs. join
- UX flow decision: inline edit vs. modal, sync vs. async confirmation

Do **not** ask:
- Stylistic preferences (pick a sensible default)
- Questions whose answers don't change the spec
- Questions you can confidently answer from existing codebase patterns
- Implementation-detail questions that belong in the diff

### How to formulate each question

For each question:

1. **Question text** — concrete and decision-shaped. Avoid open-ended "what do you think about X?"
2. **2–4 options** — each one phrase, mutually exclusive
3. **Description per option** — one short sentence stating the concrete trade-off (what you gain, what you give up)
4. **Recommendation** — pick the option you would default to if the user said "you decide". Put it first with `(Recommended)` appended to its label. **Always recommend one.**

### How to batch

`AskUserQuestion` accepts up to 4 questions per call. If there are more than 4 ambiguities, send multiple calls in sequence. Do not interleave questions with implementation work.

### After answers come back

- Apply each answer to the corresponding part of the spec
- A resolved decision becomes a **Decision** in the spec body or relevant section, not an entry in **Open Questions**
- If the project tracks decisions (per `CONTEXT.md`'s `## Format`) and a resolved decision clears the **ADR bar** (hard to reverse, surprising, *and* a real trade-off), also record it there — it outlives this spec
- Reserve the spec's **Open Questions** section for items that remain genuinely unresolvable (e.g., awaiting external input the user also doesn't have yet)

Then create a spec document that includes:

1. **Title**: Clear, descriptive title of the feature/bugfix
2. **Status**: Draft/Under Review/Approved/Implemented
3. **Authors**: Your name and date
4. **Overview**: Brief description and purpose
5. **Background/Problem Statement**: Why this feature is needed or what problem it solves
6. **Goals**: What we aim to achieve (bullet points)
7. **Non-Goals**: What is explicitly out of scope (bullet points)
8. **Technical Dependencies**:
    - External libraries/frameworks used
    - Version requirements
    - Links to relevant documentation
9. **Detailed Design**:
    - Architecture changes
    - Implementation approach
    - Code structure and file organization
    - API changes (if any)
    - Data model changes (if any)
    - Integration with external libraries (with examples from docs)
10. **User Experience**: How users will interact with this feature
11. **Testing Strategy**:
    - Unit tests
    - Integration tests
    - E2E tests (if needed)
    - Mocking strategies for external dependencies
    - **Test documentation**: Each test should include a purpose comment explaining why it exists and what it validates
    - **Meaningful tests**: Avoid tests that always pass regardless of behavior
    - **Edge case testing**: Include tests that can fail to reveal real issues
12. **Performance Considerations**: Impact on performance and mitigation strategies
13. **Security Considerations**: Security implications and safeguards
14. **Documentation**: What documentation needs to be created/updated
15. **Implementation Phases**:
    - Phase 1: MVP/Core functionality
    - Phase 2: Enhanced features (if applicable)
    - Phase 3: Polish and optimization (if applicable)
16. **Open Questions**: Genuinely unresolvable items only — decisions already settled via the Clarification Batch go in their relevant section as resolved choices, not here
17. **References**:
    - Links to related issues, PRs, or documentation
    - External library documentation links
    - Relevant design patterns or architectural decisions

Follow these guidelines:
- Use Markdown format similar to existing specs
- Be thorough and technical but also accessible
- Include code examples where helpful (especially from library docs)
- Consider edge cases and error scenarios
- Reference existing project patterns and conventions
- Use diagrams if they would clarify complex flows (using ASCII art or mermaid)
- When referencing external libraries, include version-specific information
- Do NOT include time or effort estimations (no "X days", "Y hours", or complexity estimates)

Name the spec file descriptively based on the feature:
- Features: `feat-{kebab-case-name}.md`
- Bugfixes: `fix-{issue-number}-{brief-description}.md`

## PROGRESSIVE VALIDATION CHECKPOINTS

After completing each major section:

- **Problem Statement**: Verify it's specific and measurable
- **Technical Requirements**: Confirm all dependencies are available
- **Implementation Plan**: Validate approach is technically sound
- **Testing Strategy**: Ensure testability of all requirements

At each checkpoint, if quality is insufficient, revise before proceeding.

## FINAL SPECIFICATION VALIDATION

Before marking complete:
1. **Completeness Check**: All 17 sections meaningfully filled
2. **Consistency Check**: No contradictions between sections  
3. **Implementability Check**: Someone could build this from the spec
4. **Quality Score**: Rate spec 1-10, only accept 8+

Before writing, use AgentTool to search for:
- Related existing features or code
- Similar patterns in the codebase
- Potential conflicts or dependencies
- Current library versions in package.json or equivalent