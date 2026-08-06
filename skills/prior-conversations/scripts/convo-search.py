#!/usr/bin/env python3
"""Search and read past Claude Code conversations.

Claude Code stores every session as a JSONL transcript under
~/.claude/projects/<encoded-cwd>/<session-id>.jsonl. Each worktree gets its own
directory, so conversations about the same repo are scattered across many of
them. This script groups those directories by repo and searches inside them.

Commands:
  repos                     list known repos and their session counts
  sessions                  list sessions (newest first) with title/branch/date
  search TERM [TERM ...]    find messages matching all TERMs (case-insensitive regex)
  show SESSION_ID           print a readable transcript (optionally around matches)

Scope (search/sessions): --scope repo (default) | all | current | dir:<path>
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone

PROJECTS_DIR = os.path.expanduser("~/.claude/projects")

# ---------------------------------------------------------------- repo identity

_repo_key_cache: dict[str, str] = {}


def repo_key(path: str) -> str:
    """Stable identifier for the repo a working directory belongs to.

    Worktrees of one repo must map to the same key. Preference order:
    git origin basename (survives arbitrarily named worktrees), then the
    conductor workspace layout (.../conductor/workspaces/<repo>/<workspace>),
    then the directory basename.
    """
    if path in _repo_key_cache:
        return _repo_key_cache[path]

    key = None
    if os.path.isdir(path):
        try:
            url = subprocess.run(
                ["git", "-C", path, "config", "--get", "remote.origin.url"],
                capture_output=True, text=True, timeout=5,
            ).stdout.strip()
            if url:
                key = re.sub(r"\.git$", "", url.rstrip("/").rsplit("/", 1)[-1])
        except (OSError, subprocess.SubprocessError):
            pass

    if not key:
        m = re.search(r"/conductor/workspaces/([^/]+)/", path + "/")
        key = m.group(1) if m else os.path.basename(path.rstrip("/"))

    _repo_key_cache[path] = key
    return key


def project_dirs() -> list[str]:
    if not os.path.isdir(PROJECTS_DIR):
        return []
    return [
        os.path.join(PROJECTS_DIR, d)
        for d in os.listdir(PROJECTS_DIR)
        if os.path.isdir(os.path.join(PROJECTS_DIR, d))
    ]


def transcripts_in(project_dir: str, subagents: bool = False) -> list[str]:
    """Session transcripts in a project dir, newest first.

    Top-level `<session-id>.jsonl` files are the main conversations. Subagent
    and workflow transcripts live under `<session-id>/subagents/...`; they are
    only included when asked for, since they multiply the corpus.
    """
    found: list[str] = []
    try:
        for name in os.listdir(project_dir):
            if name.endswith(".jsonl"):
                found.append(os.path.join(project_dir, name))
    except OSError:
        return []

    if subagents:
        for root, _dirs, files in os.walk(project_dir):
            if root == project_dir:
                continue
            found.extend(os.path.join(root, n) for n in files if n.endswith(".jsonl"))

    found.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return found


def parent_session_of(path: str) -> str | None:
    """For a subagent transcript, the id of the session that spawned it."""
    relative = os.path.relpath(path, PROJECTS_DIR).split(os.sep)
    # <project-dir>/<session-id>/subagents/.../agent-x.jsonl
    if len(relative) >= 3:
        return relative[1]
    return None


def dir_cwd(project_dir: str) -> str | None:
    """The working directory a project dir belongs to, read from its transcripts.

    The directory name is a lossy encoding of the path (slashes and dashes both
    become dashes), so the `cwd` field recorded inside a transcript is the only
    reliable source.
    """
    for path in transcripts_in(project_dir)[:3]:
        try:
            with open(path, "r", errors="replace") as f:
                for _ in range(200):
                    line = f.readline()
                    if not line:
                        break
                    try:
                        obj = json.loads(line)
                    except ValueError:
                        continue
                    if obj.get("cwd"):
                        return obj["cwd"]
        except OSError:
            continue
    return None


def scoped_transcripts(scope: str, cwd: str, subagents: bool = False) -> list[str]:
    """Transcript files matching the requested scope, newest first."""
    if scope.startswith("dir:"):
        target = os.path.abspath(os.path.expanduser(scope[4:]))
        dirs = [d for d in project_dirs() if dir_cwd(d) == target]
    elif scope == "all":
        dirs = project_dirs()
    elif scope == "current":
        dirs = [d for d in project_dirs() if dir_cwd(d) == cwd]
    elif scope == "repo":
        want = repo_key(cwd)
        dirs = []
        for d in project_dirs():
            c = dir_cwd(d)
            if c and repo_key(c) == want:
                dirs.append(d)
    else:
        raise SystemExit(f"unknown scope: {scope}")

    files = [f for d in dirs for f in transcripts_in(d, subagents)]
    files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    if not files:
        print(f"No transcripts for scope={scope} (cwd {cwd}, repo '{repo_key(cwd)}'). "
              f"Try --scope all, or `repos` to see what history exists.",
              file=sys.stderr)
    return files


# ---------------------------------------------------------------- transcript IO

SYSTEM_NOISE = re.compile(
    r"<system-reminder>.*?</system-reminder>"
    r"|<local-command-stdout>.*?</local-command-stdout>"
    r"|<local-command-caveat>.*?</local-command-caveat>"
    r"|<command-(?:name|message|args|contents)>.*?</command-\w+>"
    r"|<system_instruction>.*?</system_instruction>",
    re.S,
)


def message_text(obj: dict, include_tools: bool = False,
                 include_thinking: bool = False) -> str:
    msg = obj.get("message") or {}
    content = msg.get("content")
    parts: list[str] = []

    if isinstance(content, str):
        parts.append(content)
    elif isinstance(content, list):
        for block in content:
            if not isinstance(block, dict):
                continue
            kind = block.get("type")
            if kind == "text":
                parts.append(block.get("text", ""))
            elif kind == "thinking" and include_thinking:
                parts.append("[thinking] " + block.get("thinking", ""))
            elif kind == "tool_use" and include_tools:
                payload = json.dumps(block.get("input", {}))[:2000]
                parts.append(f"[tool:{block.get('name')}] {payload}")
            elif kind == "tool_result" and include_tools:
                inner = block.get("content")
                text = inner if isinstance(inner, str) else json.dumps(inner)
                parts.append("[tool_result] " + text[:2000])

    text = "\n".join(p for p in parts if p)
    return SYSTEM_NOISE.sub("", text).strip()


def session_meta(path: str) -> dict:
    """Cheap summary of a transcript: title, cwd, branch, span, prompt count."""
    meta = {
        "path": path,
        "session_id": os.path.basename(path)[: -len(".jsonl")],
        "parent_session": parent_session_of(path),
        "title": None,
        "cwd": None,
        "branch": None,
        "first_prompt": None,
        "start": None,
        "end": None,
        "prompts": 0,
    }
    try:
        with open(path, "r", errors="replace") as f:
            for line in f:
                try:
                    obj = json.loads(line)
                except ValueError:
                    continue
                kind = obj.get("type")
                if kind == "ai-title":
                    meta["title"] = obj.get("aiTitle")
                    continue
                ts = obj.get("timestamp")
                if ts:
                    meta["start"] = meta["start"] or ts
                    meta["end"] = ts
                if obj.get("cwd") and not meta["cwd"]:
                    meta["cwd"] = obj["cwd"]
                if obj.get("gitBranch"):
                    meta["branch"] = obj["gitBranch"]
                if kind == "user" and not obj.get("isSidechain"):
                    text = message_text(obj)
                    if text and not text.startswith("[tool_result]"):
                        meta["prompts"] += 1
                        if not meta["first_prompt"]:
                            meta["first_prompt"] = text[:160].replace("\n", " ")
    except OSError:
        pass
    return meta


def iter_messages(path: str, include_tools=False, include_thinking=False,
                  include_sidechains=True):
    """Yield (index, role, timestamp, text, obj) for real conversation turns."""
    try:
        f = open(path, "r", errors="replace")
    except OSError:
        return
    with f:
        for index, line in enumerate(f):
            try:
                obj = json.loads(line)
            except ValueError:
                continue
            if obj.get("type") not in ("user", "assistant"):
                continue
            if obj.get("isSidechain") and not include_sidechains:
                continue
            text = message_text(obj, include_tools, include_thinking)
            if not text:
                continue
            yield index, obj["type"], obj.get("timestamp"), text, obj


# ---------------------------------------------------------------- formatting

def fmt_time(ts: str | None) -> str:
    if not ts:
        return "?"
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone().strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return ts


def short_id(session_id: str) -> str:
    if session_id.startswith("agent-"):
        return session_id
    return session_id.split("-")[0]


def describe(meta: dict) -> str:
    """Header line identifying where a transcript came from."""
    label = f"{short_id(meta['session_id'])} · {location(meta)} · {fmt_time(meta['end'])}"
    if meta.get("parent_session"):
        label += f" · subagent of {short_id(meta['parent_session'])}"
    return f"{label} · {meta['title'] or meta['first_prompt'] or '(untitled)'}"


def location(meta_or_obj: dict) -> str:
    cwd = meta_or_obj.get("cwd") or "?"
    branch = meta_or_obj.get("gitBranch") or meta_or_obj.get("branch")
    where = os.path.basename(cwd.rstrip("/"))
    parent = os.path.basename(os.path.dirname(cwd.rstrip("/")))
    if parent and parent not in ("Projects", "/"):
        where = f"{parent}/{where}"
    return f"{where}@{branch}" if branch else where


def snippet(text: str, patterns: list[re.Pattern], width: int) -> str:
    hit = None
    for pattern in patterns:
        hit = pattern.search(text)
        if hit:
            break
    if not hit:
        return text[:width].replace("\n", " ")
    start = max(0, hit.start() - width // 2)
    end = min(len(text), hit.end() + width // 2)
    out = text[start:end].replace("\n", " ")
    return ("…" if start else "") + out + ("…" if end < len(text) else "")


def older_than(ts: str | None, days: int | None) -> bool:
    if not days or not ts:
        return False
    try:
        when = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return False
    return when < datetime.now(timezone.utc) - timedelta(days=days)


# ---------------------------------------------------------------- commands

def cmd_repos(args) -> None:
    counts: dict[str, dict] = {}
    for d in project_dirs():
        cwd = dir_cwd(d)
        if not cwd:
            continue
        entry = counts.setdefault(repo_key(cwd), {"sessions": 0, "worktrees": set()})
        files = transcripts_in(d)
        entry["sessions"] += len(files)
        entry["worktrees"].add(cwd)
    for key in sorted(counts, key=lambda k: -counts[k]["sessions"]):
        entry = counts[key]
        print(f"{key:<28} {entry['sessions']:>4} sessions  "
              f"{len(entry['worktrees'])} worktree(s)")


def cmd_sessions(args) -> None:
    files = scoped_transcripts(args.scope, args.cwd, args.subagents)
    shown = 0
    for path in files:
        meta = session_meta(path)
        if older_than(meta["end"], args.days):
            continue
        if args.branch and args.branch not in (meta["branch"] or ""):
            continue
        origin = f"  subagent of {short_id(meta['parent_session'])}" if meta["parent_session"] else ""
        print(f"{short_id(meta['session_id'])}  {fmt_time(meta['end'])}  "
              f"{location(meta)}  ({meta['prompts']} prompts){origin}")
        print(f"    {meta['title'] or meta['first_prompt'] or '(no title)'}")
        shown += 1
        if shown >= args.limit:
            print(f"    … stopping at --limit {args.limit} of {len(files)} sessions")
            break
    if not shown:
        print("No sessions matched.")


def cmd_search(args) -> None:
    patterns = [re.compile(t, re.I) for t in args.terms]
    files = scoped_transcripts(args.scope, args.cwd, args.subagents)
    hits = 0
    sessions_with_hits = 0

    for path in files:
        if args.days and older_than(
            datetime.fromtimestamp(os.path.getmtime(path), timezone.utc).isoformat(),
            args.days,
        ):
            continue

        # Cheap prefilter on the raw JSON before parsing anything.
        try:
            with open(path, "r", errors="replace") as f:
                raw = f.read()
        except OSError:
            continue
        if not all(p.search(raw) for p in patterns):
            continue

        meta = session_meta(path)
        printed_header = False
        for index, role, ts, text, obj in iter_messages(
            path, args.include_tools, args.include_thinking, not args.no_sidechains
        ):
            if args.role != "any" and role != args.role:
                continue
            if not all(p.search(text) for p in patterns):
                continue
            if not printed_header:
                print(f"\n=== {describe(meta)}")
                printed_header = True
                sessions_with_hits += 1
            marker = "sidechain " if obj.get("isSidechain") else ""
            print(f"  [{index}] {marker}{role} {fmt_time(ts)}")
            print(f"      {snippet(text, patterns, args.width)}")
            hits += 1
            if hits >= args.limit:
                break
        if hits >= args.limit:
            print(f"\n… stopped at --limit {args.limit}")
            break

    print(f"\n{hits} match(es) in {sessions_with_hits} session(s); "
          f"scope={args.scope} ({len(files)} transcripts scanned).")
    if hits:
        print("Read one with: convo-search.py show <session-id> "
              "--grep <term> --context 2")


def resolve_session(prefix: str) -> str:
    matches = []
    for d in project_dirs():
        for path in transcripts_in(d, subagents=True):
            if os.path.basename(path).startswith(prefix):
                matches.append(path)
    if not matches:
        raise SystemExit(f"No transcript found for session id starting '{prefix}'")
    if len(matches) > 1:
        raise SystemExit("Ambiguous session id; candidates:\n  " +
                         "\n  ".join(matches))
    return matches[0]


def cmd_show(args) -> None:
    path = resolve_session(args.session_id)
    meta = session_meta(path)
    print(f"# {meta['title'] or meta['first_prompt'] or '(untitled)'}")
    print(f"# session {meta['session_id']} · {location(meta)} · "
          f"{fmt_time(meta['start'])} → {fmt_time(meta['end'])}")
    if meta["parent_session"]:
        print(f"# subagent of session {meta['parent_session']}")
    print(f"# file {path}\n")

    turns = list(iter_messages(path, args.include_tools, args.include_thinking,
                               not args.no_sidechains))
    if args.grep:
        patterns = [re.compile(t, re.I) for t in args.grep]
        keep: set[int] = set()
        for position, turn in enumerate(turns):
            if all(p.search(turn[3]) for p in patterns):
                lo = max(0, position - args.context)
                hi = min(len(turns), position + args.context + 1)
                keep.update(range(lo, hi))
        selected = [(i, turns[i]) for i in sorted(keep)]
        if not selected:
            print("(no turns matched --grep in this session)")
            return
    else:
        selected = list(enumerate(turns))
        if args.tail:
            selected = selected[-args.tail:]

    previous = None
    for position, (index, role, ts, text, obj) in selected:
        if previous is not None and position != previous + 1:
            print("\n  … skipped turns …")
        previous = position
        marker = " (sidechain)" if obj.get("isSidechain") else ""
        body = text if len(text) <= args.max_chars else text[: args.max_chars] + "\n      …[truncated]"
        print(f"\n[{index}] {role}{marker} · {fmt_time(ts)}")
        print("      " + body.replace("\n", "\n      "))


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="convo-search.py", description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--cwd", default=os.getcwd(),
                        help="working directory used to resolve --scope repo/current")
    sub = parser.add_subparsers(dest="command", required=True)

    def add_scope(p):
        p.add_argument("--scope", default="repo",
                       help="repo (all worktrees of this repo, default) | all | "
                            "current (this worktree only) | dir:<path>")
        p.add_argument("--days", type=int, default=None,
                       help="only sessions touched in the last N days")
        p.add_argument("--subagents", action="store_true",
                       help="also include subagent and workflow transcripts")

    def add_content(p):
        p.add_argument("--include-tools", action="store_true",
                       help="also search/print tool calls and results")
        p.add_argument("--include-thinking", action="store_true",
                       help="also search/print assistant thinking blocks")
        p.add_argument("--no-sidechains", action="store_true",
                       help="skip subagent turns")

    p_repos = sub.add_parser("repos", help="list known repos")
    p_repos.set_defaults(func=cmd_repos)

    p_sessions = sub.add_parser("sessions", help="list sessions newest first")
    add_scope(p_sessions)
    p_sessions.add_argument("--limit", type=int, default=25)
    p_sessions.add_argument("--branch", default=None, help="filter by git branch substring")
    p_sessions.set_defaults(func=cmd_sessions)

    p_search = sub.add_parser("search", help="find messages matching all terms")
    p_search.add_argument("terms", nargs="+", help="case-insensitive regexes; all must match")
    add_scope(p_search)
    add_content(p_search)
    p_search.add_argument("--role", default="any", choices=["any", "user", "assistant"])
    p_search.add_argument("--limit", type=int, default=40, help="max matches")
    p_search.add_argument("--width", type=int, default=320, help="snippet width")
    p_search.set_defaults(func=cmd_search)

    p_show = sub.add_parser("show", help="print a transcript")
    p_show.add_argument("session_id", help="full id or unique prefix")
    add_content(p_show)
    p_show.add_argument("--grep", nargs="+", default=None,
                        help="only turns matching all terms, plus context")
    p_show.add_argument("--context", type=int, default=2,
                        help="turns of context around each --grep hit")
    p_show.add_argument("--tail", type=int, default=None,
                        help="without --grep, print only the last N turns")
    p_show.add_argument("--max-chars", type=int, default=2000,
                        help="truncate each turn to N characters")
    p_show.set_defaults(func=cmd_show)

    args = parser.parse_args()
    args.cwd = os.path.abspath(os.path.expanduser(args.cwd))
    try:
        args.func(args)
    except BrokenPipeError:
        pass


if __name__ == "__main__":
    main()
