// Public hooks cannot cancel a provider request. This gate bounds further tool
// admission, reserves a final response, and reports actual end-of-attempt usage.
import {createHash} from 'node:crypto';
export function exchangeBudget(config={},emit=()=>{}){
  const limits={modelCalls:6,toolCalls:10,estimatedTokens:300000,...config};
  for(const [k,v] of Object.entries(limits))if(!['modelCalls','toolCalls','estimatedTokens'].includes(k)||!Number.isSafeInteger(v)||v<({modelCalls:2,toolCalls:1,estimatedTokens:10000}[k])||v>({modelCalls:20,toolCalls:40,estimatedTokens:2000000}[k]))throw Error('invalid_exchange_budget');
  const runs=new Map();
  function state(e,c){
    // Never use sessionId: a conversation contains many separate exchanges.
    const id=c?.runId??e.runId;if(!id)return;
    if(!runs.has(id)){if(runs.size>=256)return;runs.set(id,{id,calls:new Set(),tools:new Set(),results:new Set(),contextBytes:0,estimatedTokens:0,blocked:0});}
    return runs.get(id);
  }
  const reason='Exchange work budget reached. Stop tool work and give a concise status with saved write receipts, pending steps and any uncertainty. Do not repeat a write or claim unsaved work succeeded. Continue remaining work only after a new user request.';
  return {
    before_prompt_build(e,c){state(e,c);return {appendSystemContext:`Exchange work budget: at most ${limits.modelCalls-1} model attempts before a reserved final response, ${limits.toolCalls} tools, target ${limits.estimatedTokens} estimated cumulative tokens including repeated context. Batch known relevant exact references with section11_context references (up to six); do not retrieve unrelated sections. At budget exhaustion stop new work, preserve write receipts, report what is saved and what remains. Never retry blocked tools or bypass limits through exec/delegation. Missing HRV alone is not a reason to stop training.`};},
    llm_input(e,c){const s=state(e,c);if(s)s.contextBytes=Math.max(s.contextBytes,Buffer.byteLength(JSON.stringify([e.systemPrompt,e.prompt,e.historyMessages,e.tools])));},
    model_call_started(e,c){const s=state(e,c);if(!s||!e.callId||s.calls.has(e.callId))return;s.calls.add(e.callId);
      // Deliberately labelled estimate, NOT billed tokens or ChatGPT quota.
      // Hooks expose actual normalized usage only at the end of an attempt.
      s.estimatedTokens+=Math.ceil(s.contextBytes/3)+16384;
    },
    before_tool_call(e,c){const s=state(e,c);if(!s)return {block:true,blockReason:'Exchange budget requires a stable run identity and available tracking capacity.'};
      const key=e.toolCallId;if(key&&s.tools.has(key))return;
      if(s.calls.size>=limits.modelCalls-1||s.tools.size>=limits.toolCalls||s.estimatedTokens>=limits.estimatedTokens){s.blocked++;return {block:true,blockReason:reason};}
      // Parallel calls reserve slots synchronously; already admitted writes finish.
      s.tools.add(key??Symbol('tool'));
    },
    after_tool_call(e,c){const s=state(e,c);if(!s)return;if(e.toolCallId&&s.results.has(e.toolCallId))return;if(e.toolCallId)s.results.add(e.toolCallId);s.contextBytes+=Buffer.byteLength(JSON.stringify(e.result??null));},
    llm_output(e,c){const s=state(e,c);if(!s)return;
      // Native usage is attempt aggregate: never add it once per model call.
      const usage={};for(const k of ['input','output','cacheRead','cacheWrite','total'])if(Number.isFinite(e.usage?.[k])&&e.usage[k]>=0)usage[k]=e.usage[k];
      emit({kind:'section11_exchange_attempt',run:createHash('sha256').update(s.id).digest('hex').slice(0,16),observedModelCalls:s.calls.size,admittedTools:s.tools.size,blockedTools:s.blocked,estimatedTokens:s.estimatedTokens,actualAttemptUsage:usage,limits,scope:'tool-admission guard; provider retries/compaction and final response are not hard-capped'});
    },
    agent_end(e,c){const id=c?.runId??e.runId;if(id)runs.delete(id);}
  };
}
