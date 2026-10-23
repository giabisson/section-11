import {test} from 'node:test';
import assert from 'node:assert/strict';
import {EventEmitter} from 'node:events';
import fs from 'node:fs';
import {schema,requestFor,executeCoaching,coachingGate} from '../../examples/agentic/openclaw/coaching-tool/policy.mjs';
const config={script:'/private/coaching_runtime.py',profile:'/private/coaching-primary.json'};

test('declared contract matches the registered write tool',()=>{
 const manifest=JSON.parse(fs.readFileSync(new URL('../../examples/agentic/openclaw/coaching-tool/openclaw.plugin.json',import.meta.url)));
 assert.deepEqual(manifest.contracts.tools,['section11_coaching']);assert.equal(manifest.toolMetadata.section11_coaching.optional,false);
 const distribution=JSON.parse(fs.readFileSync(new URL('../../manifest.json',import.meta.url)));
 assert(distribution.files['examples/agentic/openclaw/coaching-tool/schemas.mjs'],'the imported schema must ship with the plugin');
});
test('payload is JSON on stdin, with fixed argv and no shell or arbitrary paths',()=>{
 const payload={date:'2026-10-23',state:'normal',note:'$(touch /bad); private words',health_clarification:null};
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

// Structural negative control is dependency-free. The optional installed-runtime
// test below exercises the actual OpenClaw compatibility conversion and validator.
test('all nested object and array shapes are explicit, with bounded plan references',()=>{
 const visit=node=>{
  if(!node||typeof node!=='object')return;
  if(node.type==='object'){assert.equal(node.additionalProperties,false);assert(node.properties&&Object.keys(node.properties).length>0);}
  if(node.type==='array')assert(node.items);
  if(node.$ref){assert(node.$ref.startsWith('#/$defs/'));assert(schema.$defs[node.$ref.slice(8)]);}
  for(const value of Object.values(node))if(value&&typeof value==='object')Array.isArray(value)?value.forEach(visit):visit(value);
 };
 visit(schema);assert(Buffer.byteLength(JSON.stringify(schema))<22000);
 const payload=schema.properties.payload.anyOf;
 assert.deepEqual(payload[0].required,['date','state','note','health_clarification']);
 assert.deepEqual(payload[1].required,['current_athlete_context','plan']);
 assert.deepEqual(schema.properties.draft.required,['observations','decisions','candidate_plan']);
 assert(payload[0].properties.health_clarification.anyOf.some(x=>x.type==='null'));
});
test('operation payloads cannot substitute another operation or server-owned evidence',()=>{
 for(const p of [{operation:'feedback',payload:{}},{operation:'feedback',payload:{plan:{},current_athlete_context:{}}},
  {operation:'propose',payload:{date:'2026-10-23',state:'normal',note:'Synthetic',health_clarification:null}},
  {operation:'save',capture_id:'a'.repeat(64),draft:{observations:[],decisions:[],candidate_plan:null,snapshot:{}}}])assert.throws(()=>requestFor(p,config));
});
test('installed OpenClaw conversion and validation preserve write contracts',async t=>{
 if(!process.env.SECTION11_OPENCLAW_PACKAGE){t.skip('Set SECTION11_OPENCLAW_PACKAGE to test the installed OpenClaw SDK/schema pipeline.');return;}
 const {verifyInstalledSchema}=await import('../openclaw_coaching_schema_smoke.mjs');
 const result=await verifyInstalledSchema(process.env.SECTION11_OPENCLAW_PACKAGE);
 assert(result.old_schema_reproduces_failure);assert(result.valid_cases>=10);assert(result.invalid_cases>=5);
});
