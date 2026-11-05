// Installed resolver regression: synthetic configuration only, no provider calls.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {execFileSync} from 'node:child_process';

export async function verifyCompactionModel(packageRoot){
 const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
 const generated=JSON.parse(execFileSync('python3',['-c',
  "import json,sys;sys.path.insert(0,sys.argv[1]);from efficiency_config import configure_primary_models;print(json.dumps(configure_primary_models({'agents':{'defaults':{},'entries':{'main':{'model':'openai/gpt-6.1-sol@openai:synthetic-profile'}}}})))",
  path.join(root,'examples/agentic/openclaw')],{encoding:'utf8'}));
 const dist=path.join(packageRoot,'dist');
 let resolve;
 for(const file of fs.readdirSync(dist).filter(n=>/^context-engine-maintenance-.*\.mjs$/.test(n))){
  const module=await import(pathToFileURL(path.join(dist,file)).href);
  resolve=Object.values(module).find(v=>typeof v==='function'&&v.name==='resolveEmbeddedCompactionTarget');
  if(resolve)break;
 }
 assert(resolve,'installed compaction target resolver required');
 const args={config:generated,provider:'openai',modelId:'gpt-6.1-sol',defaultProvider:'openai',
  defaultModel:'gpt-6.1-sol',authProfileId:'openai:synthetic-profile',harnessRuntime:'openclaw'};
 const target=resolve(args);
 assert.equal(target.provider,'openai');assert.equal(target.model,'gpt-6-luna');
 assert.equal(target.authProfileId,args.authProfileId);
 assert.equal(generated.agents.entries.main.model,'openai/gpt-6.1-sol@openai:synthetic-profile');
 assert.equal(generated.agents.entries.main.thinkingDefault,'medium');
 assert.equal(generated.agents.defaults.compaction.thinkingLevel,'low');
 const old=structuredClone(generated);
 old.agents.defaults.compaction.model+='@openai:synthetic-profile';
 const previous=resolve({...args,config:old});
 return {compaction_model:target.model,active_auth_preserved:true,coaching_sol_medium_preserved:true,
  old_suffix_reproduced:previous.model.includes('@'),model_calls:0,calendar_writes:0};
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url))
 console.log(JSON.stringify(await verifyCompactionModel(process.argv[2]??process.env.SECTION11_OPENCLAW_PACKAGE)));
