// Creates ONE agent in the ISOLATED lc-cardtest Mongo (LibreChatCardTest): "Nucleon ADA TEST Staff (Qwen)", tools from nucleon-phaseb-staff only.
// Usage: docker exec -i lc-cardtest-mongo mongosh --quiet LibreChatCardTest --file /dev/stdin < seed_ada_agent.js
const SRV = 'nucleon-phaseb-staff';
const NAME = 'Nucleon ADA TEST Staff (Qwen)';
const src = db.agents.findOne({ id: 'agent_buNVvnQ9EN6dqrubMEhlR' });
const srcAcl = db.aclentries.findOne({ resourceId: src._id, principalType: 'user' });
db.agents.find({ name: NAME }).forEach((a) => { db.aclentries.deleteMany({ resourceId: a._id }); db.agents.deleteOne({ _id: a._id }); });
const id = 'agent_' + Array.from({ length: 21 }, () => 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'[Math.floor(Math.random() * 62)]).join('');
const tools = [].concat(['findCustomers', 'customerOverview', 'invoices', 'assessDecision', 'resolveDecision', 'decisionStatus'].map((t) => t + '_mcp_' + SRV));
const instructions = 'You help a member of staff handle customer credit requests. Use tools for every business fact; never invent numbers, dates or ids. ' +
  'For a payment-extension or new-customer trial-credit request: find the customer (and invoice), call assessDecision, then call resolveDecision with your recommendation (approve, decline or escalate) and a short reasoning. ' +
  'The backend applies the Owner\'s delegation policy: report ONLY the outcome the tool result states (repeat its statusText); never say something is approved unless the result says decided/approved. ' +
  'If information is needed from Staff, tell them to use the button on the card. Nothing is ever sent to the customer by Nucleon; Staff informs the customer. Recommend on the merits as if the information Nucleon asks for is confirmed; missing information is not a reason to escalate. ' +
  'Keep answers short.';
const now = new Date();
const doc = Object.assign({}, src, { _id: new ObjectId(), id, name: NAME, instructions, tools, mcpServerNames: [SRV], createdAt: now, updatedAt: now,
  versions: [{ name: NAME, instructions, model_parameters: src.model_parameters, provider: src.provider, model: src.model, id, tools, mcpServerNames: [SRV], createdAt: now, updatedAt: now }] });
db.agents.insertOne(doc);
const acl = Object.assign({}, srcAcl, { _id: new ObjectId(), resourceId: doc._id, createdAt: now, grantedAt: now, updatedAt: now });
db.aclentries.insertOne(acl);
print(JSON.stringify({ id, name: NAME, tools }));
