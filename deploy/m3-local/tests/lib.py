import json, urllib.request, urllib.error, http.cookiejar
B='http://127.0.0.1:8631'
CFG=json.load(open('/Users/unitylht/Developer/nucleon-local/config/records.json'))
class Api:
    def __init__(s, role):
        s.role=role; s.cj=http.cookiejar.CookieJar(policy=http.cookiejar.DefaultCookiePolicy(secure_protocols=('https','wss','http')))  # Records cookies are Secure when an https public origin is configured; loopback http is a secure context for browsers, so allow it here too
        s.op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(s.cj))
        r=s.req('POST','/api/demo/login',{'accessCode':CFG['accessCodes'][role],'role':role},csrf=False)
        assert r[0]==200, r
        s.csrf=s.req('GET','/api/session',csrf=False)[1]['csrf']
    def req(s,m,p,body=None,csrf=True,key=None):
        h={'Origin':B,'Content-Type':'application/json'}
        if csrf and m!='GET': h['X-Nucleon-CSRF']=s.csrf
        if key: h['Idempotency-Key']=key
        rq=urllib.request.Request(B+p,data=None if body is None else json.dumps(body).encode(),headers=h,method=m)
        try: r=s.op.open(rq,timeout=20)
        except urllib.error.HTTPError as e: r=e
        t=r.read().decode()
        try: return r.status,json.loads(t)
        except Exception: return r.status,t
