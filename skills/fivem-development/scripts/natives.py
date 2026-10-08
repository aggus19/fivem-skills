#!/usr/bin/env python3
"""FiveM native lookup and verification (offline cache of the official native DB).

Data sources (official, maintained by Cfx.re):
  - GTA V natives: https://static.cfx.re/natives/natives.json
  - CFX natives:   https://runtime.fivem.net/doc/natives_cfx.json

Usage:
  python natives.py update                  # download / refresh the cache
  python natives.py search <text> [--side client|server|shared] [--limit N]
  python natives.py show <NameOrHash>       # full signature + description
  python natives.py check <path> [...]      # verify natives used in .lua files exist
                                            # and are used on the correct side

Cache dir: $FIVEM_SKILL_CACHE or ~/.cache/fivem-skill
Exit code of `check`: 0 = clean, 1 = problems found, 2 = usage / cache error.
Standard library only (Python 3.8+).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

SOURCES = {
    "gta": "https://static.cfx.re/natives/natives.json",
    "cfx": "https://runtime.fivem.net/doc/natives_cfx.json",
}
CACHE_DIR = Path(os.environ.get("FIVEM_SKILL_CACHE", Path.home() / ".cache" / "fivem-skill"))
INDEX = CACHE_DIR / "natives_index.json"
MAX_AGE_DAYS = 14

# Globals that look like natives (PascalCase calls) but are Lua/CfxLua/runtime helpers.
NOT_NATIVES = {
    "Wait", "CreateThread", "SetTimeout", "ClearTimeout", "AddEventHandler", "RemoveEventHandler",
    "RegisterNetEvent", "RegisterServerEvent", "TriggerEvent", "TriggerServerEvent", "TriggerClientEvent",
    "TriggerLatentServerEvent", "TriggerLatentClientEvent", "RegisterNUICallback", "SendNUIMessage",
    "RegisterCommand", "Citizen", "Player", "Entity", "GlobalState", "LocalPlayer",
    # Lua runtime helpers defined in citizen scheduler/ (not natives)
    "GetPlayers", "GetPlayerIdentifiers", "GetPlayerTokens", "GetPlayerEP", "PerformHttpRequest",
    "PerformHttpRequestAwait", "RconPrint", "RconLog", "SetInterval", "ClearInterval",
    "MySQL", "ESX", "QBCore", "Config", "Locale", "Lang", "Bridge", "Utils",
}
CALL_RE = re.compile(r"(?<![\w.:])([A-Z][A-Za-z0-9_]+|N_0x[0-9a-fA-F]+)\s*\(")
DEF_RE = re.compile(r"(?:function\s+|local\s+function\s+|local\s+)([A-Z][A-Za-z0-9_]*)")
ASSIGN_RE = re.compile(r"^\s*([A-Z][A-Za-z0-9_]*)\s*=", re.M)


def lua_name(native_name: str, hash_: str) -> str:
    # Mirrors the citizenfx Lua codegen: lower-case, then upper-case the first letter and every
    # letter that follows an underscore (dropping that underscore). An underscore followed by a
    # digit is kept: GET_GROUND_Z_FOR_3D_COORD -> GetGroundZFor_3dCoord.
    if not native_name or native_name.lstrip("_").startswith("0x"):
        return "N_" + hash_.lower()
    n = native_name.lower()
    n = re.sub(r"^[a-z]", lambda m: m.group(0).upper(), n)
    return re.sub(r"_([a-z])", lambda m: m.group(1).upper(), n)


def fetch(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "fivem-skill/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))


def build_index() -> dict:
    index: dict[str, list] = {}
    for src, url in SOURCES.items():
        data = fetch(url)
        for ns, natives in data.items():
            for h, n in natives.items():
                side = n.get("apiset") or ("client" if src == "gta" else "shared")
                entry = {
                    "native": n.get("name", ""),
                    "hash": h,
                    "ns": ns,
                    "side": side,
                    "params": [f'{p.get("type", "?")} {p.get("name", "?")}' for p in n.get("params", [])],
                    "results": n.get("results", "void"),
                    "desc": (n.get("description") or "").strip()[:1200],
                    "src": src,
                }
                names = {lua_name(entry["native"], h), "N_" + h.lower()}
                # old names (DB aliases) are still emitted as Lua globals by the codegen
                names |= {lua_name(a, h) for a in n.get("aliases") or [] if not a.startswith("0x")}
                for nm in names:
                    # one Lua name can map to a client (GTA) and a server (CFX) native
                    index.setdefault(nm, []).append(entry)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "sources": SOURCES, "natives": index}
    INDEX.write_text(json.dumps(payload), encoding="utf-8")
    return payload


def load_index(auto_update: bool = True) -> dict:
    if INDEX.exists():
        payload = json.loads(INDEX.read_text(encoding="utf-8"))
        age = time.time() - INDEX.stat().st_mtime
        if age > MAX_AGE_DAYS * 86400:
            print(f"[natives] cache is {int(age // 86400)} days old; run `natives.py update`", file=sys.stderr)
        return payload
    if not auto_update:
        print("[natives] no cache; run `natives.py update`", file=sys.stderr)
        sys.exit(2)
    print("[natives] downloading native DB (first run)...", file=sys.stderr)
    return build_index()


def sides(entries: list) -> set:
    return {e["side"] for e in entries}


def fmt(name: str, e: dict) -> str:
    return f'{name}({", ".join(e["params"])}) -> {e["results"]}   [{e["side"]}] {e["native"]} {e["hash"]}'


def cmd_search(args) -> int:
    nat = load_index()["natives"]
    q = args.text.lower().replace("_", "")
    seen = set()
    hits = []
    for name, entries in nat.items():
      for e in entries:
        if name.startswith("N_0x") and not args.text.lower().startswith("0x") and not args.text.startswith("N_"):
            continue
        key = e["hash"]
        if key in seen:
            continue
        hay = (name + e["native"].replace("_", "") + e["hash"]).lower()
        if q in hay or (args.desc and q in e["desc"].lower()):
            if args.side and e["side"] not in (args.side, "shared"):
                continue
            seen.add(key)
            hits.append(fmt(lua_name(e["native"], e["hash"]), e))
    for line in sorted(hits)[: args.limit]:
        print(line)
    print(f"-- {len(hits)} match(es)", file=sys.stderr)
    return 0


def cmd_show(args) -> int:
    nat = load_index()["natives"]
    key = args.name
    entries = nat.get(key) or nat.get("N_" + key.lower()) or nat.get(lua_name(key, "0x0"))
    if not entries:
        print(f"not found: {key}  (try `search`)")
        return 1
    for i, e in enumerate(entries):
        if i:
            print("\n" + "-" * 60)
        print(fmt(lua_name(e["native"], e["hash"]), e))
        print(f'namespace: {e["ns"]}   source: {e["src"]}')
        print(f'docs: https://docs.fivem.net/natives/?_{e["hash"]}')
        if e["desc"]:
            print("\n" + e["desc"])
    return 0


def side_of(path: Path, text: str) -> str | None:
    p = str(path).replace("\\", "/").lower()
    if re.search(r"(^|/)(server|sv)[/_.]|_server\.lua$|/server\.lua$|sv_[^/]*\.lua$", p):
        return "server"
    if re.search(r"(^|/)(client|cl)[/_.]|_client\.lua$|/client\.lua$|cl_[^/]*\.lua$", p):
        return "client"
    return None  # shared / unknown


def cmd_check(args) -> int:
    nat = load_index()["natives"]
    files: list[Path] = []
    for raw in args.paths:
        p = Path(raw)
        files += [p] if p.is_file() else [f for f in p.rglob("*.lua") if "node_modules" not in f.parts]
    problems = 0
    for f in files:
        text = f.read_text(encoding="utf-8", errors="replace")
        local_defs = set(DEF_RE.findall(text)) | set(ASSIGN_RE.findall(text))
        side = side_of(f, text)
        for ln, line in enumerate(text.splitlines(), 1):
            code = re.sub(r"'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\"", "''", line.split("--", 1)[0])
            for m in CALL_RE.finditer(code):
                name = m.group(1)
                if name in NOT_NATIVES or name in local_defs:
                    continue
                entries = nat.get(name) or (nat.get("N_" + name[2:].lower()) if name.startswith("N_") else None)
                if not entries:
                    if args.strict:
                        print(f"{f}:{ln}: UNKNOWN  {name}() is not a known native (typo, removed, or a custom global?)")
                        problems += 1
                    continue
                avail = sides(entries)
                if side and not avail & {"shared", side}:
                    print(f"{f}:{ln}: WRONG-SIDE  {name}() is {'/'.join(sorted(avail))}-only but used in a {side} file")
                    problems += 1
    print(f"-- checked {len(files)} file(s), {problems} problem(s)", file=sys.stderr)
    return 1 if problems else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("update", help="download/refresh the native DB cache")
    s = sub.add_parser("search", help="search natives by name/hash (and optionally description)")
    s.add_argument("text")
    s.add_argument("--side", choices=["client", "server", "shared"])
    s.add_argument("--desc", action="store_true", help="also search descriptions")
    s.add_argument("--limit", type=int, default=40)
    sh = sub.add_parser("show", help="show one native")
    sh.add_argument("name")
    c = sub.add_parser("check", help="verify natives used in Lua files")
    c.add_argument("paths", nargs="+")
    c.add_argument("--strict", action="store_true", help="also report unknown PascalCase calls")
    args = ap.parse_args()
    if args.cmd == "update":
        p = build_index()
        print(f"cached {len(p['natives'])} names -> {INDEX}")
        return 0
    return {"search": cmd_search, "show": cmd_show, "check": cmd_check}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
