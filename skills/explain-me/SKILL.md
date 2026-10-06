---
name: explain-me
description: Explain a topic from the ground up, first interviewing the user to map what they already know. Use when the user says they don't understand something, asks for an explanation from scratch or ELI5, or is lost on a concept.
argument-hint: "What should I explain?"
---

Explaining straight away would spend unfamiliar words on unfamiliar words. Do what Ausubel prescribed instead — ascertain what the learner already knows, and teach them accordingly — in two phases: **map**, then **climb**.

Two rule spans both:

 - every explanation leans only on terms the user has confirmed they know, or that you have already explained in this session.
 - speak in ASD-STE100 Simplified Technical English without jargons. Don't use dense prose.

## Map

First, one picker: does the user want working **intuition**, enough to **make a decision**, or **rigorous mechanism**? Intuition about garbage collection and the mechanism of garbage collection have different prerequisite sets, so this answer prunes everything below.

Then build a Gagné learning hierarchy rooted at their question — for each node, ask *what would I have to lean on to explain this?*, never *what are the parts of this?* Search it depth-first, one `AskUserQuestion` per node: 3 of that node's prerequisites, `multiSelect: true`, plus a fourth option "None of these are familiar to me". Never inverse the question, always ask "What are you familiar with?" — so the prerequisites the user selects are the known ones, and closed; the rest are unknown, and you recurse into the first of them. A node with more than 3 prerequisites gets a second picker straight after the first.

Staying inside one line of thought is what makes the interview read as a conversation rather than a survey.

The user is the only terminator. Keep descending as long as they keep marking things unknown, however many levels that takes — no cap, and no floor you declare on their behalf. If they interrupt to say they have had enough, treat every open branch as known and start the climb.

Ground the hierarchy where accuracy is genuinely at risk: read the code when the topic is this codebase, search the docs when it is version-specific, fast-moving, or past your knowledge cutoff. Stable fundamentals need no lookup.

Keep the hierarchy itself internal. The user sees pickers, then explanations.

## Climb

Explain the hierarchy in post-order — deepest prerequisites first, root last — **one concept per message**. Each message:

- is built only from known concepts and nodes already climbed
- gives a one-sentence refresher, in passing, of each known concept it leans on — which is also how a mistaken "known" surfaces, since the user recognises when that sentence does not match what they had in mind
- ends with a picker: "Got it — next" / "Still fuzzy — explain it differently" / "Give me a concrete example"

"Still fuzzy" means the same node from a different angle, not the same explanation reworded.

Needing a term the map missed means the hierarchy was incomplete. Pause the climb, picker that term, recurse into it if the user does not know it, explain it bottom-up, then resume where you left off. The vocabulary rule is absolute.

The final message explains the root. It is the answer to the question the user originally asked — and by then every word in it is one they own.
