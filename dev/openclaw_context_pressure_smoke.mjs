// Native 2026.10.6 checks: projection only, no model calls or private athlete data.
import {schema as contextSchema} from '../examples/agentic/openclaw/context-tool/policy.mjs';
import {exchangeBudget} from '../examples/agentic/openclaw/context-tool/exchange-budget.mjs';
import assert from 'node:assert/strict';
import {readFile,readdir} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
import path from 'node:path';
export async function verifyContextPressure(packageRoot){
 const dist=path.join(packageRoot,'dist'),files=await readdir(dist);
 async function fn(prefix,name){
  for(const file of files.filter(x=>x.startsWith(prefix)&&x.endsWith('.mjs'))){
   const exports=await import(pathToFileURL(path.join(dist,file)).href);
   const found=Object.values(exports).find(x=>typeof x==='function'&&x.name===name);
   if(found)return found;
  }
  throw Error('Unsupported installed OpenClaw function: '+name);
 }
 const ai=path.join(packageRoot,'node_modules/@openclaw/ai/dist');
 const {normalizeOpenAIStrictCompatSchema}=await import(pathToFileURL(path.join(ai,'internal/tool-schema.mjs')).href);
 const {validateToolArguments}=await import(pathToFileURL(path.join(ai,'validation.mjs')).href);
 const parameters=normalizeOpenAIStrictCompatSchema(contextSchema);
 const referenceArgs={operation:'references',requests:[{source:'protocol',heading:'Synthetic exact heading'}]};
 assert.doesNotThrow(()=>validateToolArguments({name:'section11_context',parameters},{id:'schema-only',name:'section11_context',arguments:referenceArgs}));
 assert.throws(()=>validateToolArguments({name:'section11_context',parameters},{id:'invalid',name:'section11_context',arguments:{...referenceArgs,requests:[{source:'protocol',heading:'x',path:'/bad'}]}}));
 const makeHooks=await fn('hooks-','createHookRunner');
 const budget=exchangeBudget({modelCalls:3,toolCalls:2,estimatedTokens:100000});
 const registry={plugins:[{id:'section11-context',status:'loaded'}],typedHooks:Object.entries(budget).map(([hookName,handler])=>({pluginId:'section11-context',hookName,handler}))};
 const runner=makeHooks(registry),ctx={runId:'synthetic-exchange',agentId:'main'};
 const prompt=await runner.runBeforePromptBuild({prompt:'synthetic',messages:[]},ctx);
 assert(prompt.appendSystemContext.includes('Exchange work budget'));
 await runner.runModelCallStarted({runId:ctx.runId,callId:'one'},ctx);
 await runner.runModelCallStarted({runId:ctx.runId,callId:'two'},ctx);
 const denied=await runner.runBeforeToolCall({toolName:'section11_coaching',params:{operation:'save'}},ctx);
 assert.equal(denied.block,true,'native runner must honor the tool veto before invoking a write');
 assert.equal(await runner.runBeforeToolCall({toolName:'section11_context',params:{}},{runId:'new-exchange'}),undefined);
 const settings=await fn('tool-result-truncation-','resolveCacheTtlPruningSettings');
 const prune=await fn('tool-result-truncation-','pruneExpiredCacheTtlToolResults');
 const pressure=await fn('context-engine-lifecycle-','shouldPreemptivelyCompactBeforePrompt');
 const context=await fn('context-window-guard-','resolveContextWindowInfo');
 const policy={mode:'cache-ttl',ttl:'5m',tools:{allow:['section11_context'],deny:['exec','section11_coaching','write','edit','apply_patch']},hardClear:{enabled:true,placeholder:'Historical read removed; recover fresh whole context.'}};
 const resolved=settings(policy);assert(resolved.isToolPrunable('section11_context'));
 for(const tool of ['exec','section11_coaching','write','edit','apply_patch'])assert(!resolved.isToolPrunable(tool));
 const messages=[{role:'user',content:'Synthetic context; preserve pending decisions.'}];
 const result=(toolName,id,text)=>({role:'toolResult',toolName,toolCallId:id,content:[{type:'text',text}],timestamp:1});
 for(let i=0;i<9;i++){
  messages.push({role:'assistant',content:[{type:'toolCall',id:'r'+i,name:'section11_context',arguments:{operation:'build',task:'morning'}}],timestamp:1});
  messages.push(result('section11_context','r'+i,JSON.stringify({packet_complete:true,synthetic:'x'.repeat(60000),health_context:{priority:0}})));
 }
 const receipt=result('section11_coaching','saved','{"success":true,"revision_id":"synthetic-revision","approval_id":"synthetic-pending-approval","calendar_writes":0}');
 const mixed=result('exec','mixed','Synthetic mixed read/write result; keep receipt: '+JSON.stringify(receipt));
 messages.splice(3,0,receipt,mixed);
 const original=JSON.stringify(messages);
 const projectionState={replacements:new Map(),frozen:new Set(),sourceHashByKey:new Map(),ambiguousBaseKeys:new Set(),restoredCacheTtl:new Map()};
 const args={messages,settings:resolved,projectionState,contextWindowTokens:131072,pruneNewRounds:true,lastCacheTouchAt:1,now:600001};
 const projected=prune(args);
 assert(JSON.stringify(projected).length<original.length/2);
 assert.equal(JSON.stringify(messages),original,'canonical transcript must be immutable');
 for(const protectedMessage of [receipt,mixed,...messages.slice(-6)])assert.deepEqual(projected[messages.indexOf(protectedMessage)],protectedMessage);
 const replay=prune({...args,now:2,pruneNewRounds:false});assert.deepEqual(replay,projected,'projection replay must remain stable');
 const info=context({cfg:{models:{providers:{openai:{models:[{id:'gpt-6.1-sol',contextTokens:131072}]}}}},provider:'openai',modelId:'gpt-6.1-sol',modelContextTokens:1050000,modelContextWindow:1050000});
 assert.equal(info.tokens,131072);
 const oversized=[{role:'user',content:'Synthetic request '+('different training context and dated source '.repeat(25000))}];
 const decision=pressure({messages:oversized,systemPrompt:'Synthetic safety instructions',prompt:'',contextTokenBudget:131072,reserveTokens:16384});
 assert.notEqual(decision.route,'fits');assert(decision.overflowTokens>0);
 const small=pressure({messages:[{role:'user',content:'Synthetic short request'}],systemPrompt:'Preserve safety and receipts',prompt:'',contextTokenBudget:131072,reserveTokens:16384});assert.equal(small.route,'fits');
 return {native_budget_tool_veto:true,native_read_projection_reduced:true,canonical_transcript_unchanged:true,write_and_mixed_receipts_preserved:true,recent_health_preserved:true,projection_replay_stable:true,effective_context_tokens:info.tokens,oversized_prompt_blocked:true,model_calls:0};
}
if(process.argv[1]&&path.resolve(process.argv[1])===path.resolve(new URL(import.meta.url).pathname))console.log(JSON.stringify(await verifyContextPressure(process.argv[2])));
