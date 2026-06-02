---
allowed-tools: Task, Read, Grep, Agent, WebFetch, WebSearch, Glob
description: Analyzes a specification document for completeness, coherence, and reference accuracy before autonomous implementation
category: validation
argument-hint: "<path-to-spec-file>"
---

# Specification Completeness Check

Analyze the specification at: $ARGUMENTS

## Analysis Framework

This command will analyze the provided specification document to determine if it contains sufficient detail for successful autonomous implementation, while also identifying overengineering and non-essential complexity that should be removed or deferred.

### Domain Expert Consultation

When analyzing specifications that involve specific technical domains:
- **Use specialized subagents** when analysis involves specific domains (TypeScript, React, testing, databases, etc.)
- Run `claudekit list agents` to see available specialized experts
- Match specification domains to expert knowledge for thorough validation
- Use general-purpose approach only when no specialized expert fits

### What This Check Evaluates:

The analysis evaluates three fundamental aspects, each with specific criteria:

#### 1. **WHY - Intent and Purpose**
- Background/Problem Statement clarity
- Goals and Non-Goals definition
- User value/benefit explanation
- Justification vs alternatives
- Success criteria

#### 2. **WHAT - Scope and Requirements**
- Features and functionality definition
- Expected deliverables
- API contracts and interfaces
- Data models and structures
- Integration requirements:
  - External system interactions?
  - Authentication mechanisms?
  - Communication protocols?
- Performance requirements
- Security requirements

#### 3. **HOW - Implementation Details**
- Architecture and design patterns
- Implementation phases/roadmap
- Technical approach:
  - Core logic and algorithms
  - All functions and methods fully specified?
  - Execution flow clearly defined?
- Error handling:
  - All failure modes identified?
  - Recovery behavior specified?
  - Edge cases documented?
- Platform considerations:
  - Cross-platform compatibility?
  - Platform-specific implementations?
  - Required dependencies per platform?
- Resource management:
  - Performance constraints defined?
  - Resource limits specified?
  - Cleanup procedures documented?
- Testing strategy:
  - Test purpose documentation (each test explains why it exists)
  - Meaningful tests that can fail to reveal real issues
  - Edge case coverage and failure scenarios
  - Follows project testing philosophy: "When tests fail, fix the code, not the test"
- Deployment considerations

### Reference Link Validation (MANDATORY)

Before any other analysis, extract and validate **every** link and reference in the spec. This catches specs built on fabricated or misunderstood sources.

**Step 1 — Extract all references**
Scan the spec for:
- URLs (http/https links, including documentation links, API references, GitHub issues/PRs)
- File path references (e.g., `src/utils/foo.ts`, `docs/architecture.md`)
- References to specific functions, classes, config keys, CLI flags, or API endpoints

**Step 2 — Verify existence**
For each reference:
- **URLs**: Use `WebFetch` to check the link resolves. If it returns a 404 or error, flag it as **broken**.
- **File paths**: Use `Glob`/`Read` to confirm the file exists in the project.
- **Code references** (functions, classes, flags): Use `Grep` to verify they exist in the codebase.
- **Documentation references**: Fetch or read the referenced doc and confirm it exists.

**Step 3 — Verify content alignment**
For each reference that exists, read/fetch its content and check:
- Does the referenced content **support** the spec's claims? (e.g., if the spec says "as documented in [link], the API supports X" — does the doc actually say that?)
- Does the referenced content **contradict** the spec's proposed approach? (e.g., the linked doc recommends approach A, but the spec chose approach B without justification)
- Does the referenced content describe **limitations or constraints** that the spec ignores?
- Are there **alternatives documented** in the reference that the spec dismissed without adequate justification?

**Step 4 — Report findings**
Produce a **Reference Validation Report** section in the output:
- **Broken links**: References that don't resolve or point to non-existent files/code
- **Content mismatches**: References whose content contradicts the spec
- **Unsupported claims**: Spec claims attributed to a reference that the reference doesn't actually make
- **Missed guidance**: Important guidance in referenced docs that the spec ignores
- **Validated references**: References confirmed to exist and align with the spec

> **CRITICAL**: Any broken link or content mismatch is a **Critical Gap** that blocks implementation readiness. A spec that cites non-existent documentation or misrepresents referenced material cannot be trusted.

### CONTEXT.md Consistency (MANDATORY)

**Read `CONTEXT.md` in the project root first.** If it doesn't exist, flag that as a gap (the project should have one) and skip the sub-checks below. `CONTEXT.md` is a *map*: follow its `## Format` section to locate the glossary and decisions, whether inline or in linked files like `docs/glossary.md` / `docs/adr/`.

Then check the spec against it:

