import {test} from 'node:test';
import assert from 'node:assert/strict';
import {EventEmitter} from 'node:events';
import fs from 'node:fs';
import {argvFor,executeContext,reportGate} from '../../examples/agentic/openclaw/context-tool/policy.mjs';
const config={script:'/private/context_packet.py',profile:'/private/context.json'};
test('manifest declares the callable tool ownership used by the installed loader',()=>{
  const manifest=JSON.parse(fs.readFileSync(new URL('../../examples/agentic/openclaw/context-tool/openclaw.plugin.json',import.meta.url)));
  assert.deepEqual(manifest.contracts.tools,['section11_context']);assert.equal(manifest.toolMetadata.section11_context.optional,false);
});

test('only typed bounded context operations become argv, never a shell',()=>{
  const args=argvFor({operation:'section',source:'protocol',heading:'x; $(touch /bad)'},config);
  assert.equal(args.at(-1),'x; $(touch /bad)');
  for(const p of [{operation:'exec',command:'env'},{operation:'build',task:'morning',path:'/secret'},{operation:'history',start:'bad',end:'2026-10-22'},{operation:'section',source:'protocol'}])assert.throws(()=>argvFor(p,config));
});
test('report gate blocks every mutating/native tool and has a finite read budget',()=>{
  const gate=reportGate();assert.equal(gate({toolName:'exec'},{runId:'mutate'}).block,true);
  assert.equal(gate({toolName:'section11_context'},{}).block,true);
  for(let i=0;i<6;i++)assert.equal(gate({toolName:'section11_context'},{runId:'read'}),undefined);
  assert.equal(gate({toolName:'section11_context'},{runId:'read'}).block,true);
});
test('long term retrieval stays typed and exposes no arbitrary storage path',()=>{
  assert.equal(argvFor({operation:'long_term'},config).at(-1),'long_term');
  assert.equal(argvFor({operation:'history',start:'2026-06-01',end:'2026-10-23',tier:'monthly'},config).at(-1),'monthly');
  assert.equal(argvFor({operation:'history_detail',activity_id:'activity-1'},config).at(-1),'activity-1');
  assert.equal(argvFor({operation:'review',review_id:'review-1'},config).at(-1),'review-1');
  assert.equal(argvFor({operation:'intake'},config).at(-1),'intake');
  for(const p of [{operation:'intake',path:'/secret'},{operation:'long_term',path:'/secret'},{operation:'long_term',task:'morning'},{operation:'history_detail'}])assert.throws(()=>argvFor(p,config));
});
function spawnFixture(chunks,code=0){
  return (_bin,args,options)=>{
    assert.equal(options.shell,false);const child=new EventEmitter();child.stdout=new EventEmitter();child.stderr=new EventEmitter();child.kill=()=>{};
    queueMicrotask(()=>{for(const chunk of chunks)child.stdout.emit('data',chunk);child.emit('close',code);});return child;
  };
}
test('split UTF-8 is preserved and only complete packets return',async()=>{
  const b=Buffer.from('{"note":"é","packet_complete":true}');const at=b.indexOf(0xc3);
  const out=await executeContext([],undefined,spawnFixture([b.subarray(0,at+1),b.subarray(at+1)]));
  assert.equal(JSON.parse(out.content[0].text).note,'é');
  for(const [text,code] of [['{"packet_complete":true}',1],['{"private":"canary"}',0],['{"partial":',0]]){
    const result=await executeContext([],undefined,spawnFixture([Buffer.from(text)],code));assert.equal(result.isError,true);assert.ok(!JSON.stringify(result).includes('canary'));
  }
});
test('oversize output and cancellation fail without a partial result',async()=>{
  assert.equal((await executeContext([],undefined,spawnFixture([Buffer.alloc(50000)]))).isError,true);
  const abort=new AbortController();abort.abort();assert.equal((await executeContext([],abort.signal,()=>{throw Error('must not spawn')})).isError,true);
});

test('batch references are typed and cannot smuggle paths, nested operations or huge requests',()=>{
  const requests=[{source:'protocol',heading:'Warm-up'},{source:'workouts',heading:'Endurance'}];
  assert.deepEqual(JSON.parse(argvFor({operation:'references',requests},config).at(-1)),requests);
  for(const requests of [[],Array(7).fill({source:'protocol',heading:'x'}),[{source:'protocol',heading:'x',path:'/secret'}],[{source:'protocol',heading:'x',task:'weekly'}],[{source:'report',heading:'x',task:'plan'}]])assert.throws(()=>argvFor({operation:'references',requests},config));
  assert.throws(()=>argvFor({operation:'references'},config));
});

