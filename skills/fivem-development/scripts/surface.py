#!/usr/bin/env python3
"""Inventory every client-reachable server entry point and what it can mutate.

Deterministic attack-surface map for an audit. It does not decide whether an
endpoint is safe: it enumerates ALL server/shared entry points so that every
auditor (human or model) reviews the same list, and it tags the patterns that
caused real economy exploits so they are never skipped.

Entry points (Lua): RegisterNetEvent (inline and split with AddEventHandler),
RegisterServerEvent + AddEventHandler, lib.callback.register,
ESX.RegisterServerCallback, QBCore.Functions.CreateCallback, custom wrappers
named *.Register*Event/*.Register*Callback, RegisterCommand, ESX.RegisterCommand,
lib.addCommand, exports(...), SetHttpHandler. JS: onNet, exports, RegisterCommand.

Sinks (what the handler can change), followed into same-resource helper
functions up to two calls deep: money, items, vehicles, jobs/permissions, SQL
writes, coords/routing buckets, entity spawns, ExecuteCommand, broadcasts.

Risk tags are heuristics with a fixed meaning (see TAGS); confirm each by
reading the code. Endpoint IDs are stable for the same tree (sorted by path and
line), so ledgers from different runs and different reviewers line up.

Usage:
  python surface.py <server|resources dir|resource> [--json] [--all]
                    [--ledger FILE.md] [--shard K/N] [--only TEXT]
Exit code: 0 = inventory produced, 2 = usage error. Standard library only (Python 3.8+).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from resource_files import ManifestError, nearest_manifest, script_sides, walk_files  # noqa: E402

CODE_EXT = {'.lua', '.js'}

# ---------------------------------------------------------------- masking

def mask_lua(text: str) -> str:
    """Blank comments and string contents (keeps quotes, columns and newlines). Tolerant of bad input."""
    out = list(text)
    i, n = 0, len(text)

    def blank(a, b):
        for k in range(a, b):
            if out[k] != '\n':
                out[k] = ' '

    while i < n:
        c = text[i]
        if text.startswith('--', i):
            m = re.match(r'\[(=*)\[', text[i + 2:i + 2 + 64])
            if m:
                end = text.find(']' + m.group(1) + ']', i + 2 + len(m.group(0)))
                end = n if end < 0 else end + len(m.group(1)) + 2
            else:
                end = text.find('\n', i)
                end = n if end < 0 else end
            blank(i, end)
            i = end
            continue
        if c == '[':
            m = re.match(r'\[(=*)\[', text[i:i + 64])
            if m:
                end = text.find(']' + m.group(1) + ']', i + len(m.group(0)))
                end = n if end < 0 else end + len(m.group(1)) + 2
                blank(i + 1, max(i + 1, end - 1))
                i = end
                continue
        if c in '"\'`':
            j = i + 1
            while j < n and text[j] != c and text[j] != '\n':
                j += 2 if text[j] == '\\' else 1
            blank(i + 1, min(j, n))
            i = j + 1
            continue
        i += 1
    return ''.join(out)


def mask_js(text: str) -> str:
    out = list(text)
    i, n = 0, len(text)

    def blank(a, b):
        for k in range(a, b):
            if out[k] != '\n':
                out[k] = ' '

    while i < n:
        if text.startswith('//', i):
            end = text.find('\n', i)
            end = n if end < 0 else end
            blank(i, end)
            i = end
            continue
        if text.startswith('/*', i):
            end = text.find('*/', i + 2)
            end = n if end < 0 else end + 2
            blank(i, end)
            i = end
            continue
        c = text[i]
        if c in '"\'`':
            j = i + 1
            while j < n and text[j] != c and (c == '`' or text[j] != '\n'):
                j += 2 if text[j] == '\\' else 1
            blank(i + 1, min(j, n))
            i = j + 1
            continue
        i += 1
    return ''.join(out)

# ---------------------------------------------------------------- blocks

LUA_OPEN = re.compile(r'\b(function|if|do|repeat)\b')
LUA_CLOSE = re.compile(r'\b(end|until)\b')
LUA_TOKEN = re.compile(r'\b(function|if|do|repeat|end|until)\b')


def lua_block_end(masked: str, start: int) -> int:
    """Index just past the `end` matching the block opened at/after `start` (a `function` keyword)."""
    depth = 0
    for m in LUA_TOKEN.finditer(masked, start):
        if LUA_OPEN.fullmatch(m.group(1)):
            depth += 1
        else:
            depth -= 1
            if depth == 0:
                return m.end()
    return len(masked)


def js_block_end(masked: str, start: int) -> int:
    i = masked.find('{', start)
    if i < 0:
        return len(masked)
    depth = 0
    for k in range(i, len(masked)):
        if masked[k] == '{':
            depth += 1
        elif masked[k] == '}':
            depth -= 1
            if depth == 0:
                return k + 1
    return len(masked)

# ---------------------------------------------------------------- patterns

NAME = r"""['"]([^'"\n]+)['"]"""
LUA_ENTRY = [
    ('net-event', re.compile(r'\bRegisterNetEvent\s*\(\s*' + NAME + r'\s*,\s*')),
    ('callback', re.compile(r'\blib\.callback\.register\s*\(\s*' + NAME + r'\s*,\s*')),
    ('callback', re.compile(r'\bESX\.RegisterServerCallback\s*\(\s*' + NAME + r'\s*,\s*')),
    ('callback', re.compile(r'\b[\w.]*Functions\.CreateCallback\s*\(\s*' + NAME + r'\s*,\s*')),
    ('command', re.compile(r'\b(?:RegisterCommand|ESX\.RegisterCommand)\s*\(\s*' + NAME + r'\s*,\s*')),
    ('command', re.compile(r'\blib\.addCommand\s*\(\s*(?:\{\s*)?' + NAME + r'[^,]*,\s*')),
    ('export', re.compile(r'(?<![\w.:])exports\s*\(\s*' + NAME + r'\s*,\s*')),
    ('http', re.compile(r'\bSetHttpHandler\s*\(\s*()')),
]
# Custom wrappers such as Phone.API.RegisterServerEvent('x', function(src, ...)
LUA_CUSTOM = re.compile(r'\b([\w]+(?:[.:][\w]+)+)\s*\(\s*' + NAME + r'\s*,\s*(?=function\b)')
CUSTOM_NAME = re.compile(r'Register\w*(Event|Callback)|Create\w*Callback|On\w*Event', re.I)
LUA_SPLIT_REG = re.compile(r'\b(?:RegisterNetEvent|RegisterServerEvent)\s*\(\s*' + NAME + r'\s*\)')
LUA_HANDLER = re.compile(r'\bAddEventHandler\s*\(\s*' + NAME + r'\s*,\s*')
JS_ENTRY = [
    ('net-event', re.compile(r'\bonNet\s*\(\s*' + NAME + r'\s*,\s*')),
    ('export', re.compile(r'(?<![\w.])exports\s*\(\s*' + NAME + r'\s*,\s*')),
    ('command', re.compile(r'\bRegisterCommand\s*\(\s*' + NAME + r'\s*,\s*')),
]

SINKS = [
    ('money+', re.compile(r'[.:](addAccountMoney|addMoney|AddMoney|addBank)\s*\(|Functions\.AddMoney\s*\(')),
    ('money-', re.compile(r'[.:](removeAccountMoney|removeMoney|RemoveMoney|setAccountMoney|setMoney|SetMoney)\s*\(|Functions\.(RemoveMoney|SetMoney)\s*\(')),
    ('item+', re.compile(r'[.:](addInventoryItem|AddItem|GiveItem)\s*\(|Functions\.AddItem\s*\(')),
    ('item-', re.compile(r'[.:](removeInventoryItem|RemoveItem)\s*\(|Functions\.RemoveItem\s*\(')),
    ('vehicle', re.compile(r'[.:](addVehicle|removeVehicle|saveVehicle)\s*\(|owned_vehicles|player_vehicles')),
    ('job/perm', re.compile(r'[.:](setJob|setGroup|SetJob|SetPermission|setPermissionLevel)\s*\(|\badd_(ace|principal)\b|permission_level\s*=[^=]')),
    ('sql-write', re.compile(r'\bMySQL\.(insert|update|execute|prepare|transaction|rawExecute)\b|\bMySQL\.(Async|Sync)\.(execute|insert|store)\b|oxmysql[:.](insert|update|execute|prepare|transaction)\b')),
    ('coords/bucket', re.compile(r'\b(SetPlayerRoutingBucket|SetEntityRoutingBucket|SetEntityCoords)\s*\(|[.:](setRoutingBucket|setCoords)\s*\(')),
    ('spawn', re.compile(r'\b(CreateVehicle|CreateVehicleServerSetter|CreatePed|CreateObject|CreateObjectNoOffset)\s*\(|[.:](SpawnObject|SpawnVehicle|SpawnPed)\s*\(')),
    ('exec', re.compile(r'\bExecuteCommand\s*\(')),
    ('state', re.compile(r'\b(?:Entity|Player)\s*\([^)]*\)\s*\.\s*state\s*(?::\s*set\s*\(|\.\s*\w+\s*=[^=]|\[)|\bstate\s*:\s*set\s*\(')),
    ('broadcast', re.compile(r'\bTriggerClientEvent\s*\(\s*[\'"][^\'"]+[\'"]\s*,\s*-1\b|\bemitNet\s*\(\s*[\'"][^\'"]+[\'"]\s*,\s*-1\b|\bGlobalState\s*[.\[]')),
]
MUTATING = {'money+', 'money-', 'item+', 'item-', 'vehicle', 'job/perm', 'sql-write', 'coords/bucket', 'spawn', 'exec', 'state'}
CREDIT = {'money+', 'item+', 'vehicle'}

TAGS = {
    'client-value-in-sink': 'A value sent by the client reaches a sink argument: validate type, integer, range, ownership.',
    'credit-before-guard': 'Money/items are granted before a later guard (return/ban/time check): validate first, then credit.',
    'unchecked-removal': 'Pays/credits after a removal whose return value is ignored: pay only if the removal succeeded.',
    'no-balance-check': 'Removes money without reading the balance: ESX removeAccountMoney has no floor (accounts go negative).',
    'non-integer-amount': 'Client amount reaches money/items without an integer check: ESX round=true accounts charge 0 for 0.4.',
    'client-position': 'Trusts a client-reported distance/coords/position: compute it on the server.',
    'client-target': 'Acts on another player chosen by the client without a server distance/relationship check.',
    'yield-before-mutation': 'Yields (await/Wait/HTTP/sync SQL) before mutating: race window, check-then-act on stale state.',
    'no-source': 'Net event never reads `source`: who may call it?',
    'not-eq-precedence': '`not x == y` parses as `(not x) == y` (always false for numbers): use `x ~= y`.',
    'fanout': 'Client-callable path broadcasts to every player / writes GlobalState: amplification.',
    'no-rate-limit': 'Mutating client endpoint without any cooldown/rate-limit marker.',
}
GUARD = re.compile(r'\breturn\b|\bBan\s*\(|\bDropPlayer\s*\(|\bos\.time\s*\(|\bGetGameTimer\s*\(|cooldown|players_time', re.I)
YIELD = re.compile(r'\.await\b|\bCitizen\.Await\b|\bAwait\s*\(|\bWait\s*\(|\bCitizen\.Wait\s*\(|\bMySQL\.Sync\.|\bPerformHttpRequestAwait\b|\blib\.callback\.await\b|\bawait\s')
INTEGER_CHECK = re.compile(r'math\.floor|math\.tointeger|math\.type|ParseAmount|ParseInt|isInteger|Number\.isInteger|parseInt|%d|\binteger\b', re.I)
BALANCE_READ = re.compile(r'getAccount\s*\(|getMoney\s*\(|GetMoney\s*\(|PlayerData\.money|\.money\b|TryRemoveMoney|canAfford|hasMoney', re.I)
RATE = re.compile(r'cooldown|rate.?limit|RateLimit|players_time|lastUse|last_use|GetGameTimer|os\.time|busy\[|locks?\[', re.I)
POSITION = re.compile(r'\b(distance\w*|dist|coords|coord|pos|position)\b', re.I)
TARGET = re.compile(r'\b(target\w*|targetId|playerId|closestPlayer|closest\w*|serverId|otherId|receiver|buyer|seller)\b', re.I)
SERVER_DISTANCE = re.compile(r'#\s*\(|GetPlayersDistance|getDistance|Vdist|GetDistanceBetweenCoords|IsNear', re.I)
NOT_EQ = re.compile(r'\bnot\s+[\w.\[\]\'"]+\s*[=~]=')
REMOVAL_CALL = re.compile(r'^\s*(?:[\w.\[\]\'"]+[.:])?(?:removeInventoryItem|RemoveItem)\s*\(|^\s*exports[\w.\[\]\'"]*[.:]RemoveItem\s*\(')
SKIP_PARAMS = {'source', 'src', 'cb', 'callback', 'self', '_', 'resolve', 'reject', 'raw', 'rawCommand', 'args'}
OPAQUE = re.compile(r'(\\\d{2,3}){40}|(\\x[0-9a-fA-F]{2}){40}|^return\s*\(\s*function\s*\(\s*\.\.\.\s*\)')

# ---------------------------------------------------------------- model

class Endpoint:
    __slots__ = ('kind', 'name', 'resource', 'file', 'line', 'side', 'params', 'sinks', 'tags', 'evidence', 'id', 'lang')

    def __init__(self, kind, name, resource, file, line, side, params, lang):
        self.kind, self.name, self.resource, self.file, self.line = kind, name, resource, file, line
        self.side, self.params, self.lang = side, params, lang
        self.sinks, self.tags, self.evidence, self.id = {}, set(), {}, ''

    def as_dict(self):
        return {'id': self.id, 'kind': self.kind, 'name': self.name, 'resource': self.resource, 'file': self.file,
                'line': self.line, 'side': self.side, 'params': self.params,
                'sinks': {k: sorted(v) for k, v in sorted(self.sinks.items())}, 'tags': sorted(self.tags),
                'evidence': {k: v for k, v in sorted(self.evidence.items())}}


def side_heuristic(rel: str) -> str:
    p = rel.replace('\\', '/').lower()
    if re.search(r'(^|/)(server|sv)([/_.]|$)|sv_[^/]*$|_server\.\w+$|server\.\w+$', p):
        return 'server'
    if re.search(r'(^|/)(client|cl)([/_.]|$)|cl_[^/]*$|_client\.\w+$|client\.\w+$|(^|/)(web|html|ui|nui)/', p):
        return 'client'
    return 'shared'


def parse_params(masked: str, start: int, lang: str):
    """Parameter names of the function literal starting at/after `start`, plus the body span."""
    if lang == 'lua':
        m = re.compile(r'function\s*[\w.:]*\s*\(([^)]*)\)').match(masked, start)
        if not m:
            return None
        params = [p.strip() for p in m.group(1).split(',') if p.strip() and p.strip() != '...']
        return params, m.start(), lua_block_end(masked, m.start())
    m = re.compile(r'(?:async\s+)?(?:function\s*\w*\s*\(([^)]*)\)|\(([^)]*)\)\s*=>|(\w+)\s*=>)').match(masked, start)
    if not m:
        return None
    raw = m.group(1) if m.group(1) is not None else (m.group(2) if m.group(2) is not None else m.group(3))
    params = [re.sub(r'[=:].*', '', p).strip(' {}[]') for p in (raw or '').split(',')]
    return [p for p in params if p], m.start(), js_block_end(masked, m.end())


class FileInfo:
    def __init__(self, path: Path, rel: str, resource: str, side: str, text: str, lang: str):
        self.path, self.rel, self.resource, self.side, self.text, self.lang = path, rel, resource, side, text, lang
        self.masked = mask_lua(text) if lang == 'lua' else mask_js(text)
        # Long string literals (base64 images, SQL) are fine; long lines of *code* mean minified/obfuscated.
        longest_code = max((len(re.sub(r'\s+', '', line)) for line in self.masked.splitlines()), default=0)
        # Asset Escrow encrypts files in place: they start with an 'FXAP' header.
        self.opaque = text.startswith('FXAP') or bool(OPAQUE.search(text[:20000])) or longest_code > 3000

    def line_of(self, pos: int) -> int:
        return self.text.count('\n', 0, pos) + 1


def function_index(files):
    """resource -> name -> (FileInfo, start, end) for named Lua/JS functions (global and file-local)."""
    index = {}
    rx_lua = re.compile(r'\b(?:local\s+)?function\s+([\w.:]+)\s*\(')
    rx_lua_assign = re.compile(r'\b(?:local\s+)?([\w.]+)\s*=\s*function\s*\(')
    rx_js = re.compile(r'\bfunction\s+(\w+)\s*\(|\b(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?(?:function\b|\([^)]*\)\s*=>)')
    for fi in files:
        table = index.setdefault(fi.resource, {})
        if fi.lang == 'lua':
            for rx in (rx_lua, rx_lua_assign):
                for m in rx.finditer(fi.masked):
                    name = m.group(1).split('.')[-1].split(':')[-1]
                    fstart = fi.masked.find('function', m.start())
                    table.setdefault(name, (fi, fstart, lua_block_end(fi.masked, fstart)))
        else:
            for m in rx_js.finditer(fi.masked):
                name = m.group(1) or m.group(2)
                table.setdefault(name, (fi, m.start(), js_block_end(fi.masked, m.end())))
    # Aliases such as `local payMoney = defaultPaymentMethod` (ox_fuel) resolve to the aliased function.
    rx_alias = re.compile(r'^[ \t]*(?:local\s+|const\s+|let\s+|var\s+)?([A-Za-z_]\w*)\s*=\s*([A-Za-z_]\w*)\s*;?[ \t]*$', re.M)
    for fi in files:
        table = index.get(fi.resource, {})
        for m in rx_alias.finditer(fi.masked):
            if m.group(2) in table and m.group(1) not in table:
                table[m.group(1)] = table[m.group(2)]
    return index


CALL = re.compile(r'\b([A-Za-z_]\w*)\s*\(')


def collect_sinks(fi, body_start, body_end, index, depth, seen, via, out_sinks):
    body = fi.masked[body_start:body_end]
    for cat, rx in SINKS:
        for m in rx.finditer(body):
            ln = fi.line_of(body_start + m.start())
            out_sinks.setdefault(cat, set()).add(f'{fi.rel}:{ln}' + (f' via {via}' if via else ''))
    if depth <= 0:
        return
    for m in CALL.finditer(body):
        name = m.group(1)
        if name in seen or name in ('function', 'if', 'for', 'while', 'return', 'local', 'print', 'tostring', 'tonumber', 'type', 'pairs', 'ipairs'):
            continue
        target = index.get(fi.resource, {}).get(name)
        if not target:
            continue
        seen.add(name)
        tfi, tstart, tend = target
        collect_sinks(tfi, tstart, tend, index, depth - 1, seen, (via + ' > ' if via else '') + name + '()', out_sinks)


def tainted_names(body: str, params):
    """Params plus locals assigned (directly or one hop) from a param expression."""
    names = {p for p in params if p not in SKIP_PARAMS and re.fullmatch(r'[A-Za-z_]\w*', p)}
    if not names:
        return names
    assign = re.compile(r'\b(?:local\s+)?([A-Za-z_]\w*(?:\s*,\s*[A-Za-z_]\w*)*)\s*=\s*([^\n]+)')
    for _ in range(2):
        for m in assign.finditer(body):
            rhs = m.group(2)
            if any(re.search(r'\b' + re.escape(n) + r'\b', rhs) for n in names):
                for lhs in m.group(1).split(','):
                    lhs = lhs.strip()
                    if lhs and lhs not in SKIP_PARAMS:
                        names.add(lhs)
    return names


def analyse(ep: Endpoint, fi: FileInfo, start: int, end: int, index):
    collect_sinks(fi, start, end, index, 2, set(), '', ep.sinks)
    body = fi.masked[start:end]
    raw_body = fi.text[start:end]
    lines = body.split('\n')
    base_line = fi.line_of(start)
    tainted = tainted_names(body, ep.params)
    mutating = [c for c in ep.sinks if c in MUTATING]
    client_callable = ep.kind in ('net-event', 'callback', 'custom')

    def first_line(rx, cats=None):
        for idx, line in enumerate(lines):
            if cats is not None:
                if any(SINKS_D[c].search(line) for c in cats):
                    return idx
            elif rx.search(line):
                return idx
        return None

    # Client value inside a direct sink call argument.
    if client_callable and tainted:
        for idx, line in enumerate(lines):
            for cat, rx in SINKS:
                if cat not in MUTATING:
                    continue
                m = rx.search(line)
                if m and any(re.search(r'\b' + re.escape(n) + r'\b', line[m.start():]) for n in tainted):
                    ep.tags.add('client-value-in-sink')
                    ep.evidence.setdefault('client-value-in-sink', f'{fi.rel}:{base_line + idx}')
                    break
    # Client value passed into a same-resource helper that reaches a mutating sink (e.g. payMoney(source, price)).
    if client_callable and tainted and 'client-value-in-sink' not in ep.tags:
        for idx, line in enumerate(lines):
            for m in CALL.finditer(line):
                target = index.get(fi.resource, {}).get(m.group(1))
                if not target:
                    continue
                args = line[m.end():]
                if not any(re.search(r'\b' + re.escape(n) + r'\b', args) for n in tainted):
                    continue
                helper_sinks = {}
                tfi, tstart, tend = target
                collect_sinks(tfi, tstart, tend, index, 1, {m.group(1)}, m.group(1) + '()', helper_sinks)
                if any(c in MUTATING for c in helper_sinks):
                    ep.tags.add('client-value-in-sink')
                    ep.evidence.setdefault('client-value-in-sink', f'{fi.rel}:{base_line + idx} via {m.group(1)}()')
                    break
            if 'client-value-in-sink' in ep.tags:
                break
    # Credit before a later guard.
    credit_idx = first_line(None, [c for c in CREDIT if c in SINKS_D])
    if credit_idx is not None and client_callable:
        for idx in range(credit_idx + 1, len(lines)):
            if re.search(r'\bif\b', lines[idx]) and GUARD.search('\n'.join(lines[idx:idx + 4])):
                ep.tags.add('credit-before-guard')
                ep.evidence.setdefault('credit-before-guard', f'{fi.rel}:{base_line + credit_idx}')
                break
    # Removal whose result is ignored, followed by a credit.
    for idx, line in enumerate(lines):
        if REMOVAL_CALL.search(line):
            rest = '\n'.join(lines[idx + 1:])
            if SINKS_D['money+'].search(rest) or SINKS_D['item+'].search(rest):
                ep.tags.add('unchecked-removal')
                ep.evidence.setdefault('unchecked-removal', f'{fi.rel}:{base_line + idx}')
                break
    # Money removal without reading the balance.
    if SINKS_D['money-'].search(body) and not BALANCE_READ.search(body) and client_callable:
        ep.tags.add('no-balance-check')
    # Client amount without integer validation.
    if client_callable and tainted and ('money+' in ep.sinks or 'money-' in ep.sinks or 'item+' in ep.sinks or 'item-' in ep.sinks) \
            and 'client-value-in-sink' in ep.tags and not INTEGER_CHECK.search(body):
        ep.tags.add('non-integer-amount')
    # Client-reported position/distance.
    if client_callable and tainted:
        for idx, line in enumerate(lines):
            for n in tainted:
                if re.search(r'\b' + re.escape(n) + r'\s*[.\[]\s*[\'"]?' + POSITION.pattern, line, re.I) or \
                        (POSITION.fullmatch(n) and re.search(r'\b' + re.escape(n) + r'\b', line) and idx > 0):
                    ep.tags.add('client-position')
                    ep.evidence.setdefault('client-position', f'{fi.rel}:{base_line + idx}')
                    break
            if 'client-position' in ep.tags:
                break
    # Another player chosen by the client.
    if client_callable and mutating:
        target_params = [p for p in tainted if TARGET.fullmatch(p)] + \
            sorted({m.group(1) for m in re.finditer(r'\b(?:data|args|params)\s*\.\s*(' + TARGET.pattern[2:-2] + r')\b', body, re.I)})
        if target_params and not SERVER_DISTANCE.search(body):
            ep.tags.add('client-target')
            ep.evidence.setdefault('client-target', ', '.join(sorted(set(target_params)))[:80])
    # Yield before the first mutation.
    mut_idx = first_line(None, [c for c in mutating if c in SINKS_D])
    if mut_idx is not None:
        for idx in range(0, mut_idx):
            if YIELD.search(lines[idx]):
                ep.tags.add('yield-before-mutation')
                ep.evidence.setdefault('yield-before-mutation', f'{fi.rel}:{base_line + idx}')
                break
    if ep.kind == 'net-event' and fi.lang == 'lua' and not re.search(r'\bsource\b', body):
        ep.tags.add('no-source')
    for idx, line in enumerate(lines):
        if fi.lang == 'lua' and NOT_EQ.search(line):
            ep.tags.add('not-eq-precedence')
            ep.evidence.setdefault('not-eq-precedence', f'{fi.rel}:{base_line + idx}')
            break
    if client_callable and 'broadcast' in ep.sinks:
        ep.tags.add('fanout')
    if client_callable and mutating and not RATE.search(raw_body):
        ep.tags.add('no-rate-limit')


SINKS_D = dict(SINKS)

# ---------------------------------------------------------------- discovery

def load_files(root: Path):
    files, opaque, escrow = [], [], set()
    side_cache = {}
    for path in walk_files(root):
        if path.name.lower() == '.fxap' or path.suffix.lower() == '.fxap':
            mf = nearest_manifest(path)
            escrow.add(mf.parent.name if mf else path.parent.name)
        if path.suffix.lower() not in CODE_EXT or path.name in ('fxmanifest.lua', '__resource.lua'):
            continue
        mf = nearest_manifest(path)
        if mf is None:
            continue
        rel = path.name if root.is_file() else str(path.relative_to(root))
        if mf not in side_cache:
            try:
                side_cache[mf] = script_sides(mf)
            except (ManifestError, OSError, UnicodeError, ValueError):
                side_cache[mf] = None
        sides = side_cache[mf]
        resolved = path.resolve()
        if sides is not None:
            if resolved not in sides:
                continue  # not loaded by the manifest (NUI sources, tooling, dead files)
            declared = sides[resolved]
            side = 'server' if declared == {'server'} else ('client' if declared == {'client'} else 'shared')
        else:
            side = side_heuristic(rel)
        if side == 'client':
            continue
        try:
            text = path.read_text(encoding='utf-8', errors='replace')
        except OSError:
            continue
        fi = FileInfo(path, rel.replace('\\', '/'), mf.parent.name, side, text, 'lua' if path.suffix.lower() == '.lua' else 'js')
        if fi.opaque:
            opaque.append(fi.rel)
            continue
        files.append(fi)
    return files, sorted(opaque), sorted(escrow)


def resolve_handler(fi, after: int, index):
    """Return (params, start, end) for an inline function or a named handler reference."""
    parsed = parse_params(fi.masked, after, fi.lang)
    if parsed:
        return parsed
    # Options table or extra arguments before the handler (lib.addCommand, ESX.RegisterCommand): next function literal.
    lead = fi.masked[after:after + 1500]
    if lead.lstrip()[:1] in ('{', "'", '"', ','):
        nxt = re.search(r'\bfunction\b' if fi.lang == 'lua' else r'\bfunction\b|\([^)]*\)\s*=>', lead)
        if nxt:
            parsed = parse_params(fi.masked, after + nxt.start(), fi.lang)
            if parsed:
                return parsed
    m = re.compile(r'([A-Za-z_][\w.:]*)').match(fi.masked, after)
    if not m:
        return None
    target = index.get(fi.resource, {}).get(m.group(1).split('.')[-1].split(':')[-1])
    if not target:
        return None
    tfi, tstart, _ = target
    parsed = parse_params(tfi.masked, tstart, tfi.lang)
    return parsed if tfi is fi else None


def discover(files, index):
    endpoints = []
    for fi in files:
        taken = set()
        entries = LUA_ENTRY if fi.lang == 'lua' else JS_ENTRY
        for kind, rx in entries:
            for m in rx.finditer(fi.masked):
                name_src = fi.text[m.start(1):m.end(1)] if m.lastindex else ''
                res = resolve_handler(fi, m.end(), index)
                if not res:
                    continue
                params, start, end = res
                if start in taken:
                    continue
                taken.add(start)
                ep = Endpoint(kind, name_src or kind, fi.resource, fi.rel, fi.line_of(m.start()), fi.side, params, fi.lang)
                analyse(ep, fi, start, end, index)
                endpoints.append(ep)
        if fi.lang == 'lua':
            registered = {fi.text[m.start(1):m.end(1)] for m in LUA_SPLIT_REG.finditer(fi.masked)}
            for m in LUA_HANDLER.finditer(fi.masked):
                name = fi.text[m.start(1):m.end(1)]
                if name not in registered:
                    continue
                res = resolve_handler(fi, m.end(), index)
                if not res or res[1] in taken:
                    continue
                params, start, end = res
                taken.add(start)
                ep = Endpoint('net-event', name, fi.resource, fi.rel, fi.line_of(m.start()), fi.side, params, fi.lang)
                analyse(ep, fi, start, end, index)
                endpoints.append(ep)
            for m in LUA_CUSTOM.finditer(fi.masked):
                callee = m.group(1)
                if not CUSTOM_NAME.search(callee.split('.')[-1].split(':')[-1]) or callee.startswith(('lib.callback', 'ESX.Register')):
                    continue
                res = resolve_handler(fi, m.end(), index)
                if not res or res[1] in taken:
                    continue
                params, start, end = res
                taken.add(start)
                ep = Endpoint('custom', f'{fi.text[m.start(2):m.end(2)]} [{callee}]', fi.resource, fi.rel,
                              fi.line_of(m.start()), fi.side, params, fi.lang)
                analyse(ep, fi, start, end, index)
                endpoints.append(ep)
    endpoints.sort(key=lambda e: (e.resource.lower(), e.file.lower(), e.line, e.name))
    for i, ep in enumerate(endpoints, 1):
        ep.id = f'E{i:04d}'
    return endpoints

# ---------------------------------------------------------------- output

def shard_filter(endpoints, spec):
    k, n = (int(x) for x in spec.split('/'))
    if not (1 <= k <= n):
        raise ValueError('shard must be K/N with 1 <= K <= N')
    resources = sorted({e.resource for e in endpoints}, key=str.lower)
    weights = {r: sum(1 for e in endpoints if e.resource == r and (e.sinks or e.tags)) + 1 for r in resources}
    buckets = [[0, []] for _ in range(n)]
    for r in sorted(resources, key=lambda r: (-weights[r], r.lower())):
        b = min(buckets, key=lambda b: b[0])
        b[0] += weights[r]
        b[1].append(r)
    chosen = set(buckets[k - 1][1])
    return [e for e in endpoints if e.resource in chosen], sorted(chosen, key=str.lower)


def write_ledger(path: Path, endpoints, root, opaque, escrow, shard_resources):
    rows = [e for e in endpoints if e.sinks or e.tags]
    lines = [
        f'# Endpoint coverage ledger: {root}',
        '',
        'Generated by `surface.py`. Every row must end with a Status: `finding` (link the report item),',
        '`ok` (one-line reason), `opaque` (escrow/obfuscated/minified) or `not-reviewed` (reason).',
        'The audit is incomplete while any row is `TODO`. Report the counts below in the final report.',
        '',
        f'- Endpoints found: {len(endpoints)}; with sinks or tags (rows): {len(rows)}',
    ]
    if shard_resources is not None:
        lines.append(f'- Shard resources: {", ".join(shard_resources)}')
    if opaque:
        lines.append(f'- Opaque server files (not reviewable): {len(opaque)} - ' + ', '.join(opaque[:30]) + (' ...' if len(opaque) > 30 else ''))
    if escrow:
        lines.append('- Resources with escrowed files (.fxap): ' + ', '.join(escrow))
    lines += ['', '| ID | Resource | Endpoint | Kind | Location | Sinks | Tags | Status | Notes |', '|---|---|---|---|---|---|---|---|---|']
    for e in rows:
        sinks = ', '.join(sorted(e.sinks)) or '-'
        tags = ', '.join(sorted(e.tags)) or '-'
        name = e.name.replace('|', '\\|')
        lines.append(f'| {e.id} | {e.resource} | `{name}` | {e.kind} | {e.file}:{e.line} | {sinks} | {tags} | TODO | |')
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('path')
    ap.add_argument('--json', action='store_true', help='full machine-readable inventory')
    ap.add_argument('--all', action='store_true', help='also print endpoints without sinks or tags')
    ap.add_argument('--ledger', help='write a Markdown coverage ledger to this file')
    ap.add_argument('--shard', help='K/N: deterministic, balanced split by resource for parallel reviewers')
    ap.add_argument('--only', help='only resources whose name contains this text')
    a = ap.parse_args()
    root = Path(a.path)
    if not root.exists():
        print(f'not found: {root}', file=sys.stderr)
        return 2
    files, opaque, escrow = load_files(root)
    if not files and not opaque:
        print(f'no server/shared Lua or JS loaded by a manifest under {root}', file=sys.stderr)
        return 2
    index = function_index(files)
    endpoints = discover(files, index)
    if a.only:
        endpoints = [e for e in endpoints if a.only.lower() in e.resource.lower()]
    shard_resources = None
    if a.shard:
        try:
            endpoints, shard_resources = shard_filter(endpoints, a.shard)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2
    if a.ledger:
        write_ledger(Path(a.ledger), endpoints, root, opaque, escrow, shard_resources)
    if a.json:
        print(json.dumps({'root': str(root), 'endpoints': [e.as_dict() for e in endpoints], 'opaque_files': opaque,
                          'escrow_resources': escrow, 'tags': TAGS, 'shard_resources': shard_resources}, indent=2))
        return 0
    shown = endpoints if a.all else [e for e in endpoints if e.sinks or e.tags]
    current = None
    for e in shown:
        if e.resource != current:
            current = e.resource
            print(f'\n== {current}')
        print(f'  {e.id} {e.kind:9} {e.name}  ({e.file}:{e.line})')
        if e.sinks:
            print('       sinks: ' + '; '.join(f'{k} [{", ".join(sorted(v)[:3])}{" ..." if len(v) > 3 else ""}]' for k, v in sorted(e.sinks.items())))
        if e.tags:
            print('       tags:  ' + ', '.join(sorted(e.tags)))
    counts = {}
    for e in endpoints:
        for t in e.tags:
            counts[t] = counts.get(t, 0) + 1
    with_sinks = sum(1 for e in endpoints if e.sinks)
    print(f'\nSummary: {len(endpoints)} endpoint(s), {with_sinks} with sinks, '
          f'{sum(1 for e in endpoints if e.sinks or e.tags)} to review; tags: {dict(sorted(counts.items()))}')
    if opaque:
        print(f'Opaque server files (not reviewable): {len(opaque)}')
    if escrow:
        print('Escrowed resources: ' + ', '.join(escrow))
    print('-- heuristic inventory: every endpoint with sinks must be reviewed; tags are leads, not verdicts', file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
