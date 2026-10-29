# render-brief.jq — deterministic Morning Brief renderer.
# Usage: jq -r -f render-brief.jq /tmp/morning-brief.json > /tmp/morning-brief.html
# Input must conform to brief.schema.json. Output is a self-contained HTML document.
# All dynamic text is escaped with @html. The template (markup + CSS) is static, so the
# same input always produces byte-identical output.

def e: (. // "") | tostring | @html;

def link($href; $text):
  "<a href=\"" + ($href | e) + "\" target=\"_blank\" rel=\"noopener\">" + $text + "</a>";

def empty_state($msg):
  "<p class=\"empty\">" + $msg + "</p>";

def count_badge($n):
  "<span class=\"count\">" + ($n | tostring) + "</span>";

# ---- Section 1: Slack -----------------------------------------------------------------
def slack_item:
  "<li class=\"item slack\">"
  + "<div class=\"item-head\">"
  +   link(.permalink; ("<strong>" + (.from | e) + "</strong> in " + (.channel | e)))
  +   (if (.timestamp // "") != "" then "<span class=\"meta\">" + (.timestamp | e) + "</span>" else "" end)
  + "</div>"
  + "<p class=\"summary\">" + (.summary | e) + "</p>"
  + "</li>";

def slack_section:
  "<section><h2>Slack threads needing a response " + count_badge(.slack | length) + "</h2>"
  + (if (.slack | length) == 0
     then empty_state("You're all caught up — no threads waiting on you.")
     else "<ul class=\"items\">" + (.slack | map(slack_item) | join("")) + "</ul>"
     end)
  + "</section>";

# ---- Section 4: Slack top picks (rendered right after Section 1) ----------------------
def pick_item:
  "<li class=\"item slack pick\">"
  + "<div class=\"item-head\">"
  +   link(.permalink; ("<strong>" + (.from | e) + "</strong> in " + (.channel | e)))
  +   (if (.timestamp // "") != "" then "<span class=\"meta\">" + (.timestamp | e) + "</span>" else "" end)
  + "</div>"
  + "<p class=\"summary\">" + (.summary | e) + "</p>"
  + "<p class=\"why\">" + (.why | e) + "</p>"
  + "</li>";

def picks_section:
  (.slackPicks // []) as $picks
  | "<section><h2>Slack picks you may have missed " + count_badge($picks | length) + "</h2>"
  + (if ($picks | length) == 0
     then empty_state("Nothing stood out.")
     else "<ul class=\"items\">" + ($picks | map(pick_item) | join("")) + "</ul>"
     end)
  + "</section>";

# ---- Section 2: Linear ----------------------------------------------------------------
def linear_item:
  "<li class=\"item linear" + (if .flagged then " flagged" else "" end) + "\">"
  + "<div class=\"item-head\">"
  +   link(.url; ("<span class=\"id\">" + (.identifier | e) + "</span> " + (.title | e)))
  +   (if .flagged then "<span class=\"flag\">flagged</span>" else "" end)
  + "</div>"
  + "<div class=\"meta\">"
  +   "<span class=\"pill\">" + (.status | e) + "</span>"
  +   (if (.priority // "") != "" then "<span class=\"pill\">" + (.priority | e) + "</span>" else "" end)
  +   (if (.dueDate // null) != null then "<span class=\"pill due\">due " + (.dueDate | e) + "</span>" else "" end)
  + "</div>"
  + "</li>";

def linear_section:
  "<section><h2>Linear issues " + count_badge(.linear | length) + "</h2>"
  + (if (.linear | length) == 0
     then empty_state("Nothing assigned in Todo or In Progress.")
     # Flagged first, then the rest; preserve input order within each group.
     else ((.linear | map(select(.flagged))) + (.linear | map(select(.flagged | not)))) as $sorted
          | "<ul class=\"items\">" + ($sorted | map(linear_item) | join("")) + "</ul>"
     end)
  + "</section>";

# ---- Section 3: GitHub ----------------------------------------------------------------
def pr_head:
  "<div class=\"item-head\">"
  + link(.url; ("<span class=\"id\">" + (.repository | e) + " #" + (.number | tostring | e) + "</span> " + (.title | e)))
  + "</div>";

def ready_item:
  "<li class=\"item pr\">" + pr_head
  + (if (.mergeable // "") == "CONFLICTING"
     then "<div class=\"meta\"><span class=\"pill warn\">merge conflict</span></div>" else "" end)
  + "</li>";

def awaiting_item:
  "<li class=\"item pr\">" + pr_head
  + "<div class=\"meta\">"
  +   "<span class=\"pill warn\">" + (.unresolvedThreads | tostring) + " unresolved thread" + (if .unresolvedThreads == 1 then "" else "s" end) + "</span>"
  +   "<span class=\"pill\">" + (.reviewDecision | e) + "</span>"
  + "</div></li>";

def unresponded_item:
  "<li>"
  + link(.url; ("<strong>@" + (.author | e) + "</strong>"))
  + " <span class=\"meta\">" + (.createdAt | e) + "</span>"
  + "<p class=\"summary\">" + (.excerpt | e) + "</p>"
  + "</li>";

def attention_item:
  (.unresponded // []) as $items
  | "<li class=\"item pr\">" + pr_head
  + "<div class=\"meta\">"
  +   "<span class=\"pill\">@" + (.author | e) + "</span>"
  +   (if ($items | length) > 0 then "<span class=\"pill warn\">" + ($items | length | tostring) + " unresponded</span>" else "" end)
  +   ((.reasons // []) | map("<span class=\"pill reason\">" + (. | e) + "</span>") | join(""))
  + "</div>"
  + (if ($items | length) > 0
     then "<ul class=\"unresponded\">" + ($items | map(unresponded_item) | join("")) + "</ul>"
     else "<p class=\"why\">No approval yet. The author waits for your review.</p>"
     end)
  + "</li>";

# title/arr/renderer are FILTER params (no $), so `renderer` is applied per-element by map.
# Passing them as $value params would evaluate the renderer once against the root document.
def pr_subgroup(title; arr; renderer):
  "<h3>" + title + " " + count_badge(arr | length) + "</h3>"
  + (if (arr | length) == 0
     then empty_state("None.")
     else "<ul class=\"items\">" + (arr | map(renderer) | join("")) + "</ul>"
     end);

def github_section:
  (.github.readyToMerge // []) as $ready
  | (.github.awaitingApproval // []) as $awaiting
  | (.github.needingAttention // []) as $attention
  | "<section><h2>GitHub PRs " + count_badge(($ready | length) + ($awaiting | length) + ($attention | length)) + "</h2>"
  + pr_subgroup("My PRs ready to merge"; $ready; ready_item)
  + pr_subgroup("My PRs awaiting approval (unresolved threads)"; $awaiting; awaiting_item)
  + pr_subgroup("Needing my attention"; $attention; attention_item)
  + "</section>";

# ---- Document -------------------------------------------------------------------------
"<!doctype html>"
+ "<html lang=\"en\"><head><meta charset=\"utf-8\">"
+ "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
+ "<title>Morning Brief — " + (.date | e) + "</title>"
+ "<style>"
+ ":root{--bg:#fbfbfa;--card:#fff;--fg:#1a1a1a;--muted:#6b6b6b;--border:#e6e6e3;--accent:#3b5bdb;--warn:#c92a2a;--flag:#e8590c;--pill:#f1f1ef;}"
+ "@media (prefers-color-scheme: dark){:root{--bg:#16161a;--card:#1e1e24;--fg:#ececec;--muted:#9a9aa2;--border:#2c2c34;--accent:#91a7ff;--warn:#ff8787;--flag:#ffa94d;--pill:#2a2a32;}}"
+ "*{box-sizing:border-box;}"
+ "body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.55 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;}"
+ "main{max-width:46rem;margin:0 auto;padding:2.5rem 1.25rem 4rem;}"
+ "header{margin-bottom:2rem;}"
+ "header h1{font-size:1.9rem;margin:0 0 .25rem;letter-spacing:-.02em;}"
+ "header .date{color:var(--muted);font-size:1rem;}"
+ "section{margin:2rem 0;}"
+ "h2{font-size:1.15rem;margin:0 0 .9rem;display:flex;align-items:center;gap:.5rem;border-bottom:1px solid var(--border);padding-bottom:.5rem;}"
+ "h3{font-size:.95rem;color:var(--muted);margin:1.25rem 0 .6rem;font-weight:600;display:flex;align-items:center;gap:.45rem;}"
+ ".count{font-size:.78rem;font-weight:600;color:var(--muted);background:var(--pill);border-radius:999px;padding:.05rem .5rem;}"
+ "ul.items{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:.6rem;}"
+ ".item{background:var(--card);border:1px solid var(--border);border-radius:.6rem;padding:.85rem 1rem;}"
+ ".item.flagged{border-color:var(--flag);}"
+ ".item-head{display:flex;justify-content:space-between;align-items:baseline;gap:.75rem;}"
+ ".item a{color:var(--accent);text-decoration:none;}"
+ ".item a:hover{text-decoration:underline;}"
+ ".item .id{font-variant-numeric:tabular-nums;color:var(--muted);font-weight:600;}"
+ ".summary{margin:.4rem 0 0;color:var(--fg);}"
+ ".meta{display:flex;flex-wrap:wrap;gap:.4rem;align-items:center;margin-top:.5rem;color:var(--muted);font-size:.82rem;}"
+ ".pill{background:var(--pill);border-radius:.4rem;padding:.1rem .45rem;font-size:.78rem;color:var(--fg);}"
+ ".pill.warn{color:var(--warn);}"
+ ".pill.due{color:var(--flag);}"
+ ".pill.reason{text-transform:lowercase;}"
+ ".flag{color:var(--flag);font-size:.75rem;font-weight:600;text-transform:uppercase;letter-spacing:.04em;}"
+ ".why{margin:.35rem 0 0;color:var(--muted);font-size:.88rem;}"
+ ".unresponded{list-style:none;margin:.6rem 0 0;padding:0 0 0 .75rem;border-left:2px solid var(--warn);display:flex;flex-direction:column;gap:.4rem;}"
+ ".unresponded li{font-size:.9rem;}"
+ ".empty{color:var(--muted);font-style:italic;margin:.25rem 0;}"
+ "footer{margin-top:3rem;color:var(--muted);font-size:.78rem;text-align:center;}"
+ "</style></head><body><main>"
+ "<header><h1>Morning Brief</h1><div class=\"date\">" + (.date | e) + "</div></header>"
+ slack_section
+ picks_section
+ linear_section
+ github_section
+ (if (.generatedAt // "") != "" then "<footer>Generated " + (.generatedAt | e) + "</footer>" else "" end)
+ "</main></body></html>"
