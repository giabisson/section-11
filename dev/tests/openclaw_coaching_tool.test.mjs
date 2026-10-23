import {test} from 'node:test';
import assert from 'node:assert/strict';
import {EventEmitter} from 'node:events';
import fs from 'node:fs';
import {requestFor,executeCoaching,coachingGate} from '../../examples/agentic/openclaw/coaching-tool/policy.mjs';
const config={script:'/private/coaching_runtime.py',profile:'/private/coaching-primary.json'};

test('declared contract matches the registered write tool',()=>{
 const manifest=JSON.parse(fs.readFileSync(new URL('../../examples/agentic/openclaw/coaching-tool/openclaw.plugin.json',import.meta.url)));
 assert.deepEqual(manifest.contracts.tools,['section11_coaching']);assert.equal(manifest.toolMetadata.section11_coaching.optional,false);
});
test('payload is JSON on stdin, with fixed argv and no shell or arbitrary paths',()=>{
 const payload={note:'$(touch /bad); private words'};
 const r=requestFor({operation:'feedback',payload},config);
 assert.deepEqual(r.args,[config.script,'--profile',config.profile]);assert.deepEqual(JSON.parse(r.body).payload,payload);
 for(const p of [{operation:'save',capture_id:'../secret',draft:{}},{operation:'state',path:'/secret'},{operation:'prepare',start:'bad',end:'2026-10-23'},{operation:'propose',payload:[]},{operation:'publish',payload:{}},{operation:'feedback',payload:{text:'x'.repeat(2000001)}}])assert.throws(()=>requestFor(p,config));
});
test('coaching operations have a finite per-run budget without blocking other tools',()=>{
 const gate=coachingGate();assert.equal(gate({toolName:'section11_context'},{}),undefined);
 assert.equal(gate({toolName:'section11_coaching'},{}).block,true);
 for(let i=0;i<8;i++)assert.equal(gate({toolName:'section11_coaching'},{runId:'a'}),undefined);
 assert.equal(gate({toolName:'section11_coaching'},{runId:'a'}).block,true);
 assert.equal(gate({toolName:'section11_coaching'},{runId:'b'}),undefined);
});
function fixture(text,code=0){return (_bin,args,opts)=>{
 assert.equal(opts.shell,false);const c=new EventEmitter();c.stdout=new EventEmitter();c.stderr=new EventEmitter();c.stdin=new EventEmitter();c.stdin.end=body=>assert.equal(body,'{}');c.kill=()=>{};
 queueMicrotask(()=>{c.stdout.emit('data',Buffer.from(text));c.emit('close',code);});return c;
};}
test('only complete successful acknowledgements return; uncertain writes remain uncertain',async()=>{
 const r={args:[],body:'{}'};
 assert.equal(JSON.parse((await executeCoaching(r,undefined,fixture('{"success":true,"packet_complete":true}'))).content[0].text).success,true);
 for(const [body,code] of [['{"success":true}',0],['{"success":true,"packet_complete":true}',1],['{"private":"canary"}',0],['x'.repeat(50000),0]]){
  const out=await executeCoaching(r,undefined,fixture(body,code));assert.equal(out.isError,true);assert(!JSON.stringify(out).includes('canary'));
 }
});
