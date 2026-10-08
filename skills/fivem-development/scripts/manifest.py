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

# Also works with python -I; imports only this script's installed sibling helper.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from resource_files import LIST_DIRECTIVES, ManifestError, glob_match, parse_manifest

DEP_DIRECTIVES = {"dependency", "dependencies"}
# '@resource/...' imports that are commonly used without a `dependency` line; still recommended.
COMMON_IMPORTS = {"ox_lib", "oxmysql", "es_extended", "qbx_core", "qb-core", "ox_core"}

def parse(text: str) -> dict[str, list[str]]:
    return parse_manifest(text)


def check(res: Path) -> tuple[list[str], list[str]]:
    errors, warns = [], []
    mf = res / "fxmanifest.lua"
    if not mf.exists():
        if (res / "__resource.lua").exists():
            return ["__resource.lua is deprecated; create fxmanifest.lua (fx_version 'cerulean')"], []
        return [f"no fxmanifest.lua in {res}"], []
    try:
        d = parse(mf.read_text(encoding="utf-8-sig"))
    except (ManifestError, OSError, UnicodeError) as exc:
        return [f"cannot statically validate manifest: {exc}"], []

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
    resolved = {}
    for key in LIST_DIRECTIVES:
        for entry in d.get(key, []):
            if entry.startswith('@'):
                continue
            try:
                resolved[entry] = glob_match(res, entry)
            except (ManifestError, ValueError, OSError) as exc:
                errors.append(f"{key}: {exc}")
                resolved[entry] = []
    server_paths = {p.resolve() for key in ('server_script', 'server_scripts')
                    for entry in d.get(key, []) for p in resolved.get(entry, [])}
    server_only = (d.get('server_only') or [''])[0].lower() in ('yes', 'true', '1')
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
            matches = resolved.get(entry, [])
            if not matches:
                errors.append(f"{kind}: '{entry}' matches no file")
                continue
            for path in matches:
                rel = path.relative_to(res.resolve()).as_posix()
                low = rel.lower()
                server_name = re.search(r"(^|/)(server|sv)([/_.]|$)|(^|/)sv_|_server\.\w+$", low)
                if not server_only and kind in ('client', 'shared', 'files') and (server_name or path.resolve() in server_paths):
                    errors.append(f"{kind}: '{entry}' exposes server file '{rel}' to clients; review download contents")
                if kind == 'server' and re.search(r"(^|/)(client|cl)([/_.]|$)|(^|/)cl_", low):
                    warns.append(f"server script '{rel}' looks client-side")

    ui = (d.get("ui_page") or [None])[0]
    if ui:
        if ui.startswith(("http://", "https://")):
            warns.append(f"ui_page is a remote URL ({ui}); fine for dev servers, ship built files for production")
        else:
            try:
                pages = glob_match(res, ui)
            except (ManifestError, ValueError, OSError) as exc:
                return errors + [f"ui_page: {exc}"], warns
            if len(pages) != 1:
                errors.append(f"ui_page '{ui}' does not exist or is ambiguous (build the NUI with the project's package manager)")
                return errors, warns
            file_entries = d.get("file", []) + d.get("files", [])
            covered = any(pages[0].resolve() in [p.resolve() for p in resolved.get(f, [])] for f in file_entries)
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
