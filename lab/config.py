"""The Lab's configuration: a JSON file. The recordsLog path is relative to the file; the records instance is reached
over HTTP. An MCP bearer token must be long, so the example's placeholders never work as tokens."""
import json
from pathlib import Path

DEFAULTS = {'host': '127.0.0.1', 'port': 8630, 'rootPath': '/lab', 'recordsUrl': 'http://127.0.0.1:8631', 'publicOrigins': [], 'mcpTokens': {}, 'recordsLog': None, 'recordsCodes': {}, 'recordsPublicUrl': None, 'timingLog': None}


def load(path):
    path = Path(path)
    config = {**DEFAULTS, **json.loads(path.read_text())}   # other keys are tolerated: older files still hold store and model
    if config['recordsLog']:
        config['recordsLog'] = str((path.parent / Path(config['recordsLog']).expanduser()).resolve())
    tokens, origins, codes = config['mcpTokens'], config['publicOrigins'], config['recordsCodes']
    if not isinstance(tokens, dict) or any(len(t) < 32 or role not in ('owner', 'staff') for t, role in tokens.items()):
        raise ValueError('mcpTokens: {"<a random token of 32 characters or more>": "owner" | "staff"}')
    if not isinstance(codes, dict) or not all(role in ('owner', 'staff') and isinstance(code, str) for role, code in codes.items()):
        raise ValueError('recordsCodes: the records\' SERVICE codes {"owner": "<code>", "staff": "<code>"} (or leave it out and set recordsLog)')
    if config['timingLog'] is not None and not (isinstance(config['timingLog'], str) and config['timingLog'].strip()):
        raise ValueError('timingLog: a file path such as "logs/tool-timing.jsonl" (relative to the Lab\'s working directory), or leave it out')
    public = config['recordsPublicUrl']
    if public is not None and (not isinstance(public, str) or public.rstrip('/') not in (
            'http://127.0.0.1:8631', 'http://127.0.0.1:18631', 'https://nucleon.tail492813.ts.net:8443', 'https://nucleon.dracooz.top')):
        raise ValueError('recordsPublicUrl: "http://127.0.0.1:8631" (the local runtime), "http://127.0.0.1:18631" (the isolated test instance), '
                         '"https://nucleon.tail492813.ts.net:8443" (the local runtime over Tailscale Serve), '
                         '"https://nucleon.dracooz.top" (the PoV\'s public origin, Cloudflare Tunnel), or leave it out')
    if not isinstance(origins, list) or not all(isinstance(o, str) and o.startswith(('http://', 'https://')) for o in origins):
        raise ValueError('publicOrigins: ["https://<public host>"]')
    return config
