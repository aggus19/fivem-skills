#!/usr/bin/env python3
"""Static security / performance / compatibility audit for FiveM resources.

Heuristic scanner: it finds *candidates* for review, it does not prove a bug.
Every finding must be confirmed by reading the code (see references/audit-checklist.md).
Scans code (.lua/.js/.ts/.tsx/.jsx/.vue/.svelte/.cs), fxmanifest.lua, *.cfg files and known dropper file names.

Usage:
  python audit.py <resource_or_resources_dir> [--min low|medium|high|critical] [--json]

Exit code: 0 = no high/critical findings, 1 = high/critical findings, 2 = usage error.
Standard library only (Python 3.8+).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

SEV = {"low": 0, "medium": 1, "high": 2, "critical": 3}
SKIP_DIRS = {"node_modules", ".git", "dist", "build", ".next", "stream"}
CODE_EXT = {".lua", ".js", ".ts", ".cs", ".tsx", ".jsx", ".mjs", ".cjs", ".vue", ".svelte"}
CFG_EXT = {".cfg"}
# File names dropped by known backdoor families (Blum/Cipher, 2026). Legit tooling uses babel.config.js etc.
DROPPER_NAMES = {"yarn_builder.js", "webpack_builder.js", "babel_config.js"}


@dataclass
class Finding:
    severity: str
    rule: str
    file: str
    line: int
    message: str
    snippet: str


# (rule id, severity, applies-to side: "any"|"server"|"client", regex, message)
LINE_RULES = [
    # --- backdoors / remote code execution -------------------------------------------------
    ("rce-load-http", "critical", "any",
     r"PerformHttpRequest\s*\([^)]*\)[\s\S]{0,0}|PerformHttpRequest.*\b(load|loadstring)\b",
     "PerformHttpRequest combined with load(): classic FiveM backdoor (remote code execution)."),
    ("rce-load", "high", "any", r"(?<![\w.])(load|loadstring|dofile|loadfile)\s*\(",
     "Dynamic code loading. Legit uses are rare; check the source of the string being loaded."),
    ("rce-assert-load", "critical", "any", r"assert\s*\(\s*load\s*\(",
     "assert(load(...)) pattern: very common in leaked/obfuscated backdoors."),
    ("os-exec", "critical", "server", r"\b(os\.execute|io\.popen|os\.remove|os\.rename)\s*\(",
     "Shell / filesystem access from a resource."),
    ("node-child-process", "critical", "server", r"require\s*\(\s*['\"](child_process|vm)['\"]\s*\)|\beval\s*\(|new\s+Function\s*\(",
     "Node child_process / eval / new Function: arbitrary code execution vector."),
    ("obfuscation-hex", "high", "any", r"(\\x[0-9a-fA-F]{2}){12,}",
     "Long hex-escaped string: typical obfuscation used to hide backdoors."),
    ("obfuscation-bytes", "high", "any", r"(\\\d{2,3}){16,}|string\.char\s*\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*\d+",
     "Byte-escaped string / string.char chain: possible obfuscated payload."),
    ("known-backdoor", "critical", "any",
     r"cipher-panel|ciphercheats|ciphercorp|blum-panel|warden-panel|gfxpanel|\bhelpCode\b|\bhelpEmptyCode\b"
     r"|_G\s*\[\s*['\"]\\x|\bmiauss?\b|GlobalState\s*[.\[]\s*['\"]?ggWP\b|\bbertjj\b|JohnsUrUncle"
     r"|9ns1\.com|fivems\.lt|jking\.lt|giithub\.net|2ns3\.net|kutingplays",
     "Matches a known FiveM backdoor signature (Cipher / Blum / Warden / GFX panel family)."),
    ("js-charcode-decoder", "high", "any",
     r"fromCharCode\s*\([^)]*\^|fromCharCode\s*\(\s*(\d+\s*,\s*){8,}|charCodeAt\s*\([^)]*\)\s*\^",
     "Char-code / XOR string decoder: typical obfuscation of JS backdoor stagers."),
    ("js-raw-network", "medium", "server", r"require\s*\(\s*['\"](node:)?(https?|net|dgram|tls)['\"]\s*\)",
     "Raw Node network module in server JS: verify the destination (droppers fetch second-stage code this way)."),
    ("write-manifest", "critical", "any",
     r"(SaveResourceFile|writeFile(Sync)?|appendFile(Sync)?)\s*\([^\n]*(fxmanifest|__resource|server\.cfg)",
     "Code writes fxmanifest.lua / server.cfg: self-replicating backdoor behaviour."),
    ("save-other-resource", "medium", "server",
     r"SaveResourceFile\s*\(\s*(?!GetCurrentResourceName\s*\(|cache\.resource\b)",
     "SaveResourceFile with a target that may not be this resource: confirm it cannot write into other resources."),
    ("ace-from-code", "high", "server", r"ExecuteCommand\s*\([^)]*\b(add_ace|add_principal|remove_principal)\b",
     "Permissions changed from code: confirm the principal/identifier can never be client-controlled."),
    ("execute-command", "high", "server", r"\bExecuteCommand\s*\(",
     "ExecuteCommand on the server: make sure no client-controlled data reaches it."),
    ("http-exfil", "medium", "server", r"PerformHttpRequest\s*\(\s*['\"]https?://(?!api\.fivemanage\.com|discord\.com/api/webhooks)",
     "Outbound HTTP request: verify destination and that no secrets/license keys are sent."),
    ("convar-secret", "medium", "server", r"GetConvar\s*\(\s*['\"](sv_licenseKey|rcon_password|mysql_connection_string|sv_tebexSecret|steam_webApiKey)",
     "Reading a secret convar: make sure it is never sent to clients or HTTP endpoints."),
    # --- SQL --------------------------------------------------------------------------------
    ("sql-concat", "critical", "server",
     r"(MySQL\.[\w.]+|exports\.oxmysql:\w+|oxmysql:\w+)\s*\(\s*('[^']*'|\"[^\"]*\"|\[\[[\s\S]*?\]\])\s*\.\.",
     "SQL built with string concatenation: SQL injection. Use ? / @named placeholders."),
    ("sql-format", "critical", "server", r"(MySQL\.[\w.]+)\s*\(\s*\(?\s*('[^']*%s|\"[^\"]*%s)|string\.format\s*\(\s*['\"]\s*(SELECT|INSERT|UPDATE|DELETE)",
     "SQL built with string.format/%s: SQL injection. Use placeholders."),
    ("sql-template-literal", "critical", "server",
     r"\b(query|execute|insert|update|scalar|single|prepare|rawExecute)\s*\(\s*`[^`]*\$\{",
     "SQL built with a JS template literal: SQL injection. Use ? placeholders and a parameter array."),
    ("sql-mysql-async", "medium", "any", r"@mysql-async|MySQL\.Async\.|MySQL\.Sync\.|@ghmattimysql",
     "mysql-async / ghmattimysql are deprecated: use oxmysql (MySQL.query.await, MySQL.insert.await ...)."),
    # --- trust boundary ---------------------------------------------------------------------
    ("client-money-event", "high", "client",
     r"TriggerServerEvent\s*\(\s*['\"][^'\"]*(money|cash|bank|pay|reward|salary|addItem|giveItem|additem|giveitem|sell|buy)[^'\"]*['\"]\s*,[^)]*\d",
     "Client sends an economic action with a numeric value: server must compute prices/amounts itself."),
    ("client-trusted-price", "high", "client", r"TriggerServerEvent\s*\([^)]*\b(price|amount|count|reward|payout)\b",
     "Client sends price/amount: never trust it, recalculate server-side."),
    ("server-event-giveitem", "medium", "server",
     r"(AddMoney|addMoney|addAccountMoney|AddItem|addInventoryItem|ox_inventory:AddItem|exports\.ox_inventory:AddItem)\s*\(",
     "Economy mutation: confirm the triggering path validates source, distance, job, cooldown and amounts."),
    ("deprecated-register-server-event", "low", "server", r"\bRegisterServerEvent\s*\(",
     "RegisterServerEvent is legacy: use RegisterNetEvent (and validate `source`)."),
    ("client-setcoords-from-net", "medium", "server", r"SetEntityCoords\s*\(\s*GetPlayerPed\s*\(\s*source",
     "Teleporting a player on a client request: validate destination server-side."),
    ("webhook-exposed", "high", "client", r"discord(app)?\.com/api/webhooks/\d+",
     "Discord webhook URL in a client/shared file: every player downloads it. Keep webhooks in server convars."),
    ("client-replicated-statebag", "medium", "client", r"\.state\s*:\s*set\s*\([^)]*,\s*true\s*\)",
     "Client writes a replicated state bag: the server must not trust it; blocked under sv_stateBagStrictMode."),
    ("nui-unsafe-html", "medium", "client",
     r"\.innerHTML\s*\+?=|dangerouslySetInnerHTML|\bv-html\b|\{@html\b|[\w)\]]\.html\([^)\s]",
     "Raw HTML injection in NUI: escape player-controlled text (XSS inside the game client)."),
    ("nui-to-server-direct", "medium", "client", r"RegisterNUICallback[\s\S]{0,0}.*TriggerServerEvent",
     "NUI callback forwards data straight to the server: validate everything on the server."),
    # --- deprecated / legacy APIs -----------------------------------------------------------
    ("esx-getsharedobject-event", "medium", "any", r"TriggerEvent\s*\(\s*['\"]esx:getSharedObject",
     "Legacy ESX pattern. Use `shared_script '@es_extended/imports.lua'` or exports.es_extended:getSharedObject()."),
    ("getplayerped-minus1", "low", "client", r"GetPlayerPed\s*\(\s*-1\s*\)",
     "GetPlayerPed(-1): prefer PlayerPedId() or ox_lib `cache.ped`."),
    ("citizen-prefix", "low", "any", r"Citizen\.(Wait|CreateThread|SetTimeout)\s*\(",
     "Citizen.* prefix is unnecessary: use Wait / CreateThread / SetTimeout."),
    ("getplayers-loop-identifiers", "low", "server", r"GetPlayerIdentifiers\s*\(",
     "Prefer GetPlayerIdentifierByType(src, 'license') over iterating identifiers."),
    ("qb-getcoreobject-in-loop", "low", "any", r"while[\s\S]{0,40}GetCoreObject",
     "Fetch the core object once at file scope, not inside loops."),
    # --- performance --------------------------------------------------------------------------
    ("wait-zero-loop", "medium", "client", r"\bWait\s*\(\s*0\s*\)",
     "Wait(0) runs every frame. Only acceptable while drawing/handling input; use dynamic sleep otherwise."),
    ("draw-marker-everywhere", "low", "client", r"\bDrawMarker\s*\(",
     "DrawMarker every frame: gate by distance, or use ox_lib points/zones / ox_target."),
    ("get-closest-loop", "low", "client", r"GetGamePool\s*\(\s*['\"]CPed",
     "Iterating the whole ped pool: cache and throttle, or use lib.getClosest* helpers."),
]

MANIFEST_RULES = [
    ("manifest-legacy", "high", r"resource_manifest_version", "Legacy __resource.lua style manifest: migrate to fxmanifest.lua (fx_version 'cerulean')."),
    ("manifest-old-fxversion", "medium", r"fx_version\s+['\"](adamant|bodacious)['\"]", "Old fx_version: use 'cerulean'."),
    ("manifest-node16", "medium", r"node_version\s+['\"]16['\"]", "node_version '16': Node 16 was removed from FXServer (2026); use '22' or omit."),
    ("manifest-mysql-async", "medium", r"@mysql-async|@ghmattimysql", "Deprecated DB wrapper in manifest: use '@oxmysql/lib/MySQL.lua'."),
    ("manifest-no-game", "medium", r"\A(?![\s\S]*\bgames?\s*[\s{(]*['\"](gta5|rdr3|common)['\"])", "`game 'gta5'` missing."),
]


def side_for(rel: str) -> str:
    p = rel.replace("\\", "/").lower()
    if re.search(r"(^|/)(server|sv)([/_.]|$)|sv_[^/]*$|_server\.\w+$|server\.\w+$", p):
        return "server"
    if re.search(r"(^|/)(client|cl)([/_.]|$)|cl_[^/]*$|_client\.\w+$|client\.\w+$|(^|/)(web|html|ui|nui)/", p):
        return "client"
    return "shared"


def iter_files(root: Path):
    for f in root.rglob("*"):
        if f.is_file() and not (set(f.parts) & SKIP_DIRS) and f.suffix.lower() in CODE_EXT:
            yield f


def _block(lines: list[str], i: int) -> list[str]:
    """Lines of the block opened at line i (rough Lua do/function/if ... end matching)."""
    depth = 0
    out = []
    for line in lines[i:i + 400]:
        code = re.sub(r"(['\"]).*?\1", "", line.split("--", 1)[0])
        depth += len(re.findall(r"\b(do|then|function)\b", code)) - len(re.findall(r"\belseif\b", code))
        depth -= len(re.findall(r"\bend\b", code))
        out.append(line)
        if depth <= 0:
            break
    return out


def scan_wait_loops(text: str, rel: str, out: list[Finding]):
    """while true loops with no Wait/yield inside -> client freeze / server hitch."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if re.search(r"\bwhile\s+true\s+do\b", line.split("--", 1)[0]):
            body = "\n".join(_block(lines, i))
            if not re.search(r"\b(Wait|Citizen\.Wait|coroutine\.yield|lib\.waitFor)\s*\(", body):
                out.append(Finding("high", "loop-without-wait", rel, i + 1,
                                   "`while true do` without Wait(): will freeze the game/server thread.", line.strip()[:160]))


