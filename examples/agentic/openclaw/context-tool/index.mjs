import {definePluginEntry,buildJsonPluginConfigSchema} from 'openclaw/plugin-sdk/plugin-entry';
import {exchangeBudget} from './exchange-budget.mjs';
import manifest from './openclaw.plugin.json' with {type:'json'};
import {schema,argvFor,executeContext,reportGate,boundedNoticeFilter} from './policy.mjs';

export default definePluginEntry({id:'section11-context',name:'Section 11 bounded context',
  configSchema:()=>buildJsonPluginConfigSchema(manifest.configSchema),
  register(api){
    api.registerTool({name:'section11_context',label:'Section 11 context',description:'Batch exact reference reads with operation references (requests array, up to six source/heading pairs), or fresh bounded coaching data, saved intake or exact protocol/library/dossier sections. Follow required_retrieval for deferred facts; intake returns the complete saved onboarding record. Read-only; no shell or arbitrary paths.',parameters:schema,
      async execute(_id,params,signal){
        try{return await executeContext(argvFor(params,api.pluginConfig),signal);}
        catch{return {isError:true,content:[{type:'text',text:'Invalid bounded context request.'}]};}
      }});
    if(api.pluginConfig?.exchangeBudget && api.pluginConfig?.reportMode!==true){
      const hooks=exchangeBudget(api.pluginConfig.exchangeBudget,record=>api.logger.info(JSON.stringify(record)));
      for(const [name,handler] of Object.entries(hooks))api.on(name,handler);
    }
    if(api.pluginConfig?.quietBoundedContextNotices===true)api.on('message_sending',boundedNoticeFilter);
    if(api.pluginConfig?.reportMode===true)api.on('before_tool_call',reportGate());
  }
});
