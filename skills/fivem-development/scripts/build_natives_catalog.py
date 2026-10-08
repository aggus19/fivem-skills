#!/usr/bin/env python3
"""Generate a complete, compact markdown catalogue of every FiveM native.

Reads the official native DBs (same sources as natives.py):
  - GTA V natives: https://static.cfx.re/natives/natives.json
  - CFX natives:   https://runtime.fivem.net/doc/natives_cfx.json
and writes:
  <out>/README.md            index: namespaces, counts, generation date, sources, legend
  <out>/<NAMESPACE>.md       one file per GTA namespace (PLAYER.md, VEHICLE.md, ...)
  <out>/CFX-CLIENT.md, CFX-SERVER.md, CFX-SHARED.md   CFX natives split by apiset

Each entry: Lua name, Lua call signature (typed params), Lua return values (pointer params become
returns, mirroring citizenfx ext/natives/codegen_out_lua.lua), side, hash, minimum game build when
the DB says so, old names (aliases, still callable in Lua), one-line description and docs link.

Usage:
  python scripts/build_natives_catalog.py [--out DIR] [--refresh]

Default --out is assets/natives next to this script's parent. Raw JSON is cached in
$FIVEM_SKILL_CACHE (default ~/.cache/fivem-skill) as raw_gta.json / raw_cfx.json and re-downloaded
when older than natives.MAX_AGE_DAYS or with --refresh. Standard library only (Python 3.8+).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import natives as nv  # noqa: E402  (reuse SOURCES, CACHE_DIR, fetch, lua_name, MAX_AGE_DAYS)

DOCS = "https://docs.fivem.net/natives/?_{}"
STRING_TYPES = {"char*", "const char*"}
CFX_FILES = {"client": "CFX-CLIENT", "server": "CFX-SERVER", "shared": "CFX-SHARED"}
SIDE_NOTE = {
    "client": "client only",
    "server": "server only",
    "shared": "client and server",
}


# ---------------------------------------------------------------- data loading
def load_raw(refresh: bool) -> tuple[dict, float]:
    """Return ({src: json}, fetched_epoch). Uses a raw cache next to natives.py's index."""
    data = {}
    fetched = time.time()
    nv.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    for src, url in nv.SOURCES.items():
        path = nv.CACHE_DIR / f"raw_{src}.json"
        stale = not path.exists() or (time.time() - path.stat().st_mtime) > nv.MAX_AGE_DAYS * 86400
        if refresh or stale:
            print(f"[catalog] downloading {url}", file=sys.stderr)
            payload = nv.fetch(url)
            path.write_text(json.dumps(payload), encoding="utf-8")
        data[src] = json.loads(path.read_text(encoding="utf-8"))
        fetched = min(fetched, path.stat().st_mtime)
    return data, fetched


# ---------------------------------------------------------------- formatting helpers
def is_pointer(ptype: str) -> bool:
    return ptype.endswith("*") and ptype not in STRING_TYPES


def lua_signature(n: dict) -> tuple[str, str]:
    """(typed Lua argument list, Lua return list) following codegen_out_lua.lua:
    pointer args are dropped from the call and returned after the native's own result, except when
    the native has exactly one pointer and it is the last argument (then it is passed AND returned)."""
    params = n.get("params", [])
    ptrs = [p for p in params if is_pointer(p.get("type", ""))]
    single = len(ptrs) == 1 and params and is_pointer(params[-1].get("type", ""))
    args = [f'{p.get("type", "?")} {p.get("name", "?")}' if not is_pointer(p.get("type", ""))
            else f'{p["type"][:-1]} {p.get("name", "?")} (in/out)'
            for p in params if not is_pointer(p.get("type", "")) or single]
    rets = []
    res = n.get("results") or "void"
    if res != "void":
        rets.append(res)
    rets += [f'{p["type"][:-1]} {p.get("name", "?")}' for p in ptrs]
    return ", ".join(args), (", ".join(rets) if rets else "void")


_FENCE = re.compile(r"```[a-zA-Z]*")
_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_TAG = re.compile(r"<[^>]+>")
_BUILD = re.compile(r"NativeDB Introduced:\s*v(\d+)")


def min_build(desc: str) -> int:
    m = _BUILD.findall(desc or "")
    return max(int(x) for x in m) if m else 0


