// Adds the Doctor (11 Nov 2026) to the EXISTING "Nucleon ADA Owner (Qwen)" agent in the normal 3080 Mongo: the read-only tool doctor and one paragraph of
// instructions. Idempotent: running it twice changes nothing more. It touches no other agent and no other field.
// Usage: docker exec -i chat-mongodb mongosh --quiet LibreChat --file /dev/stdin < update_owner_agent_doctor.js
const SRV = 'nucleon-local-owner';
const NAME = 'Nucleon ADA Owner (Qwen)';
const TOOL = 'doctor_mcp_' + SRV;
const PARA = 'Doctor ("why do I still get so many requests", "why do I keep correcting the agent", "what should I change"): call doctor, with the question that fits (came, corrections, help, outcomes, customers, rules) or with none to see all six headlines. Report only the lines it returns. Keep each number with its starting point, its gain and its cost; never add, subtract or estimate a number yourself. If the tool has not worked something out, say so. You cannot change settings: the Owner does that in Quick setup, which shows the effect before saving.';
const RECORDS = (typeof NUCLEON_RECORDS_URL !== 'undefined') ? NUCLEON_RECORDS_URL : 'https://nucleon.dracooz.top';   // as in seed_owner_agent_3080.js
// After the live trial of 11 Nov: the agent named the Control panel's address for Quick setup and dropped the "now" numbers.
const LINKS = 'Quick setup is at ' + RECORDS + '/#/quick-setup and the Doctor page, with a button under each suggestion that opens Quick setup filled in, is at ' + RECORDS + '/#/doctor. Give these two addresses, '
  + 'not the Control panel, when a Doctor answer suggests a change. When you repeat a suggestion, keep its "now" number and what it would decide on today\'s open invoices.';
const a = db.agents.findOne({ name: NAME });
if (!a) { print(JSON.stringify({ error: 'no agent named ' + NAME })); quit(1); }
const had = a.tools || [], said = a.instructions || '';
const tools = had.includes(TOOL) ? had : had.concat([TOOL]);
let instructions = said.includes('call doctor') ? said : (said ? said + ' ' : '') + PARA;
if (!instructions.includes('/#/quick-setup')) instructions = instructions + ' ' + LINKS;
const changed = tools.length !== had.length || instructions !== said;
if (changed) {   // as update_owner_agent_queue.js does: the agent and its latest version edited in place
  const versions = a.versions || [];
  if (versions.length) { versions[versions.length - 1].instructions = instructions; versions[versions.length - 1].tools = tools; }
  db.agents.updateOne({ _id: a._id }, { $set: { tools, instructions, versions, updatedAt: new Date() } });
}
print(JSON.stringify({ id: a.id, changed, tools: tools.length, hasDoctor: tools.includes(TOOL) }));
