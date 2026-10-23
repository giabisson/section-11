import {spawn} from 'node:child_process';
import path from 'node:path';

export const schema = {type:'object',additionalProperties:false,required:['operation'],properties:{
  operation:{type:'string',enum:['build','intake','activities','history','long_term','history_detail','review','headings','section']},
  task:{type:'string',enum:['morning','weekly','workout','plan','post_workout']},
  activity_id:{type:'string',maxLength:128},review_id:{type:'string',maxLength:128},start:{type:'string'},end:{type:'string'},
  tier:{type:'string',enum:['daily','weekly','monthly']},
  source:{type:'string',enum:['protocol','workouts','dossier','report']},
  heading:{type:'string',minLength:1,maxLength:200}
}};

export function argvFor(params, config) {
  if (!config || !path.isAbsolute(config.script ?? '') || !path.isAbsolute(config.profile ?? '')) throw Error('invalid_config');
  if (!params || Object.keys(params).some(k=>!Object.hasOwn(schema.properties,k))) throw Error('invalid_params');
  const args=[config.script,'--profile',config.profile];
  const allowed={build:['task','activity_id'],history:['start','end','tier'],long_term:[],intake:[],activities:['task','activity_id'],history_detail:['activity_id'],review:['review_id'],headings:['source','task'],section:['source','task','heading']};
  const fields=allowed[params.operation];
  if (!fields || Object.keys(params).some(k=>k!=='operation'&&!fields.includes(k))) throw Error('invalid_operation');
  args.push(params.operation);
  for (const field of fields) {
    const value=params[field];
    if (value===undefined) continue;
    const spec=schema.properties[field];
    if(typeof value!=='string'||value.length> (spec.maxLength??128)||value.includes('\0')||(spec.enum&&!spec.enum.includes(value)))throw Error('invalid_value');
    if(['start','end'].includes(field)&&!/^\d{4}-\d{2}-\d{2}$/.test(value))throw Error('invalid_date');
    args.push('--'+field.replaceAll('_','-'),value);
  }
  if(['build','activities'].includes(params.operation)&&!params.task)throw Error('task_required');
  if(params.operation==='history'&&(!params.start||!params.end))throw Error('dates_required');
  if(params.operation==='history_detail'&&!params.activity_id)throw Error('activity_id_required');
  if(['headings','section'].includes(params.operation)&&!params.source)throw Error('source_required');
  if(params.operation==='section'&&!params.heading)throw Error('heading_required');
  return args;
}

export function executeContext(args, signal, spawnImpl=spawn) {
  return new Promise(resolve=>{
    let child,chunks=[],bytes=0,settled=false;
    const finish=value=>{if(settled)return;settled=true;clearTimeout(timer);signal?.removeEventListener('abort',abort);resolve(value);};
    const failure=()=>finish({isError:true,content:[{type:'text',text:'Context read failed or exceeded its bound; no partial packet supplied.'}]});
    const abort=()=>{child?.kill('SIGKILL');failure();};
    const timer=setTimeout(abort,15000);
    if(signal?.aborted){abort();return;}
    signal?.addEventListener('abort',abort,{once:true});
    try {
      child=spawnImpl('/usr/bin/python3',args,{shell:false,stdio:['ignore','pipe','pipe']});
      child.stdout.on('data',chunk=>{bytes+=chunk.length;if(bytes>49153){abort();return;}chunks.push(chunk);});
      // Discard stderr, which may contain private source text. Bound it too.
      let errorBytes=0;child.stderr.on('data',chunk=>{errorBytes+=chunk.length;if(errorBytes>4096)abort();});
      child.on('error',failure);
      child.on('close',code=>{
        if(settled)return;
        try {
          const packet=JSON.parse(Buffer.concat(chunks).toString('utf8'));
          if(code!==0||packet.packet_complete!==true)throw Error('incomplete');
          finish({content:[{type:'text',text:JSON.stringify(packet)}]});
        }catch{failure();}
      });
    }catch{failure();}
  });
}

export function reportGate() {
  const counts=new Map();
  return (event,ctx)=>{
    const id=ctx.runId??event.runId??ctx.sessionId;
    if(!id)return {block:true,blockReason:'Report tool authority requires a run identity.'};
    const count=(counts.get(id)??0)+1;counts.set(id,count);
    if(counts.size>256)counts.delete(counts.keys().next().value);
    if(event.toolName!=='section11_context'||count>6)return {block:true,blockReason:'Report runs allow only six bounded read-only context calls.'};
  };
}
