// Appends two sentences to the Owner agent's instructions (normal 3080 Mongo), 6 Nov 2026, after Hoang's test: with two cases waiting, the Owner's
// assistant reported one (it paraphrased workQueue instead of repeating its sentence), and the agents restated the decision card under their reply.
// NOT run by the build: the product lead runs it. Idempotent: a sentence already present is not added again.
// Usage: docker exec -i chat-mongodb mongosh --quiet LibreChat --file /dev/stdin < update_owner_agent_queue.js
const NAME = 'Nucleon ADA Owner (Qwen)';
const ADD = [
  "What is waiting: workQueue. Repeat its summaryText as it is and name every case in decisionCasesForYou; never leave one out, and never say nothing waits while that list has cases.",
  "Do not restate a card: no amounts, lists or sections from a result that the card under your reply already shows. One or two sentences, then the next step.",
];
const a = db.agents.findOne({ name: NAME });
if (!a) { print(JSON.stringify({ error: 'agent not found', name: NAME })); quit(1); }
let ins = a.instructions || '';
for (const s of ADD) if (!ins.includes(s)) ins = ins + ' ' + s;
const versions = a.versions || [];
if (versions.length) versions[versions.length - 1].instructions = ins;
db.agents.updateOne({ _id: a._id }, { $set: { instructions: ins, versions, updatedAt: new Date() } });
const b = db.agents.findOne({ _id: a._id });
print(JSON.stringify({ id: b.id, length: b.instructions.length, added: ADD.filter((s) => !(a.instructions || '').includes(s)).length }));
