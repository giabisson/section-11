// Installed whole-skill read plus budgeted discovery/planning path. No provider calls.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL,fileURLToPath} from 'node:url';
import {exchangeBudget} from '../examples/agentic/openclaw/context-tool/exchange-budget.mjs';

export async function verifyPlanningEntry(packageRoot){
 const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
 const dist=path.join(packageRoot,'dist');
 const name=fs.readdirSync(dist).find(n=>/^agent-tools\.read-.*\.mjs$/.test(n));
 assert(name,'installed native read implementation required');
 const source=fs.readFileSync(path.join(dist,name),'utf8');
 const alias=source.match(/wrapReadToolWithSkillContent as (\w+)/)?.[1];assert(alias);
 const wrap=(await import(pathToFileURL(path.join(dist,name)).href))[alias];
 const read=async content=>{
  const locator='node://section11-entry/SKILL.md';
  const tool=wrap({name:'read',parameters:{},execute(){throw Error('unexpected filesystem access');}},
   [{filePath:locator,readContent:content}],{modelContextWindowTokens:131072});
  return tool.execute('synthetic-entry-read',{path:locator,limit:260});
 };
 const current=fs.readFileSync(path.join(root,'SKILL.md'),'utf8');
 const result=await read(current);
 assert.equal(result.details?.kind,'text');
 assert.equal(result.details?.content,current,'whole entry must be served, not an error or excerpt');
 assert(result.content.some(b=>b.text?.includes('planning_setup')));
 // The retained former-size reference reproduces the production whole-skill refusal.
 const refused=await read(fs.readFileSync(path.join(root,'SKILL_REFERENCE.md'),'utf8'));
 assert(refused.content.some(b=>b.text?.includes('Skill instructions cannot be partially served')));
 const records=[],budget=exchangeBudget({},r=>records.push(r)),ctx={runId:'synthetic-broker-plan'};
 budget.before_prompt_build({},ctx);
 let model=0,tool=0;
 function turn(){budget.llm_input({systemPrompt:'Synthetic prompt',historyMessages:[]},ctx);budget.model_call_started({callId:String(++model)},ctx);}
 function admitted(name,result={}){
  const e={toolName:name,toolCallId:String(++tool)};
  assert.equal(budget.before_tool_call(e,ctx),undefined,`stage ${name} must fit unchanged guard`);
  budget.after_tool_call({...e,result},ctx);
 }
 turn();admitted('tool_call');admitted('skills_read',result);
 // Same model turn: broker wrappers AND nested tools both consume their real slots.
 turn();admitted('tool_call');admitted('section11_context');admitted('tool_call');
 admitted('section11_coaching');admitted('tool_describe');
 turn();admitted('tool_call');admitted('section11_coaching',{success:true,revision_id:'synthetic-only'});
 turn();budget.llm_output({usage:{input:0,output:0}},ctx);
 assert.equal(records[0].blockedTools,0);assert.equal(records[0].admittedTools,9);
 budget.agent_end({},ctx);
 return {whole_skill_bytes:Buffer.byteLength(current),native_read_verified:true,budget_replay_model_turns:model,
  budget_replay_tool_admissions:tool,scope:'Deterministic native read and control-flow replay; not live model planning quality.',
  model_calls:0,messages_sent:0,calendar_writes:0};
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url))
 console.log(JSON.stringify(await verifyPlanningEntry(process.argv[2]??process.env.SECTION11_OPENCLAW_PACKAGE)));
