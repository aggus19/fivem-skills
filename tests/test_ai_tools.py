"""Offline tests for rcon.py and server_info.py (loopback fake servers only).
Run: python -m unittest discover -s tests -v"""
import contextlib
import importlib.util
import io
import json
import os
import socket
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parent.parent / "skills" / "fivem-development" / "scripts"


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / (name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


rcon = load("rcon")
server_info = load("server_info")


class FakeUdp:
    """Loopback UDP server answering one datagram with a canned reply."""

    def __init__(self, reply_fn):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", 0))
        self.sock.settimeout(5)
        self.port = self.sock.getsockname()[1]
        self.received = []
        self.reply_fn = reply_fn
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        try:
            data, addr = self.sock.recvfrom(65535)
        except OSError:
            return
        self.received.append(data)
        reply = self.reply_fn(data)
        if reply is not None:
            self.sock.sendto(reply, addr)

    def close(self):
        self.sock.close()
        self.thread.join(2)


class RconTests(unittest.TestCase):
    def test_build_packet(self):
        self.assertEqual(rcon.build_packet("pw", "ensure x"), b"\xff\xff\xff\xffrcon pw ensure x")

    def test_password_with_space_refused(self):
        with self.assertRaises(rcon.RconError):
            rcon.build_packet("a b", "status")
        with self.assertRaises(rcon.RconError):
            rcon.build_packet("", "status")

    def test_parse_reply_and_colors(self):
        out = rcon.parse_reply(b"\xff\xff\xff\xffprint ^2ok^7 done\n")
        self.assertEqual(rcon.strip_colors(out), "ok done\n")

    def test_loopback_check(self):
        self.assertTrue(rcon.is_loopback("127.0.0.1"))
        self.assertTrue(rcon.is_loopback("localhost"))
        self.assertFalse(rcon.is_loopback("8.8.8.8"))
        self.assertFalse(rcon.is_loopback("example.com"))

    def test_send_roundtrip(self):
        srv = FakeUdp(lambda d: b"\xff\xff\xff\xffprint Started resource x\n")
        try:
            reply = rcon.send_rcon("127.0.0.1", srv.port, "secret", "ensure x", 2)
        finally:
            srv.close()
        self.assertIn("Started resource x", reply)
        self.assertEqual(srv.received[0], b"\xff\xff\xff\xffrcon secret ensure x")

    def test_timeout_error(self):
        srv = FakeUdp(lambda d: None)
        try:
            with self.assertRaises(rcon.RconError):
                rcon.send_rcon("127.0.0.1", srv.port, "secret", "status", 0.3)
        finally:
            srv.close()

    def _run_main(self, argv, env):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.dict(os.environ, env, clear=False), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = rcon.main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_main_requires_env_password(self):
        env = {k: v for k, v in os.environ.items() if k != "FIVEM_RCON_PASSWORD"}
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.dict(os.environ, env, clear=True), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = rcon.main(["status"])
        self.assertEqual(code, 2)
        self.assertIn("FIVEM_RCON_PASSWORD", err.getvalue())

    def test_main_refuses_remote(self):
        code, _, err = self._run_main(["--host", "203.0.113.5", "status"], {"FIVEM_RCON_PASSWORD": "x"})
        self.assertEqual(code, 2)
        self.assertIn("non-loopback", err)

    def test_main_invalid_password_and_expect(self):
        srv = FakeUdp(lambda d: b"\xff\xff\xff\xffprint Invalid password.\n")
        try:
            code, out, _ = self._run_main(["--port", str(srv.port), "status"], {"FIVEM_RCON_PASSWORD": "bad"})
        finally:
            srv.close()
        self.assertEqual(code, 1)
        self.assertIn("Invalid password", out)

        srv = FakeUdp(lambda d: b"\xff\xff\xff\xffprint Started resource foo\n")
        try:
            code, _, _ = self._run_main(["--port", str(srv.port), "--expect", "Started resource foo", "ensure", "foo"],
                                        {"FIVEM_RCON_PASSWORD": "good"})
        finally:
            srv.close()
        self.assertEqual(code, 0)

        srv = FakeUdp(lambda d: b"\xff\xff\xff\xffprint nothing\n")
        try:
            code, _, _ = self._run_main(["--port", str(srv.port), "--expect", "Started", "ensure", "foo"],
                                        {"FIVEM_RCON_PASSWORD": "good"})
        finally:
            srv.close()
        self.assertEqual(code, 1)


class _Handler(BaseHTTPRequestHandler):
    seen = []

    def log_message(self, *args):
        pass

    def do_GET(self):
        _Handler.seen.append((self.path, self.headers.get("X-Players-Token")))
        routes = {
            "/info.json": {"server": "FXServer-test v1", "resources": ["chat", "myres"]},
            "/dynamic.json": {"hostname": "Test", "clients": 1, "sv_maxclients": 8,
                              "gametype": "x", "mapname": "y", "iv": "1"},
            "/players.json": [{"id": 0, "name": "Player", "identifiers": [], "ping": 0}],
        }
        body = routes.get(self.path)
        if body is None:
            self.send_response(404)
            self.end_headers()
            return
        data = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


class ServerInfoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = HTTPServer(("127.0.0.1", 0), _Handler)
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def _run(self, argv, env=None):
        out, err = io.StringIO(), io.StringIO()
        base = {k: v for k, v in os.environ.items() if k != "FIVEM_PLAYERS_TOKEN"}
        base.update(env or {})
        with mock.patch.dict(os.environ, base, clear=True), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = server_info.main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_summary_json_placeholders(self):
        code, out, _ = self._run(["127.0.0.1:%d" % self.port, "--json", "--resource", "myres"])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["resource_count"], 2)
        self.assertTrue(data["resource_listed"])
        self.assertTrue(data["players_are_placeholders"])
        self.assertEqual(data["clients"], 1)

    def test_missing_resource_exit_1(self):
        code, _, err = self._run(["http://127.0.0.1:%d" % self.port, "--resource", "nope"])
        self.assertEqual(code, 1)
        self.assertIn("NOT listed", err)

    def test_token_sent_as_header(self):
        _Handler.seen.clear()
        code, out, _ = self._run(["127.0.0.1:%d" % self.port, "--json"], {"FIVEM_PLAYERS_TOKEN": "tok"})
        self.assertEqual(code, 0)
        self.assertFalse(json.loads(out)["players_are_placeholders"])
        self.assertIn(("/players.json", "tok"), _Handler.seen)

    def test_unreachable_exit_2(self):
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        code, _, err = self._run(["127.0.0.1:%d" % port, "--timeout", "1"])
        self.assertEqual(code, 2)
        self.assertIn("cannot read", err)

    def test_getinfo_probe(self):
        reply = b"\xff\xff\xff\xffinfoResponse\n\\sv_maxclients\\8\\clients\\1\\challenge\\fivem0\\iv\\123"
        srv = FakeUdp(lambda d: reply)
        try:
            info = server_info.getinfo_probe("127.0.0.1", srv.port, 2)
        finally:
            srv.close()
        self.assertEqual(info["clients"], "1")
        self.assertEqual(srv.received[0], b"\xff\xff\xff\xffgetinfo fivem0")
        with self.assertRaises(ValueError):
            server_info.getinfo_probe("127.0.0.1", 1, 1, challenge=b"123456789")


if __name__ == "__main__":
    unittest.main()
