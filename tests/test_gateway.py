import http.client
import sys
import threading
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server import Gateway

class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.server = Gateway(('127.0.0.1', 0), [sys.executable, '-c', 'import sys; print(sys.stdin.read().upper())'], 'fixture')
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.start()
    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join()
    def ask(self, body, token='fixture', **headers):
        conn = http.client.HTTPConnection(*self.server.server_address)
        conn.request('POST', '/ask', body, {'Authorization': 'Bearer '+token, **headers})
        response = conn.getresponse(); result = response.status, response.read().decode(); conn.close(); return result
    def test_command_receives_text_without_shell_interpolation(self):
        self.assertEqual(self.ask('hello $(id)'), (200, 'HELLO $(ID)'))
    def test_rejects_wrong_token(self):
        self.assertEqual(self.ask('hello', token='wrong')[0], 401)
    def test_accepts_json(self):
        self.assertEqual(self.ask('{"q":"hello"}', **{'Content-Type':'application/json'}), (200,'HELLO'))
    def test_rejects_bad_json(self):
        self.assertEqual(self.ask('{', **{'Content-Type':'application/json'})[0],400)
    def test_reports_failed_command_without_stderr(self):
        self.server.command=[sys.executable,'-c','import sys;sys.stderr.write("private");sys.exit(1)']
        self.assertEqual(self.ask('hello'),(502,'Assistant failed'))
    def test_reports_timeout(self):
        self.server.timeout=0.05
        self.server.command=[sys.executable,'-c','import time;time.sleep(2)']
        self.assertEqual(self.ask('hello')[0],504)

if __name__ == '__main__': unittest.main()
