// Adds the "one kind per request, ask instead of retrying" rule to the ADA agent's instructions only (normal 3080 Mongo), 27 Oct 2026.
// Why: an ambiguous prompt (a trial credit and an extension in one sentence, no invoice) made Qwen retry with invented arguments until the
// agent step limit. Usage: docker exec -i chat-mongodb mongosh --quiet LibreChat --file /dev/stdin < update_ada_agent_clarify.js
const a = db.agents.findOne({ name: 'Nucleon ADA Staff (Qwen)' });
const extra = ' Each request is exactly one kind: a trial credit for a new customer (order amount and terms in days) or an extension of one existing invoice (its invoice number and the new due date). If the message mixes the two, or an extension names no invoice, do not guess: ask Staff one short question about what they mean, before calling assessDecision. Never invent an invoice number or any other argument. If a tool returns INVALID_ARGUMENT or a schema error, do not retry with made-up values: ask Staff for the missing detail.';
if (a.instructions.indexOf('Each request is exactly one kind') < 0) {
  const ins = a.instructions + extra;
  const versions = a.versions || [];
  if (versions.length) versions[versions.length - 1].instructions = ins;
  db.agents.updateOne({ _id: a._id }, { $set: { instructions: ins, versions, updatedAt: new Date() } });
}
const b = db.agents.findOne({ _id: a._id });
print(JSON.stringify({ id: b.id, tools: b.tools.length, length: b.instructions.length, hasRule: b.instructions.indexOf('Each request is exactly one kind') >= 0 }));
