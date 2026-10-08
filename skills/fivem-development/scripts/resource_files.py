"""Static manifest/file helpers. Never execute manifests. Python 3.8+, stdlib only.

Supports literal directive calls, lists, comments, Lua quoted/long strings and
metadata extras. Computed directives require a manual/runtime review and fail
explicitly; this is deliberately not a complete Lua interpreter or syntax check.
"""
from __future__ import annotations

import re
from pathlib import Path, PureWindowsPath

LIST_DIRECTIVES = {
    'client_script': 'client', 'client_scripts': 'client',
    'server_script': 'server', 'server_scripts': 'server',
    'shared_script': 'shared', 'shared_scripts': 'shared',
    'file': 'files', 'files': 'files',
}
SKIP_DIRS = {'.git', 'node_modules', '__pycache__'}
LONG_OPEN = re.compile(r'\[(=*)\[')
NAME = re.compile(r'[A-Za-z_][A-Za-z_0-9]*')
DECIMAL_ESCAPE = re.compile(r'[0-9]{1,3}')


class ManifestError(ValueError):
    pass


def tokens(text):
    """Yield (kind, decoded value, start, end), retaining source positions."""
    i = 0
    while i < len(text):
        start = i
        if text[i].isspace():
            i += 1
            continue
        comment = text.startswith('--', i)
        pos = i + 2 if comment else i
        long = LONG_OPEN.match(text, pos)
        if long:
            endmark = ']' + long[1] + ']'
            begin = pos + len(long[0])
            end = text.find(endmark, begin)
            if end < 0:
                raise ManifestError('unterminated long string/comment')
            i = end + len(endmark)
            if not comment:
                value = text[begin:end]
                yield 'string', value[1:] if value.startswith('\n') else value, start, i
            continue
        if comment:
            end = text.find('\n', i)
            i = len(text) if end < 0 else end
            continue
        if text[i] in "\"'`":
            quote = text[i]
            i += 1
            chars = []
            while i < len(text) and text[i] != quote:
                c = text[i]
                i += 1
                if c in '\r\n':
                    raise ManifestError('newline in quoted string')
                if c == '\\':
                    if i == len(text):
                        raise ManifestError('unterminated escape')
                    c = text[i]
                    i += 1
                    escapes = {'a': '\a', 'b': '\b', 'f': '\f', 'n': '\n', 'r': '\r', 't': '\t', 'v': '\v'}
                    if c == 'z':
                        while i < len(text) and text[i].isspace():
                            i += 1
                        continue
                    if c == 'x':
                        digits = text[i:i + 2]
                        if not re.fullmatch(r'[0-9a-fA-F]{2}', digits):
                            raise ManifestError('invalid hexadecimal string escape')
                        chars.append(chr(int(digits, 16)))
                        i += 2
                        continue
                    if c.isdigit():
                        number = DECIMAL_ESCAPE.match(text, i - 1)
                        if not number:
                            raise ManifestError('invalid decimal string escape')
                        digits = number[0]
                        if int(digits) > 255:
                            raise ManifestError('decimal string escape exceeds 255')
                        chars.append(chr(int(digits)))
                        i += len(digits) - 1
                        continue
                    if c not in escapes and c not in "\\\"'\n\r`":
                        raise ManifestError('unsupported string escape: \\' + c)
                    c = escapes.get(c, c)
                chars.append(c)
            if i == len(text):
                raise ManifestError('unterminated quoted string')
            i += 1
            yield ('hash' if quote == '`' else 'string'), ''.join(chars), start, i
            continue
        word = NAME.match(text, i)
        if word:
            i += len(word[0])
            yield 'name', word[0], start, i
        else:
            i += 1
            yield text[start], text[start], start, i


def mask_lua(text):
    """Remove comments and strings, preserving columns/newlines for diagnostics."""
    chars = ['\n' if c == '\n' else ' ' for c in text]
    for kind, value, start, end in tokens(text):
        if kind not in ('string', 'hash'):
            chars[start:end] = text[start:end]
    return ''.join(chars)