def one_line(desc: str, limit: int = 170) -> str:
    """First sentence of a description, stripped of markdown, code, build notes and examples."""
    if not desc:
        return ""
    text = _FENCE.sub("\n", desc)
    keep = []
    for line in text.splitlines():
        s = line.strip()
        if re.fullmatch(r"_?[A-Z0-9_]+", s):  # heading that just repeats the native name
            continue
        if not s or s.startswith(("NativeDB", "//", "--", "#", "Example", "|")):
            continue
        if "::" in s or s.endswith((";", "{", "}")) or s.lower().startswith(("int ", "bool ", "void ", "local ")):
            continue
        keep.append(s)
        if len(" ".join(keep)) > limit * 2:
            break
    text = " ".join(keep)
    text = _LINK.sub(r"\1", text)
    text = _TAG.sub("", text)
    text = text.replace("**", "").replace("`", "").replace("\\_", "_").replace("|", "/")
    text = re.sub(r"\s+", " ", text).strip(" -*>")
    m = re.match(r"(.+?[.!?])(?:\s|$)", text)
    if m and len(m.group(1)) >= 12:
        text = m.group(1)
    if len(text) > limit:
        text = text[: limit - 1].rsplit(" ", 1)[0] + "…"
    return text


def entry_line(n: dict, side: str) -> str:
    h = n["hash"]
    name = nv.lua_name(n.get("name", ""), h)
    args, rets = lua_signature(n)
    parts = [f"- **`{name}`**`({args})` → `{rets}`"]
    meta = ["", side, f"[`{h}`]({DOCS.format(h)})"]
    b = min_build(n.get("description", ""))
    if b > 323:  # v323 is the original PC build: no gating information
        meta.append(f"build ≥{b}")
    if (n.get("name") or "").startswith("_"):
        meta.append("community name")
    aliases = [a for a in n.get("aliases") or [] if not a.startswith("0x")]
    if aliases:
        meta.append("aka " + ", ".join(f"`{nv.lua_name(a, h)}`" for a in aliases[:3]))
    parts[0] += " · ".join(meta)
    d = one_line(n.get("description", ""))
    if d:
        parts.append("— " + d)
    return " ".join(parts)


# ---------------------------------------------------------------- page builders
def build_page(title: str, side: str, natives_: list, fetched: str, blurb: str) -> str:
    named = sorted((n for n in natives_ if n.get("name")), key=lambda n: nv.lua_name(n["name"], n["hash"]))
    unnamed = sorted((n for n in natives_ if not n.get("name")), key=lambda n: n["hash"].lower())
    out = [
        f"# {title} natives ({len(natives_)})",
        "",
        f"Baseline: native DB fetched {fetched} · generated by `scripts/build_natives_catalog.py` — do not edit by hand.",
        f"Side: **{SIDE_NOTE.get(side, side)}** · {blurb}",
        "Legend: `Name(args)` → `Lua returns` (pointer params are returned, see [README](README.md#legend)) · side · hash/docs link.",
        "",
        "Contents: [Named natives](#named-natives) · [Unnamed natives (N_0x…)](#unnamed-natives)",
        "",
        f"## Named natives ({len(named)})",
        "",
    ]
    out += [entry_line(n, side) for n in named] or ["_none_"]
    out += ["", f"## Unnamed natives ({len(unnamed)})", ""]
    if unnamed:
        out.append("UNNAMED: no official name yet; call as `N_0x<hash>` or `Citizen.InvokeNative(0x<hash>, ...)`. "
                   "Behaviour is often undocumented — verify before use.")
        out.append("")
        out += [entry_line(n, side) for n in unnamed]
    else:
        out.append("_none_")
    return "\n".join(out) + "\n"


