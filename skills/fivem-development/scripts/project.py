#!/usr/bin/env python3
"""Whole-server inventory: the facts every audit must start from, computed the same way every time.

Sections (all on by default):
  cfg       *.cfg exec chain from server.cfg; removed/duplicated convars
  ensure    ensure/start targets vs resource folders (categories expanded), never-started resources,
            duplicate resource names, dependencies started after their dependants
  versions  installed manifest versions vs assets/baseline.json (min-safe and baseline), with file:line
  datafiles every data_file path resolves to a file; it is also covered by files {}
  assets    stream files > 16 MiB, duplicate stream file names across resources, largest resources
  repo      git HEAD/dirty state, nested .git and node_modules inside resources, scripts (*.bat/*.cmd/
            *.ps1/*.sh) that reference files which do not exist

Usage:
  python project.py <server root or resources dir> [--json] [--section NAME ...]
Exit code: 0 = no high finding, 1 = at least one high finding, 2 = usage error.
Standard library only (Python 3.8+). Never prints convar values (they may be secrets).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from resource_files import ManifestError, glob_match, parse_data_files, parse_manifest  # noqa: E402

BASELINE = Path(__file__).resolve().parent.parent / 'assets' / 'baseline.json'
SKIP = {'.git', 'node_modules', '__pycache__', 'cache', '.vs', '.idea'}
STREAM_EXT = {'.ytd', '.yft', '.ydr', '.ydd', '.ybn', '.ymap', '.ytyp', '.ycd', '.ynv', '.ypt', '.ymt', '.awc', '.rpf'}
LIMIT_MB = 16
REMOVED_CONVARS = re.compile(r'^sv_experimental', re.I)
SECTIONS = ('cfg', 'ensure', 'versions', 'datafiles', 'assets', 'repo')
SEV_ORDER = {'info': 0, 'low': 1, 'medium': 2, 'high': 3}


class Report:
    def __init__(self):
        self.items = []

    def add(self, section, severity, code, message, where=''):
        self.items.append({'section': section, 'severity': severity, 'code': code, 'message': message, 'where': where})


def human(n):
    for unit in ('B', 'KiB', 'MiB', 'GiB'):
        if n < 1024 or unit == 'GiB':
            return f'{n:.1f} {unit}' if unit != 'B' else f'{n} B'
        n /= 1024.0
    return f'{n:.1f} GiB'


def find_layout(path: Path):
    """Return (server_root, resources_dir). Accepts the server root or the resources dir itself."""
    path = path.resolve()
    if (path / 'resources').is_dir():
        return path, path / 'resources'
    if path.name.lower() == 'resources' or any((path / d).is_dir() and d.startswith('[') for d in os.listdir(path)):
        return path, path
    return path, path


def discover_resources(resources: Path):
    """name -> list of (dir, category chain). FiveM does not nest resources inside resources."""
    found = {}
    for base, dirs, names in os.walk(str(resources)):
        dirs[:] = sorted(d for d in dirs if d not in SKIP)
        if 'fxmanifest.lua' in names or '__resource.lua' in names:
            p = Path(base)
            rel = p.relative_to(resources)
            cats = [part for part in rel.parts[:-1] if part.startswith('[') and part.endswith(']')]
            found.setdefault(p.name, []).append((p, cats))
            dirs[:] = []  # do not descend into a resource
    return found


# ---------------------------------------------------------------- cfg

CFG_LINE = re.compile(r'^\s*([+]?)(\w[\w:.-]*)\s*(.*)$')


def cfg_commands(path: Path):
    """Yield (line_no, command, args) for a cfg, honoring '#' and '//' comments and ';' splitting."""
    try:
        text = path.read_text(encoding='utf-8-sig', errors='replace')
    except OSError:
        return
    for ln, raw in enumerate(text.splitlines(), 1):
        line = raw.split('#', 1)[0]
        if line.lstrip().startswith('//'):
            continue
        parts, buf, quoted = [], '', False
        for ch in line:
            if ch == '"':
                quoted = not quoted
            if ch == ';' and not quoted:
                parts.append(buf)
                buf = ''
            else:
                buf += ch
        parts.append(buf)
        for part in parts:
            m = CFG_LINE.match(part)
            if m:
                yield ln, m.group(2), m.group(3).strip()


def cfg_chain(root: Path, resources: Path, report: Report):
    """Ordered list of (cfg path, line, cmd, args) following exec from server.cfg; plus unreferenced cfgs."""
    candidates = []
    for d in {root, resources}:
        candidates += sorted(p for p in d.glob('*.cfg') if p.is_file())
    start = next((p for p in candidates if p.name.lower() == 'server.cfg'), None)
    ordered, visited = [], set()

    def visit(cfg: Path):
        if cfg in visited or not cfg.is_file():
            return
        visited.add(cfg)
        for ln, cmd, args in cfg_commands(cfg):
            ordered.append((cfg, ln, cmd, args))
            if cmd.lower() == 'exec' and args:
                target = args.strip().strip('"').strip("'")
                for base in (cfg.parent, root, resources):
                    if (base / target).is_file():
                        visit((base / target).resolve())
                        break
                else:
                    report.add('cfg', 'medium', 'exec-missing', f'exec target not found: {target}', f'{cfg.name}:{ln}')

    if start:
        visit(start.resolve())
    else:
        report.add('cfg', 'medium', 'no-server-cfg', 'No server.cfg found next to the server root or resources dir.')
    unreferenced = [p for p in candidates if p.resolve() not in visited]
    for p in unreferenced:
        report.add('cfg', 'info', 'cfg-not-execd',
                   f'{p.name} is not exec\'d from server.cfg (may be passed with +exec on the command line; '
                   'it is analysed separately below)', p.name)
    return ordered, unreferenced


def check_convars(commands, report: Report, label):
    seen = {}
    for cfg, ln, cmd, args in commands:
        low = cmd.lower()
        if low in ('set', 'setr', 'sets') and args:
            name = args.split()[0].strip('"')
            value = args[len(args.split()[0]):].strip()
        elif low.startswith(('sv_', 'onesync_', 'rate', 'mysql_')) and low not in ('sv_licensekey',):
            name, value = cmd, args
        else:
            continue
        where = f'{cfg.name}:{ln}'
        if REMOVED_CONVARS.match(name):
            report.add('cfg', 'low', 'convar-removed', f'{name}: sv_experimental* convars were removed (2026-04); delete the line.', where)
        key = name.lower()
        if key in seen and seen[key][1] != value:
            report.add('cfg', 'medium', 'convar-conflict',
                       f'{name} is set more than once with different values ({label}); the last one wins.', f'{seen[key][0]} and {where}')
        seen[key] = (where, value)


# ---------------------------------------------------------------- ensure

def check_ensure(commands, resources_map, report: Report, label):
    started, order = {}, []
    category_members = {}
    for name, entries in resources_map.items():
        for _, cats in entries:
            for c in cats:
                category_members.setdefault(c.lower(), set()).add(name)
    for cfg, ln, cmd, args in commands:
        if cmd.lower() not in ('ensure', 'start', 'restart'):
            continue
        target = args.split()[0].strip('"') if args else ''
        if not target:
            continue
        where = f'{cfg.name}:{ln}'
        if target.startswith('['):
            members = category_members.get(target.lower())
            if not members:
                report.add('ensure', 'high', 'ensure-missing-category',
                           f'{cmd} {target}: no folder named {target} exists ({label}); nothing in it starts. '
                           'Check the spelling against the real category folders.', where)
                continue
            for m in sorted(members):
                started.setdefault(m, where)
                order.append(m)
        else:
            if target not in resources_map:
                report.add('ensure', 'high', 'ensure-missing-resource', f'{cmd} {target}: resource folder not found ({label}).', where)
                continue
            if target in started and started[target] != where:
                report.add('ensure', 'low', 'ensure-duplicate', f'{target} started twice ({label}).', f'{started[target]} and {where}')
            started.setdefault(target, where)
            order.append(target)
    return started, order


def check_dependencies(resources_map, order, report: Report):
    position = {name: i for i, name in reversed(list(enumerate(order)))}
    for name, entries in sorted(resources_map.items()):
        if name not in position:
            continue
        mf = entries[0][0] / 'fxmanifest.lua'
        try:
            data = parse_manifest(mf.read_text(encoding='utf-8-sig'))
        except (ManifestError, OSError, UnicodeError):
            continue
        for dep in data.get('dependency', []) + data.get('dependencies', []):
            dep = dep.split(':')[0].lstrip('/')
            if dep in position and position[dep] > position[name]:
                report.add('ensure', 'info', 'dependency-after',
                           f'{name} is started before its dependency {dep}; FXServer starts dependencies on demand, '
                           'but explicit order makes startup errors easier to read.', name)


# ---------------------------------------------------------------- versions

def version_tuple(v):
    nums = re.findall(r'\d+', v or '')
    return tuple(int(x) for x in nums[:4]) if nums else None


def manifest_version(mf: Path):
    try:
        text = mf.read_text(encoding='utf-8-sig')
    except OSError:
        return None, None
    m = re.search(r'^\s*version\s*[\(]?\s*[\'"]([^\'"]+)[\'"]', text, re.M)
    if not m:
        return None, None
    return m.group(1), text.count('\n', 0, m.start()) + 1


def check_versions(resources_map, report: Report, root: Path):
    try:
        baseline = json.loads(BASELINE.read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        report.add('versions', 'medium', 'baseline-missing', f'cannot read {BASELINE.name}: {exc}')
        return []
    rows = []
    for name, info in sorted(baseline.get('resources', {}).items()):
        if name not in resources_map:
            continue
        path = resources_map[name][0][0]
        version, line = manifest_version(path / 'fxmanifest.lua')
        where = f'{os.path.relpath(path / "fxmanifest.lua", root)}:{line}' if line else os.path.relpath(path / 'fxmanifest.lua', root)
        installed, base, safe = version_tuple(version), version_tuple(info.get('baseline')), version_tuple(info.get('min_safe'))
        if installed is None:
            status, sev = 'unknown', 'low'
        elif safe and installed < safe:
            status, sev = '< min-safe', 'high'
        elif base and installed < base:
            status, sev = '< baseline', 'low'
        elif base and installed > base:
            status, sev = '> baseline', 'info'
        else:
            status, sev = '= baseline', 'info'
        rows.append({'resource': name, 'installed': version or '?', 'min_safe': info.get('min_safe') or '-',
                     'baseline': info.get('baseline'), 'status': status, 'where': where})
        if sev != 'info':
            extra = f" Advisory: {info['advisory']}." if info.get('advisory') and status == '< min-safe' else ''
            report.add('versions', sev, 'version-' + status.replace(' ', '').replace('<', 'below-').replace('-', '', 0),
                       f'{name} {version or "?"} is {status} (min-safe {info.get("min_safe") or "-"}, baseline {info.get("baseline")}, '
                       f'verified {baseline.get("verified")}).{extra} A fork can carry a stale manifest version: confirm with its changelog/commit.',
                       where)
    return rows


# ---------------------------------------------------------------- data files / assets

def check_datafiles(resources_map, report: Report, root: Path):
    broken_total = 0
    for name, entries in sorted(resources_map.items()):
        for path, _ in entries:
            mf = path / 'fxmanifest.lua'
            if not mf.is_file():
                continue
            try:
                text = mf.read_text(encoding='utf-8-sig')
                pairs = parse_data_files(text)
                files_globs = parse_manifest(text).get('files', []) + parse_manifest(text).get('file', [])
            except (ManifestError, OSError, UnicodeError) as exc:
                report.add('datafiles', 'medium', 'manifest-unparsed', f'{name}: cannot parse manifest statically ({exc}).', str(mf))
                continue
            missing, uncovered = [], []
            covered = set()
            for g in files_globs:
                try:
                    covered.update(p.resolve() for p in glob_match(path, g))
                except ManifestError:
                    pass
            for dtype, rel, line in pairs:
                try:
                    hits = glob_match(path, rel)
                except ManifestError:
                    hits = []
                if not hits:
                    missing.append(f'{rel} (line {line}, {dtype})')
                elif not any(h.resolve() in covered for h in hits) and not rel.replace('\\', '/').startswith('stream/'):
                    uncovered.append(f'{rel} (line {line})')
            if missing:
                broken_total += len(missing)
                report.add('datafiles', 'medium', 'datafile-missing',
                           f'{name}: {len(missing)} of {len(pairs)} data_file path(s) do not exist, e.g. ' + '; '.join(missing[:5]),
                           os.path.relpath(mf, root))
            if uncovered:
                report.add('datafiles', 'low', 'datafile-not-in-files',
                           f'{name}: {len(uncovered)} data_file path(s) are not listed in files {{}} (clients may not receive them), e.g. '
                           + '; '.join(uncovered[:3]), os.path.relpath(mf, root))
    return broken_total


def check_assets(resources_map, report: Report, root: Path):
    sizes, big, names = {}, [], {}
    for name, entries in resources_map.items():
        for path, _ in entries:
            total = 0
            for base, dirs, files in os.walk(str(path)):
                dirs[:] = [d for d in dirs if d not in SKIP]
                for f in files:
                    fp = Path(base) / f
                    try:
                        size = fp.stat().st_size
                    except OSError:
                        continue
                    total += size
                    if fp.suffix.lower() in STREAM_EXT:
                        if size > LIMIT_MB * 1024 * 1024:
                            big.append((size, os.path.relpath(fp, root)))
                        names.setdefault(f.lower(), []).append(name)
            sizes[name] = sizes.get(name, 0) + total
    big.sort(reverse=True)
    if big:
        report.add('assets', 'medium', 'asset-over-16mib',
                   f'{len(big)} streamed file(s) exceed {LIMIT_MB} MiB (slow joins, memory spikes); largest: '
                   + '; '.join(f'{p} ({human(s)})' for s, p in big[:8]))
    # Streaming is keyed by file name: any repeated name (same or different resource) means one copy is dead weight.
    dupes = {n: r for n, r in names.items() if len(r) > 1}
    cross = {n: r for n, r in dupes.items() if len(set(r)) > 1}
    if dupes:
        sample = sorted(dupes.items())[:8]
        report.add('assets', 'low', 'asset-duplicate-name',
                   f'{len(dupes)} streamed file name(s) appear more than once ({len(cross)} across different resources); '
                   'only one copy is used - compare content before deleting. E.g. '
                   + '; '.join(f'{n} x{len(r)} [{", ".join(sorted(set(r)))}]' for n, r in sample))
    top = sorted(sizes.items(), key=lambda kv: -kv[1])[:10]
    report.add('assets', 'info', 'asset-largest', 'Largest resources: ' + '; '.join(f'{n} {human(s)}' for n, s in top)
               + f'. Total: {human(sum(sizes.values()))}.')
    return {'over_limit': len(big), 'duplicate_names': len(dupes), 'duplicate_names_cross_resource': len(cross),
            'total_bytes': sum(sizes.values())}


# ---------------------------------------------------------------- repo

def git(root: Path, *args):
    try:
        out = subprocess.run(['git', '-C', str(root), *args], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout if out.returncode == 0 else None


SCRIPT_REF = re.compile(r'''(?:%~dp0|\$PSScriptRoot[\\/]|\./|\.\\)?((?:[\w.-]+[\\/])*[\w.-]+\.(?:py|js|ps1|sh|bat|cmd|cfg|exe|json))''', re.I)


def check_repo(root: Path, resources: Path, report: Report):
    repo_dir = root if git(root, 'rev-parse', '--git-dir') else resources
    head = git(repo_dir, 'rev-parse', '--short', 'HEAD')
    if head:
        top = (git(repo_dir, 'rev-parse', '--show-toplevel') or str(repo_dir)).strip()
        status = git(repo_dir, 'status', '--porcelain', '--', '.') or ''
        lines = [l for l in status.splitlines() if l.strip()]
        deleted = [l[3:] for l in lines if l[:2].strip().startswith('D')]
        report.add('repo', 'info', 'git-state', f'Repository {top} at HEAD {head.strip()}; {len(lines)} uncommitted change(s) under the '
                   f'audited path ({len(deleted)} deleted). Audit what is deployed: say whether you reviewed HEAD or the working tree.')
        if deleted:
            report.add('repo', 'low', 'git-deleted-files', f'{len(deleted)} tracked file(s) deleted in the working tree, e.g. '
                       + ', '.join(deleted[:6]))
        subs = git(root, 'submodule', 'status')
        if subs:
            for l in subs.splitlines():
                if l[:1] in ('+', '-', 'U'):
                    report.add('repo', 'low', 'git-submodule-drift', f'submodule not at the recorded commit: {l.strip()}')
    else:
        report.add('repo', 'info', 'git-none', 'Not a git repository (or git unavailable): no history to diff against.')
    for base, dirs, _ in os.walk(str(resources)):
        rel = os.path.relpath(base, resources)
        for d in list(dirs):
            if d in ('.git', 'node_modules') and rel != '.':
                p = Path(base) / d
                size = sum(f.stat().st_size for f in p.rglob('*') if f.is_file()) if d == '.git' else None
                report.add('repo', 'low', 'nested-' + d.strip('.').replace('_', '-'),
                           f'{d} inside resources: {os.path.relpath(p, root)}' + (f' ({human(size)})' if size else '')
                           + ' - not served to clients but inflates deploys/backups; build outside the resources tree.')
        dirs[:] = [d for d in dirs if d not in SKIP]
    for script in sorted(list(root.glob('*.bat')) + list(root.glob('*.cmd')) + list(root.glob('*.ps1')) + list(root.glob('*.sh'))):
        try:
            text = script.read_text(encoding='utf-8', errors='replace')
        except OSError:
            continue
        for ln, line in enumerate(text.splitlines(), 1):
            if re.match(r'\s*(rem\b|::|#)', line, re.I):
                continue
            for m in SCRIPT_REF.finditer(line):
                ref = m.group(1).replace('\\', '/')
                if '/' not in ref or ref.lower().startswith(('http', 'c:/', 'd:/')):
                    continue
                if not (root / ref).exists() and not (script.parent / ref).exists():
                    report.add('repo', 'medium', 'script-missing-target', f'{script.name} references {ref}, which does not exist.',
                               f'{script.name}:{ln}')


# ---------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('path')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--section', action='append', choices=SECTIONS, help='run only these sections (repeatable)')
    ap.add_argument('--versions', action='store_true', help='shortcut for --section versions')
    a = ap.parse_args()
    path = Path(a.path)
    if not path.is_dir():
        print(f'not a directory: {path}', file=sys.stderr)
        return 2
    sections = set(a.section or ([] if not a.versions else ['versions']) or SECTIONS)
    if not sections:
        sections = set(SECTIONS)
    root, resources = find_layout(path)
    resources_map = discover_resources(resources)
    if not resources_map:
        print(f'no resources (fxmanifest.lua) under {resources}', file=sys.stderr)
        return 2
    report = Report()
    out = {'root': str(root), 'resources_dir': str(resources), 'resources': len(resources_map)}
    for name, entries in sorted(resources_map.items()):
        if len(entries) > 1:
            report.add('ensure', 'high', 'resource-name-duplicate',
                       f'resource name {name} exists {len(entries)} times; only one can start: '
                       + ', '.join(os.path.relpath(p, root) for p, _ in entries))
    commands, unreferenced = cfg_chain(root, resources, report) if sections & {'cfg', 'ensure'} else ([], [])
    if 'cfg' in sections:
        check_convars(commands, report, 'server.cfg chain')
        for cfg in unreferenced:
            check_convars([(cfg, ln, c, a2) for ln, c, a2 in cfg_commands(cfg)], report, cfg.name)
    if 'ensure' in sections:
        started, order = check_ensure(commands, resources_map, report, 'server.cfg chain')
        for cfg in unreferenced:
            s2, o2 = check_ensure([(cfg, ln, c, a2) for ln, c, a2 in cfg_commands(cfg)], resources_map, report, cfg.name)
            for k, v in s2.items():
                started.setdefault(k, v)
            order += o2
        check_dependencies(resources_map, order, report)
        never = sorted(n for n in resources_map if n not in started)
        if never:
            report.add('ensure', 'info', 'never-started', f'{len(never)} resource(s) on disk are never started by any cfg '
                       '(dead code is still audited; it may be started later): ' + ', '.join(never[:40]))
        out['started'] = len(started)
    if 'versions' in sections:
        out['versions'] = check_versions(resources_map, report, root)
    if 'datafiles' in sections:
        out['broken_data_files'] = check_datafiles(resources_map, report, root)
    if 'assets' in sections:
        out['assets'] = check_assets(resources_map, report, root)
    if 'repo' in sections:
        check_repo(root, resources, report)
    items = sorted(report.items, key=lambda i: (SECTIONS.index(i['section']), -SEV_ORDER[i['severity']], i['code'], i['where']))
    out['findings'] = items
    if a.json:
        print(json.dumps(out, indent=2))
    else:
        print(f'Server root: {root}\nResources dir: {resources}\nResources found: {len(resources_map)}'
              + (f'; started by cfg: {out["started"]}' if 'started' in out else ''))
        if out.get('versions'):
            print('\nInstalled versions vs baseline (assets/baseline.json):')
            print(f'  {"resource":16} {"installed":10} {"min-safe":9} {"baseline":9} {"status":12} where')
            for r in out['versions']:
                print(f'  {r["resource"]:16} {r["installed"]:10} {r["min_safe"]:9} {r["baseline"]:9} {r["status"]:12} {r["where"]}')
        current = None
        for i in items:
            if i['section'] != current:
                current = i['section']
                print(f'\n== {current}')
            print(f'  [{i["severity"].upper():6}] {i["code"]}: {i["message"]}' + (f'\n           at {i["where"]}' if i['where'] else ''))
        counts = {s: sum(1 for i in items if i['severity'] == s) for s in ('high', 'medium', 'low', 'info')}
        print(f'\nSummary: {counts}')
    return 1 if any(i['severity'] == 'high' for i in items) else 0


if __name__ == '__main__':
    sys.exit(main())