def parse_manifest(text):
    stream = list(tokens(text))
    i = 0
    out = {}

    def fail(message):
        pos = stream[i][2] if i < len(stream) else len(text)
        raise ManifestError('line %s: %s (static literal manifests only)' % (text.count('\n', 0, pos) + 1, message))

    def argument():
        nonlocal i
        if i >= len(stream):
            fail('missing argument')
        kind, value, _, _ = stream[i]
        i += 1
        if kind == 'string':
            return [value]
        if kind == '(':
            values = argument()
            if i >= len(stream) or stream[i][0] != ')':
                fail('expected closing parenthesis')
            i += 1
            return values
        if kind == '{':
            values = []
            while i < len(stream) and stream[i][0] != '}':
                if stream[i][0] != 'string':
                    fail('expected literal string in list')
                values.append(stream[i][1])
                i += 1
                if i < len(stream) and stream[i][0] in (',', ';'):
                    i += 1
                elif i < len(stream) and stream[i][0] != '}':
                    fail('expected list separator')
            if i >= len(stream):
                fail('unterminated list')
            i += 1
            return values
        fail('computed or unsupported argument')

    while i < len(stream):
        if stream[i][0] == ';':
            i += 1
            continue
        if stream[i][0] != 'name':
            fail('expected directive')
        key = stream[i][1]
        i += 1
        values = argument()
        out.setdefault(key, []).extend(values)
        # Chained metadata extras (data_file 'TYPE' 'path', convar_category, etc.).
        while i < len(stream) and stream[i][0] in ('string', '{', '('):
            if key in LIST_DIRECTIVES or key in ('dependency', 'dependencies', 'ui_page'):
                fail('unexpected extra argument to ' + key)
            if stream[i][0] == 'string':
                i += 1
                continue
            stack = []
            while i < len(stream):
                kind = stream[i][0]
                i += 1
                if kind in ('{', '('):
                    stack.append('}' if kind == '{' else ')')
                elif kind in ('}', ')'):
                    if not stack or stack.pop() != kind:
                        fail('unbalanced metadata extras')
                    if not stack:
                        break
            if stack:
                fail('unterminated metadata extras')
    return out


def parse_data_files(text):
    """Return [(type, path, line)] for `data_file 'TYPE' 'path'` and `data_file 'TYPE' { 'a', 'b' }`.

    parse_manifest() keeps only the directive's first argument (the type); this
    reads the chained path argument(s) so they can be checked against the disk.
    """
    stream = list(tokens(text))
    out = []
    i = 0
    while i < len(stream):
        kind, value, start, _ = stream[i]
        if kind == 'name' and value == 'data_file':
            j = i + 1
            if j < len(stream) and stream[j][0] == '(':
                j += 1
            if j < len(stream) and stream[j][0] == 'string':
                dtype = stream[j][1]
                j += 1
                if j < len(stream) and stream[j][0] == ')':
                    j += 1
                line = text.count('\n', 0, start) + 1
                if j < len(stream) and stream[j][0] == 'string':
                    out.append((dtype, stream[j][1], line))
                    j += 1
                elif j < len(stream) and stream[j][0] == '{':
                    j += 1
                    while j < len(stream) and stream[j][0] != '}':
                        if stream[j][0] == 'string':
                            out.append((dtype, stream[j][1], line))
                        j += 1
            i = j
            continue
        i += 1
    return out


def glob_match(root, pattern):
    root = root.resolve()
    pattern = pattern.replace('\\', '/')
    if not pattern or pattern.startswith('/') or PureWindowsPath(pattern).drive or '..' in pattern.split('/'):
        raise ManifestError('path must stay inside resource: ' + pattern)
    # Cfx supports **.lua as well as **/*.lua.
    pattern = re.sub(r'\*\*(?!/|$)', '**/*', pattern)
    # Cfx globs only know * and **: '[category]' folders are literal names, not character classes.
    pattern = re.sub(r'[\[\]]', lambda m: '[' + m.group(0) + ']', pattern)
    matches = sorted(p for p in root.glob(pattern) if p.is_file())
    for path in matches:
        try:
            path.resolve().relative_to(root)
        except ValueError:
            raise ManifestError('symlink leaves resource: ' + str(path))
    return matches


def walk_files(root):
    """Include shipped build/stream code; skip dependencies and VCS directories."""
    if root.is_file():
        yield root
        return
    import os
    for base, dirs, names in os.walk(str(root), followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for name in sorted(names):
            path = Path(base) / name
            if path.is_file():
                yield path


def nearest_manifest(path):
    for parent in path.resolve().parents:
        candidate = parent / 'fxmanifest.lua'
        if candidate.is_file():
            return candidate
    return None


def script_sides(manifest):
    """Map resolved local script paths to the runtimes in which they execute."""
    data = parse_manifest(manifest.read_text(encoding='utf-8-sig'))
    result = {}
    for key, kind in LIST_DIRECTIVES.items():
        if kind == 'files':
            continue
        for entry in data.get(key, []):
            if entry.startswith('@'):
                continue  # external resource must be checked separately
            for path in glob_match(manifest.parent, entry):
                result.setdefault(path.resolve(), set()).update({'client', 'server'} if kind == 'shared' else {kind})
    return result