import {exchangeBudget} from '../../examples/agentic/openclaw/context-tool/exchange-budget.mjs';
test('exchange call ceiling reserves final response; session does not carry budget',()=>{
  const b=exchangeBudget({modelCalls:6}),ctx={runId:'a',sessionId:'same'};
  b.before_prompt_build({},ctx);
  for(let i=0;i<5;i++)b.model_call_started({callId:String(i)},ctx);
  assert.equal(b.before_tool_call({toolName:'section11_context',toolCallId:'fifth-stage'},ctx),undefined);
  b.model_call_started({callId:'final'},ctx);
  assert.equal(b.before_tool_call({toolName:'section11_context'},ctx).block,true);
  assert.equal(b.before_tool_call({toolName:'section11_coaching',params:{operation:'save'}},ctx).block,true);
  assert.equal(b.before_tool_call({toolName:'exec'},ctx).block,true);
  assert.equal(b.before_tool_call({}, {runId:'b',sessionId:'same'}),undefined);
  assert.equal(b.before_tool_call({}, {sessionId:'same'}).block,true);
});
test('parallel tool reservations stop at cap, results and receipts are immutable',()=>{
  const b=exchangeBudget({toolCalls:2}),ctx={runId:'parallel'};
  for(let i=0;i<2;i++)assert.equal(b.before_tool_call({toolName:'section11_coaching',toolCallId:String(i)},ctx),undefined);
  assert.equal(b.before_tool_call({toolCallId:'3'},ctx).block,true);
  const e={toolCallId:'0',result:{success:true,revision:'receipt'}};const before=JSON.stringify(e);
  b.after_tool_call(e,ctx);assert.equal(JSON.stringify(e),before);
});
test('estimated token guard and measured usage stay separate; duplicate observed calls count once',()=>{
  const records=[],b=exchangeBudget({estimatedTokens:20000},r=>records.push(r)),ctx={runId:'token'};
  b.llm_input({systemPrompt:'x'.repeat(15000)},ctx);
  b.model_call_started({callId:'one'},ctx);b.model_call_started({callId:'one'},ctx);
  assert.equal(b.before_tool_call({},ctx).block,true);
  b.llm_output({usage:{input:10,cacheRead:100,output:5,total:115}},ctx);
  const attempt=records.find(r=>r.kind==='section11_exchange_attempt');
  assert.equal(attempt.observedModelCalls,1);assert.equal(attempt.actualAttemptUsage.total,115);
  assert(attempt.estimatedTokens>20000);assert(!JSON.stringify(records).includes('xxxxx'));
  b.agent_end({},ctx);assert.equal(b.before_tool_call({},ctx),undefined);
  assert.throws(()=>exchangeBudget({modelCalls:1}));
});

test('explicit full-context mode records large repeated inputs without a token veto and retains call guards',()=>{
 const records=[],b=exchangeBudget({estimatedTokens:0,modelCalls:3,toolCalls:2},r=>records.push(r)),ctx={runId:'full-window'};
 assert(b.before_prompt_build({},ctx).appendSystemContext.includes('telemetry only'));
 for(let i=0;i<2;i++){
  b.llm_input({systemPrompt:'x'.repeat(4200000)},ctx);b.model_call_started({callId:String(i)},ctx);
  assert.equal(b.before_tool_call({toolName:'section11_context',toolCallId:'read'+i},ctx),undefined);
 }
 b.llm_output({usage:{input:100,output:5}},ctx);
 const measured=records.find(r=>r.kind==='section11_exchange_attempt');
 assert(measured.estimatedTokens>2000000);assert.equal(measured.actualAttemptUsage.input,100);
 assert.equal(b.before_tool_call({toolName:'section11_coaching',toolCallId:'third'},ctx).block,true);
 assert.equal(records.at(-1).cause,'tool_calls');
 const limited=exchangeBudget({estimatedTokens:0,modelCalls:2}),other={runId:'full-window-model-cap'};
 limited.model_call_started({callId:'one'},other);limited.model_call_started({callId:'final'},other);
 assert.equal(limited.before_tool_call({toolName:'section11_coaching'},other).block,true);
 for(const estimatedTokens of [-1,1,9999,2000001])assert.throws(()=>exchangeBudget({estimatedTokens}));
});

import {boundedNoticeFilter,BOUNDED_CONTEXT_NOTICE} from '../../examples/agentic/openclaw/context-tool/policy.mjs';
test('quiet notice filter cancels only exact standalone Telegram maintenance notice',()=>{
 const ctx={channelId:'telegram'};
 assert.equal(boundedNoticeFilter({content:BOUNDED_CONTEXT_NOTICE},ctx).cancel,true);
 assert.equal(boundedNoticeFilter({content:'  '+BOUNDED_CONTEXT_NOTICE+'\n'},ctx).cancel,true);
 for(const content of ['⚠️ Stop training: new symptoms.', 'Your plan was saved.', BOUNDED_CONTEXT_NOTICE+'\nActual coaching answer.', 'You asked about: '+BOUNDED_CONTEXT_NOTICE])assert.equal(boundedNoticeFilter({content},ctx),undefined);
 assert.equal(boundedNoticeFilter({content:BOUNDED_CONTEXT_NOTICE,metadata:{mediaUrls:['synthetic-media']}},ctx),undefined);
 assert.equal(boundedNoticeFilter({content:BOUNDED_CONTEXT_NOTICE},{channelId:'slack'}),undefined);
 assert.equal(boundedNoticeFilter({content:BOUNDED_CONTEXT_NOTICE},{}),undefined);
});

