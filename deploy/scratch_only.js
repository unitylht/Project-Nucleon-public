// The guard of every check script that writes or resets: it runs only against a scratch server on this machine. Called before any
// request and before the log is read; on refusal it prints why and exits 2.
//   require('./scratch_only')(script, base, log)
// base: parsed with new URL; the hostname must be 127.0.0.1 or localhost, and the port neither 8620 (the shared instance) nor 8621
// (the preview). log: the scratch server's own service log, named explicitly (argument or NUCLEON_LOG), never either instance's log.
'use strict';
const fs = require('fs');
const os = require('os');
const path = require('path');

const SHARED_PORTS = ['8620', '8621'];
const real = p => { try { return fs.realpathSync(p); } catch { return path.resolve(p); } };
const SHARED_LOGS = ['Library/Logs/nucleon/service.log', 'Library/Logs/nucleon-preview/service.log'].map(p => real(path.join(os.homedir(), p)));

module.exports = function scratchOnly(script, base, log) {
  const refuse = why => {
    console.error(`${script}: refused, ${why}. It writes or resets records, so it runs only against a scratch server on this machine (http://127.0.0.1:<port> or http://localhost:<port>, not 8620 or 8621) with that server's own log.`);
    process.exit(2);
  };
  let url;
  try { url = new URL(base); } catch { refuse(`${JSON.stringify(base)} is not a URL`); }
  if (!['127.0.0.1', 'localhost'].includes(url.hostname)) refuse(`the host of ${base} is ${JSON.stringify(url.hostname)}`);
  if (SHARED_PORTS.includes(url.port)) refuse(`port ${url.port} is the ${url.port === '8620' ? 'shared instance' : 'preview'}`);
  if (!log) refuse('no service log was named (give it as the argument or NUCLEON_LOG)');
  if (SHARED_LOGS.includes(real(log))) refuse(`${log} is the log of the shared instance or the preview`);
};
