#!/usr/bin/env python3
"""Summarise FXServer / txAdmin console logs into actionable problems, grouped and counted.

Finds the logs by itself (txData/<profile>/logs/fxserver.log, logs/*.log next to the server) or
takes explicit files. Streams the file, so multi-GB logs are fine. Groups:

  script-error   SCRIPT ERROR lines with resource, file:line and the first stack frame
  load-failure   scripts or modules that failed to load (missing file, Cannot find module, parse errors)
  resource       resources that could not start (escrow entitlement, missing resource/category, no manifest,
                 missing files inside a resource)
  hitch          server/sync/network thread hitch warnings (count, worst interval)
  database       slow queries per resource (oxmysql), oversized result sets, DB server version
  assets         streamed assets over the memory warning threshold (per resource, worst, oversized)
  config         removed/internal/unknown convars and commands, missing exec files, listing/license errors
  security       framework/library security advisories printed at startup (e.g. state bag strict mode off)
  lifecycle      server starts, shutdowns, crashes/unexpected exits
  warning        other warnings per resource (top messages)

Usage:
  python logs.py [path ...] [--json] [--last] [--top N]
  path = a log file, a server root/resources dir (logs are searched nearby) or nothing (current dir)
Exit code: 0 = parsed, 2 = no log found. Secrets that look like keys/tokens/webhooks are masked.
Standard library only (Python 3.8+).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REFS = {
    'script-error': 'console-logs.md, debugging.md',
    'load-failure': 'console-logs.md, debugging.md',
    'resource': 'console-logs.md, debugging.md, licensing-and-policy.md (escrow), fxmanifest.md',
    'hitch': 'console-logs.md, hitch-diagnostics.md',
    'database': 'console-logs.md, database-optimization.md, hitch-diagnostics.md',
    'assets': 'console-logs.md, mapping-streaming.md, vehicles-and-handling.md',
    'config': 'console-logs.md, convars-and-commands.md, server-ops.md',
    'security': 'console-logs.md, security.md, convars-and-commands.md',
    'lifecycle': 'console-logs.md, debugging.md, txadmin.md',
    'warning': 'console-logs.md, debugging.md',
}

LINE = re.compile(r'^\[\s*([^\]]*?)\s*\]\s?(.*)$')
TXA = re.compile(r'^\s*║\s*([^║]*?)\s*║\s?(.*)$')
SECRET = re.compile(r'(?P<keep>sv_licenseKey\s+|licenseKey["\']?\s*[:=]\s*["\']?|(?:password|passwd|pwd)=)[^;\s"\']+'
                    r'|cfxk_\w+|https://(?:discord(?:app)?\.com|ptb\.discord\.com)/api/webhooks/\S+'
                    r'|\bbot\d{6,}:[\w-]{20,}|\b[A-Za-z0-9_\-]{32,}\b', re.I)

RULES = [
    # group, code, regex, severity
    ('script-error', 'script-error', re.compile(r'SCRIPT ERROR:\s*(?:@?([\w\-]+)/)?([^:\s]+):(\d+):\s*(.*)'), 'high'),
    ('load-failure', 'error-loading-script', re.compile(r'Error loading script (\S+) in resource ([\w\-]+):\s*(.*)'), 'high'),
    ('load-failure', 'failed-to-load-script', re.compile(r'Failed to load script (\S+)'), 'high'),
    ('load-failure', 'cannot-find-module', re.compile(r"Cannot find module '([^']+)'"), 'high'),
    ('load-failure', 'error-parsing-script', re.compile(r'Error parsing script (\S+) in resource ([\w\-]+)'), 'high'),
    ('resource', 'escrow-entitlement', re.compile(r'You lack the required entitlement to use ([\w\-]+)'), 'high'),
    ('resource', 'resource-not-started', re.compile(r"Couldn't start resource ([\w\-]+)"), 'high'),
    ('resource', 'category-not-found', re.compile(r"Couldn't find resource category (\[[^\]]+\])"), 'high'),
    ('resource', 'resource-not-found', re.compile(r"Couldn't find resource ([\w\-]+)"), 'high'),
    ('resource', 'no-manifest', re.compile(r'Warning: (\S+) does not have a resource manifest'), 'low'),
    ('resource', 'file-not-loaded', re.compile(r"Warning: could not load '([^']+)'"), 'medium'),
    ('hitch', 'thread-hitch', re.compile(r'(server|sync|network|svMain|svSync|svNetwork)?\s*thread hitch warning: timer interval of (\d+) milliseconds', re.I), 'medium'),
    ('database', 'slow-query', re.compile(r'(?:\[[^\]]*\]\s*)?([\w\-]+) took (\d+)ms to execute a query'), 'medium'),
    ('database', 'oversized-result', re.compile(r'([\w\-]+) executed a query with an oversized result set \((\d+) results\)'), 'medium'),
    ('database', 'db-connected', re.compile(r'\[([^\]]+)\] Database server connection established'), 'info'),
    ('assets', 'asset-memory', re.compile(r'Asset (\S+) uses ([\d.]+) MiB of (virtual|physical) memory\.?(.*)'), 'low'),
    ('config', 'convar-removed', re.compile(r'`?(\w+)`? has been removed'), 'low'),
    ('config', 'convar-internal', re.compile(r"Warning: '(\w+)' is an internal ConVar"), 'low'),
    ('config', 'unknown-command', re.compile(r'No such command (\S+?)\.?$'), 'low'),
    ('config', 'exec-missing', re.compile(r'No such config file: (\S+)'), 'medium'),
    ('config', 'argument-count', re.compile(r'Argument count mismatch \(passed (\d+), wanted (\d+)\)'), 'low'),
    ('config', 'listing-host', re.compile(r'Force indirect listing is enabled, but no host override is set'), 'medium'),
    ('config', 'license-missing', re.compile(r'does not have a license key specified'), 'high'),
    ('security', 'secret-in-log', re.compile(r'sv_licenseKey\s+\S{8,}|cfxk_\w{8,}|/api/webhooks/\d+/[\w-]{20,}|\bbot\d{6,}:[\w-]{20,}|'
                                             r'mysql_connection_string\s+\S*password=', re.I), 'medium'),
    ('security', 'statebag-strict-off', re.compile(r'sv_stateBagStrictMode is currently DISABLED'), 'medium'),
    ('security', 'security-advisory', re.compile(r'SECURITY WARNING|security advisory', re.I), 'info'),
    ('lifecycle', 'server-start', re.compile(r'FXServer Starting'), 'info'),
    ('lifecycle', 'server-shutdown', re.compile(r'Server shutting down'), 'info'),
    ('lifecycle', 'process-close', re.compile(r'Server process close detected|Restarting server'), 'medium'),
    ('lifecycle', 'fatal', re.compile(r'Fatal Error|Unhandled exception|crash dump|has crashed', re.I), 'high'),
]
WARNING = re.compile(r'\bwarn(ing)?\b', re.I)
STACK_FRAME = re.compile(r'^\s*>\s*(.*?)\s*\(@([\w\-]+)/([^:]+):(\d+)\)')
SEV = {'info': 0, 'low': 1, 'medium': 2, 'high': 3}


def mask(text: str) -> str:
    return SECRET.sub(lambda m: (m.group('keep') or '') + '<redacted>', text)


def find_logs(path: Path):
    if path.is_file():
        return [path]
    found = []
    bases = [path] + list(path.resolve().parents)[:3]
    for base in bases:
        for tx in (base / 'txData', base / 'txdata'):
            if tx.is_dir():
                found += sorted(tx.glob('*/logs/fxserver.log'))
        for name in ('logs', 'log'):
            if (base / name).is_dir():
                found += sorted(p for p in (base / name).glob('*.log') if 'fxserver' in p.name.lower() or 'server' in p.name.lower())
        found += sorted(base.glob('fxserver*.log')) + sorted(base.glob('server*.log'))
        if found:
            break
    unique = []
    for p in found:
        if p.resolve() not in [u.resolve() for u in unique] and p.stat().st_size > 0:
            unique.append(p)
    return unique


class Summary:
    def __init__(self):
        self.groups = {}
        self.sessions = 0

    def add(self, group, code, key, sev, example, where, value=None):
        g = self.groups.setdefault(group, {})
        item = g.setdefault((code, key), {'group': group, 'code': code, 'key': key, 'severity': sev, 'count': 0,
                                          'first': where, 'last': where, 'example': example, 'max': None, 'extra': {}})
        item['count'] += 1
        item['last'] = where
        if value is not None and (item['max'] is None or value > item['max']):
            item['max'] = value
        return item


def parse(paths, last_only=False):
    s = Summary()
    for path in paths:
        if last_only:
            starts = []
            with path.open(encoding='utf-8', errors='replace') as fh:
                for no, raw in enumerate(fh, 1):
                    if 'FXServer Starting' in raw:
                        starts.append(no)
            begin = starts[-1] if starts else 1
        else:
            begin = 1
        pending_error = None
        with path.open(encoding='utf-8', errors='replace') as fh:
            for no, raw in enumerate(fh, 1):
                if no < begin:
                    continue
                line = raw.rstrip('\r\n')
                channel, msg = '', line
                m = LINE.match(line) or TXA.match(line)
                if m:
                    channel, msg = m.group(1).strip(), m.group(2)
                where = f'{path.name}:{no}'
                resource = channel.split(':', 2)[1] if channel.startswith(('script:', 'resources:')) and ':' in channel else ''
                if pending_error is not None:
                    fm = STACK_FRAME.match(msg)
                    if fm:
                        pending_error['extra'].setdefault('frame', f'{fm.group(2)}/{fm.group(3)}:{fm.group(4)} ({fm.group(1)})')
                        pending_error = None
                        continue
                    if msg.strip() and not msg.strip().startswith(('>', 'stack', 'at ')):
                        pending_error = None
                matched = False
                for group, code, rx, sev in RULES:
                    mm = rx.search(msg)
                    if not mm:
                        continue
                    matched = True
                    if code == 'script-error':
                        res = mm.group(1) or resource or '?'
                        key = f'{res}/{mm.group(2)}:{mm.group(3)}: {mm.group(4)[:160]}'
                        pending_error = s.add(group, code, key, sev, mask(line[:300]), where)
                    elif code == 'thread-hitch':
                        thread = (mm.group(1) or 'server').lower().replace('sv', '')
                        s.add(group, code, f'{thread} thread', sev, mask(line[:200]), where, int(mm.group(2)))
                    elif code == 'slow-query':
                        s.add(group, code, mm.group(1), sev, mask(line[:200]), where, int(mm.group(2)))
                    elif code == 'oversized-result':
                        s.add(group, code, mm.group(1), sev, mask(line[:200]), where, int(mm.group(2)))
                    elif code == 'asset-memory':
                        name = mm.group(1)
                        res = name.split('/')[0] if '/' in name else (resource or '?')
                        item = s.add(group, code, res, sev, mask(line[:200]), where, float(mm.group(2)))
                        if 'Oversized' in mm.group(4) or 'WILL' in mm.group(4):
                            item['extra']['oversized'] = item['extra'].get('oversized', 0) + 1
                        worst = item['extra'].get('worst')
                        if worst is None or float(mm.group(2)) > worst[1]:
                            item['extra']['worst'] = (name, float(mm.group(2)), mm.group(3))
                    elif code == 'server-start':
                        s.sessions += 1
                        s.add(group, code, 'starts', sev, '', where)
                    else:
                        key = mm.group(1) if mm.groups() and mm.group(1) else (resource or code)
                        if code == 'error-loading-script':
                            key = f'{mm.group(2)}/{mm.group(1)}: {mm.group(3)[:120]}'
                        elif code == 'argument-count':
                            key = f'passed {mm.group(1)}, wanted {mm.group(2)}'
                        elif code in ('listing-host', 'license-missing', 'process-close', 'fatal', 'server-shutdown', 'secret-in-log'):
                            key = code
                        s.add(group, code, key, sev, mask(line[:240]), where)
                    break
                if not matched and WARNING.search(channel + ' ' + msg[:40]) and msg.strip():
                    norm = re.sub(r'\d+', 'N', msg.strip())[:120]
                    s.add('warning', 'warning', f'{resource or channel or "?"}: {norm}', 'low', mask(line[:200]), where)
    return s


HINTS = {
    'script-error': 'Fix the first error of each resource first; later errors are often consequences (debugging.md).',
    'error-loading-script': 'A file listed in fxmanifest.lua failed to load: missing file, syntax error or wrong side.',
    'failed-to-load-script': 'Run manifest.py on the resource; check the file exists and is listed for the right side.',
    'cannot-find-module': 'Server JS dependency missing: build/install the resource (lockfile) or remove the require.',
    'escrow-entitlement': 'Escrowed resource not granted to this server key (Keymaster). Expected on dev servers with another key.',
    'resource-not-started': 'See the lines above it in the log for the cause (dependency, entitlement, manifest).',
    'category-not-found': 'An `ensure [category]` names a folder that does not exist (typo or moved folder): nothing in it starts.',
    'resource-not-found': '`ensure`/`start` names a resource folder that does not exist.',
    'no-manifest': 'A folder inside resources/ has no fxmanifest.lua: move non-resource folders (docs, tools, tests) out of resources/.',
    'file-not-loaded': 'A resource tried to load a file that does not exist (often a locale/config file).',
    'thread-hitch': 'Correlate with what ran at that moment (profiler, slow queries, restarts); see hitch-diagnostics.md.',
    'slow-query': 'Find the query (oxmysql debug/ui), add indexes, avoid per-tick or per-player queries.',
    'oversized-result': 'SELECT returns too many rows: paginate, select columns, or filter in SQL.',
    'db-connected': 'Database server version reported by the driver.',
    'asset-memory': 'Streamed assets over the warning threshold: compress textures, drop unused LODs; >16 MiB physical breaks streaming.',
    'convar-removed': 'Delete the convar from the cfg; it has no effect anymore.',
    'convar-internal': 'This convar cannot be set from the cfg; remove the line.',
    'unknown-command': 'A cfg or console line calls a command that does not exist (typo, missing resource, removed command).',
    'exec-missing': '`exec` points to a file that does not exist (path is relative to the server data folder).',
    'argument-count': 'A cfg line has the wrong number of arguments (often `set name` without a value).',
    'listing-host': 'sv_forceIndirectListing without sv_listingHostOverride: the server will not list correctly.',
    'license-missing': 'sv_licenseKey not set for this launch (check the cfg and +set on the command line).',
    'secret-in-log': 'A secret (license key, webhook, bot token, DB password) was printed to the console: rotate it, and never share raw logs.',
    'statebag-strict-off': 'Clients may write replicated state bags: enable sv_stateBagStrictMode after testing resources.',
    'security-advisory': 'A library printed a security advisory at startup: read it and fix the configuration.',
    'process-close': 'The process stopped unexpectedly or was restarted by txAdmin: check the lines before it.',
    'fatal': 'Fatal error or crash: read the lines before it and the crash dump if any.',
    'server-start': 'Number of server starts in the analysed log.',
    'server-shutdown': 'Graceful shutdowns.',
    'warning': 'Other warnings, grouped by resource and message shape.',
}


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors='replace')
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('paths', nargs='*', default=['.'])
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--last', action='store_true', help='only the last server session in each log')
    ap.add_argument('--top', type=int, default=8, help='items shown per group (text output)')
    a = ap.parse_args()
    logs = []
    for p in a.paths:
        logs += find_logs(Path(p))
    if not logs:
        print('no FXServer/txAdmin log found (pass the log file, e.g. txData/<profile>/logs/fxserver.log)', file=sys.stderr)
        return 2
    summary = parse(logs, a.last)
    items = [i for g in summary.groups.values() for i in g.values()]
    items.sort(key=lambda i: (-SEV[i['severity']], list(REFS).index(i['group']) if i['group'] in REFS else 99, -i['count'], i['key']))
    if a.json:
        out = {'logs': [str(p) for p in logs], 'sessions': summary.sessions, 'items': items, 'hints': HINTS, 'references': REFS}
        print(json.dumps(out, indent=2, default=list))
        return 0
    print('Logs: ' + ', '.join(str(p) for p in logs) + (' (last session only)' if a.last else ''))
    print(f'Server starts seen: {summary.sessions}')
    for group in REFS:
        rows = [i for i in items if i['group'] == group]
        if not rows:
            continue
        rows.sort(key=lambda i: (-SEV[i['severity']], -(i['max'] or 0) if group in ('hitch', 'database', 'assets') else -i['count'], i['key']))
        print(f'\n== {group}  (see references/{REFS[group]})')
        for i in rows[:a.top]:
            extra = ''
            if i['max'] is not None:
                extra = f' worst {i["max"]:g}' + (' ms' if group in ('hitch', 'database') and i['code'] != 'oversized-result' else '')
            if i['extra'].get('worst'):
                n, v, kind = i['extra']['worst']
                extra = f' worst {n} {v:g} MiB {kind}' + (f'; {i["extra"]["oversized"]} flagged oversized' if i['extra'].get('oversized') else '')
            if i['extra'].get('frame'):
                extra += f'; at {i["extra"]["frame"]}'
            print(f'  [{i["severity"].upper():6}] {i["code"]}: {i["key"]}  x{i["count"]}{extra}  ({i["first"]})')
        if len(rows) > a.top:
            print(f'  ... {len(rows) - a.top} more (use --top or --json)')
        codes = sorted({i['code'] for i in rows[:a.top]})
        for c in codes:
            print(f'    - {c}: {HINTS.get(c, "")}')
    counts = {s: sum(1 for i in items if i['severity'] == s) for s in ('high', 'medium', 'low', 'info')}
    print(f'\nSummary (distinct problems): {counts}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
