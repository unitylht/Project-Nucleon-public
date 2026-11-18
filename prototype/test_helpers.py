"""Helpers the Records tests share. Not a test module. All data is fictional. No real model is called."""
import json

from agent import MockAdapter
from server import DeskTools

PARAGRAPH = ('This customer has struggled recently, but I have known them for years. They have an event next month and should '
             "recover. I would consider a small extension, but I don't want their debt to increase for now.")
NAMED = PARAGRAPH.replace('This customer', 'Bayside Café', 1)
REQUEST = 'Could we pay invoice DEMO-501 on 2026-10-30 instead?'
SHARED = 'Bayside Café pays by bank transfer on Fridays.'


class Recording(MockAdapter):
    """The mock, keeping what each model call was sent: (task, messages as JSON, tools)."""

    def __init__(self):
        self.seen = []

    def respond(self, task, messages, tools=None, schema=None, timeout=None):
        self.seen.append((task, json.dumps(messages, ensure_ascii=False), tools))
        return super().respond(task, messages, tools, schema, timeout)


OWNER_ACTOR = {'role': 'owner', 'id': 'owner_demo'}


def tell_owner(case, text, key, visibility='owner'):
    """What the owner said, kept as a confirmed statement (the desk page used to do this in two steps): the words are read by the
    interpretStatement tool's own code (a reading; nothing is stored, and no tool operation is claimed), then App.new_statement stores
    them. The statement is about the one customer the reading names, else it is the business's."""
    app = case.app
    with app.lock:
        today = app.today(app.fixture())
        tools = DeskTools(app, OWNER_ACTOR, text, today, app.adapter_for(app.agent_mode)[0], app.deadline_seconds)
    reading = tools._interpretStatement({'text': text}).payload['reading']
    with app.lock:
        found = app.evidence().find_customers(reading['customerQuery']) if reading['customerQuery'] else []
    scope = {'kind': 'customer', 'customerId': found[0][0]['id']} if len(found) == 1 else {'kind': 'business'}
    return app.new_statement(OWNER_ACTOR, text, thread_id=None, scope=scope, visibility=visibility, status='confirmed', lines=reading['lines'],
                             source={'kind': 'turn', 'id': 'turn_' + key}, checks=reading['checks'])
