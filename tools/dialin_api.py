#!/usr/bin/env python3
"""
Dial-In repo writer — the only sanctioned way to change dialins.json / wishlist.json.

Writes with plain git, using whatever git access this machine or session already has:
  * fetches origin/main and reads the file from there (never from a stale local copy)
  * validates entries against schema.json before writing
  * builds a commit on top of origin/main and pushes it straight to main;
    if main moved in the meantime, it re-fetches, re-applies the change and retries
  * never touches your working tree or current branch; if you are on main with a
    clean tree, it fast-forwards it afterwards
  * keeps dialins.json wrapped as {_appWrittenAt, entries} so the app picks it up

Usage
  python3 tools/dialin_api.py add      entries.json [--dry-run]
  python3 tools/dialin_api.py update   ID patch.json [--dry-run]
  python3 tools/dialin_api.py wishlist items.json [--dry-run]
  python3 tools/dialin_api.py check                    # validate the live dialins.json, print the count
  python3 tools/dialin_api.py list     [--limit 20]    # newest entries, one line each

entries.json / items.json: one object or a list of objects.
Missing optional fields get schema defaults; a missing id is generated.
"""
import argparse, json, os, re, subprocess, sys, tempfile, time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REMOTE, BRANCH = "origin", "main"
REF = f"{REMOTE}/{BRANCH}"

# ── GIT ───────────────────────────────────────────────────────────────────────
def git(*args, data=None, env=None, check=True):
    r = subprocess.run(["git", "-C", str(ROOT), *args], input=data, capture_output=True,
                       env={**os.environ, **(env or {})})
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {r.stderr.decode(errors='replace').strip()}")
    return r

def fetch():
    git("fetch", "-q", REMOTE, BRANCH)

def read_json(path):
    """Parsed JSON of `path` on origin/main (None if the file doesn't exist). Call fetch() first."""
    r = git("show", f"{REF}:{path}", check=False)
    return json.loads(r.stdout) if r.returncode == 0 else None

def commit_file(path, content_bytes, message):
    """Commit `path` = content on top of origin/main, without touching the working tree."""
    parent = git("rev-parse", REF).stdout.decode().strip()
    blob = git("hash-object", "-w", "--stdin", data=content_bytes).stdout.decode().strip()
    with tempfile.TemporaryDirectory() as tmp:
        env = {"GIT_INDEX_FILE": os.path.join(tmp, "index")}
        git("read-tree", parent, env=env)
        git("update-index", "--add", "--cacheinfo", f"100644,{blob},{path}", env=env)
        tree = git("write-tree", env=env).stdout.decode().strip()
    return git("commit-tree", tree, "-p", parent, "-m", message).stdout.decode().strip()

def sync_local_main():
    """Fast-forward the local main if it is checked out and clean; otherwise just say so."""
    cur = git("rev-parse", "--abbrev-ref", "HEAD").stdout.decode().strip()
    dirty = git("status", "--porcelain", "--untracked-files=no").stdout.strip()
    if cur == BRANCH and not dirty and git("merge", "--ff-only", "-q", REF, check=False).returncode == 0:
        return
    print(f"  (local copy not updated — run `git pull` on {BRANCH} when convenient)")

