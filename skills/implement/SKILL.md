---
name: implement
description: "Implement a piece of work based on a spec or set of tickets."
disable-model-invocation: true
---

Implement the work described by the user in the spec or tickets.

Use /tdd where possible, at pre-agreed seams.

Run typechecking regularly, single test files regularly, and the full test suite once at the end.

Once done, use /standards-spec-review to review the work.

Commit your work to the current branch.

Then write the handoff record to `$(git rev-parse --absolute-git-dir)/agent-work/implement.md`. Overwrite an earlier record. It lets /validate and /ship continue from a different session. Include:

- **Source** — ticket IDs and URLs, spec paths.
- **Base** — the output of `git merge-base main HEAD`.
- **Acceptance criteria** — copied verbatim from the ticket or spec, numbered.
- **Testing instructions** — copied verbatim from the ticket, the spec, or its comments, if any.
- **Built** — one line per criterion: what now satisfies it.
- **How to run** — the commands that start the app or exercise the change locally, if you used any.
- **Gaps** — deviations from the spec, criteria not done, and known risks.

Then run /validate.