- **Terminology alignment.** Every domain term in the spec that the glossary defines must be used with the glossary's meaning. Flag terms the spec uses loosely, redefines, or substitutes with an undefined synonym. Flag new load-bearing terms the spec introduces that are missing from the glossary — they should be added.
- **Decision capture (only if the project tracks decisions).** If — and only if — `CONTEXT.md`'s `## Format` declares a decisions/ADR location, check that any spec decision clearing the **ADR bar** (hard to reverse, surprising, *and* a genuine trade-off) is recorded there. If the project tracks no decisions, skip this check entirely — do not push the project to adopt ADRs.

Report under a **Context Consistency** heading: terminology mismatches, missing glossary terms, and (when applicable) uncaptured ADR-bar decisions. Treat a redefined core term as a **Critical Gap**; treat an uncaptured irreversible decision as a Critical Gap only when the project tracks decisions.

### Additional Quality Checks:

**Completeness Assessment**
- Missing critical sections
- Unresolved decisions
- Open questions

**Clarity Assessment**  
- Ambiguous statements
- Assumed knowledge
- Inconsistencies

**Overengineering Assessment**
- Features not aligned with core user needs
- Premature optimizations
- Unnecessary complexity patterns

### Overengineering Detection:

**Core Value Alignment Analysis**
Evaluate whether features directly serve the core user need:
- Does this feature solve a real, immediate problem?
- Is it being used frequently enough to justify complexity?
- Would a simpler solution work for 80% of use cases?

**YAGNI Principle (You Aren't Gonna Need It)**
Be aggressive about cutting features:
- If unsure whether it's needed → Cut it
- If it's for "future flexibility" → Cut it
- If only 20% of users need it → Cut it
- If it adds any complexity → Question it, probably cut it

**Common Overengineering Patterns to Detect:**

1. **Premature Optimization**
   - Caching for rarely accessed data
   - Performance optimizations without benchmarks
   - Complex algorithms for small datasets
   - Micro-optimizations before profiling

2. **Feature Creep**
   - "Nice to have" features (cut them)
   - Edge case handling for unlikely scenarios (cut them)
   - Multiple ways to do the same thing (keep only one)
   - Features that "might be useful someday" (definitely cut)

3. **Over-abstraction**
   - Generic solutions for specific problems
   - Too many configuration options
   - Unnecessary plugin/extension systems
   - Abstract classes with single implementations

4. **Infrastructure Overhead**
   - Complex build pipelines for simple tools
   - Multiple deployment environments for internal tools
   - Extensive monitoring for non-critical features
   - Database clustering for low-traffic applications

5. **Testing Extremism**
   - 100% coverage requirements
   - Testing implementation details
   - Mocking everything
   - Edge case tests for prototype features

**Simplification Recommendations:**
- Identify features to cut from the spec entirely
- Suggest simpler alternatives
- Highlight unnecessary complexity
- Recommend aggressive scope reduction to core essentials

### Output Format:

The analysis will provide:
- **Summary**: Overall readiness assessment (Ready/Not Ready)
- **Reference Validation**: Broken links, content mismatches, unsupported claims, missed guidance
- **Context Consistency**: Terminology mismatches with the glossary, missing glossary terms, and uncaptured ADR-bar decisions (only if the project tracks decisions)
- **Critical Gaps**: Must-fix issues blocking implementation
- **Missing Details**: Specific areas needing clarification
- **Risk Areas**: Potential implementation challenges
- **Overengineering Analysis**: 
  - Non-core features that should be removed entirely
  - Complexity that doesn't align with usage patterns
  - Suggested simplifications or complete removal
- **Features to Cut**: Specific items to remove from the spec
- **Essential Scope**: Absolute minimum needed to solve the core problem
- **Recommendations**: Next steps to improve the spec

### Example Overengineering Detection:

When analyzing a specification, the validator might identify patterns like:

**Example 1: Unnecessary Caching**
- Spec includes: "Cache user preferences with Redis"
- Analysis: User preferences accessed once per session
- Recommendation: Use in-memory storage or browser localStorage for MVP

**Example 2: Premature Edge Cases**
- Spec includes: "Handle 10,000+ concurrent connections"
- Analysis: Expected usage is <100 concurrent users
- Recommendation: Cut this entirely - let it fail at scale if needed

**Example 3: Over-abstracted Architecture**
- Spec includes: "Plugin system for custom validators"
- Analysis: Only 3 validators needed, all known upfront
- Recommendation: Implement validators directly, no plugin system needed

**Example 4: Excessive Testing Requirements**
- Spec includes: "100% code coverage with mutation testing"
- Analysis: Tool used occasionally, not mission-critical
- Recommendation: Focus on core functionality tests (70% coverage)

**Example 5: Feature Creep**
- Spec includes: "Support 5 export formats (JSON, CSV, XML, YAML, TOML)"
- Analysis: 95% of users only need JSON
- Recommendation: Cut all formats except JSON - YAGNI (You Aren't Gonna Need It)

This comprehensive analysis helps ensure specifications are implementation-ready while keeping scope focused on core user needs, reducing both ambiguity and unnecessary complexity.