test('historical analysis accepts one exact ID and no credential or path overrides',async t=>{
  const args=argvFor({operation:'activity_analysis',activity_id:'i193686489'},config);
  assert.deepEqual(args,[config.script,'--profile',config.profile,'activity_analysis','--activity-id','i193686489']);
  for(const p of [{operation:'activity_analysis'},
    {operation:'activity_analysis',activity_id:'../secret'},
    {operation:'activity_analysis',activity_id:'i123',path:'/other'},
    {operation:'activity_analysis',activity_id:'i123',credentials_dir:'/other'}])assert.throws(()=>argvFor(p,config));
  const deadlines=[];const original=globalThis.setTimeout;
  t.mock.method(globalThis,'setTimeout',(fn,ms)=>{deadlines.push(ms);return original(fn,ms);});
  await executeContext(args,undefined,spawnFixture([Buffer.from('{"packet_complete":true}')],0));
  await executeContext(argvFor({operation:'section',source:'protocol',heading:'activity_analysis'},config),undefined,spawnFixture([Buffer.from('{"packet_complete":true}')],0));
  assert.deepEqual(deadlines,[60000,15000]);
});

test('block comparison selectors are typed, bounded and confined to two activities',async t=>{
 const p={operation:'compare_blocks',activity_id:'i205776483',reference_activity_id:'i193686489',step_index:1,reference_step_index:1};
 const args=argvFor(p,config);
 assert.deepEqual(args,[config.script,'--profile',config.profile,'compare_blocks','--activity-id','i205776483','--reference-activity-id','i193686489','--step-index','1','--reference-step-index','1']);
 assert.doesNotThrow(()=>argvFor({operation:p.operation,activity_id:p.activity_id,reference_activity_id:p.reference_activity_id},config));
 for(const changes of [{reference_activity_id:p.activity_id},{reference_activity_id:'../other'},{reference_activity_id:undefined},{step_index:-1},{step_index:32},{step_index:'1'},{step_index:1.5},{path:'/other'}])assert.throws(()=>argvFor({...p,...changes},config));
 const deadlines=[];const original=globalThis.setTimeout;
 t.mock.method(globalThis,'setTimeout',(fn,ms)=>{deadlines.push(ms);return original(fn,ms);});
 await executeContext(args,undefined,spawnFixture([Buffer.from('{"packet_complete":true}')],0));
 assert.deepEqual(deadlines,[120000]);
});

test('backend reference errors retain actionable metadata but never partial bodies',async()=>{
 const error={ok:false,error_code:'reference_selection_required',context_complete:false,packet_complete:false,
  reference_errors:[{source:'workouts',requested_heading:'AE',candidates:['AE-1: Short'],private:'PRIVATE_CANARY'}],private:'PRIVATE_CANARY'};
 const out=await executeContext([],undefined,spawnFixture([Buffer.from(JSON.stringify(error))],1));
 assert.equal(out.isError,true);const body=JSON.parse(out.content[0].text);
 assert.equal(body.packet_complete,false);assert.equal(body.reference_errors[0].candidates[0],'AE-1: Short');
 assert(!JSON.stringify(body).includes('PRIVATE_CANARY'));
 const malformed={...error,error_code:'bad error with PRIVATE_CANARY'};
 const failed=await executeContext([],undefined,spawnFixture([Buffer.from(JSON.stringify(malformed))],1));
 assert(!JSON.stringify(failed).includes('PRIVATE_CANARY'));
});


test('native Section 11 broker wrappers do not consume a second operation slot',()=>{
 const records=[],b=exchangeBudget({toolCalls:2},r=>records.push(r)),ctx={runId:'native-broker'};
 const broker=(i,id='section11_coaching')=>b.before_tool_call({toolName:'tool_call',toolCallId:'outer'+i,params:{id}},ctx);
 assert.equal(broker(0),undefined);
 assert.equal(b.before_tool_call({toolName:'section11_coaching',toolCallId:'tool_call:outer0:section11_coaching:1'},ctx),undefined);
 assert.equal(broker(1),undefined);
 assert.equal(b.before_tool_call({toolName:'section11_coaching',toolCallId:'tool_call:outer1:section11_coaching:2'},ctx),undefined);
 assert.equal(broker(2).block,true);
 assert.equal(b.before_tool_call({toolName:'section11_context',toolCallId:'direct'},ctx).block,true);
 assert(records.every(r=>r.cause==='tool_calls'));
 const other=exchangeBudget({toolCalls:1}),c={runId:'unknown-broker'};
 assert.equal(other.before_tool_call({toolName:'tool_call',params:{id:'other_plugin'}},c),undefined);
 assert.equal(other.before_tool_call({toolName:'other_plugin'},c).block,true);
});

