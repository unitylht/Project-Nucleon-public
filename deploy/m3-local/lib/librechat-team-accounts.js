// Runs inside the LibreChat container (copied in by bin/team-accounts). Reads {members:[{email,name,username,password}], agentId,
// rotate} as JSON on stdin. Creates each missing account (an existing one is left as it is, password included, unless rotate is
// true: then its password is set to the one given) and lets the USER role view the ADA agent. Never prints a password.
const appRequire = require('module').createRequire('/app/config/team-accounts.js');
const connect = appRequire('./connect');

(async () => {
  let raw = '';
  for await (const chunk of process.stdin) raw += chunk;
  const { members, agentId, rotate } = JSON.parse(raw);
  await connect();
  const mongoose = appRequire('mongoose');
  const { User, Agent } = appRequire('@librechat/data-schemas').createModels(mongoose);
  const { registerUser } = appRequire('~/server/services/AuthService');
  const { grantPermission } = appRequire('~/server/services/PermissionService');
  const { PrincipalType, ResourceType, AccessRoleIds, SystemRoles } = appRequire('librechat-data-provider');

  const out = { accounts: [], agentShared: false };
  for (const m of members) {
    const existing = await User.findOne({ $or: [{ email: m.email }, { username: m.username }] }, { _id: 1 }).lean();
    if (existing) {
      if (rotate) {
        const bcrypt = appRequire('bcryptjs');   // the same hashing as registerUser (AuthService)
        const hash = await bcrypt.hash(m.password, await bcrypt.genSalt(10));
        await User.updateOne({ _id: existing._id }, { $set: { password: hash } });
        await mongoose.connection.db.collection('sessions').deleteMany({ user: existing._id });   // sign out old sessions
      }
      out.accounts.push({ email: m.email, status: rotate ? 'password rotated' : 'exists' });
      continue;
    }
    const r = await registerUser({ ...m, confirm_password: m.password }, { emailVerified: true });
    out.accounts.push({ email: m.email, status: r.status === 200 ? 'created' : 'failed: ' + r.message });
  }

  const agent = await Agent.findOne({ id: agentId }, { _id: 1, author: 1 }).lean();
  await grantPermission({
    principalType: PrincipalType.ROLE,
    principalId: SystemRoles.USER,
    resourceType: ResourceType.AGENT,
    resourceId: agent._id,
    accessRoleId: AccessRoleIds.AGENT_VIEWER,
    grantedBy: agent.author,
  });
  out.agentShared = true;
  console.log('RESULT ' + JSON.stringify(out));
  process.exit(0);
})().catch((e) => { console.error('ERROR ' + e.message); process.exit(1); });
