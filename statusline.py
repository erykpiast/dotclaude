#!/usr/bin/env python3
"""Claude Code status line: sparkline charts for context usage, input tokens, output tokens."""

import json
import math
import os
import sys
import time

BLOCKS = " ▁▂▃▄▅▆▇█"
CHART_ROWS = 4
SLOT_SECS = 180  # 3 minutes per column
GREEN = "\033[32m"
YELLOW = "\033[33m"
ORANGE = "\033[38;5;208m"
RED = "\033[31m"
BLUE = "\033[34m"
RESET = "\033[0m"
DIM = "\033[2m"
WHITE = "\033[97m"

EMPTY_COL = [f"{DIM}░{RESET}"] * CHART_ROWS


def format_tokens(n):
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.0f}k"
    return str(n)


def color_for_pct(pct):
    if pct < 30:
        return GREEN
    if pct < 60:
        return ORANGE
    return RED


def render_bar_column(value, max_val, num_rows, color_fn=None, fixed_color=None):
    """Return a list of characters (bottom to top) for one bar column."""
    if max_val <= 0:
        return [" "] * num_rows
    normalized = min(value / max_val, 1.0) * num_rows
    col = []
    for row in range(num_rows):
        fill = normalized - row
        if fill >= 1.0:
            idx = 8
        elif fill > 0:
            idx = max(1, int(fill * 8))
        else:
            idx = 0
        char = BLOCKS[idx]
        if char != " ":
            if fixed_color:
                char = f"{fixed_color}{char}{RESET}"
            elif color_fn:
                char = f"{color_fn(value)}{char}{RESET}"
        col.append(char)
    return col  # index 0 = bottom row


def label_width(y_labels):
    """Compute the display width needed for y-axis labels (plus | separator)."""
    return max(len(l) for l in y_labels) + 1


def render_chart(data, max_val, width, y_labels, lw, color_fn=None, fixed_color=None):
    """Render a chart. None entries in data become dim placeholder columns."""
    visible = data[-width:] if len(data) > width else data
    columns = []
    for v in visible:
        if v is None:
            columns.append(EMPTY_COL)
        else:
            col = render_bar_column(v, max_val, CHART_ROWS, color_fn, fixed_color)
            # Fill empty cells above the bar with dim blocks
            col = [f"{DIM}░{RESET}" if c == " " else c for c in col]
            columns.append(col)

    # Pad to width with placeholders (right side for time-based charts)
    while len(columns) < width:
        columns.append(EMPTY_COL)

    lines = []
    for row_idx in range(CHART_ROWS - 1, -1, -1):
        label = y_labels[CHART_ROWS - 1 - row_idx] if (CHART_ROWS - 1 - row_idx) < len(y_labels) else ""
        bar = "".join(col[row_idx] for col in columns)
        lines.append(f"{DIM}{label:>{lw - 1}s}{RESET}{WHITE}|{RESET}{bar}")
    return lines


