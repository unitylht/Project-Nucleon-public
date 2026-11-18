"""The records instance over HTTP, as the person: every request forwards the browser's whole Cookie header, so the records
decide the role and what it may see. A client per request keeps it independent of the event loop that runs it. Every call is timed
against the turn under way (lab.timing). A call whose connection failed before an answer came (refused, reset, closed) is sent once
more, the same request with the same Idempotency-Key, so the records run a write at most once; a timeout is not sent again (the records
may still be working), and nothing else is replayed."""
import httpx2

from .timing import records_call

TIMEOUT = httpx2.Timeout(300, connect=10)   # the records tool deadline is 300 s (a local model may be busy)
RESENT = (httpx2.ConnectError, httpx2.RemoteProtocolError, httpx2.ReadError, httpx2.WriteError)   # no answer came; a timeout is not one of them


class Cookie(str):
    """The browser's Cookie header, with the role this request acts as when the session holds several (the AI Agent's): it goes to
    the records as X-Nucleon-Role. A plain string carries none, as before."""
    role = None

    def __new__(cls, header, role=None):
        self = super().__new__(cls, header)
        self.role = role
        return self


def headers_for(cookie, more=None):
    role = getattr(cookie, 'role', None)
    return {'Cookie': cookie or '', **({'X-Nucleon-Role': role} if role else {}), **(more or {})}


class Records:
    def __init__(self, base_url, transport=None):
        self.base_url, self.transport = base_url.rstrip('/'), transport   # transport: a test's stand-in for the network

    def client(self):
        return httpx2.AsyncClient(base_url=self.base_url, timeout=TIMEOUT, **({'transport': self.transport} if self.transport else {}))

    async def session(self, cookie, prefer=None):
        """{role, workspace, identity, held} for a signed-in owner or staff member, else None (no session, several roles, or the
        console). The AI Agent holds a session for every role: the role is `prefer` if held, else staff; the answer says which."""
        with records_call():
            return await self._session(cookie, prefer)

    async def _session(self, cookie, prefer):
        async with self.client() as c:
            r = await c.get('/api/session', headers={'Cookie': cookie or ''})
            s = r.json() if r.status_code == 200 else {}
            held = [x for x in s.get('signedIn', []) if x in ('staff', 'owner')]
            if not s.get('authenticated') and s.get('identity') and held:   # several roles held, by one identity: pick one
                role = prefer if prefer in held else 'staff' if 'staff' in held else held[0]
                r = await c.get('/api/session', headers=headers_for(Cookie(cookie or '', role)))
                s = r.json() if r.status_code == 200 else {}
        if not s.get('authenticated') or s.get('role') not in ('owner', 'staff'):
            return None
        out = {'role': s['role'], 'workspace': s.get('workspace')}
        if s.get('identity') and s['identity'].get('kind') == 'agent':
            out.update(identity=s['identity'], held=sorted(set(s.get('signedIn', [])) | {s['role']}))
        return out

    async def info(self, cookie):
        """{dataMode, asOfDate} of the records' own session for this request (the role the cookie carries): read only."""
        async with self.client() as c:
            r = await c.get('/api/session', headers=headers_for(cookie))
        s = r.json() if r.status_code == 200 else {}
        return {'dataMode': s.get('dataMode'), 'asOfDate': s.get('asOfDate')}

    async def tools(self, cookie):
        """GET api/tools: (status, body), the registry for this role."""
        with records_call():
            async with self.client() as c:
                r = await c.get('/api/tools', headers=headers_for(cookie))
        return r.status_code, r.json()

    async def call(self, cookie, name, args, message, current=None, key=None):
        """POST api/tools/<name>: {ok: true, result} or {ok: false, error, message}, an HTTP refusal (403, 404, 409) included. key: the
        write's Idempotency-Key (the same key for the same operation), kept when it is sent again."""
        headers = headers_for(cookie, {'Idempotency-Key': key} if key else None)
        body = {'args': args, 'message': message, 'current': current or {}}
        with records_call():
            async with self.client() as c:
                try:
                    r = await c.post('/api/tools/' + name, headers=headers, json=body)
                except RESENT:   # no answer: the same request once more (the records answer a key they saw with what they did then)
                    r = await c.post('/api/tools/' + name, headers=headers, json=body)
        body = r.json()
        return body if r.status_code == 200 else {'ok': False, 'error': body.get('error', 'HTTP_' + str(r.status_code)), 'message': body.get('message', '')}
