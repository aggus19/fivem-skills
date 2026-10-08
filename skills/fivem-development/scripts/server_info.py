#!/usr/bin/env python3
"""Summarise a running FXServer from its public HTTP endpoints (no RCON needed).

Reads /info.json, /dynamic.json and /players.json on the game port and prints a summary.
Unauthenticated /players.json returns placeholder entries (only the count is real); set
env var FIVEM_PLAYERS_TOKEN (= sv_playersToken) for real data. Plain headers only, so
sv_requestParanoia never blocks your IP. Optional UDP `getinfo` liveness probe.

Usage:
  python server_info.py [host:port | http://host:port] [--resource NAME] [--getinfo]
                        [--timeout 4] [--json]
Exit codes: 0 ok, 1 --resource not found in info.json, 2 server unreachable/usage error.
Standard library only (Python 3.8+). See references/ai-dev-workflow-and-mcp.md.
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import urllib.error
import urllib.request

TOKEN_ENV = "FIVEM_PLAYERS_TOKEN"


def normalize_base(target: str) -> str:
    target = target.strip().rstrip("/")
    if "://" not in target:
        target = "http://" + target
    return target


def fetch_json(base: str, path: str, timeout: float, headers=None):
    req = urllib.request.Request(base + path, headers=dict(headers or {}))
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def getinfo_probe(host: str, port: int, timeout: float, challenge: bytes = b"fivem0") -> dict:
    """UDP out-of-band getinfo; challenge must be <= 8 bytes. Returns the key/value map."""
    if len(challenge) > 8:
        raise ValueError("getinfo challenge must be at most 8 bytes")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(timeout)
        sock.sendto(b"\xff\xff\xff\xffgetinfo " + challenge, (host, port))
        data, _ = sock.recvfrom(65535)
    text = data.decode("utf-8", errors="replace")
    if "infoResponse" not in text:
        raise ValueError("unexpected getinfo reply: %r" % text[:80])
    parts = text.split("\n", 1)[1].split("\\")[1:] if "\n" in text else []
    return dict(zip(parts[0::2], parts[1::2]))


def summarize(info, dynamic, players, resource=None, has_token=False) -> dict:
    resources = list((info or {}).get("resources") or [])
    out = {
        "server": (info or {}).get("server"),
        "hostname": (dynamic or {}).get("hostname"),
        "clients": (dynamic or {}).get("clients"),
        "sv_maxclients": (dynamic or {}).get("sv_maxclients"),
        "gametype": (dynamic or {}).get("gametype"),
        "mapname": (dynamic or {}).get("mapname"),
        "resource_count": len(resources),
        "players_listed": len(players) if isinstance(players, list) else None,
        "players_are_placeholders": (not has_token) and bool(players),
    }
    if resource is not None:
        out["resource"] = resource
        out["resource_listed"] = resource in resources
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Summarise an FXServer via /info.json etc.")
    ap.add_argument("target", nargs="?", default="127.0.0.1:30120")
    ap.add_argument("--resource", help="exit 1 if this resource is not in info.json")
    ap.add_argument("--getinfo", action="store_true", help="also send a UDP getinfo probe")
    ap.add_argument("--timeout", type=float, default=4.0)
    ap.add_argument("--json", action="store_true", help="print the summary as JSON")
    args = ap.parse_args(argv)

    base = normalize_base(args.target)
    token = os.environ.get(TOKEN_ENV, "")
    try:
        info = fetch_json(base, "/info.json", args.timeout)
        dynamic = fetch_json(base, "/dynamic.json", args.timeout)
        players = fetch_json(base, "/players.json", args.timeout,
                             {"X-Players-Token": token} if token else None)
    except urllib.error.HTTPError as exc:
        print("error: HTTP %s from %s (rate limit 4/s, or sv_requestParanoia block)" % (exc.code, exc.url),
              file=sys.stderr)
        return 2
    except (urllib.error.URLError, OSError, ValueError) as exc:
        print("error: cannot read %s: %s" % (base, exc), file=sys.stderr)
        return 2

    summary = summarize(info, dynamic, players, args.resource, bool(token))
    if args.getinfo:
        hp = base.split("://", 1)[1].split("/")[0]
        host, _, port = hp.partition(":")
        try:
            summary["getinfo"] = getinfo_probe(host, int(port or 30120), args.timeout)
        except (OSError, ValueError) as exc:
            summary["getinfo_error"] = str(exc)

    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        for key, value in summary.items():
            print("%-24s %s" % (key, value))
        if summary["players_are_placeholders"]:
            print("note: /players.json is anonymized without %s (only the count is real)" % TOKEN_ENV)
    if args.resource is not None and not summary["resource_listed"]:
        print("resource %r is NOT listed in info.json" % args.resource, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
