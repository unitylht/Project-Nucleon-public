// Runs inside the LibreChat container (copied in by bin/role-accounts). Reads {accounts:[{role,email,name,username,password}], ownerAgentId, ownerRole}
// as JSON on stdin. Creates each missing account (an existing one is left as it is, password included). The account whose role is
// ownerRole becomes the author and ACL owner of the Owner agent; every other user entry on that agent is downgraded to viewer
// (the admin keeps read access to it). Role-level shares (the Staff agent, role USER) are not touched. Never prints a password.
const appRequire = require('module').createRequire('/app/config/role-accounts.js');
const connect = appRequire('./connect');

(async () => {
  let raw = '';
  for await (const chunk of process.stdin) raw += chunk;
  const { accounts, ownerAgentId, ownerRole } = JSON.parse(raw);
  await connect();
  const mongoose = appRequire('mongoose');
  const { User, Agent, AclEntry } = appRequire('@librechat/data-schemas').createModels(mongoose);
  const { registerUser } = appRequire('~/server/services/AuthService');
  const { grantPermission } = appRequire('~/server/services/PermissionService');
  const { PrincipalType, ResourceType, AccessRoleIds } = appRequire('librechat-data-provider');

  const out = { accounts: [], ownerAgent: null };
  for (const m of accounts) {
    if (await User.findOne({ $or: [{ email: m.email }, { username: m.username }] })) {
      out.accounts.push({ email: m.email, status: 'exists' });
      continue;
    }
    const { role, ...reg } = m;
    const r = await registerUser({ ...reg, confirm_password: m.password }, { emailVerified: true });
    out.accounts.push({ email: m.email, status: r.status === 200 ? 'created' : 'failed: ' + r.message });
  }

  const ownerAcc = accounts.find((a) => a.role === ownerRole);
  const owner = await User.findOne({ email: ownerAcc.email }, { _id: 1 }).lean();
  const agent = await Agent.findOne({ id: ownerAgentId }, { _id: 1, author: 1 }).lean();
  const prevAuthor = String(agent.author);
  // existing direct user entries (the seeding admin) become viewers
  const entries = await AclEntry.find({ resourceType: ResourceType.AGENT, resourceId: agent._id, principalType: PrincipalType.USER }).lean();
  await Agent.updateOne({ _id: agent._id }, { $set: { author: owner._id } });
  await grantPermission({ principalType: PrincipalType.USER, principalId: owner._id, resourceType: ResourceType.AGENT, resourceId: agent._id,
    accessRoleId: AccessRoleIds.AGENT_OWNER, grantedBy: owner._id });
  for (const e of entries) {
    if (String(e.principalId) === String(owner._id)) continue;
    await grantPermission({ principalType: PrincipalType.USER, principalId: e.principalId, resourceType: ResourceType.AGENT, resourceId: agent._id,
      accessRoleId: AccessRoleIds.AGENT_VIEWER, grantedBy: owner._id });
  }
  const now = await AclEntry.find({ resourceType: ResourceType.AGENT, resourceId: agent._id }).lean();
  out.ownerAgent = { prevAuthor, author: String(owner._id), acl: now.map((e) => ({ type: e.principalType, id: String(e.principalId), bits: e.permBits })) };
  console.log('RESULT ' + JSON.stringify(out));
  process.exit(0);
})().catch((e) => { console.error('ERROR ' + e.message); process.exit(1); });
