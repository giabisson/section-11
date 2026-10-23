import {test, beforeEach, afterEach} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {registerGuard} from '../../examples/agentic/openclaw/credential-guard/register.mjs';
import {loadSecrets, redact, beforeTool, protectResult, protectMessage} from '../../examples/agentic/openclaw/credential-guard/policy.mjs';

let root, file, files;
const secret = 'synthetic-intervals-credential-847921';
beforeEach(() => {
  root = fs.mkdtempSync(path.join(os.tmpdir(), 's11-guard-'));
  file = path.join(root, '.sync_config.json'); files = [file];
  fs.writeFileSync(file, JSON.stringify({athlete_id: 'i123456', intervals_key: secret}), {mode: 0o600});
});
afterEach(() => fs.rmSync(root, {recursive: true, force: true}));

test('known secrets and encoded Basic auth are removed before model replay', () => {
  const basic = Buffer.from(`API_KEY:${secret}`).toString('base64');
  const input = {content: [{type: 'text', text: `${secret} Authorization: Basic ${basic}`}], details: {nested: [secret], messageDelivery: {sourceReplyDelivered: true}}};
  const out = protectResult(input, files);
  assert(!JSON.stringify(out).includes(secret)); assert(!JSON.stringify(out).includes(basic));
  assert.equal(out.details.messageDelivery.sourceReplyDelivered, true);
  assert(input.content[0].text.includes(secret));
});
test('plain and shell credential-file inspection are blocked', () => {
  for (const p of [{path: file}, {command: `cat '${file}'`}, {command: 'cat ~/.openclaw/openclaw.json'}, {command: 'cat .env'}, {command: 'printenv'}, {command: 'env'}, {command: 'cat /proc/self/environ'}]) {
    assert.equal(beforeTool({toolName: 'read', params: p}, files).block, true);
  }
});
test('symlink aliases to a protected source are blocked', () => {
  const alias = path.join(root, 'innocent.json'); fs.symlinkSync(file, alias);
  assert.equal(beforeTool({params: {path: alias}}, files).block, true);
});
test('tool arguments containing credentials are blocked without echoing them', () => {
  const decision = beforeTool({params: {command: `push.py --api-key ${secret}`}}, files);
  assert.equal(decision.block, true); assert(!JSON.stringify(decision).includes(secret));
});
test('normal coaching data and private credential-loading tools remain available', () => {
  for (const command of ['python3 /opt/section11/examples/agentic/push.py list', 'env python3 /opt/section11/examples/agentic/push.py push --json week.json', 'python3 coaching_plan.py --data-dir /private/plan show --compact']) {
    assert.equal(beforeTool({params: {command}}, files), undefined);
  }
  assert.equal(beforeTool({params: {path: '/athlete/latest.json'}}, files), undefined);
});
test('freshly rotated credentials are reloaded without a cached old value', () => {
  const other = 'synthetic-rotated-credential-194662';
  fs.writeFileSync(file, JSON.stringify({intervals_key: other}));
  assert.equal(protectResult({content: other}, files).content, '[CREDENTIAL REDACTED]');
});
test('missing, invalid, public or symlinked sources fail closed', () => {
  for (const state of ['missing', 'invalid', 'public', 'symlink']) {
    const p = path.join(root, state);
    if (state === 'invalid') fs.writeFileSync(p, '{', {mode: 0o600});
    if (state === 'public') fs.writeFileSync(p, JSON.stringify({intervals_key: secret}), {mode: 0o644});
    if (state === 'symlink') fs.symlinkSync(file, p);
    assert.equal(beforeTool({params: {}}, [p]).block, true);
    const result = protectResult({content: secret, details: {secret}}, [p]);
    assert.equal(result.isError, true); assert(!JSON.stringify(result).includes(secret));
    const msg = protectMessage({role: 'toolResult', content: secret, details: {secret}}, [p]);
    assert.equal(msg.role, 'toolResult'); assert(!JSON.stringify(msg).includes(secret));
  }
});
test('missing configuration and empty credentials fail closed', () => {
  for (const source of [undefined, [], ['relative.json']]) assert.equal(beforeTool({params: {}}, source).block, true);
  fs.writeFileSync(file, JSON.stringify({athlete_id: 'i123456'}));
  assert.throws(() => loadSecrets(files));
});
test('JSON escaped and URL encoded provider/OAuth credentials are protected', () => {
  const token = 'synthetic-credential-with-"quotes"/and+symbols';
  fs.writeFileSync(file, JSON.stringify({nested: {access_token: token}}));
  const out = redact([token, encodeURIComponent(token), JSON.stringify(token).slice(1, -1)], loadSecrets(files));
  assert.deepEqual(out, Array(3).fill('[CREDENTIAL REDACTED]'));
});
test('plugin registers pre-model middleware and synchronous transcript hooks', () => {
  const hooks = {}, middlewares = [];
  registerGuard({pluginConfig: {credentialFiles: files}, on: (name, handler) => {hooks[name] = handler;}, registerAgentToolResultMiddleware: handler => middlewares.push(handler)});
  assert.equal(middlewares.length, 1);
  assert(!JSON.stringify(middlewares[0]({result: {content: secret}})).includes(secret));
  for (const name of ['tool_result_persist', 'before_message_write']) {
    const out = hooks[name]({message: {role: 'toolResult', content: secret}});
    assert(!(out instanceof Promise)); assert(!JSON.stringify(out).includes(secret));
  }
  assert.equal(hooks.message_sending({content: secret}).content, '[CREDENTIAL REDACTED]');
});

test('configured credential directory can be passed to the CLI without exposing its private file',()=>{
 const command=`python3 /source/examples/agentic/coaching_plan.py --credentials-dir ${root} --data-dir /private/managed preview --revision rev-synthetic`;
 assert.equal(beforeTool({toolName:'exec',params:{command}},files),undefined);
 assert.equal(beforeTool({toolName:'read',params:{path:file}},files).block,true);
});
