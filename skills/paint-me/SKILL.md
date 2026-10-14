---
name: paint-me
description: Explain a codebase, a module, or a concept as a dark, plain HTML page with diagrams, and open it in the browser. Use when the user asks for a visual, a diagram, a drawing, or to "show" how something works, or when an answer depends on structure, sequence, or a mechanism. Also used by explain-me for concepts with structure.
argument-hint: "What should I paint?"
---

A page answers one question with pictures first. Prose only connects the pictures.

## When to start

- The user asks for a visual ("draw", "show me", "diagram", "paint"): start.
- An answer depends on structure, sequence, or a mechanism, and the user did not ask for a visual: ask one question first, "Open a visual?", with `AskUserQuestion`. Start only on yes.
- Inside an `explain-me` session: do not ask. Paint each concept that has structure, sequence, or a mechanism.

## Steps

1. Find the one question that the page answers. Write the answer as one sentence.
2. Read the sources. For a codebase, read the code before you draw. Never draw a module, a call, or a data flow that you did not see in the code.
3. Plan the figures: one main figure, and up to three supporting figures or one table. Each figure makes one claim.
4. Copy `TEMPLATE.html` (next to this file). Keep its `<style>` and `<script>` blocks. Replace the example content.
5. Write the page to `~/Documents/explainers/<YYYY-MM-DD>-<slug>.html`. Get the date with `date +%F`. Create the folder if it does not exist. `<slug>` is lowercase words joined with `-`.
6. Check the page (see **Check**). Fix every problem, then check again.
7. Open the page with `open <path>`.
8. Reply in the terminal with the one-sentence answer and the file path. Nothing more.

## Page shape

Use this order on every page:

1. `<h1>` title.
2. `<p class="answer">` with the one-sentence answer.
3. The main figure, with the caption `<b>Fig. 1.</b>` plus one claim.
4. Up to three more figures, or one table. Each figure has a numbered caption with one claim.
5. `<h2>Sources</h2>` with a list of `path:line` references or links.

A short paragraph between figures is allowed. It connects two figures. It does not repeat what a figure shows.

## Figure types

| Content | Figure | Engine |
| --- | --- | --- |
| Modules and their dependencies | Architecture map | Mermaid `flowchart` |
| Decisions and branches | Flow chart | Mermaid `flowchart` |
| Calls between parts over time | Sequence diagram | Mermaid `sequenceDiagram` |
| Layers, boundaries, nesting | Containment diagram | Mermaid `flowchart` with `subgraph`, or SVG sketch |
| A small mechanism Mermaid cannot show | Sketch | Hand-written inline SVG |
| Options against criteria | Comparison table | HTML `<table>` |
| A change to a structure | Before/after toggle | `data-panes="tabs"` |
| A process over time, in stages | Step-through | `data-panes="steps"` |

Template details:

- Mark nodes in a Mermaid flowchart with `class <id> focus` (blue accent), `add` (green), `remove` (red, dashed), or `warn` (amber). The template adds these `classDef` lines.
- An SVG sketch uses only the CSS variables for colors (`var(--line)`, `var(--accent)`, ...). Set its `width` attribute to the `viewBox` width, so the text keeps its size.
- `data-panes` groups: each child element is one pane. For `tabs`, give each child a `data-label`.
- Use `<span class="tag add">`, `remove`, or `warn` for status in tables.

## Rules

- A figure has at most 12 nodes. Split a larger figure into an overview and a detail figure.
- Each arrow carries a verb label ("calls", "reads", "emits").
- Use the blue accent for one thing per figure: the thing that the caption is about.
- Use green, red, and amber only for a change or a status. Always add a text label. Never show information by color alone.
- Do not add gradients, shadows, glow, emoji, decorative motion, cards inside cards, or centered body text.
- Do not add JavaScript beyond the template script.
- Write all prose in ASD-STE100 Simplified Technical English.
- Every claim about code cites `path:line` in the sources list.

## Check

Take a screenshot with headless Chrome. The `#all` suffix shows every pane of a toggle or a step-through:

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --disable-gpu --hide-scrollbars \
  --window-size=1280,2400 --virtual-time-budget=10000 \
  --screenshot=/tmp/paint-me-<slug>.png "file://<path>#all" 2>/dev/null
```

Read the screenshot. If the page is longer than the screenshot, increase the height. Look for:

- A Mermaid syntax error (a red error box or raw diagram text).
- Text that overlaps, is clipped, or is too small to read.
- A figure that does not show its caption claim.

## Revisions

When the user asks for a change, overwrite the same file, check it again, and tell the user to reload the tab.
