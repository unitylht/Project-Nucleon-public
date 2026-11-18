"""Rotate the Staff/Owner access codes of both Nucleon pairs. Prints no code; writes them to a mode-600 text file for the user."""
import json, os, secrets, time

L = os.path.expanduser('~/Developer/nucleon-local/')
ALPHA = 'abcdefghjkmnpqrstuvwxyz23456789'   # no look-alikes


def new(prefix, role):
    return prefix + role + '-' + ''.join(secrets.choice(ALPHA) for _ in range(8))


swap = {}
out = {}
for f, prefix, label in (('records.json', 'demo-', 'DEMO (fictional data) - the public address https://nucleon.dracooz.top'),
                         ('records-ntk.json', 'ntk-', 'NTK (real data) - not public at the moment; keep for the next NTK round')):
    p = L + 'config/' + f
    d = json.load(open(p))
    fresh = {role: new(prefix, role) for role in ('staff', 'owner')}
    for role in fresh:
        swap[d['accessCodes'][role]] = fresh[role]
    d['accessCodes'] = fresh
    with open(p, 'w') as h:
        json.dump(d, h, indent=2); h.write('\n')
    os.chmod(p, 0o600)
    out[label] = fresh

for f in ('demo-launcher.html', 'team-message.txt'):
    p = L + f
    s = open(p).read()
    for a, b in swap.items():
        s = s.replace(a, b)
    with open(p, 'w') as h:
        h.write(s)

path = L + 'config/access-codes-' + time.strftime('%Y%m%d') + '.txt'
with open(path, 'w') as h:
    h.write('Nucleon access codes, rotated ' + time.strftime('%d %b %Y %H:%M') + '. The old codes no longer work.\n\n')
    for label, codes in out.items():
        h.write(label + '\n  Staff: ' + codes['staff'] + '\n  Owner: ' + codes['owner'] + '\n\n')
    h.write('Sign in at https://nucleon.dracooz.top : choose Staff or Owner, then type the code.\nThe assistant (chat) signs in separately with each person\'s own account.\n')
os.chmod(path, 0o600)
print(path)
