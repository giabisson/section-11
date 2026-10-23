import {definePluginEntry,buildJsonPluginConfigSchema} from 'openclaw/plugin-sdk/plugin-entry';
import manifest from './openclaw.plugin.json' with {type:'json'};
import {schema,requestFor,executeCoaching,coachingGate} from './policy.mjs';

export default definePluginEntry({id:'section11-coaching',name:'Section 11 managed coaching',
 configSchema:()=>buildJsonPluginConfigSchema(manifest.configSchema),
 register(api){api.registerTool({name:'section11_coaching',label:'Section 11 plans and reviews',
  description:'Read or propose the actual private managed plan, record dated athlete feedback, prepare fresh source evidence and save a validated review. Local persistence only; never publishes calendar changes or sends messages. Ask current goals/availability before onboarding. feedback payload: date/state/note/nullable health_clarification. propose payload: current_athlete_context and complete schema-1 plan. save draft: observations/decisions/nullable candidate_plan. Backend checks remain authoritative.',
  parameters:schema,async execute(_id,params,signal){try{return await executeCoaching(requestFor(params,api.pluginConfig),signal);}catch{return {isError:true,content:[{type:'text',text:'Invalid managed-coaching request.'}]};}}
 });api.on('before_tool_call',coachingGate());}
});
