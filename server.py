#!/usr/bin/env python3
"""GNATOVSKIE Voice Gateway: authenticated text requests to a local assistant CLI."""
import hmac
import json
import os
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class Gateway(ThreadingHTTPServer):
    daemon_threads = True
    def __init__(self, address, command, token, timeout=90, workdir=None):
        if not token or not command or not all(isinstance(x, str) for x in command):
            raise ValueError('A token and a command argument array are required')
        self.command, self.token, self.timeout, self.workdir = command, token, timeout, workdir
        self.slots = threading.BoundedSemaphore(2)
        super().__init__(address, Handler)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass  # Requests can contain personal data.

    def reply(self, status, text):
        body = text.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        self.connection.settimeout(10)
        if self.path != '/ask':
            return self.reply(404, 'Not found')
        given = self.headers.get('Authorization', '').encode()
        expected = ('Bearer ' + self.server.token).encode()
        if not hmac.compare_digest(given, expected):
            return self.reply(401, 'Unauthorized')
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 16384:
                return self.reply(413, 'Request must contain 1 to 16384 bytes')
            raw = self.rfile.read(size)
            if len(raw) != size:
                return self.reply(400, 'Incomplete request')
            text = raw.decode('utf-8')
            if self.headers.get('Content-Type', '').startswith('application/json'):
                text = json.loads(text)['q']
            if not isinstance(text, str) or not text.strip() or len(text) > 4000:
                return self.reply(400, 'Question must contain 1 to 4000 characters')
        except (ValueError, KeyError, TypeError, OSError):
            return self.reply(400, 'Invalid question')
        if not self.server.slots.acquire(blocking=False):
            return self.reply(429, 'Busy')
        try:
            result = subprocess.run(self.server.command, input=text, text=True,
                capture_output=True, timeout=self.server.timeout, cwd=self.server.workdir)
            if result.returncode:
                return self.reply(502, 'Assistant failed')
            self.reply(200, result.stdout.strip())
        except subprocess.TimeoutExpired:
            self.reply(504, 'Assistant timed out')
        except OSError:
            self.reply(502, 'Assistant unavailable')
        finally:
            self.server.slots.release()


def main():
    token = Path(os.environ['VOICE_TOKEN_FILE']).read_text().strip()
    command = json.loads(os.environ['VOICE_COMMAND'])
    if not isinstance(command, list):
        raise ValueError('VOICE_COMMAND must be a JSON argument array')
    Gateway((os.environ.get('VOICE_HOST', '127.0.0.1'), int(os.environ.get('VOICE_PORT', '8787'))),
        command, token, int(os.environ.get('VOICE_TIMEOUT', '90')),
        os.environ.get('VOICE_WORKDIR')).serve_forever()


if __name__ == '__main__':
    main()
