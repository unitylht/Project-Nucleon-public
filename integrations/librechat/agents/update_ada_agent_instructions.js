// Adds two sentences to the ADA agent's instructions only (normal 3080 Mongo). Usage: docker exec -i chat-mongodb mongosh --quiet LibreChat --file /dev/stdin < update_ada_agent_instructions.js
const a = db.agents.findOne({ name: 'Nucleon ADA Staff (Qwen)' });
const extra = ' Call resolveDecision once per request. After resolveDecision has returned, do not call assessDecision or resolveDecision again for the same request in this turn: just report the result. Use decisionStatus only when asked where a request stands.';
if (a.instructions.indexOf('Call resolveDecision once per request') < 0) {
  const ins = a.instructions + extra;
  const versions = a.versions || [];
  if (versions.length) versions[versions.length - 1].instructions = ins;
  db.agents.updateOne({ _id: a._id }, { $set: { instructions: ins, versions, updatedAt: new Date() } });
}
const b = db.agents.findOne({ _id: a._id });
print(JSON.stringify({ id: b.id, tools: b.tools.length, hasRule: b.instructions.indexOf('Call resolveDecision once') >= 0 }));
