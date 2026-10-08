#!/usr/bin/env python3
"""Create a new FiveM resource from the skill templates.

The default is dependency-free Lua. The explicit ox-shop profile adds ox_lib,
oxmysql and an example framework bridge; purchases require project integration.

Usage:
  python scaffold.py <resource_name> [--profile minimal|ox-shop] [--out DIR] [--nui]

Examples:
  python scaffold.py my_shop --profile ox-shop --out ./resources/[custom]
  python scaffold.py police_mdt --nui --author "Team" --description "MDT"

Standard library only (Python 3.8+).
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATES = HERE.parent / "assets" / "templates"
TEXT_EXT = {".lua", ".json", ".lock", ".md", ".sql", ".ts", ".tsx", ".html", ".css", ".yml", ".toml", ""}
RESERVED_PREFIXES = ("ox_", "qbx_", "esx_", "qb-", "es_")
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,47}$")


def strip_lua_comments(text: str) -> str:
    """Drop Lua comments from generated code: shipped files (client downloads, server dumps) must not explain logic."""
    out, i, n = [], 0, len(text)
    while i < n:
        if text.startswith("--", i):
            m = re.match(r"--\[(=*)\[", text[i:i + 64])
            if m:
                end = text.find("]" + m.group(1) + "]", i + len(m.group(0)))
                i = n if end < 0 else end + len(m.group(1)) + 2
            else:
                end = text.find("\n", i)
                i = n if end < 0 else end
            continue
        c = text[i]
        if c in "\"'":
            j = i + 1
            while j < n and text[j] != c and text[j] != "\n":
                j += 2 if text[j] == "\\" else 1
            out.append(text[i:j + 1])
            i = j + 1
            continue
        if c == "[":
            m = re.match(r"\[(=*)\[", text[i:i + 64])
            if m:
                end = text.find("]" + m.group(1) + "]", i + len(m.group(0)))
                end = n if end < 0 else end + len(m.group(1)) + 2
                out.append(text[i:end])
                i = end
                continue
        out.append(c)
        i += 1
    stripped = [line.rstrip() for line in "".join(out).split("\n")]
    original = text.split("\n")
    kept = [line for line, orig in zip(stripped, original) if line.strip() or not orig.strip()]
    collapsed = []
    for line in kept:
        if not line.strip() and collapsed and not collapsed[-1].strip():
            continue
        collapsed.append(line)
    return "\n".join(collapsed).strip("\n") + "\n"


def render(path: Path, values: dict[str, str], nui: bool, keep_comments: bool = False) -> None:
    if path.suffix not in TEXT_EXT:
        return
    text = path.read_text(encoding="utf-8")
    def replacement(match):
        value = values.get(match[1], match[0])
        if path.name == 'fxmanifest.lua':
            value = (value.replace('\\', '\\\\').replace("'", "\\'")
                     .replace('\r', '\\r').replace('\n', '\\n').replace('\t', '\\t'))
        return value
    text = re.sub(r'\{\{(\w+)\}\}', replacement, text)
    if path.name == "fxmanifest.lua":
        out = []
        for line in text.splitlines():
            if line.rstrip().endswith("-- @nui"):
                if not nui:
                    continue
                line = line.rstrip()[: -len("-- @nui")].rstrip()
            out.append(line)
        text = "\n".join(out) + "\n"
    elif path.suffix == ".lua" and not keep_comments:
        text = strip_lua_comments(text)
    path.write_text(text, encoding="utf-8")


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
    ap.add_argument("name")
    ap.add_argument("--out", default=".")
    ap.add_argument("--profile", choices=("minimal", "ox-shop"), default="minimal",
                    help="minimal: no dependencies (default); ox-shop: opt-in economy integration example")
    ap.add_argument("--nui", action="store_true", help="add a React 19 + Vite 8 + TypeScript NUI in web/")
    ap.add_argument("--author", default="you")
    ap.add_argument("--description", default="FiveM resource")
    ap.add_argument("--force", action="store_true", help="overwrite an existing folder")
    ap.add_argument("--keep-comments", action="store_true",
                    help="keep the template's explanatory Lua comments (learning only; never ship them)")
    a = ap.parse_args()

    if not NAME_RE.match(a.name):
        print("error: resource name must be lowercase letters, digits, '-' or '_' (2-48 chars)", file=sys.stderr)
        return 2
    if a.name.startswith(RESERVED_PREFIXES):
        print(f"warning: '{a.name}' uses a prefix reserved by another ecosystem ({', '.join(RESERVED_PREFIXES)})",
              file=sys.stderr)

    output_root = Path(a.out).resolve()
    dest = output_root / a.name
    # Verify the actual target before any recursive deletion, including Windows junctions.
    if dest.is_symlink() or dest.resolve() != dest:
        print(f"error: refusing to replace linked resource directory {dest}", file=sys.stderr)
        return 2
    if dest.exists():
        if not a.force:
            print(f"error: {dest} already exists (use --force to overwrite)", file=sys.stderr)
            return 2
        if not dest.is_dir() or dest.resolve().parent != output_root:
            print(f"error: unsafe overwrite target {dest}", file=sys.stderr)
            return 2
        shutil.rmtree(dest)

    template = "resource-minimal" if a.profile == "minimal" else "resource-lua"
    shutil.copytree(TEMPLATES / template, dest)
    if not a.nui and (dest / "client" / "nui.lua").exists():
        (dest / "client" / "nui.lua").unlink()
    if a.nui:
        shutil.copy2(TEMPLATES / "resource-lua" / "client" / "nui.lua", dest / "client" / "nui.lua")
        shutil.copytree(TEMPLATES / "nui-react-vite", dest / "web", ignore=shutil.ignore_patterns("node_modules", "dist"))

    values = {"RESOURCE_NAME": a.name, "AUTHOR": a.author, "DESCRIPTION": a.description}
    for f in dest.rglob("*"):
        if f.is_file():
            render(f, values, a.nui, a.keep_comments)

    print(f"created {dest}")
    print("next steps:")
    if a.profile == "ox-shop":
        print("  Review README integration requirements; example purchases are disabled until recovery is wired.")
        print(f"  1. add `ensure {a.name}` to server.cfg (after oxmysql, ox_lib and your framework)")
    else:
        print(f"  1. implement your feature, then add `ensure {a.name}` to server.cfg; no library dependencies.")
    if a.nui:
        print(f"  2. in {dest / 'web'}: bun install --frozen-lockfile; bun run --bun build (or adopt npm with one reviewed lockfile).")
    print(f"  3. python {HERE / 'manifest.py'} {dest}")
    print(f"  4. python {HERE / 'audit.py'} {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
