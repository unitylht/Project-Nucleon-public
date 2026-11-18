"""A minimal Chrome DevTools Protocol client on the standard library, for deploy/action_page_check.py: starts Playwright's cached headless Chromium on a
free loopback debugging port with a throwaway profile, and evaluates JavaScript in its one page. No packages needed."""
import base64, json, os, socket, struct, subprocess, tempfile, time, urllib.request

import glob
CHROME = os.environ.get('CHROME_HEADLESS') or next(iter(sorted(glob.glob(os.path.expanduser(
    '~/Library/Caches/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-mac-arm64/chrome-headless-shell')))), None)


def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


class WS:
    def __init__(self, url):
        host, port, path = url[5:].split('/', 1)[0].split(':')[0], int(url[5:].split('/', 1)[0].split(':')[1]), '/' + url[5:].split('/', 1)[1]
        self.s = socket.create_connection((host, port), timeout=30)
        key = base64.b64encode(os.urandom(16)).decode()
        self.s.sendall(('GET %s HTTP/1.1\r\nHost: %s:%d\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\n\r\n' % (path, host, port, key)).encode())
        buf = b''
        while b'\r\n\r\n' not in buf:
            buf += self.s.recv(1)
        assert b' 101 ' in buf.split(b'\r\n')[0], buf
        self.buf = b''

    def send(self, text):
        data = text.encode()
        head = bytearray([0x81])
        n = len(data)
        if n < 126: head.append(0x80 | n)
        elif n < 65536: head += bytes([0x80 | 126]) + struct.pack('>H', n)
        else: head += bytes([0x80 | 127]) + struct.pack('>Q', n)
        mask = os.urandom(4)
        self.s.sendall(bytes(head) + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))

    def _read(self, n):
        while len(self.buf) < n:
            chunk = self.s.recv(65536)
            if not chunk: raise EOFError
            self.buf += chunk
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def recv(self):
        msg = b''
        while True:
            b1, b2 = self._read(2)
            n = b2 & 0x7f
            if n == 126: n = struct.unpack('>H', self._read(2))[0]
            elif n == 127: n = struct.unpack('>Q', self._read(8))[0]
            payload = self._read(n)
            op = b1 & 0x0f
            if op == 8: raise EOFError
            if op in (9, 10): continue
            msg += payload
            if b1 & 0x80: return msg.decode()


class Browser:
    def __init__(self):
        self.port = free_port()
        self.dir = tempfile.mkdtemp(prefix='cdp-')
        self.proc = subprocess.Popen([CHROME, '--remote-debugging-port=%d' % self.port, '--user-data-dir=' + self.dir, '--no-sandbox', '--disable-gpu', '--window-size=1280,900', 'about:blank'],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(100):
            try:
                targets = json.load(urllib.request.urlopen('http://127.0.0.1:%d/json' % self.port, timeout=1))
                page = next(t for t in targets if t['type'] == 'page')
                break
            except Exception:
                time.sleep(0.1)
        else:
            raise RuntimeError('chrome did not start')
        self.ws, self.n, self.events = WS(page['webSocketDebuggerUrl']), 0, []
        self.cmd('Page.enable'); self.cmd('Runtime.enable')

    def cmd(self, method, **params):
        self.n += 1
        mid = self.n
        self.ws.send(json.dumps({'id': mid, 'method': method, 'params': params}))
        while True:
            m = json.loads(self.ws.recv())
            if m.get('id') == mid:
                if 'error' in m: raise RuntimeError(m['error'])
                return m['result']
            self.events.append(m)

    def js(self, expr, await_=True):
        r = self.cmd('Runtime.evaluate', expression=expr, returnByValue=True, awaitPromise=await_)
        if 'exceptionDetails' in r:
            raise RuntimeError(json.dumps(r['exceptionDetails'])[:800])
        return r['result'].get('value')

    def goto(self, url):
        self.cmd('Page.navigate', url=url)
        time.sleep(0.6)

    def wait(self, expr, timeout=10):
        end = time.time() + timeout
        while time.time() < end:
            try:
                if self.js(expr): return True
            except RuntimeError:
                pass
            time.sleep(0.1)
        return False

    def errors(self):
        out = []
        for e in self.events:
            if e.get('method') == 'Runtime.exceptionThrown': out.append(json.dumps(e['params'])[:300])
            if e.get('method') == 'Runtime.consoleAPICalled' and e['params']['type'] == 'error': out.append(json.dumps(e['params']['args'])[:300])
        return out

    def close(self):
        self.proc.terminate()
