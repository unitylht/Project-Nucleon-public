import sys; sys.path.insert(0,'/Users/unitylht/Developer/nucleon-local/tests/s6b')
from lc import *
OWNER_AG=sys.argv[1]; STAFF_AG='agent_biPGuKnO2VgHEQ67HsLHL'
JS="""async ([id])=>{const t=(await (await fetch('/api/auth/refresh',{method:'POST',credentials:'include'})).json()).token;
const h={Authorization:'Bearer '+t,'Content-Type':'application/json'};
const g=await fetch('/api/agents/'+id,{headers:h}); const getS=g.status; let d=null; try{d=(await g.json()).description}catch(e){}
const p=await fetch('/api/agents/'+id,{method:'PATCH',headers:h,body:JSON.stringify({description:d})});
return {get:getS,patch:p.status}}"""
with sync_playwright() as p:
    for role in ['owner','staff']:
        b,ctx,pg=session(p); a=role_creds(role); login(pg,a['email'],a['password'])
        for nm,ag in [('ownerAgent',OWNER_AG),('staffAgent',STAFF_AG)]:
            print(role,nm,pg.evaluate(JS,[ag]))
        b.close()
