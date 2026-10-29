#!/usr/bin/env python3
"""
slack-picks-candidates.py
Collects every Slack thread with activity in a time window, in the channels I am a member
of, that I have not seen: I did not post in it, react in it, or get @-mentioned in it.
Prints one JSON document to stdout. The morning brief prompt ranks these threads; this
script does the exhaustive part, so no thread is skipped because a model stopped paging.

Token: $SLACK_USER_TOKEN, else the macOS Keychain item "morning-brief-slack".
User token scopes: channels:history, groups:history, channels:read, groups:read,
search:read, users:read.

Usage: slack-picks-candidates.py --oldest <unix ts> --latest <unix ts> --lookback YYYY-MM-DD
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta

API = "https://slack.com/api/"
KEYCHAIN_SERVICE = "morning-brief-slack"
MAX_TEXT = 800
MAX_MESSAGES_PER_THREAD = 40
MY_MESSAGES_PAGES = 3
# Root messages with these subtypes are not conversations.
SYSTEM_SUBTYPES = {
    "bot_message", "channel_join", "channel_leave", "channel_topic", "channel_purpose",
    "channel_name", "channel_archive", "channel_unarchive", "pinned_item", "unpinned_item",
}


def read_token():
    token = os.environ.get("SLACK_USER_TOKEN")
    if token:
        return token
    result = subprocess.run(
        ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-w"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        sys.exit(f"No Slack token: set SLACK_USER_TOKEN or add Keychain item '{KEYCHAIN_SERVICE}'.")
    return result.stdout.strip()


TOKEN = None


def call(method, **params):
    data = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None}).encode()
    while True:
        request = urllib.request.Request(API + method, data=data, headers={"Authorization": f"Bearer {TOKEN}"})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = json.load(response)
        except urllib.error.HTTPError as error:
            if error.code == 429:
                time.sleep(int(error.headers.get("Retry-After", "5")))
                continue
            raise
        if not body.get("ok"):
            if body.get("error") == "ratelimited":
                time.sleep(5)
                continue
            raise RuntimeError(f"{method}: {body.get('error')}")
        return body


def paginate(method, key, **params):
    cursor = None
    while True:
        body = call(method, cursor=cursor, **params)
        yield from body.get(key, [])
        cursor = body.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            return


def search(query, max_pages=None):
    """search.messages pages by page number, not cursor. Newest first."""
    page = 1
    while True:
        body = call("search.messages", query=query, count=100, page=page, sort="timestamp", sort_dir="desc")
        messages = body.get("messages", {})
        yield from messages.get("matches", [])
        pages = messages.get("paging", {}).get("pages", 0)
        if page >= pages or (max_pages and page >= max_pages):
            return
        page += 1


def local_time(ts):
    return datetime.fromtimestamp(float(ts)).strftime("%Y-%m-%d %H:%M")


def thread_ts_from_permalink(permalink):
    query = urllib.parse.parse_qs(urllib.parse.urlparse(permalink).query)
    return query.get("thread_ts", [None])[0]


def main():
    global TOKEN
    parser = argparse.ArgumentParser()
    parser.add_argument("--oldest", required=True, type=float)
    parser.add_argument("--latest", required=True, type=float)
    parser.add_argument("--lookback", required=True, help="Start date (YYYY-MM-DD) for my own messages.")
    args = parser.parse_args()
    TOKEN = read_token()

    auth = call("auth.test")
    me, workspace_url = auth["user_id"], auth["url"]

    channels = {
        c["id"]: c["name"]
        for c in paginate("users.conversations", "channels", types="public_channel,private_channel",
                          exclude_archived="true", limit=200)
    }
    users = {u["id"]: u for u in paginate("users.list", "members", limit=200)}

    def name(user_id):
        user = users.get(user_id, {})
        return user.get("profile", {}).get("display_name") or user.get("real_name") or user_id or "unknown"

    def is_bot(message):
        user = users.get(message.get("user"), {})
        return bool(message.get("bot_id")) or message.get("user") == "USLACKBOT" or user.get("is_bot", False)

    def readable(text):
        text = re.sub(r"<@(U[A-Z0-9]+)(\|[^>]*)?>", lambda m: "@" + name(m.group(1)), text or "")
        return text[:MAX_TEXT] + ("…" if len(text) > MAX_TEXT else "")

    def permalink(channel_id, ts, thread_ts):
        link = f"{workspace_url}archives/{channel_id}/p{ts.replace('.', '')}"
        if thread_ts and thread_ts != ts:
            link += f"?thread_ts={thread_ts}&cid={channel_id}"
        return link

    def in_window(ts):
        return args.oldest <= float(ts) < args.latest

    # 1. Root messages posted in the window, from every channel's history.
    threads = {}  # (channel_id, thread_ts) -> root message from history, or None
    for channel_id in channels:
        for message in paginate("conversations.history", "messages", channel=channel_id,
                                oldest=f"{args.oldest:.6f}", latest=f"{args.latest:.6f}", limit=200):
            threads.setdefault((channel_id, message.get("thread_ts", message["ts"])), message)

    # 2. Replies posted in the window, to find older threads with new activity. Slack date
    # filters are exclusive whole days, so widen by a day and filter on the exact ts.
    after = (date.fromtimestamp(args.oldest) - timedelta(days=1)).isoformat()
    before = (date.fromtimestamp(args.latest) + timedelta(days=1)).isoformat()
    search_matches = 0
    for match in search(f"is:thread after:{after} before:{before}"):
        if float(match["ts"]) < args.oldest:
            break  # Newest first, so every later match is older than the window too.
        search_matches += 1
        channel_id = match.get("channel", {}).get("id")
        if channel_id not in channels or not in_window(match["ts"]):
            continue
        thread_ts = thread_ts_from_permalink(match.get("permalink", "")) or match["ts"]
        threads.setdefault((channel_id, thread_ts), None)

    # 3. Read each thread and apply the "I have not seen it" rules.
    candidates, dropped = [], {"bot_or_system_root": 0, "i_posted": 0, "i_reacted": 0, "i_mentioned": 0,
                                "only_bot_replies_in_window": 0}
    for (channel_id, thread_ts), root in threads.items():
        # A broadcast reply in the channel history is not the root, so read the thread.
        if root is None or root.get("reply_count") or root["ts"] != thread_ts:
            messages = list(paginate("conversations.replies", "messages", channel=channel_id, ts=thread_ts, limit=200))
        else:
            messages = [root]
        if not messages:
            continue
        root = messages[0]
        if is_bot(root) or root.get("subtype") in SYSTEM_SUBTYPES:
            dropped["bot_or_system_root"] += 1
            continue
        if any(m.get("user") == me for m in messages):
            dropped["i_posted"] += 1
            continue
        if any(me in r.get("users", []) for m in messages for r in m.get("reactions", [])):
            dropped["i_reacted"] += 1
            continue
        if any(f"<@{me}" in (m.get("text") or "") for m in messages):
            dropped["i_mentioned"] += 1
            continue

        root_in_window = in_window(root["ts"])
        shown = [m for m in messages[1:] if not is_bot(m) and (root_in_window or in_window(m["ts"]))]
        shown = shown[-MAX_MESSAGES_PER_THREAD:]
        if not root_in_window and not shown:
            dropped["only_bot_replies_in_window"] += 1
            continue
        candidates.append({
            "channel": "#" + channels[channel_id],
            "root_in_window": root_in_window,
            "root": {
                "from": name(root.get("user")),
                "time": local_time(root["ts"]),
                "text": readable(root.get("text")),
                "permalink": permalink(channel_id, root["ts"], None),
            },
            "reply_count": len(messages) - 1,
            "replies": [{
                "from": name(m.get("user")),
                "time": local_time(m["ts"]),
                "in_window": in_window(m["ts"]),
                "text": readable(m.get("text")),
                "permalink": permalink(channel_id, m["ts"], thread_ts),
            } for m in shown],
            "_last": max(float(m["ts"]) for m in messages),
        })
    candidates.sort(key=lambda c: c.pop("_last"), reverse=True)

    # 4. My own recent messages, for the interest profile.
    lookback_after = (date.fromisoformat(args.lookback) - timedelta(days=1)).isoformat()
    def where(channel):
        if channel.get("is_im"):
            return "DM"
        if channel.get("is_mpim"):
            return "group DM"
        return "#" + channel.get("name", "unknown")

    # End at the window end, so a brief for a past day does not see later messages.
    my_messages = [{
        "channel": where(m.get("channel", {})),
        "time": local_time(m["ts"]),
        "text": readable(m.get("text"))[:200],
    } for m in search(f"from:<@{me}> after:{lookback_after} before:{before}", max_pages=MY_MESSAGES_PAGES)
        if float(m["ts"]) < args.latest]

    json.dump({
        "window": {"from": local_time(args.oldest), "to": local_time(args.latest)},
        "stats": {
            "channels_scanned": len(channels),
            "threads_with_activity": len(threads),
            "search_matches": search_matches,
            "dropped": dropped,
            "candidates": len(candidates),
        },
        "my_recent_messages": my_messages,
        "candidates": candidates,
    }, sys.stdout, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
