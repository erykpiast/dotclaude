#!/usr/bin/env python3
"""Claude Code status line: sparkline charts for context usage, input tokens, output tokens."""

import json
import math
import os
import sys

BLOCKS = " ▁▂▃▄▅▆▇█"
CHART_ROWS = 4
MAX_HISTORY = 50
GREEN = "\033[32m"
YELLOW = "\033[33m"
ORANGE = "\033[38;5;208m"
RED = "\033[31m"
BLUE = "\033[34m"
RESET = "\033[0m"
DIM = "\033[2m"
WHITE = "\033[97m"


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
    # Normalize value to range [0, num_rows] in block units
    normalized = min(value / max_val, 1.0) * num_rows
    col = []
    for row in range(num_rows):
        fill = normalized - row
        if fill >= 1.0:
            idx = 8  # full block
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
    """Compute the display width needed for y-axis labels (plus │ separator)."""
    return max(len(l) for l in y_labels) + 1  # +1 for │


def render_chart(data, max_val, width, y_labels, lw, color_fn=None, fixed_color=None):
    """Render a chart as a list of strings (top to bottom). lw = label width."""
    # Build columns for visible data points
    visible = data[-width:] if len(data) > width else data
    columns = []
    for v in visible:
        columns.append(render_bar_column(v, max_val, CHART_ROWS, color_fn, fixed_color))

    # Pad columns to width
    while len(columns) < width:
        columns.insert(0, [" "] * CHART_ROWS)

    # Build rows (top to bottom: row index CHART_ROWS-1 down to 0)
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

    # History file
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
                    if len(parts) == 3:
                        history.append(tuple(float(x) for x in parts))
                    elif len(parts) == 1:
                        history.append((float(parts[0]), 0, 0))
                except ValueError:
                    continue

    history.append((pct, input_tokens, output_tokens))
    history = history[-MAX_HISTORY:]

    with open(hist_path, "w") as f:
        for h in history:
            f.write(f"{h[0]},{h[1]},{h[2]}\n")

    pct_data = [h[0] for h in history]
    in_data = [h[1] for h in history]
    out_data = [h[2] for h in history]

    # Y-axis labels
    pct_labels = ["100", "75", "50", "25"]

    def nice_max(raw_max):
        """Round up to a nice number divisible by 4, with headroom above raw_max."""
        if raw_max <= 0:
            return 4
        target = raw_max * 1.33  # ~33% headroom
        # Find smallest 4*step >= target where step is 1,2,5 * 10^n
        mag = 10 ** math.floor(math.log10(target / 4))
        for ns in (1, 2, 5, 10):
            step = ns * mag
            if 4 * step >= target:
                return int(4 * step)
        return int(4 * 10 * mag)

    raw_max_in = max(in_data) if in_data else 1
    raw_max_out = max(out_data) if out_data else 1
    max_in = nice_max(raw_max_in)
    max_out = nice_max(raw_max_out)

    def make_token_labels(mx):
        labels = []
        for i in range(CHART_ROWS):
            val = mx * (CHART_ROWS - i) / CHART_ROWS
            labels.append(format_tokens(int(val)))
        return labels

    in_labels = make_token_labels(max_in)
    out_labels = make_token_labels(max_out)

    # Compute label widths per chart (includes +1 for separator)
    pct_lw = label_width(pct_labels)
    in_lw = label_width(in_labels)
    out_lw = label_width(out_labels)

    # Turn counter gap
    turns_count = str(len(history))
    turns_label = f"↻{turns_count}"
    turns_margin = 4 - len(turns_count)  # 3 spaces for 1 digit, 2 for 2, 1 for 3
    left_gap = len(turns_label) + turns_margin

    # Terminal width and chart sizing
    try:
        term_cols = os.get_terminal_size().columns
    except OSError:
        term_cols = 80
    total_label_space = pct_lw + in_lw + out_lw
    gaps = 2 * 2  # 2-space gap between charts
    chart_width = max(5, (term_cols - left_gap - total_label_space - gaps) // 3)

    # Render charts
    ctx_chart = render_chart(pct_data, 100, chart_width, pct_labels, pct_lw, color_fn=color_for_pct)
    in_chart = render_chart(in_data, max_in, chart_width, in_labels, in_lw, fixed_color=YELLOW)
    out_chart = render_chart(out_data, max_out, chart_width, out_labels, out_lw, fixed_color=BLUE)

    # Footer line: name left-aligned, value right-aligned within each chart
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
        line = f"{WHITE}{gap_pad}{RESET}{ctx_chart[i]}  {in_chart[i]}  {out_chart[i]}"
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