def scan_net_handlers(text: str, rel: str, out: list[Finding]):
    """Server net events that never reference `source` are suspicious (no caller validation)."""
    for m in re.finditer(r"RegisterNetEvent\s*\(\s*['\"]([^'\"]+)['\"]\s*,\s*function\s*\(([^)]*)\)", text):
        start = m.end()
        body = text[start:start + 2500]
        end = re.search(r"\n\S*end\)", body)
        body = body[: end.start()] if end else body
        if "source" not in body:
            line = text.count("\n", 0, m.start()) + 1
            out.append(Finding("medium", "net-event-no-source", rel, line,
                               f"Net event '{m.group(1)}' never uses `source`: who is allowed to call it?",
                               m.group(0)[:160]))


CFG_RULES = [
    ("cfg-public-secret", "high",
     r"^\s*(setr|sets)\s+\S*(key|secret|token|webhook|password|passwd|connection_string)\S*\s",
     "Secret-looking convar set with setr/sets: replicated to clients or public in server info. Use `set`."),
    ("cfg-lockdown-inactive", "medium", r"^\s*set[rs]?\s+sv_entityLockdown\s+['\"]?inactive",
     "sv_entityLockdown inactive: clients may create any networked entity. Prefer strict (or relaxed)."),
    ("cfg-statebag-not-strict", "low", r"^\s*set[rs]?\s+sv_stateBagStrictMode\s+['\"]?(false|0)\b",
     "sv_stateBagStrictMode disabled: clients can write replicated state bags."),
    ("cfg-scripthook-allowed", "medium", r"^\s*set[rs]?\s+sv_scriptHookAllowed\s+['\"]?(true|1)\b",
     "sv_scriptHookAllowed enabled: clients may load ScriptHookV mods (cheat vector)."),
]


