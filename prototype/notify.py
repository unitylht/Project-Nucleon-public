"""Notices: what Nucleon tells a person outside the page they are looking at. Every notice is a row (the role it is for, what it is about, the case) that the
Home page lists until it is read, and, when the config names a webhook, a POST of the same text to it (a Rocket.Chat or Slack incoming webhook takes {text};
anything else gets the whole JSON). The POST runs on its own thread with a short timeout: a slow or absent endpoint never delays a decision.

Config: "notifications": {"webhook": "https://...", "timeoutSeconds": 5, "publicUrl": "https://nucleon.example"} (publicUrl is prepended to the links in
the webhook text; the page's own links stay relative)."""
import json
import threading
import urllib.request


class Notifier:
    def __init__(self, config=None, log=None):
        c = config or {}
        self.webhook = c.get('webhook')
        self.timeout = float(c.get('timeoutSeconds', 5))
        self.public_url = (c.get('publicUrl') or '').rstrip('/')
        self.log = log or (lambda *a: None)
        self.sent = []   # tests read what would have been posted

    def post(self, notice):
        """Fire and forget. notice: {id, role, kind, text, caseId, link}."""
        text = ('[' + notice['role'] + '] ' if notice.get('role') else '') + notice['text'] + ((' ' + self.public_url + '/' + notice['link']) if notice.get('link') and self.public_url else '')
        payload = {**notice, 'text': text}
        self.sent.append(payload)
        if not self.webhook:
            return
        data = json.dumps(payload).encode('utf-8')

        def go():
            try:
                req = urllib.request.Request(self.webhook, data=data, headers={'Content-Type': 'application/json'})
                with urllib.request.urlopen(req, timeout=self.timeout):
                    pass
            except Exception as e:   # never the caller's problem
                self.log('notice webhook failed: ' + str(e)[:160])
        threading.Thread(target=go, daemon=True).start()