test('token estimate excludes transcript-only duplicates and nested broker results',()=>{
 const records=[],b=exchangeBudget({},r=>records.push(r)),ctx={runId:'projection'};
 b.llm_input({historyMessages:[{role:'toolResult',content:[{type:'text',text:'visible'}],details:{duplicate:'x'.repeat(2000000)}}]},ctx);
 b.after_tool_call({toolName:'section11_context',toolCallId:'tool_call:outer:section11_context:1',result:{content:[{type:'text',text:'nested'.repeat(200000)}]}},ctx);
 b.after_tool_call({toolName:'tool_call',toolCallId:'outer',result:{content:[{type:'text',text:'once'}],details:{duplicate:'x'.repeat(2000000)}}},ctx);
 b.model_call_started({callId:'1'},ctx);assert.equal(b.before_tool_call({toolName:'section11_context'},ctx),undefined);
 b.llm_output({},ctx);assert(records[0].estimatedTokens<20000);
});


test('entry skill activity example satisfies the actual required task contract',()=>{
 const text=fs.readFileSync(new URL('../../SKILL.md',import.meta.url),'utf8');
 const examples=[...text.matchAll(/`(\{"operation":"activities"[^`]+\})`/g)].map(m=>JSON.parse(m[1]));
 assert(examples.length>0);
 for(const example of examples)assert.doesNotThrow(()=>argvFor(example,config));
});


test('normal multi-workout planning passes old checkpoints but all hard caps remain',()=>{
 const records=[],b=exchangeBudget({},r=>records.push(r)),ctx={runId:'full-plan'};
 b.llm_input({systemPrompt:'Bounded synthetic context'},ctx);
 for(let stage=1;stage<=7;stage++){
  b.model_call_started({callId:String(stage)},ctx);
  for(let i=0;i<3;i++)assert.equal(b.before_tool_call({toolName:i===2?'section11_coaching':'read',toolCallId:stage+'-'+i},ctx),undefined);
 }
 assert.equal(records.filter(r=>r.kind==='section11_exchange_checkpoint').length,2);
 assert(records.every(r=>r.kind!=='section11_exchange_block'));
 for(let i=21;i<32;i++)assert.equal(b.before_tool_call({toolName:'read',toolCallId:'more-'+i},ctx),undefined);
 assert.equal(b.before_tool_call({toolName:'section11_coaching',toolCallId:'over'},ctx).block,true);
 const calls=exchangeBudget(),other={runId:'model-cap'};
 for(let i=0;i<9;i++)calls.model_call_started({callId:String(i)},other);
 assert.equal(calls.before_tool_call({toolName:'section11_coaching'},other),undefined);
 calls.model_call_started({callId:'final'},other);
 assert.equal(calls.before_tool_call({toolName:'section11_coaching'},other).block,true);
});


test('model-call IDs reused after compaction are charged again, not within an attempt',()=>{
 const records=[],b=exchangeBudget({modelCalls:3},r=>records.push(r)),ctx={runId:'compaction'};
 b.llm_input({},ctx);b.model_call_started({callId:'same'},ctx);b.model_call_started({callId:'same'},ctx);
 b.llm_input({},ctx);b.model_call_started({callId:'same'},ctx);b.model_call_started({callId:'same'},ctx);
 assert.equal(b.before_tool_call({toolName:'section11_context'},ctx),undefined);
 b.llm_input({},ctx);b.model_call_started({callId:'same'},ctx);
 assert.equal(b.before_tool_call({toolName:'section11_context'},ctx).block,true);
 b.llm_output({},ctx);assert.equal(records.find(r=>r.kind==='section11_exchange_attempt').observedModelCalls,3);
});

test('workout inputs expose only fixed environment and checked template selectors',()=>{
 const p={operation:'workout_inputs',environment:'indoor',templates:['AE-1','AE-2']};
 assert.deepEqual(argvFor(p,config),[config.script,'--profile',config.profile,'workout_inputs','--environment','indoor','--templates-json','["AE-1","AE-2"]']);
 for(const patch of [{environment:undefined},{environment:'auto'},{templates:[]},{templates:['../secret']},{templates:['AE-1','AE-1']},{athlete_id:'i999'},{path:'/secret'}])assert.throws(()=>argvFor({...p,...patch},config));
});
