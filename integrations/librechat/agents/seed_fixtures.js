// Seeds two controlled SAVED conversations into the ISOLATED lc-cardtest Mongo (LibreChatCardTest) only.
// Shapes are copied from a real conversation produced earlier by the terse test agent (SRC_CONVO): the real
// customerOverview card attachment (balanceEstablished:false, caveat text) and real findCustomers/customerOverview
// outputs. Fixture A: one assistant message with a group of three adjacent tool calls (parallel step), no labels.
// Fixture B: same calls, split into two labelled batches so the client folds them into an Activity Section.
// Both end with a final answer that states the amount WITHOUT the caveat.
// Usage: docker exec -i lc-cardtest-mongo mongosh --quiet LibreChatCardTest --file /dev/stdin < seed_fixtures.js
const SRC_MSG = db.messages.findOne({ isCreatedByUser: false, 'attachments.type': 'ui_resources' }, {}, { sort: { createdAt: 1 } });
if (!SRC_MSG) { throw new Error('no source conversation with a card found'); }
const SRC_CONVO = db.conversations.findOne({ conversationId: SRC_MSG.conversationId });
const SRC_USER = db.messages.findOne({ conversationId: SRC_MSG.conversationId, isCreatedByUser: true });
const calls = SRC_MSG.content.filter((p) => p.type === 'tool_call').map((p) => p.tool_call);
const find = calls.find((c) => c.name.startsWith('findCustomers'));
const overview = calls.find((c) => c.name.startsWith('customerOverview'));
const card = SRC_MSG.attachments.find((a) => a.type === 'ui_resources');
const cardResources = card.ui_resources;
const invoices = {
  customerId: 'customer_demo_02',
  invoices: [
    { ref: 'DEMO-201', amountText: 'AUD 480.00 (stated)', status: 'open', due: '2026-10-09' },
    { ref: 'DEMO-202', amountText: 'AUD 2,100.00 (stated)', status: 'open', due: '2026-11-06' },
  ],
  note: 'controlled fixture output consistent with the card',
};
const FINAL = '\n\nHarbour Demo Logistics owes AUD 2,580.00.';
const mk = (id, name, args, output, n) => ({
  type: 'tool_call',
  tool_call: Object.assign({}, find, { id, name: name + '_mcp_nucleon-local-staff', args: JSON.stringify(args), output, stepId: 'step_fixture_' + n }),
});
// Tool-call ids are unique per conversation (as in real data): the client's in-memory disclosure record is keyed by them.
const calls3 = (k) => ({
  tcFind: mk('fx-' + k + '-find', 'findCustomers', { query: 'Harbour Demo Logistics' }, find.output, k + '1'),
  tcInv: mk('fx-' + k + '-inv', 'invoices', { customerId: 'customer_demo_02' }, JSON.stringify(invoices), k + '2'),
  tcOv: { type: 'tool_call', tool_call: Object.assign({}, overview, { id: 'fx-' + k + '-ov', stepId: 'step_fixture_' + k + '3' }) },
});
const label = (text) => ({ type: 'activity_label', activity_label: text, status: 'ok', pending: false });
const think = { type: 'think', think: 'Look up the customer, then its invoices, then the overview.' };
const finalText = { type: 'text', text: FINAL };

function seed(conversationId, title, k, content) {
  db.conversations.deleteMany({ conversationId });
  db.messages.deleteMany({ conversationId });
  const now = new Date();
  const userId = conversationId + '-u';
  const asstId = conversationId + '-a';
  const u = Object.assign({}, SRC_USER, { messageId: userId, conversationId, createdAt: now, updatedAt: now,
    text: 'How much does Harbour Demo Logistics owe?' });
  delete u._id;
  const a = Object.assign({}, SRC_MSG, { messageId: asstId, parentMessageId: userId, conversationId, createdAt: new Date(now.getTime() + 1000),
    updatedAt: new Date(now.getTime() + 1000), content, text: '',
    attachments: [Object.assign({}, card, { messageId: asstId, conversationId, toolCallId: 'fx-' + k + '-ov', ui_resources: cardResources })] });
  delete a._id;
  const ru = db.messages.insertOne(u), ra = db.messages.insertOne(a);
  const c = Object.assign({}, SRC_CONVO, { conversationId, title, createdAt: now, updatedAt: new Date(now.getTime() + 1000),
    messages: [ru.insertedId, ra.insertedId] });
  delete c._id;
  db.conversations.insertOne(c);
}
const A = calls3('A'), B = calls3('B');
seed('fixture-grouped-0001', 'FIXTURE grouped calls', 'A', [think, A.tcFind, A.tcInv, A.tcOv, finalText]);
seed('fixture-activity-0001', 'FIXTURE activity section', 'B', [
  think, B.tcFind, B.tcInv, label('Looked up Harbour Demo Logistics and its invoices'),
  B.tcOv, label('Opened the customer overview'), finalText,
]);
print(JSON.stringify({ ok: true, balanceEstablishedFalse: overview.output.includes('"balanceEstablished": false'), hasCaveatText: overview.output.includes('caveatText') }));
