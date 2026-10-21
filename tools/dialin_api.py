#!/usr/bin/env python3
"""
Dial-In repo writer — shared by the app chat and the data chat.

Safe by design:
  * reads through the GitHub API (never the cached raw CDN)
  * writes with the file's sha; if someone else wrote in between, it re-reads,
    re-applies the change and retries — entries are never lost
  * validates entries against schema.json before writing
  * keeps dialins.json wrapped as {_appWrittenAt, entries} so the app auto-syncs

Token: env var GITHUB_TOKEN (or --token). Never hardcode it in this file.

Usage
  python dialin_api.py add     entries.json [--dry-run]
  python dialin_api.py update  ID patch.json [--dry-run]
  python dialin_api.py wishlist items.json [--dry-run]
  python dialin_api.py check                       # validate the live dialins.json
  python dialin_api.py list    [--limit 20]        # newest entries, one line each

entries.json / items.json: one object or a list of objects.
Missing optional fields get schema defaults; a missing id is generated.
"""
import argparse, base64, json, os, re, sys, time, urllib.error, urllib.request
from datetime import date

OWNER, REPO, BRANCH = "trynerlu", "coffee-dialins", "main"
API = f"https://api.github.com/repos/{OWNER}/{REPO}/contents"

# ── HTTP ──────────────────────────────────────────────────────────────────────
def _token(args=None):
    t = (getattr(args, "token", None) or os.environ.get("GITHUB_TOKEN") or "").strip()
    if not t:
        sys.exit("No token: set GITHUB_TOKEN or pass --token")
    return t

def _req(method, path, token, body=None):
    url = f"{API}/{path}" + (f"?ref={BRANCH}&_={int(time.time()*1000)}" if method == "GET" else "")
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
    })
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        try: payload = json.loads(e.read() or b"{}")
        except Exception: payload = {}
        return e.code, payload

def read_file(path, token):
    """Return (bytes or None, sha or None)."""
    st, j = _req("GET", path, token)
    if st == 404: return None, None
    if st != 200: raise RuntimeError(f"read {path}: HTTP {st} {j.get('message','')}")
    return base64.b64decode(j["content"]), j["sha"]

def read_json(path, token):
    raw, sha = read_file(path, token)
    return (json.loads(raw) if raw else None), sha

def put_file(path, content_bytes, token, sha, message):
    body = {"message": message, "branch": BRANCH,
            "content": base64.b64encode(content_bytes).decode()}
    if sha: body["sha"] = sha
    return _req("PUT", path, token, body)

def update_json(path, mutate, token, message, attempts=5, dry_run=False):
    """Read-modify-write with sha guard. mutate(list) -> list."""
    for i in range(attempts):
        data, sha = read_json(path, token)
        arr = [] if data is None else (data if isinstance(data, list) else data.get("entries", []))
        nxt = mutate(json.loads(json.dumps(arr)))
        payload = {"_appWrittenAt": int(time.time()*1000), "entries": nxt} if path == "dialins.json" else nxt
        if dry_run:
            return nxt
        st, j = put_file(path, json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"),
                         token, sha, message)
        if st in (200, 201): return nxt
        if st in (409, 422):           # someone else wrote — re-read and re-apply
            time.sleep(1.2); continue
        raise RuntimeError(f"write {path}: HTTP {st} {j.get('message','')}")
    raise RuntimeError(f"{path} kept changing — gave up after {attempts} attempts")

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

def load_schema(token):
    s, _ = read_json("schema.json", token)
    return s or {}

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
    if not (0 <= (e.get("rating") or 0) <= 5): errs.append("rating must be 0–5")
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
    stars = "★"*int(e.get("rating") or 0)
    bm = "/".join(e.get("brewMethods") or [])
    return f"{e['date']}  {e.get('roaster','')} — {e.get('coffeeName','')}  [{bm}] {stars}  ({e['id']})"

def cmd_add(args):
    tok = _token(args); schema = load_schema(tok)
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
    update_json("dialins.json", mut, tok, f"Add {len(entries)} entr{'y' if len(entries)==1 else 'ies'} via dialin_api",
                dry_run=args.dry_run)
    print(("[dry-run] would add" if args.dry_run else "✓ Added"), len(entries))
    for e in entries: print("  ", summary(e))

def cmd_update(args):
    tok = _token(args); schema = load_schema(tok)
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
    update_json("dialins.json", mut, tok, f"Update {args.id} via dialin_api", dry_run=args.dry_run)
    print(("[dry-run] would update" if args.dry_run else "✓ Updated"), summary(result["e"]))

def cmd_wishlist(args):
    tok = _token(args)
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
    update_json("wishlist.json", lambda cur: items + [c for c in cur if c["id"] not in ids], tok,
                f"Add {len(items)} wishlist item(s) via dialin_api", dry_run=args.dry_run)
    print(("[dry-run] would add" if args.dry_run else "✓ Added"), len(items), "wishlist item(s)")

def cmd_check(args):
    tok = _token(args); schema = load_schema(tok)
    data, _ = read_json("dialins.json", tok)
    entries = data if isinstance(data, list) else data.get("entries", [])
    print(f"{len(entries)} entries | wrapped: {not isinstance(data, list)}")
    n = 0
    for e in entries:
        errs, _ = validate(normalize(e), schema)
        for x in errs: print(f"  ✗ {e.get('coffeeName','?')} ({e['id']}): {x}"); n += 1
    print("✓ all valid" if not n else f"{n} problem(s)")

def cmd_list(args):
    tok = _token(args)
    data, _ = read_json("dialins.json", tok)
    entries = data if isinstance(data, list) else data.get("entries", [])
    for e in sorted(entries, key=lambda x: x.get("date",""), reverse=True)[:args.limit]:
        print(summary(e))

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--token"); ap.add_argument("--dry-run", action="store_true")
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