def update_json(path, mutate, message, attempts=5, dry_run=False):
    """Read-modify-write on origin/main, retried if main moves. mutate(list) -> list."""
    for _ in range(attempts):
        fetch()
        data = read_json(path)
        arr = [] if data is None else (data if isinstance(data, list) else data.get("entries", []))
        nxt = mutate(json.loads(json.dumps(arr)))
        if dry_run:
            return nxt
        payload = {"_appWrittenAt": int(time.time()*1000), "entries": nxt} if path == "dialins.json" else nxt
        sha = commit_file(path, (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"), message)
        if git("push", "-q", REMOTE, f"{sha}:refs/heads/{BRANCH}", check=False).returncode == 0:
            fetch(); sync_local_main()
            return nxt
        time.sleep(1.5)                 # main moved (or push refused) — re-read and re-apply
    raise RuntimeError(f"could not push {path} to {BRANCH} after {attempts} attempts "
                       f"(check `git push` works in this session)")

# ── SCHEMA ────────────────────────────────────────────────────────────────────
DEFAULTS = {
    "roastDate": "", "frozenDate": "", "thawDate": "", "kitId": "",
    "origin": "", "region": "", "process": "", "roastLevel": "", "roaster": "",
    "flavorNotes": "", "grindSetting": "", "grinder": "",
    "doseIn": 0, "yieldOut": 0, "timeSeconds": 0, "temperature": 0, "rating": 0,
    "dialStatus": "dialed", "beanLocation": "empty", "experimenting": False,
    "wouldBuy": False, "isChoice": False, "isEarlyEntry": False,
    "tags": [], "dialEase": None, "dialStability": None, "filterPours": [],
    "coffeeUrl": "", "coffeeDescription": "", "notes": "",
    # v3.2 library fields
    "review": "", "variety": "", "producer": "", "farm": "", "altitude": "",
}
DEPRECATED = ["intendedFor","dialDifficulty","shotStability","roasterUrl",
              "filterBloomGrams","filterBloomSeconds","bagStatus","status"]

def load_schema():
    return read_json("schema.json") or {}

def slug(s): return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")[:24] or "coffee"

def normalize(e):
    e = {**DEFAULTS, **e}
    if not e.get("id"):
        e["id"] = f"d-{int(time.time()*1000)}-{slug(e.get('roaster',''))[:6]}-{slug(e.get('coffeeName',''))[:10]}"
        time.sleep(0.002)
    if not e.get("date"): e["date"] = date.today().isoformat()
    for k in DEPRECATED + ["photo"]: e.pop(k, None)   # photos are input only, never stored
    for p in e.get("filterPours") or []:
        if "startSecondl" in p: p["startSeconds"] = p.pop("startSecondl")
    return e

def validate(e, schema):
    errs, warns = [], []
    en = schema.get("enums", {})
    for k in ("id", "date", "coffeeName"):
        if not e.get(k): errs.append(f"missing {k}")
    if not isinstance(e.get("brewMethods"), list) or not e["brewMethods"]:
        errs.append("brewMethods must be a non-empty list")
    checks = [("process","process"),("roastLevel","roastLevel"),("dialStatus","dialStatus"),
              ("beanLocation","beanLocation"),("dialEase","dialEase"),("dialStability","dialStability")]
    for field, key in checks:
        v = e.get(field)
        if v not in (None, "") and key in en and v not in en[key]:
            errs.append(f"{field}={v!r} not in {en[key]}")
    for m in e.get("brewMethods") or []:
        if "brewMethods" in en and m not in en["brewMethods"]: errs.append(f"brewMethod {m!r} unknown")
    if e.get("kitId") and "kitIds" in schema and e["kitId"] not in schema["kitIds"]:
        errs.append(f"kitId {e['kitId']!r} unknown")
    for t in e.get("tags") or []:
        if "tags" in en and t not in en["tags"]: warns.append(f"tag {t!r} not in standard list")
    r = e.get("rating") or 0
    if not (0 <= r <= 5) or (r * 2) != int(r * 2): errs.append("rating must be 0–5 in 0.5 steps")
    for p in e.get("filterPours") or []:
        if set(p) != {"phase","targetGrams","startSeconds"}: errs.append(f"bad pour phase {p}")
    for d in ("date","roastDate","frozenDate","thawDate"):
        v = e.get(d)
        if v and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", v): errs.append(f"{d} must be YYYY-MM-DD")
    if not e.get("review") and not e.get("notes"): warns.append("no review/notes text")
    return errs, warns

# ── COMMANDS ──────────────────────────────────────────────────────────────────
def _load_objs(path):
    obj = json.load(open(path, encoding="utf-8"))
    return obj if isinstance(obj, list) else [obj]

def summary(e):
    r = e.get("rating") or 0
    stars = "★"*int(r) + ("½" if r % 1 else "")
    bm = "/".join(e.get("brewMethods") or [])
    return f"{e['date']}  {e.get('roaster','')} — {e.get('coffeeName','')}  [{bm}] {stars}  ({e['id']})"

def cmd_add(args):
    fetch(); schema = load_schema()
    entries = [normalize(e) for e in _load_objs(args.file)]
    bad = False
    for e in entries:
        errs, warns = validate(e, schema)
        for w in warns: print(f"  ! {e['coffeeName']}: {w}")
        for x in errs: print(f"  ✗ {e.get('coffeeName','?')}: {x}"); bad = True
    if bad: sys.exit("Validation failed — nothing written.")
    ids = {e["id"] for e in entries}
    def mut(cur):
        dup = [c["id"] for c in cur if c["id"] in ids]
        if dup: raise RuntimeError(f"ids already exist (use update): {dup}")
        return entries + cur
    update_json("dialins.json", mut, f"Add {len(entries)} entr{'y' if len(entries)==1 else 'ies'} via dialin_api",
                dry_run=args.dry_run)
    print(("[dry-run] would add" if args.dry_run else "✓ Added"), len(entries))
    for e in entries: print("  ", summary(e))

def cmd_update(args):
    fetch(); schema = load_schema()
    patch = json.load(open(args.file, encoding="utf-8"))
    result = {}
    def mut(cur):
        i = next((k for k, c in enumerate(cur) if c["id"] == args.id), None)
        if i is None: raise RuntimeError(f"no entry {args.id}")
        merged = normalize({**cur[i], **patch})
        errs, warns = validate(merged, schema)
        if errs: raise RuntimeError("; ".join(errs))
        cur[i] = merged; result["e"] = merged
        return cur
    update_json("dialins.json", mut, f"Update {args.id} via dialin_api", dry_run=args.dry_run)
    print(("[dry-run] would update" if args.dry_run else "✓ Updated"), summary(result["e"]))

def cmd_wishlist(args):
    items = _load_objs(args.file)
    today = date.today().isoformat()
    for w in items:
        w.setdefault("id", f"w-{int(time.time()*1000)}-{slug(w.get('roaster',''))[:10]}"); time.sleep(0.002)
        w.setdefault("type", "radar"); w.setdefault("addedDate", today)
        for k in ("coffeeName","source","date","flavorNotes","notes","url","orderedDate","dialinId"): w.setdefault(k, "")
        w.setdefault("ordered", False)
        if not w.get("roaster"): sys.exit("wishlist item missing roaster")
        if w["type"] not in ("radar","tasted"): sys.exit(f"bad type {w['type']}")
    ids = {w["id"] for w in items}
    update_json("wishlist.json", lambda cur: items + [c for c in cur if c["id"] not in ids],
                f"Add {len(items)} wishlist item(s) via dialin_api", dry_run=args.dry_run)
    print(("[dry-run] would add" if args.dry_run else "✓ Added"), len(items), "wishlist item(s)")

def cmd_check(args):
    fetch(); schema = load_schema()
    data = read_json("dialins.json") or []
    entries = data if isinstance(data, list) else data.get("entries", [])
    print(f"{len(entries)} entries | wrapped: {not isinstance(data, list)}")
    n = 0
    for e in entries:
        errs, _ = validate(normalize(e), schema)
        for x in errs: print(f"  ✗ {e.get('coffeeName','?')} ({e['id']}): {x}"); n += 1
    print("✓ all valid" if not n else f"{n} problem(s)")

def cmd_list(args):
    fetch()
    data = read_json("dialins.json") or []
    entries = data if isinstance(data, list) else data.get("entries", [])
    for e in sorted(entries, key=lambda x: x.get("date",""), reverse=True)[:args.limit]:
        print(summary(e))

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add");      a.add_argument("file")
    u = sub.add_parser("update");   u.add_argument("id"); u.add_argument("file")
    w = sub.add_parser("wishlist"); w.add_argument("file")
    sub.add_parser("check")
    l = sub.add_parser("list");     l.add_argument("--limit", type=int, default=20)
    for p in (a, u, w): p.add_argument("--dry-run", action="store_true", default=argparse.SUPPRESS)  # don't override a top-level --dry-run
    args = ap.parse_args()
    if args.dry_run: print("[dry-run] nothing will be written")
    {"add": cmd_add, "update": cmd_update, "wishlist": cmd_wishlist,
     "check": cmd_check, "list": cmd_list}[args.cmd](args)

if __name__ == "__main__":
    main()
