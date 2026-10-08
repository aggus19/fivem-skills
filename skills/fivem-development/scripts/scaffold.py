#!/usr/bin/env python3
"""Create a new FiveM resource from the skill templates.

The generated resource uses ox_lib + oxmysql and a framework bridge that auto-detects
Qbox / ESX / QBCore / standalone at runtime (override with the `<name>:framework` convar).

Usage:
  python scaffold.py <resource_name> [--out DIR] [--nui] [--author NAME] [--description TEXT] [--force]

Examples:
  python scaffold.py my_shop --out ./resources/[custom]
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
TEXT_EXT = {".lua", ".json", ".md", ".sql", ".ts", ".tsx", ".html", ".css", ".yml", ".toml", ""}
RESERVED_PREFIXES = ("ox_", "qbx_", "esx_", "qb-", "es_")
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,47}$")


def render(path: Path, values: dict[str, str], nui: bool) -> None:
    if path.suffix not in TEXT_EXT:
        return
    text = path.read_text(encoding="utf-8")
    for k, v in values.items():
        text = text.replace("{{" + k + "}}", v)
    if path.name == "fxmanifest.lua":
        out = []
        for line in text.splitlines():
            if line.rstrip().endswith("-- @nui"):
                if not nui:
                    continue
                line = line.rstrip()[: -len("-- @nui")].rstrip()
            out.append(line)
        text = "\n".join(out) + "\n"
    path.write_text(text, encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("name")
    ap.add_argument("--out", default=".")
    ap.add_argument("--nui", action="store_true", help="add a React 19 + Vite 8 + TypeScript NUI in web/")
    ap.add_argument("--author", default="you")
    ap.add_argument("--description", default="FiveM resource")
    ap.add_argument("--force", action="store_true", help="overwrite an existing folder")
    a = ap.parse_args()

    if not NAME_RE.match(a.name):
        print("error: resource name must be lowercase letters, digits, '-' or '_' (2-48 chars)", file=sys.stderr)
        return 2
    if a.name.startswith(RESERVED_PREFIXES):
        print(f"warning: '{a.name}' uses a prefix reserved by another ecosystem ({', '.join(RESERVED_PREFIXES)})",
              file=sys.stderr)

    dest = Path(a.out) / a.name
    if dest.exists():
        if not a.force:
            print(f"error: {dest} already exists (use --force to overwrite)", file=sys.stderr)
            return 2
        shutil.rmtree(dest)

    shutil.copytree(TEMPLATES / "resource-lua", dest)
    if not a.nui:
        (dest / "client" / "nui.lua").unlink()
    else:
        shutil.copytree(TEMPLATES / "nui-react-vite", dest / "web", ignore=shutil.ignore_patterns("node_modules", "dist"))

    values = {"RESOURCE_NAME": a.name, "AUTHOR": a.author, "DESCRIPTION": a.description}
    for f in dest.rglob("*"):
        if f.is_file():
            render(f, values, a.nui)

    print(f"created {dest}")
    print("next steps:")
    print(f"  1. add `ensure {a.name}` to server.cfg (after oxmysql, ox_lib and your framework)")
    if a.nui:
        print(f"  2. cd {dest / 'web'} && npm install && npm run build   (ships web/dist)")
    print(f"  3. python {HERE / 'manifest.py'} {dest}")
    print(f"  4. python {HERE / 'audit.py'} {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
