// Read-only native SDK/schema regression. No model/provider calls or real writes.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL,fileURLToPath} from 'node:url';
import {schema,operationSchemas} from '../examples/agentic/openclaw/coaching-tool/schemas.mjs';

export async function verifyInstalledSchema(packageRoot){
 const internal=name=>import(pathToFileURL(path.join(packageRoot,'node_modules/@openclaw/ai/dist',name)).href);
 const {normalizeOpenAIStrictCompatSchema,normalizeToolParameterSchema,normalizeStrictOpenAIJsonSchema,projectRuntimeToolInputSchema}=await internal('internal/tool-schema.mjs');
 const {validateToolArguments}=await internal('validation.mjs');
 const {projectOpenAITools}=await internal('internal/openai.mjs');
 const check=(parameters,args)=>validateToolArguments({name:'section11_coaching',parameters},{id:'synthetic-schema-only',name:'section11_coaching',arguments:structuredClone(args)});
 const feedback={date:'2026-10-23',state:'normal',note:'Synthetic schema-only case; never athlete feedback',health_clarification:null};
 const old={type:'object',required:['operation'],properties:{operation:{type:'string'},payload:{type:'object'},draft:{type:'object'}}};
 check(old,{operation:'feedback',payload:feedback});
 const broken=normalizeOpenAIStrictCompatSchema(old);
 assert.deepEqual(broken.properties.payload.properties,{});assert.equal(broken.properties.payload.additionalProperties,false);
 assert.throws(()=>check(broken,{operation:'feedback',payload:feedback}));
 const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
 const plan=JSON.parse(fs.readFileSync(path.join(root,'examples/json-examples/coaching_plan.example.json')));
 const review=JSON.parse(fs.readFileSync(path.join(root,'examples/json-examples/coaching_review.example.json')));
 const payload={current_athlete_context:{date:'2026-10-23',source:'Synthetic schema-only source',goals_and_availability:'Synthetic context'},plan};
 const cases=[{operation:'state'},{operation:'feedback',payload:feedback},
  {operation:'feedback',payload:{...feedback,health_clarification:{compatible:false,reason:'Synthetic clarification'}}},
  {operation:'feedback',payload:{...feedback,health_clarification:{compatible:true,reason:'Synthetic clarification'}}},
  {operation:'propose',payload},{operation:'prepare',start:'2026-10-01',end:'2026-10-23'},
  {operation:'save',capture_id:'a'.repeat(64),draft:{observations:review.observations,decisions:review.decisions,candidate_plan:null}},
  {operation:'save',capture_id:'a'.repeat(64),draft:{observations:[],decisions:review.decisions,candidate_plan:plan}},
  {operation:'propose',payload:{...payload,plan:{...plan,sessions:[]}}}];
 cases.push({operation:'propose',payload:{...payload,plan:JSON.parse(fs.readFileSync(path.join(root,'examples/json-examples/event_context.example.json')))}});
 const complex=JSON.parse(fs.readFileSync(path.join(root,'examples/json-examples/checked_complex_workouts.example.json')));
 for(const workout of complex){
  const p=structuredClone(plan);p.sessions=[{session_id:'synthetic',purpose:'Schema fixture',alternatives:[],session_budget_minutes:180,workout}];cases.push({operation:'propose',payload:{...payload,plan:p}});
 }
 const intake={request_id:'synthetic-intake',parent_revision:null,entries:[{key:'goal',kind:'goal',text:'Synthetic reported objective',observed_on:'2026-10-23',source:'Synthetic message only',valid_from:null,valid_until:null,review_on:'2026-11-01'}],open_questions:[]};
 cases.push({operation:'intake',payload:intake});
 const invalid=[{operation:'feedback',payload:{...feedback,unexpected:true}},
  {operation:'feedback',payload:{...feedback,health_clarification:{compatible:'yes',reason:'Synthetic'}}},
  {operation:'feedback',payload:{...feedback,state:'invented'}},
  {operation:'propose',payload:{...payload,plan:{...plan,arbitrary:true}}},
  {operation:'save',capture_id:'a'.repeat(64),draft:{observations:[],decisions:[],candidate_plan:null,snapshot:{}}},
  {operation:'save',capture_id:'a'.repeat(64),draft:{observations:[{arbitrary:true}],decisions:review.decisions,candidate_plan:null}},
  {operation:'state',path:'/arbitrary'}];
 invalid.push({operation:'intake',payload:{...intake,entries:[{...intake.entries[0],untrusted_snapshot:{}}]}});
 const projected=projectOpenAITools([{name:'section11_coaching',parameters:schema}]);assert.equal(projected.diagnostics.length,0);
 const stages={declared:schema,compat:normalizeOpenAIStrictCompatSchema(schema),
  normalized:normalizeToolParameterSchema(schema,{modelProvider:'openai',modelId:'gpt-6-astra'}),
  strict:normalizeStrictOpenAIJsonSchema(normalizeOpenAIStrictCompatSchema(schema)),
  runtime_projection:projectRuntimeToolInputSchema(schema).schema,provider_projection:projected.tools[0].parameters};
 for(const [name,parameters] of Object.entries(stages)){
  for(const args of cases)assert.doesNotThrow(()=>check(parameters,args),name+' must accept '+args.operation);
  for(const args of invalid)assert.throws(()=>check(parameters,args),name+' must reject malformed '+args.operation);
 }
 for(const args of cases)assert.doesNotThrow(()=>check(operationSchemas[args.operation],args));
 for(const args of [{operation:'feedback',payload},{operation:'propose',payload:feedback}])assert.throws(()=>check(operationSchemas[args.operation],args));
 return {old_schema_reproduces_failure:true,valid_cases:cases.length,invalid_cases:invalid.length,conversion_stages:Object.keys(stages),model_calls:0,messages_sent:0,calendar_writes:0};
}
if(process.argv[1]&&path.resolve(process.argv[1])===path.resolve(fileURLToPath(import.meta.url))){
 const result=await verifyInstalledSchema(process.argv[2]??process.env.SECTION11_OPENCLAW_PACKAGE);console.log(JSON.stringify(result));
}