def build_readme(rows: list, fetched: str, total: int, unnamed: int) -> str:
    out = [
        "# FiveM native catalogue",
        "",
        f"Baseline: native DB fetched {fetched} · generated by `python scripts/build_natives_catalog.py` (regenerate, don't edit).",
        f"**{total} natives** in **{len(rows)} files** ({unnamed} unnamed `N_0x…`).",
        "",
        "Contents: [Files](#files) · [Legend](#legend) · [How to use](#how-to-use) · [Sources](#sources)",
        "",
        "## Files",
        "",
        "| File | Side | Natives | Unnamed |",
        "|---|---|---:|---:|",
    ]
    for fname, side, cnt, un in rows:
        out.append(f"| [{fname}]({fname}) | {side} | {cnt} | {un} |")
    out += [
        "",
        "## Legend",
        "",
        "Each line: **`LuaName`**`(typed args)` → `Lua return values` · side · hash (link to docs.fivem.net) · "
        "`build ≥N` (minimum game build from the DB) · `aka` old names · — first sentence of the description.",
        "",
        "- Lua names follow the citizenfx codegen (`ext/natives/codegen_out_lua.lua`): `GET_ENTITY_COORDS` → `GetEntityCoords`; "
        "an underscore before a digit is kept (`GetGroundZFor_3dCoord`); unnamed natives are `N_0x<hash>`.",
        "- **Pointer params** (`int*`, `float*`, `Vector3*`, `BOOL*`, `Entity*`, …) are not passed from Lua; they are "
        "returned after the native's own result: `local hit, groundZ = GetGroundZFor_3dCoord(x, y, z, false, false)`. "
        "Exception: if the only pointer is the last parameter it is passed in *and* returned "
        "(e.g. `DeleteEntity(entity)`, `SetEntityAsNoLongerNeeded(entity)`).",
        "- `char*` = string, `Hash` = number (strings are auto-hashed by the Lua wrapper), `BOOL` = boolean, "
        "`Entity/Ped/Vehicle/Object/Player/Blip/Cam` = integer handles.",
        "- `aka` names (DB aliases) are emitted by the codegen as extra globals, so old scripts keep working; prefer the current name.",
        "- `community name`: the DB name starts with `_` (reverse-engineered, not Rockstar's); the Lua name drops the underscore.",
        "- GTA namespaces are **client-side** in FiveM. Server-side natives live only in CFX-SERVER/CFX-SHARED "
        "(a few names such as `GetEntityCoords` exist on both sides with different parameters).",
        "",
        "## How to use",
        "",
        "- Grep this folder (`grep -n \"SetVehicleFuel\" assets/natives/*.md`) or use `python scripts/natives.py search|show`.",
        "- Curated, task-grouped list with pitfalls: [references/natives-essentials.md](../../references/natives-essentials.md).",
        "",
        "## Sources",
        "",
        f"- GTA V natives: {nv.SOURCES['gta']}",
        f"- CFX natives: {nv.SOURCES['cfx']}",
        "- Native docs: https://docs.fivem.net/natives/ · DB source: https://github.com/citizenfx/natives",
        "- Lua codegen (naming / pointer rules): https://github.com/citizenfx/fivem/blob/master/ext/natives/codegen_out_lua.lua",
    ]
    return "\n".join(out) + "\n"


def _safe_console():
    """Never crash on consoles that cannot encode a character (Windows cp1252, redirected pipes)."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass


def main() -> int:
    _safe_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent.parent / "assets" / "natives"))
    ap.add_argument("--refresh", action="store_true", help="re-download the native DBs")
    args = ap.parse_args()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        data, fetched_ts = load_raw(args.refresh)
    except Exception as exc:  # network / JSON errors
        print(f"[catalog] cannot load native DB: {exc}", file=sys.stderr)
        return 2
    fetched = time.strftime("%Y-%m-%d", time.localtime(fetched_ts))

    pages = {}  # filename stem -> (side, [natives], blurb)
    for ns, items in data["gta"].items():
        pages[ns] = ("client", list(items.values()), f"GTA V `{ns}` namespace.")
    for side, stem in CFX_FILES.items():
        pages[stem] = (side, [], f"CitizenFX (FiveM-specific) natives, apiset `{side}`.")
    for ns, items in data["cfx"].items():
        for n in items.values():
            side = n.get("apiset") or "shared"
            pages[CFX_FILES.get(side, "CFX-SHARED")][1].append(n)

    rows = []
    total = unnamed_total = 0
    for stem in sorted(pages, key=lambda s: (s.startswith("CFX"), s)):
        side, items, blurb = pages[stem]
        fname = f"{stem}.md"
        with (out_dir / fname).open('w', encoding='utf-8', newline='\n') as target:
            target.write(build_page(stem, side, items, fetched, blurb))
        un = sum(1 for n in items if not n.get("name"))
        rows.append((fname, side, len(items), un))
        total += len(items)
        unnamed_total += un
    with (out_dir / 'README.md').open('w', encoding='utf-8', newline='\n') as target:
        target.write(build_readme(rows, fetched, total, unnamed_total))
    print(f"wrote {len(rows)} namespace files + README.md ({total} natives, {unnamed_total} unnamed) -> {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
