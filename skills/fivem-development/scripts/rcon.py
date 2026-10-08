#!/usr/bin/env python3
"""Send ONE RCON command to an FXServer over UDP and print the reply.

FXServer RCON is an out-of-band UDP datagram to the game port:
    FF FF FF FF  "rcon"  " "  <password> " " <command>
Reply: one datagram  FF FF FF FF "print " <captured output>.  (Not Valve/Source RCON.)

Usage:
  FIVEM_RCON_PASSWORD=... python rcon.py [--host 127.0.0.1] [--port 30120]
        [--timeout 3] [--expect REGEX] [--allow-remote] <command...>
The password is read ONLY from the env var FIVEM_RCON_PASSWORD (never argv: it would
land in shell history). It cannot contain whitespace (the server splits on the first space).
Dev servers only; RCON is plaintext. See references/ai-dev-workflow-and-mcp.md.
Exit codes: 0 ok, 1 --expect did not match / server rejected, 2 usage/network error.
Standard library only (Python 3.8+).
"""
from __future__ import annotations

import argparse
import ipaddress
import os
import re
import socket
import sys

OOB = b"\xff\xff\xff\xff"
ENV_VAR = "FIVEM_RCON_PASSWORD"
COLOR_RE = re.compile(r"\^[0-9]")


class RconError(Exception):
    pass


def build_packet(password: str, command: str) -> bytes:
    if not password:
        raise RconError("empty RCON password")
    if re.search(r"\s", password):
        raise RconError("RCON password must not contain whitespace "
                        "(FXServer splits the packet on the first space/newline)")
    command = command.strip()
    if not command:
        raise RconError("empty command")
    return OOB + b"rcon " + password.encode("utf-8") + b" " + command.encode("utf-8")


def parse_reply(data: bytes) -> str:
    if data.startswith(OOB):
        data = data[4:]
    if data.startswith(b"print "):
        data = data[6:]
    elif data.startswith(b"print"):
        data = data[5:]
    return data.decode("utf-8", errors="replace")


def strip_colors(text: str) -> str:
    return COLOR_RE.sub("", text)


def is_loopback(host: str) -> bool:
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def send_rcon(host: str, port: int, password: str, command: str, timeout: float = 3.0) -> str:
    packet = build_packet(password, command)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(timeout)
        try:
            sock.sendto(packet, (host, port))
            data, _ = sock.recvfrom(65535)
        except socket.timeout:
            raise RconError("no reply within %.1fs (server down, wrong port, or rate limited: "
                            "0.2/s burst 5 per IP)" % timeout)
        except OSError as exc:
            raise RconError("network error: %s" % exc)
    return parse_reply(data)


def _safe_console():
    """Never crash on consoles that cannot encode a character (Windows cp1252, redirected pipes)."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass


def main(argv=None) -> int:
    _safe_console()
    ap = argparse.ArgumentParser(description="Send one RCON command to FXServer (UDP).")
    ap.add_argument("command", nargs="+", help="console command, e.g. ensure myres")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=30120)
    ap.add_argument("--timeout", type=float, default=3.0)
    ap.add_argument("--expect", metavar="REGEX", help="exit 1 unless the reply matches")
    ap.add_argument("--allow-remote", action="store_true",
                    help="permit non-loopback hosts (RCON is plaintext!)")
    args = ap.parse_args(argv)

    password = os.environ.get(ENV_VAR, "")
    if not password:
        print("error: set the RCON password in env var %s (never pass it as an argument)" % ENV_VAR,
              file=sys.stderr)
        return 2
    if not is_loopback(args.host) and not args.allow_remote:
        print("error: refusing non-loopback host %r (RCON is plaintext); use --allow-remote" % args.host,
              file=sys.stderr)
        return 2
    try:
        reply = strip_colors(send_rcon(args.host, args.port, password,
                                       " ".join(args.command), args.timeout))
    except RconError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2
    print(reply.rstrip("\n"))
    low = reply.strip().lower()
    if low.startswith("invalid password") or low.startswith("the server must set rcon_password"):
        return 1
    if args.expect and not re.search(args.expect, reply):
        print("error: reply did not match --expect %r" % args.expect, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