def scan_cfg(root: Path, out: list[Finding]):
    """server.cfg-style files: secrets in replicated/public convars, weak OneSync security settings."""
    files = [root] if root.is_file() else root.rglob("*")
    for f in files:
        if not (f.is_file() and f.suffix.lower() in CFG_EXT) or (set(f.parts) & SKIP_DIRS):
            continue
        rel = f.name if root.is_file() else str(f.relative_to(root))
        for ln, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            code = line.split("#", 1)[0]
            for rid, sev, rx, msg in CFG_RULES:
                if re.search(rx, code, re.I):
                    out.append(Finding(sev, rid, rel, ln, msg, line.strip()[:160]))


def scan_dropper_names(root: Path, out: list[Finding]):
    for f in root.rglob("*"):
        if f.is_file() and f.name.lower() in DROPPER_NAMES and not (set(f.parts) & SKIP_DIRS):
            out.append(Finding("critical", "known-backdoor", str(f.relative_to(root)), 1,
                               "File name matches a known backdoor dropper (Blum/Cipher family).", f.name))


def audit(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    compiled = [(rid, sev, side, re.compile(rx, re.I if rid.startswith("client-") else 0), msg) for rid, sev, side, rx, msg in LINE_RULES]
    manifests = list(root.rglob("fxmanifest.lua")) + list(root.rglob("__resource.lua"))
    manifests = [m for m in manifests if not (set(m.parts) & SKIP_DIRS)]
    for mf in manifests:
        text = mf.read_text(encoding="utf-8", errors="replace")
        rel = str(mf.relative_to(root))
        for rid, sev, rx, msg in MANIFEST_RULES:
            if re.search(rx, text, re.M):
                findings.append(Finding(sev, rid, rel, 1, msg, ""))
        if mf.name == "__resource.lua":
            findings.append(Finding("high", "manifest-legacy", rel, 1, "__resource.lua is deprecated: use fxmanifest.lua.", ""))
    scan_cfg(root, findings)
    if root.is_dir():
        scan_dropper_names(root, findings)
    for f in iter_files(root):
        if f.name in ("fxmanifest.lua", "__resource.lua"):
            continue
        rel = str(f.relative_to(root))
        side = side_for(rel)
        text = f.read_text(encoding="utf-8", errors="replace")
        handles_net = bool(re.search(r"RegisterNetEvent|lib\.callback\.register|RegisterServerCallback|CreateCallback|onNet\(", text))
        for ln, line in enumerate(text.splitlines(), 1):
            code = line.split("--", 1)[0] if f.suffix == ".lua" else line
            if not code.strip():
                continue
            for rid, sev, rside, rx, msg in compiled:
                if rside != "any" and side not in (rside, "shared"):
                    continue
                if rid == "server-event-giveitem" and (not handles_net or re.match(r"\s*(local\s+)?function\b", code)):
                    continue
                if rside != "any" and side == "shared" and rside == "client" and rid.startswith("client-"):
                    continue
                if rx.search(code):
                    findings.append(Finding(sev, rid, rel, ln, msg, line.strip()[:160]))
        if len(max(text.splitlines() or [""], key=len)) > 3000:
            findings.append(Finding("high", "minified-or-obfuscated", rel, 1,
                                    "Very long single line: minified/obfuscated code. Unreviewable in a resource.", ""))
        if f.suffix == ".lua":
            scan_wait_loops(text, rel, findings)
            if side in ("server", "shared"):
                scan_net_handlers(text, rel, findings)
    # rce-load-http first alternative is a no-op guard; keep only true combos
    findings = [x for x in findings if not (x.rule == "rce-load-http" and not re.search(r"\bload(string)?\b", x.snippet))]
    return findings


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path")
    ap.add_argument("--min", default="low", choices=list(SEV))
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    root = Path(a.path)
    if not root.exists():
        print(f"not found: {root}", file=sys.stderr)
        return 2
    res = [f for f in audit(root) if SEV[f.severity] >= SEV[a.min]]
    res.sort(key=lambda f: (-SEV[f.severity], f.file, f.line))
    if a.json:
        print(json.dumps([asdict(f) for f in res], indent=2))
    else:
        for f in res:
            print(f"[{f.severity.upper():8}] {f.rule:34} {f.file}:{f.line}\n           {f.message}\n           > {f.snippet}")
        counts = {s: sum(1 for f in res if f.severity == s) for s in SEV}
        print(f"\nSummary: {counts}  (heuristic: confirm each finding manually)")
    return 1 if any(SEV[f.severity] >= 2 for f in res) else 0


if __name__ == "__main__":
    sys.exit(main())
