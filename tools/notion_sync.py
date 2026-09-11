import argparse
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = "https://api.notion.com/v1/"
NOTION_VERSION = "2022-06-28"
DB_NAME = "YouTube Videos"
SENTINEL = "Source of truth:"
BATCH = 90
PAUSE = 0.35

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def load_env():
    env = {}
    p = os.path.join(ROOT, ".env")
    if os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return {**env, **os.environ}


def die(msg):
    print("ERROR: " + msg)
    sys.exit(1)


TOKEN = None


def call(path, method="GET", body=None):
    req = urllib.request.Request(
        API + path,
        method=method,
        data=json.dumps(body).encode("utf-8") if body is not None else None,
        headers={
            "Authorization": "Bearer " + TOKEN,
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        try:
            detail = json.loads(detail).get("message", detail)
        except ValueError:
            pass
        die(f"Notion {method} {path} -> {e.code}: {detail[:400]}")


def paged(path):
    cursor = None
    while True:
        sep = "&" if "?" in path else "?"
        url = f"{path}{sep}page_size=100" + (f"&start_cursor={cursor}" if cursor else "")
        res = call(url)
        for item in res["results"]:
            yield item
        if not res.get("has_more"):
            return
        cursor = res["next_cursor"]


def plain(rich):
    return "".join(x.get("plain_text", "") for x in rich or [])


INLINE = re.compile(r"(\*\*.+?\*\*|`[^`]+?`)")
MARKERS = {"⚠️": ("⚠️", "yellow_background"),
           "💡": ("💡", "blue_background"),
           "🎬": ("🎬", "gray_background")}


def rt(text):
    out = []
    for piece in INLINE.split(text):
        if not piece:
            continue
        ann = {}
        if piece.startswith("**") and piece.endswith("**"):
            piece, ann["bold"] = piece[2:-2], True
        elif piece.startswith("`") and piece.endswith("`"):
            piece, ann["code"] = piece[1:-1], True
        for i in range(0, max(len(piece), 1), 1900):
            out.append({"type": "text", "text": {"content": piece[i:i + 1900]},
                        "annotations": dict(ann)})
    return out or [{"type": "text", "text": {"content": ""}}]


def block(kind, text, **extra):
    body = {"rich_text": rt(text)}
    body.update(extra)
    return {"object": "block", "type": kind, kind: body}


def callout(text, emoji, color):
    return {"object": "block", "type": "callout",
            "callout": {"rich_text": rt(text),
                        "icon": {"type": "emoji", "emoji": emoji},
                        "color": color}}


DIVIDER = {"object": "block", "type": "divider", "divider": {}}


def _flush_quote(buf, blocks):
    if not buf:
        return
    head = buf[0].lstrip()
    for mark, (emoji, color) in MARKERS.items():
        if head.startswith(mark):
            blocks.append(callout("\n".join(buf).lstrip()[len(mark):].lstrip(), emoji, color))
            buf.clear()
            return
    for line in buf:
        if line.strip():
            blocks.append(block("paragraph", line.strip()))
    buf.clear()


def script_to_blocks(md):
    blocks, quote = [], []
    for raw in md.splitlines():
        line = raw.strip()
        if line.startswith(">"):
            quote.append(line[1:].strip())
            continue
        _flush_quote(quote, blocks)
        if not line:
            continue
        if line.startswith("---"):
            blocks.append(DIVIDER)
        elif line.startswith("### "):
            blocks.append(block("heading_3", line[4:]))
        elif line.startswith("## "):
            blocks.append(block("heading_2", line[3:]))
        elif line.startswith("# "):
            blocks.append(block("heading_1", line[2:]))
        elif line.startswith("`["):
            blocks.append(callout(line, "🎬", "gray_background"))
        else:
            blocks.append(block("paragraph", line))
    _flush_quote(quote, blocks)
    return blocks


def find_db(root_page):
    for b in paged(f"blocks/{root_page}/children"):
        if b["type"] == "child_database" and b["child_database"].get("title") == DB_NAME:
            return b["id"]
    die(f"no child database named {DB_NAME!r} under NOTION_LONGS_PAGE_ID ({root_page}). "
        "Check the integration is shared into the Content Plan page.")


def row_summary(row):
    props = row["properties"]
    return {
        "title": plain(props["Video"]["title"]) if "Video" in props else "",
        "stage": (props.get("Stage", {}).get("select") or {}).get("name") or "",
        "project": plain(props.get("Project", {}).get("rich_text")),
        "url": row["url"],
        "id": row["id"],
    }


def find_row(db, project, title):
    rows = [row_summary(r) for r in paged_query(db)]
    for r in rows:
        if r["project"].replace("\\", "/").strip("/") == project:
            return r, "project"
    if title:
        for r in rows:
            if r["title"].strip().lower() == title.strip().lower():
                return r, "title"
    return None, None


def paged_query(db):
    cursor = None
    while True:
        body = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        res = call(f"databases/{db}/query", "POST", body)
        for item in res["results"]:
            yield item
        if not res.get("has_more"):
            return
        cursor = res["next_cursor"]


def stage_options(db):
    schema = call(f"databases/{db}")["properties"]
    return [o["name"] for o in schema.get("Stage", {}).get("select", {}).get("options", [])]


def synced_from(page_id):
    blocks = list(paged(f"blocks/{page_id}/children"))
    for i, b in enumerate(blocks):
        if b["type"] == "callout" and plain(b["callout"]["rich_text"]).startswith(SENTINEL):
            return i, [x["id"] for x in blocks[i:]]
    return None, []


def clear_tail(page_id, keep, passes=4):
    removed = 0
    for attempt in range(passes):
        doomed = [b["id"] for b in list(paged(f"blocks/{page_id}/children"))[keep:]]
        if not doomed:
            return removed
        if attempt:
            print(f"  re-scan found {len(doomed)} more (listing lag)")
        for bid in doomed:
            call(f"blocks/{bid}", "DELETE")
            removed += 1
            time.sleep(PAUSE)
    die(f"could not clear the old body after {passes} passes — check the page by hand.")


def main():
    global TOKEN
    ap = argparse.ArgumentParser(description="Sync a video project into the Notion tracker.")
    ap.add_argument("project", nargs="?", help="project dir, e.g. videos/video-1")
    ap.add_argument("--apply", action="store_true", help="actually write (default is a dry run)")
    ap.add_argument("--resync", action="store_true",
                    help="replace an existing synced body instead of refusing")
    ap.add_argument("--props-only", action="store_true", help="skip the script body, properties only")
    ap.add_argument("--stage", help="override notion.json's stage")
    ap.add_argument("--list", action="store_true", help="list the tracker's rows and exit")
    args = ap.parse_args()

    env = load_env()
    TOKEN = env.get("NOTION_TOKEN")
    root_page = env.get("NOTION_LONGS_PAGE_ID")
    if not TOKEN or not root_page:
        die("NOTION_TOKEN and NOTION_LONGS_PAGE_ID must be set in .env (see .env.example).")

    db = find_db(root_page)

    if args.list:
        print(f"{DB_NAME}  ({db})\n")
        for r in (row_summary(x) for x in paged_query(db)):
            print(f"  {r['stage'] or '-':<14} {r['project'] or '-':<16} {r['title'][:64]}")
        return

    if not args.project:
        ap.error("a project dir is required (or use --list)")

    project = args.project.replace("\\", "/").strip("/")
    pdir = os.path.join(ROOT, project) if not os.path.isabs(args.project) else args.project
    if not os.path.isdir(pdir):
        die(f"no such project dir: {project} (run from the repo root)")

    cfg = {}
    cfg_path = os.path.join(pdir, "notion.json")
    if os.path.exists(cfg_path):
        cfg = json.load(open(cfg_path, encoding="utf-8"))
    stage = args.stage or cfg.get("stage")

    stages = stage_options(db)
    if stage and stage not in stages:
        die(f"stage {stage!r} is not a Stage option. Valid: {', '.join(stages)}")

    row, matched_by = find_row(db, project, cfg.get("title"))
    print(f"project : {project}")
    print(f"config  : {'notion.json' if cfg else '(none — properties will be minimal)'}")
    print(f"row     : " + (f"{row['title']!r} matched by {matched_by} — {row['url']}"
                           if row else "NONE — will create"))

    props = {"Project": {"rich_text": rt(project)}}
    if stage:
        props["Stage"] = {"select": {"name": stage}}
    for key, name in (("pillar", "Pillar"),):
        if cfg.get(key):
            props[name] = {"select": {"name": cfg[key]}}
    for key, name in (("hook_angle", "Hook Angle"), ("notes", "Notes"),
                      ("thumbnail_text", "Thumbnail Text")):
        if cfg.get(key):
            props[name] = {"rich_text": rt(cfg[key])}
    if not row and not cfg.get("title"):
        die("creating a new row needs a title — add \"title\" to notion.json.")
    if not row:
        props["Video"] = {"title": rt(cfg["title"])}
    print(f"props   : {', '.join(sorted(props))}")

    blocks = []
    if not args.props_only:
        rel = cfg.get("script", "script/script.md")
        spath = os.path.join(pdir, rel)
        if not os.path.exists(spath):
            die(f"no script at {project}/{rel} — pass --props-only, or set \"script\" in notion.json.")
        today = time.strftime("%Y-%m-%d")
        blocks = [
            callout(f"{SENTINEL} {project}/{rel} in the repo — synced here {today}. "
                    "Edit in the repo, not here.", "📌", "blue_background"),
        ]
        if cfg.get("checklist"):
            blocks.append(block("heading_2", "Record checklist"))
            blocks += [block("to_do", t, checked=False) for t in cfg["checklist"]]
        blocks.append(DIVIDER)
        blocks += script_to_blocks(open(spath, encoding="utf-8").read())
        kinds = {}
        for b in blocks:
            kinds[b["type"]] = kinds.get(b["type"], 0) + 1
        print(f"body    : {len(blocks)} blocks from {rel} — {kinds}")

    keep = None
    if row and blocks:
        idx, stale = synced_from(row["id"])
        if stale:
            keep = idx
            print(f"existing: a synced body starts at block {idx + 1} ({len(stale)} blocks). "
                  + (f"--resync will replace it, keeping the {idx} block(s) above it."
                     if args.resync else "Pass --resync to replace it."))
            if not args.resync:
                die("refusing to append a second copy of the script. Re-run with --resync.")

    if not args.apply:
        print("\nDRY RUN — nothing written. Re-run with --apply.")
        return

    if row:
        call(f"pages/{row['id']}", "PATCH", {"properties": props})
        page_id = row["id"]
        print("\nupdated properties")
    else:
        page = call("pages", "POST", {"parent": {"database_id": db}, "properties": props})
        page_id = page["id"]
        print("\ncreated row " + page["url"])

    if keep is not None:
        print(f"removed {clear_tail(page_id, keep)} stale blocks")

    for i in range(0, len(blocks), BATCH):
        chunk = blocks[i:i + BATCH]
        call(f"blocks/{page_id}/children", "PATCH", {"children": chunk})
        print(f"  appended {i + len(chunk)}/{len(blocks)}")
        time.sleep(PAUSE)

    print("\nDONE: " + call(f"pages/{page_id}")["url"])


if __name__ == "__main__":
    main()