def main():
    data = json.loads(sys.stdin.read())
    sid = data.get("session_id", "unknown")
    cw = data.get("context_window", {})
    pct = cw.get("used_percentage") or 0
    input_tokens = cw.get("total_input_tokens") or 0
    output_tokens = cw.get("total_output_tokens") or 0

    # Count agentic turns: assistant messages with stop_reason=end_turn
    transcript_path = data.get("transcript_path", "")
    turns = 0
    if transcript_path and os.path.exists(transcript_path):
        with open(transcript_path) as f:
            for line in f:
                if '"end_turn"' not in line:
                    continue
                try:
                    obj = json.loads(line)
                    if obj.get("type") != "assistant":
                        continue
                    msg = obj.get("message", {})
                    if msg.get("stop_reason") != "end_turn":
                        continue
                    content = msg.get("content", [])
                    ctypes = {c.get("type") for c in content} if isinstance(content, list) else set()
                    if "text" in ctypes:
                        turns += 1
                except ValueError:
                    pass

    now = time.time()

    # History file — format: timestamp,pct,input_tokens,output_tokens
    hist_path = f"/tmp/claude-sl-{sid}.dat"
    history = []
    if os.path.exists(hist_path):
        with open(hist_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    parts = line.split(",")
                    if len(parts) == 4:
                        history.append(tuple(float(x) for x in parts))
                    # Discard old 3-field entries (no timestamp)
                except ValueError:
                    continue

    history.append((now, pct, input_tokens, output_tokens))

    # Keep last 2 hours of history (covers any reasonable chart width), cap at 500
    history = [h for h in history if h[0] >= now - 7200]
    history = history[-500:]

    with open(hist_path, "w") as f:
        for h in history:
            f.write(f"{h[0]},{h[1]},{h[2]},{h[3]}\n")

    # Compute max values from all retained history (for labels, before chart_width is known)
    raw_max_in = max((h[2] for h in history), default=1)
    raw_max_out = max((h[3] for h in history), default=1)

    def nice_max(raw_max):
        if raw_max <= 0:
            return 4
        target = raw_max * 1.33
        mag = 10 ** math.floor(math.log10(target / 4))
        for ns in (1, 2, 5, 10):
            step = ns * mag
            if 4 * step >= target:
                return int(4 * step)
        return int(4 * 10 * mag)

    max_in = nice_max(raw_max_in)
    max_out = nice_max(raw_max_out)

    def make_token_labels(mx):
        labels = []
        for i in range(CHART_ROWS):
            val = mx * (CHART_ROWS - i) / CHART_ROWS
            labels.append(format_tokens(int(val)))
        return labels

    pct_labels = ["100", "75", "50", "25"]
    in_labels = make_token_labels(max_in)
    out_labels = make_token_labels(max_out)

    pct_lw = label_width(pct_labels)
    in_lw = label_width(in_labels)
    out_lw = label_width(out_labels)

    # Turn counter
    turns_count = str(turns)
    turns_label = f"↻{turns_count}"
    turns_margin = 4 - len(turns_count)
    left_gap = len(turns_label) + turns_margin

    # Turns bar (multi-column, y-scale 0–50, width matches ↻N label)
    TURNS_MAX = 50
    bar_width = len(turns_label)

    def turns_color(t):
        if t < 20:
            return GREEN
        if t <= 50:
            return ORANGE
        return RED

    clamped = min(turns, TURNS_MAX)
    normalized = (clamped / TURNS_MAX) * CHART_ROWS if TURNS_MAX > 0 else 0
    tc = turns_color(turns)
    turns_bar_rows = []
    for row in range(CHART_ROWS):
        fill = normalized - row
        if fill >= 1.0:
            idx = 8
        elif fill > 0:
            idx = max(1, int(fill * 8))
        else:
            idx = 0
        char = BLOCKS[idx]
        if char != " ":
            turns_bar_rows.append(f"{tc}{char * bar_width}{RESET}")
        else:
            turns_bar_rows.append(f"{DIM}{'░' * bar_width}{RESET}")

    # Terminal width and chart sizing
    try:
        term_cols = os.get_terminal_size().columns
    except OSError:
        term_cols = 80
    total_label_space = pct_lw + in_lw + out_lw
    gaps = 2 * 2
    chart_width = max(5, (term_cols - left_gap - total_label_space - gaps) // 3)

    # Bucket data into time slots (each column = SLOT_SECS)
    window_secs = chart_width * SLOT_SECS
    first_ts = history[0][0]
    if now - first_ts < window_secs:
        window_start = first_ts
    else:
        window_start = now - window_secs
    windowed = [h for h in history if h[0] >= window_start]

    slots = [None] * chart_width
    for ts, p, inp, out in windowed:
        slot_idx = min(int((ts - window_start) / SLOT_SECS), chart_width - 1)
        slots[slot_idx] = (p, inp, out)

    # Interpolate gaps between data points
    filled = [(i, s) for i, s in enumerate(slots) if s is not None]
    for k in range(len(filled) - 1):
        i_a, val_a = filled[k]
        i_b, val_b = filled[k + 1]
        for j in range(i_a + 1, i_b):
            t = (j - i_a) / (i_b - i_a)
            slots[j] = tuple(a + (b - a) * t for a, b in zip(val_a, val_b))

    pct_data = [s[0] if s is not None else None for s in slots]
    in_data = [s[1] if s is not None else None for s in slots]
    out_data = [s[2] if s is not None else None for s in slots]

    # Render charts
    ctx_chart = render_chart(pct_data, 100, chart_width, pct_labels, pct_lw, color_fn=color_for_pct)
    in_chart = render_chart(in_data, max_in, chart_width, in_labels, in_lw, fixed_color=YELLOW)
    out_chart = render_chart(out_data, max_out, chart_width, out_labels, out_lw, fixed_color=BLUE)

    # Footer
    ctx_total = pct_lw + chart_width
    in_total = in_lw + chart_width
    out_total = out_lw + chart_width

    def make_footer(name, value, total_w, lw):
        indent = " " * lw
        gap = total_w - lw - len(name) - len(value)
        if gap < 1:
            gap = 1
        return indent + name + " " * gap + value

    gap_pad = ' ' * left_gap

    ctx_footer = make_footer("Context", f"{pct:.0f}%", ctx_total, pct_lw)
    in_footer = make_footer("In tokens", format_tokens(int(input_tokens)), in_total, in_lw)
    out_footer = make_footer("Out tokens", format_tokens(int(output_tokens)), out_total, out_lw)
    footer = f"{WHITE}{gap_pad}{ctx_footer}  {in_footer}  {out_footer}{RESET}"

    for i in range(CHART_ROWS):
        bar_str = turns_bar_rows[CHART_ROWS - 1 - i]
        pad = ' ' * turns_margin
        line = f"{bar_str}{pad}{ctx_chart[i]}  {in_chart[i]}  {out_chart[i]}"
        print(line)
    xaxis_prefix = f"{turns_label}{' ' * turns_margin}"
    xaxis = f"{WHITE}{xaxis_prefix}{' ' * (pct_lw - 1)}·{'─' * chart_width}  {' ' * (in_lw - 1)}·{'─' * chart_width}  {' ' * (out_lw - 1)}·{'─' * chart_width}{RESET}"
    print(xaxis)
    print(footer)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"status error: {e}", file=sys.stderr)
        print("--")
