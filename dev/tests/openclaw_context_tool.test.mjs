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
