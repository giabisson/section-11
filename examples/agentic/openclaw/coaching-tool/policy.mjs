import {spawn} from 'node:child_process';
import path from 'node:path';

export const schema={type:'object',additionalProperties:false,required:['operation'],properties:{
 operation:{type:'string',enum:['state','propose','feedback','prepare','save']},
 payload:{type:'object'},start:{type:'string'},end:{type:'string'},
 capture_id:{type:'string',pattern:'^[a-f0-9]{64}$'},draft:{type:'object'}
}};

export function requestFor(params,config){
 if(!path.isAbsolute(config?.script??'')||!path.isAbsolute(config?.profile??''))throw Error('fixed_paths_required');
 const fields={state:['operation'],propose:['operation','payload'],feedback:['operation','payload'],prepare:['operation','start','end'],save:['operation','capture_id','draft']}[params?.operation];
 if(!fields||Object.keys(params).some(k=>!fields.includes(k))||fields.some(k=>!Object.hasOwn(params,k)))throw Error('invalid_fields');
 for(const key of ['start','end'])if(params[key]!==undefined&&!/^\d{4}-\d{2}-\d{2}$/.test(params[key]))throw Error('invalid_date');
 if(params.capture_id!==undefined&&!/^[a-f0-9]{64}$/.test(params.capture_id))throw Error('invalid_capture');
 for(const key of ['payload','draft'])if(params[key]!==undefined&&(!params[key]||typeof params[key]!=='object'||Array.isArray(params[key])))throw Error('invalid_object');
 const body=JSON.stringify(params);if(Buffer.byteLength(body)>2000000)throw Error('input_size_limit');
 return {args:[config.script,'--profile',config.profile],body};
}

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
    try{const p=JSON.parse(Buffer.concat(chunks).toString('utf8'));if(code!==0||p.packet_complete!==true||p.success!==true)throw Error('invalid_ack');finish({content:[{type:'text',text:JSON.stringify(p)}]});}catch{failure();}
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
