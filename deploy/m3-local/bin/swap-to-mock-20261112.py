"""12 Nov 2026: make the fictional mock pair the public pair (8631/8630) and move the NTK real-data pair to loopback 8641/8640.
Rotates the service codes and the MCP tokens of both pairs (they were shown in a session transcript). Prints no secret.
Run with both pairs stopped. Backups of the four configs and LibreChat's .env must already exist."""
import json, os, re, secrets

C = os.path.expanduser('~/Developer/nucleon-local/config/')
ENV = os.path.expanduser('~/Developer/LibreChat/.env')
STAFF, OWNER = 'agent_biPGuKnO2VgHEQ67HsLHL', 'agent_x8IHmsGoFKdtDgdQcgmTX'


def load(n):
    return json.load(open(C + n))


def save(n, d):
    with open(C + n, 'w') as f:   # in place: keeps the file's mode
        json.dump(d, f, indent=2)
        f.write('\n')
    os.chmod(C + n, 0o600)


def codes():
    return {'staff': secrets.token_urlsafe(18), 'owner': secrets.token_urlsafe(18)}


rec, ntk, lab, labntk = load('records.json'), load('records-ntk.json'), load('lab.json'), load('lab-ntk.json')
assert rec['port'] == 8641 and ntk['port'] == 8631 and lab['port'] == 8640 and labntk['port'] == 8630, 'not in the expected starting state'

mock_codes, ntk_codes = codes(), codes()
mock_tokens = {'staff': secrets.token_urlsafe(36), 'owner': secrets.token_urlsafe(36)}
ntk_tokens = {'staff': secrets.token_urlsafe(36), 'owner': secrets.token_urlsafe(36)}

# the mock pair becomes the public pair
rec.update(port=8631, serviceCodes=mock_codes, publicOrigins=['http://127.0.0.1:8631', 'https://nucleon.dracooz.top'],
           assistantUrl='https://creditease.dracooz.top/c/new?agent_id=' + STAFF, ownerAssistantUrl='https://creditease.dracooz.top/c/new?agent_id=' + OWNER)
lab.update(port=8630, recordsUrl='http://127.0.0.1:8631', publicOrigins=['http://host.docker.internal:8630'], recordsCodes=mock_codes,
           mcpTokens={mock_tokens['owner']: 'owner', mock_tokens['staff']: 'staff'}, recordsPublicUrl='https://nucleon.dracooz.top')
# the NTK pair goes to loopback, with no assistant links (the assistants now work on the fictional data)
ntk.update(port=8641, serviceCodes=ntk_codes, publicOrigins=['http://127.0.0.1:8641'])
ntk.pop('assistantUrl', None), ntk.pop('ownerAssistantUrl', None)
labntk.update(port=8640, recordsUrl='http://127.0.0.1:8641', publicOrigins=['http://host.docker.internal:8640'], recordsCodes=ntk_codes,
              mcpTokens={ntk_tokens['owner']: 'owner', ntk_tokens['staff']: 'staff'})
labntk.pop('recordsPublicUrl', None)

env = open(ENV).read()
for name, value in (('NUCLEON_LOCAL_STAFF_MCP_TOKEN', mock_tokens['staff']), ('NUCLEON_LOCAL_OWNER_MCP_TOKEN', mock_tokens['owner'])):
    env, n = re.subn(r'(?m)^' + name + r'=.*$', name + '=' + value, env)
    assert n == 1, name
with open(ENV, 'r+') as f:   # in place: the file is bind-mounted into the container, so the inode must stay
    f.seek(0), f.write(env), f.truncate()

save('records.json', rec), save('records-ntk.json', ntk), save('lab.json', lab), save('lab-ntk.json', labntk)
print('configs and LibreChat .env rewritten: mock pair 8631/8630 (public), NTK pair 8641/8640 (loopback); service codes and MCP tokens rotated')
