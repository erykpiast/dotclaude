---
description: Draw a diagram on the Blueberry canvas from a description or current context
allowed-tools: Read, Write, Bash, mcp__blueberry__blueberry_get_context
argument-hint: "<description of what to draw>"
---

Draw a diagram on the Blueberry canvas based on: $ARGUMENTS

## Process

1. First call `mcp__blueberry__blueberry_get_context` to confirm the canvas is available.
2. Run `blueberry canvas:draw-guide` to get the current style guide.
3. Design the diagram layout, then draw it using `blueberry canvas:draw`.
4. After drawing, run `blueberry capture:canvas` to verify the result.

## Drawing Rules

### Text inside shapes (REQUIRED)

NEVER overlay a separate text element on top of a shape. Always bind text inside its container:

1. Give the container an explicit `id` (e.g., `"id": "box-auth"`)
2. Add `"boundElements": [{"type": "text", "id": "txt-auth"}]` to the container
3. On the text element, set `"containerId": "box-auth"` and use the same `x`, `width` as the container
4. Use `"textAlign": "center"` for horizontal centering

Example:
```json
{"type":"rectangle","id":"box-auth","x":100,"y":100,"width":200,"height":50,"strokeColor":"#ffffff","roughness":2,"boundElements":[{"type":"text","id":"txt-auth"}]},
{"type":"text","id":"txt-auth","x":100,"y":110,"width":200,"text":"Auth Service","fontSize":20,"fontFamily":1,"strokeColor":"#ffffff","textAlign":"center","containerId":"box-auth"}
```

### Labels on arrows (REQUIRED)

Arrow labels must be bound to the arrow, not placed as free-floating text:

1. Give the arrow an explicit `id` (e.g., `"id": "arr-request"`)
2. Add `"boundElements": [{"type": "text", "id": "txt-request"}]` to the arrow
3. On the text element, set `"containerId": "arr-request"`

Example:
```json
{"type":"arrow","id":"arr-request","x":300,"y":125,"width":200,"height":0,"points":[[0,0],[200,0]],"endArrowhead":"arrow","strokeColor":"#ffffff","roughness":2,"boundElements":[{"type":"text","id":"txt-request"}]},
{"type":"text","id":"txt-request","x":370,"y":110,"text":"HTTP request","fontSize":14,"fontFamily":1,"strokeColor":"#999999","containerId":"arr-request"}
```

### Arrow-to-shape connections

The Blueberry canvas API does NOT support `startBinding`/`endBinding` on arrows — these are silently ignored. Arrows will be visually positioned between shapes but won't auto-follow when shapes are dragged. This is a known limitation.

To make arrows visually connect to shapes, calculate start/end points based on shape positions:
- Arrow starting from bottom of a box: `x` = box center X, `y` = box Y + box height
- Arrow ending at top of a box: endpoint = `[0, gap_to_next_box]`

### ID naming convention

Use descriptive prefixed IDs:
- Shapes: `box-<name>`, e.g., `box-api`, `box-db`
- Text: `txt-<name>`, matching the parent, e.g., `txt-api`, `txt-db`
- Arrows: `arr-<from>-<to>`, e.g., `arr-api-db`
- Frames: `frame-<name>`, e.g., `frame-backend`

### General

- Always use unique temp file paths: `/tmp/canvas-<purpose>-<random>.json`
- Use `roughness: 2` and `fontFamily: 1` (Virgil) for the hand-drawn style
- White strokes/text (`#ffffff`) on the dark canvas background
- Use `#999999` for secondary/muted elements
- Use color sparingly — only for emphasis (e.g., highlighted path, error state)
- NEVER remove existing canvas elements unless explicitly asked
