#!/usr/bin/env python3
"""Validate a FiveM fxmanifest.lua against the files on disk.

Checks:
  - fx_version / game present and current; node_version not obsolete
  - every client/server/shared script and `files` glob matches at least one file
  - ui_page exists and is listed in `files` (NUI pages must be streamed to the client)
  - '@other_resource/...' imports have a matching dependency (or are well-known)
  - server-only files listed as client scripts (leaks server code to clients) and vice versa
  - duplicates and deprecated directives

Usage:
  python manifest.py <resource_dir> [<resource_dir> ...]
Exit code: 0 = ok (warnings allowed), 1 = errors, 2 = usage error.
Standard library only (Python 3.8+).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

LIST_DIRECTIVES = {
    "client_script": "client", "client_scripts": "client",
    "server_script": "server", "server_scripts": "server",
    "shared_script": "shared", "shared_scripts": "shared",
    "file": "files", "files": "files",
}
DEP_DIRECTIVES = {"dependency", "dependencies"}
# '@resource/...' imports that are commonly used without a `dependency` line; still recommended.
COMMON_IMPORTS = {"ox_lib", "oxmysql", "es_extended", "qbx_core", "qb-core", "ox_core"}

STR = r"""(?:'([^']*)'|"([^"]*)"|\[\[(.*?)\]\])"""


def strings(chunk: str) -> list[str]:
    return [a or b or c for a, b, c in re.findall(STR, chunk, re.S)]


def parse(text: str) -> dict[str, list[str]]:
    text = re.sub(r"--\[\[.*?\]\]", "", text, flags=re.S)
    text = "\n".join(l.split("--", 1)[0] for l in text.splitlines())
    out: dict[str, list[str]] = {}
    for m in re.finditer(r"\b([a-z_0-9]+)\s*(\{[^}]*\}|\(\s*\{[^}]*\}\s*\)|" + STR + r")", text, re.S):
        key = m.group(1)
        out.setdefault(key, []).extend(strings(m.group(2)))
    return out


def glob_match(root: Path, pattern: str) -> list[Path]:
    pattern = pattern.replace("\\", "/")
    if any(ch in pattern for ch in "*?["):
        return [p for p in root.glob(pattern) if p.is_file()]
    p = root / pattern
    return [p] if p.is_file() else []


def check(res: Path) -> tuple[list[str], list[str]]:
    errors, warns = [], []
    mf = res / "fxmanifest.lua"
    if not mf.exists():
        if (res / "__resource.lua").exists():
            return ["__resource.lua is deprecated; create fxmanifest.lua (fx_version 'cerulean')"], []
        return [f"no fxmanifest.lua in {res}"], []
    d = parse(mf.read_text(encoding="utf-8", errors="replace"))

    fx = (d.get("fx_version") or [""])[0]
    if not fx:
        errors.append("fx_version missing (use 'cerulean')")
    elif fx != "cerulean":
        warns.append(f"fx_version '{fx}' is outdated; use 'cerulean'")
    games = d.get("game", []) + d.get("games", [])
    if not games:
        errors.append("game missing (game 'gta5')")
    # Lua 5.3 was removed from FXServer in 2025-06: `lua54 'yes'` is optional (harmless, kept for old servers).
    if (d.get("node_version") or [""])[0] == "16":
        errors.append("node_version '16' no longer exists (Node 16 removed in 2026); use '22' or omit")
    if "use_experimental_fxv2_oal" in d:
        warns.append("use_experimental_fxv2_oal: vectors are not unpacked; pass .x/.y/.z explicitly to natives")
    if "resource_manifest_version" in d:
        errors.append("resource_manifest_version is legacy (__resource.lua era); remove it")
    for k in ("author", "description", "version"):
        if k not in d:
            warns.append(f"metadata `{k}` missing (recommended)")

    deps = set()
    for k in DEP_DIRECTIVES:
        deps.update(x.split("/")[0] for x in d.get(k, []))

    seen = {}
    for key, kind in LIST_DIRECTIVES.items():
        for entry in d.get(key, []):
            if entry in seen and seen[entry] == kind:
                warns.append(f"duplicate entry '{entry}' in {kind}")
            seen[entry] = kind
            if entry.startswith("@"):
                dep = entry[1:].split("/")[0]
                if dep not in deps:
                    msg = f"'{entry}' imported but `{dep}` not in dependencies"
                    (warns if dep in COMMON_IMPORTS else errors).append(msg + (" (add `dependency '" + dep + "'`)"))
                if dep in ("mysql-async", "ghmattimysql"):
                    errors.append(f"'{entry}': deprecated DB wrapper, use '@oxmysql/lib/MySQL.lua'")
                continue
            matches = glob_match(res, entry)
            if not matches:
                errors.append(f"{kind}: '{entry}' matches no file")
                continue
            low = entry.lower()
            if kind == "client" and re.search(r"(^|/)(server|sv)(/|_)|sv_|server\.lua$", low):
                errors.append(f"client script '{entry}' looks server-only: server code would be sent to every client")
            if kind == "server" and re.search(r"(^|/)(client|cl)(/|_)|cl_|client\.lua$", low):
                warns.append(f"server script '{entry}' looks client-side")
            if kind == "shared" and re.search(r"(^|/)(server|sv)(/|_)", low):
                errors.append(f"shared script '{entry}' looks server-only: it is also sent to clients")

    ui = (d.get("ui_page") or [None])[0]
    if ui:
        if ui.startswith(("http://", "https://")):
            warns.append(f"ui_page is a remote URL ({ui}); fine for dev servers, ship built files for production")
        else:
            if not (res / ui).is_file():
                errors.append(f"ui_page '{ui}' does not exist (did you build the NUI? e.g. `npm run build`)")
                return errors, warns
            file_entries = d.get("file", []) + d.get("files", [])
            covered = any((res / ui).resolve() in [p.resolve() for p in glob_match(res, f)] for f in file_entries)
            if not covered:
                errors.append(f"ui_page '{ui}' is not covered by `files {{ ... }}`: the client will get a blank NUI")
    return errors, warns


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    total_err = 0
    for arg in sys.argv[1:]:
        res = Path(arg)
        errors, warns = check(res)
        print(f"== {res}")
        for e in errors:
            print(f"  ERROR  {e}")
        for w in warns:
            print(f"  WARN   {w}")
        if not errors and not warns:
            print("  OK")
        total_err += len(errors)
    return 1 if total_err else 0


if __name__ == "__main__":
    sys.exit(main())
