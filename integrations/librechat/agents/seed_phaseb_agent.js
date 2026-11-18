// Creates ONE agent in the ISOLATED lc-cardtest Mongo (LibreChatCardTest): "Nucleon PHASE-B TEST Staff (Qwen)", tools from nucleon-phaseb-staff only.
// Usage: docker exec -i lc-cardtest-mongo mongosh --quiet LibreChatCardTest --file /dev/stdin < seed_phaseb_agent.js
const SRV = 'nucleon-phaseb-staff';
const NAME = 'Nucleon PHASE-B TEST Staff (Qwen)';
const src = db.agents.findOne({ id: 'agent_buNVvnQ9EN6dqrubMEhlR' });
const srcAcl = db.aclentries.findOne({ resourceId: src._id, principalType: 'user' });
db.agents.find({ name: NAME }).forEach((a) => { db.aclentries.deleteMany({ resourceId: a._id }); db.agents.deleteOne({ _id: a._id }); });
const id = 'agent_' + Array.from({ length: 21 }, () => 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'[Math.floor(Math.random() * 62)]).join('');
const tools = [].concat(['findCustomers', 'customerOverview', 'invoices', 'prepareRequest', 'actionStatus'].map((t) => t + '_mcp_' + SRV));
const instructions = 'You help a member of staff with customer payment questions. Use the tools for all business facts; never invent numbers or ids. ' +
  'If a tool reports that records are incomplete or unconfirmed, say so. When asked to prepare a payment-extension request, find the customer and invoice, then call prepareRequest. ' +
  'prepareRequest only PREPARES a proposal: nothing is submitted. A person must review and confirm it in Nucleon. ' +
  'Never say a request was submitted unless actionStatus says it is executed (submitted). Keep answers short.';
const now = new Date();
const doc = Object.assign({}, src, { _id: new ObjectId(), id, name: NAME, instructions, tools, mcpServerNames: [SRV], createdAt: now, updatedAt: now,
  versions: [{ name: NAME, instructions, model_parameters: src.model_parameters, provider: src.provider, model: src.model, id, tools, mcpServerNames: [SRV], createdAt: now, updatedAt: now }] });
db.agents.insertOne(doc);
const acl = Object.assign({}, srcAcl, { _id: new ObjectId(), resourceId: doc._id, createdAt: now, grantedAt: now, updatedAt: now });
db.aclentries.insertOne(acl);
print(JSON.stringify({ id, name: NAME, tools }));
