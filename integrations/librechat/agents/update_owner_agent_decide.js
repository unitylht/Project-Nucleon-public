// The Owner's work list is called "Decide" in Nucleon's navigation (the address #/review is unchanged). This renames "Review page" to "Decide page" in the
// instructions of the EXISTING "Nucleon ADA Owner (Qwen)" agent in the normal 3080 Mongo (11 Nov 2026). Idempotent; touches no other agent and no other field.
// Usage: docker exec -i chat-mongodb mongosh --quiet LibreChat --file /dev/stdin < update_owner_agent_decide.js
const NAME = 'Nucleon ADA Owner (Qwen)';
const a = db.agents.findOne({ name: NAME });
if (!a) { print(JSON.stringify({ error: 'no agent named ' + NAME })); quit(1); }
const said = a.instructions || '';
const instructions = said.replace(/\bReview page\b/g, 'Decide page').replace(/\bthe Review link\b/g, 'the Decide link');
const changed = instructions !== said;
if (changed) {   // as update_owner_agent_doctor.js does: the agent and its latest version edited in place
  const versions = a.versions || [];
  if (versions.length) versions[versions.length - 1].instructions = instructions;
  db.agents.updateOne({ _id: a._id }, { $set: { instructions, versions, updatedAt: new Date() } });
}
print(JSON.stringify({ id: a.id, changed, before: (said.match(/Review page/g) || []).length, after: (instructions.match(/Review page/g) || []).length,
  decide: (instructions.match(/Decide page/g) || []).length, stillReview: (instructions.match(/[^.]{0,40}\bReview\b[^.]{0,40}/g) || []).slice(0, 5) }));
