import {spawn} from 'node:child_process';
import path from 'node:path';
import {operationSchemas} from './schemas.mjs';

export {schema} from './schemas.mjs';

export function requestFor(params,config){
 if(!path.isAbsolute(config?.script??'')||!path.isAbsolute(config?.profile??''))throw Error('fixed_paths_required');
 const operation=operationSchemas[params?.operation];
 const fields=operation?Object.keys(operation.properties):undefined;
 if(!fields||Object.keys(params).some(k=>!fields.includes(k))||operation.required.some(k=>!Object.hasOwn(params,k)))throw Error('invalid_fields');
 for(const key of ['start','end'])if(params[key]!==undefined&&!/^\d{4}-\d{2}-\d{2}$/.test(params[key]))throw Error('invalid_date');
 if(params.capture_id!==undefined&&!/^[a-f0-9]{64}$/.test(params.capture_id))throw Error('invalid_capture');
 for(const key of ['payload','draft','feedback'])if(params[key]!==undefined){
  const value=params[key],spec=key==='feedback'?operationSchemas.feedback.properties.payload:params.operation==='planning_setup'&&key==='payload'?operationSchemas.intake.properties.payload:operation.properties[key];
  if(params.operation==='planning_setup'&&['payload','feedback'].includes(key)&&value===null)continue;
  if(!value||typeof value!=='object'||Array.isArray(value))throw Error('invalid_object');
  if(!spec?.properties||Object.keys(value).some(k=>!Object.hasOwn(spec.properties,k))||spec.required.some(k=>!Object.hasOwn(value,k)))throw Error('invalid_operation_payload');
 }
 if(params.references!==undefined){
  if(!Array.isArray(params.references)||params.references.length<1||params.references.length>6)throw Error('invalid_references');
  for(const r of params.references)if(!r||Object.keys(r).some(k=>!['source','heading','task'].includes(k))||!['protocol','workouts','dossier','report'].includes(r.source)||typeof r.heading!=='string'||!r.heading.length||r.heading.length>200||(r.task!==undefined&&(r.source!=='report'||!['morning','weekly','post_workout'].includes(r.task))))throw Error('invalid_reference');
 }
 const body=JSON.stringify(params);if(Buffer.byteLength(body)>2000000)throw Error('input_size_limit');
 return {args:[config.script,'--profile',config.profile],body};
}

const validationHints={
 continuous_role_or_dose:'Continuous templates require role work for every main step (including easy endurance). Check total_seconds and work_zones against workout_inputs; preserve dose/targets unless a genuine constraint requires changing them.',
 template_pattern:'Check the installed template pattern, repetitions, recoveries, cadence and configured zones. Never strip the prescription to bypass validation.',
 compiled_description:'Omit a caller-rendered description or supply the exact compiler rendering. Keep the structured prescription.',
 compiled_duration:'Declared duration must equal every expanded step including recoveries; fix metadata or the intended dose explicitly.',
 stale_parent:'Read the current saved plan and preserve changes before proposing against its actual parent revision.',
 request_id_conflict:'This request ID belongs to different saved content. Recover its receipt/current state before using a new request ID.',
};

export function executeCoaching(request,signal,spawnImpl=spawn){
 return new Promise(resolve=>{
  let child,bytes=0,chunks=[],done=false;
  const finish=value=>{if(done)return;done=true;clearTimeout(timer);signal?.removeEventListener('abort',abort);resolve(value);};
  const failure=()=>finish({isError:true,content:[{type:'text',text:'Coaching operation failed or its acknowledgement was incomplete. Read stored state/reviews before retrying; do not assume a write failed.'}]});
  const abort=()=>{child?.kill('SIGKILL');failure();};const timer=setTimeout(abort,85000);
  if(signal?.aborted){abort();return;}signal?.addEventListener('abort',abort,{once:true});
  try{
   child=spawnImpl('/usr/bin/python3',request.args,{shell:false,stdio:['pipe','pipe','pipe']});
   child.stdin.on('error',failure);child.stdin.end(request.body);
   child.stdout.on('data',chunk=>{bytes+=chunk.length;if(bytes>49153){abort();return;}chunks.push(chunk);});
   let errors=0;child.stderr.on('data',chunk=>{errors+=chunk.length;if(errors>4096)abort();});
   child.on('error',failure);child.on('close',code=>{
    if(done)return;
    try{const p=JSON.parse(Buffer.concat(chunks).toString('utf8'));
     if(code===2&&p.packet_complete===true&&p.success===false&&p.error_code==='plan_validation_failed'&&p.plan_saved===false&&p.calendar_writes===0&&Object.hasOwn(validationHints,p.validation_code)){finish({isError:true,content:[{type:'text',text:JSON.stringify({success:false,error_code:p.error_code,validation_code:p.validation_code,plan_saved:false,calendar_writes:0,packet_complete:true,hint:validationHints[p.validation_code]})}]});return;}
     if(code!==0||p.packet_complete!==true||p.success!==true)throw Error('invalid_ack');finish({content:[{type:'text',text:JSON.stringify(p)}]});}catch{failure();}
   });
  }catch{failure();}
 });
}

export function coachingGate(){
 const counts=new Map();
 return (event,ctx)=>{
  if(event.toolName!=='section11_coaching')return;
  const id=ctx.runId??event.runId;
  if(!id)return {block:true,blockReason:'Managed coaching requires a run identity.'};
  const count=(counts.get(id)??0)+1;counts.set(id,count);
  if(counts.size>256)counts.delete(counts.keys().next().value);
  if(count>8)return {block:true,blockReason:'Managed coaching allows eight bounded operations per run. Read saved state before retrying a write.'};
 };
}
