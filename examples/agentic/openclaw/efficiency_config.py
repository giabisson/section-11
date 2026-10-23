"""Pure primary-only configuration and durable source-pointer construction."""
import copy

RECOVERY_HEADING='Section 11 context recovery'


def configure(config):
    c=copy.deepcopy(config);defaults=c['agents']['defaults']
    defaults['contextPruning']={'mode':'cache-ttl','ttl':'5m','tools':{'allow':['section11_context'],'deny':['exec','section11_coaching','write','edit','apply_patch']},
                               'hardClear':{'enabled':True,'placeholder':'[Historical coaching context removed. Read a fresh section11_context packet before using numbers or prescribing.]'}}
    compaction=defaults.setdefault('compaction',{})
    compaction.update(mode='safeguard',identifierPolicy='strict',recentTurnsPreserve=3,
                      qualityGuard={'enabled':True,'maxRetries':1},maxActiveTranscriptBytes=262144,
                      keepRecentTokens=8192,midTurnPrecheck={'enabled':True})
    # Direct typed reads remain distinguishable from writes and mixed exec results.
    c.setdefault('tools',{})['codeMode']=False
    sections=compaction.setdefault('postCompactionSections',[])
    if RECOVERY_HEADING not in sections:sections.append(RECOVERY_HEADING)
    # This OAuth route supports its session cache key, not API lifetime fields.
    # "short" explicitly leaves lifetime selection to the provider.
    c['agents']['entries']['main'].setdefault('params',{})['cacheRetention']='short'
    return c



PRIMARY_MODEL='openai/gpt-6.1-sol'
UTILITY_MODEL='openai/gpt-6-luna'
CONTEXT_TOKENS=131072


def configure_primary_models(config):
    """Explicit operator policy: Sol medium owns coaching; Luna is a helper.

    Retain the verified primary authentication pin. Closed model policy prevents
    old overrides, fallbacks or benchmark promotion from reintroducing Astra.
    Separate account configurations are never read or changed by this function.
    """
    c=copy.deepcopy(config);defaults=c['agents']['defaults'];main=c['agents']['entries']['main']
    old=main.get('model',defaults.get('model',{}).get('primary',''))
    if not isinstance(old,str):raise ValueError('explicit_primary_model_required')
    suffix='@'+old.split('@',1)[1] if '@' in old else ''
    allowed=[PRIMARY_MODEL,UTILITY_MODEL]
    defaults['model']={'primary':PRIMARY_MODEL+suffix}
    defaults['thinkingDefault']='medium';defaults['utilityModel']=UTILITY_MODEL+suffix
    defaults['modelPolicy']={'allow':allowed}
    defaults['models']={key:value for key,value in defaults.get('models',{}).items() if key in allowed}
    main['model']=PRIMARY_MODEL+suffix;main['utilityModel']=UTILITY_MODEL+suffix
    main['modelPolicy']={'allow':allowed}
    main['models']={key:value for key,value in main.get('models',{}).items() if key in allowed}
    for registry in (defaults['models'],main['models']):
        settings=registry.setdefault(PRIMARY_MODEL,{})
        settings['agentRuntime']={'id':'openclaw'}
        registry.setdefault(UTILITY_MODEL,{})['agentRuntime']={'id':'openclaw'}
    # Context caps belong to provider catalog metadata, not per-agent aliases.
    # Leave transport, base URL and authentication fields untouched.
    provider=c.setdefault('models',{}).setdefault('providers',{}).setdefault('openai',{})
    models=provider.setdefault('models',[])
    model=next((row for row in models if row.get('id')=='gpt-6.1-sol'),None)
    if model is None:
        model={'id':'gpt-6.1-sol','name':'GPT-6.1 Sol'};models.append(model)
    model.update(contextTokens=CONTEXT_TOKENS,maxTokens=16384)
    compaction=defaults.setdefault('compaction',{})
    compaction.update(model=UTILITY_MODEL+suffix,thinkingLevel='low')
    compaction.setdefault('memoryFlush',{})['model']=UTILITY_MODEL+suffix
    defaults.setdefault('subagents',{}).update(model=UTILITY_MODEL+suffix,thinking='low')
    return c


def configure_keyword_memory(config):
    """Deliberately opt the primary agent into local keyword-only memory recall.

    OpenClaw 2026.10.6 uses agents.entries.<id>.memory.search. Do not rely
    on provider fallback: an FTS index can otherwise conflict with default
    OpenAI embedding identity on the next query. No session backfill is enabled.
    """
    c=copy.deepcopy(config)
    search=c['agents']['entries']['main'].setdefault('memory',{}).setdefault('search',{})
    search.update(provider='none',sources=['memory'],rememberAcrossConversations=False)
    return c


def recovery_block(context_profile,profile_path):
    return f'''## {RECOVERY_HEADING}

Use direct section11_context and section11_coaching tools for coaching operations; do not wrap typed reads in exec. Mixed exec/write results are deliberately protected, not prunable read data. The primary coaching model is GPT-6.1 Sol at medium; Luna handles utility summarization and explicitly delegated bounded tasks. Never select Astra or use Luna to independently change the training strategy. Tools themselves execute deterministically without an extra model call.

After compaction, reset, history omission or tool-result pruning, read a fresh section11_context task packet before quoting any current number or prescribing. Historical JSON fragments and memory notes are not valid current packets. Require valid whole JSON and packet_complete:true. If intake entries, dossier sections or history rows are explicitly deferred, follow required_retrieval before relying on those facts; use section11_context intake for the complete saved goals and constraints. A transport marker is not health clearance or complete history. Use exact source sections and date-filtered history for omitted dependencies.

The operator-selected stable athlete source is `{context_profile['dossier']}`; its authority/coverage is labelled by the fresh reader profile `{profile_path}`. Read the fresh task packet's `athlete_intake` for saved goals, dated availability and recovery constraints, even when no plan exists. Read observation/validity/review flags; historical health is not current clearance. Save explicit onboarding facts with section11_coaching operation intake and verify state before claiming success. Ask only missing/changed/current-health questions, not the whole intake again. Do not copy an old calendar as current availability. Check the current private managed-plan revision/review if one exists; absent/unavailable records are unknown, never permission to reconstruct a plan from memory or change a calendar.

`MEMORY.md` is a small durable source index and stable preference note. Persist only explicit athlete-confirmed durable preferences/constraints with source/date; temporary symptoms, availability and feedback need an observation date and expiry/recheck, not promotion to timeless facts. Preserve unresolved asks, user corrections, decision/confirmation status and exact plan revision IDs across compaction. If those are unavailable, clarify before acting. Never save credentials, duplicate whole packets or keep dynamic training metrics in the always-loaded memory file. Existing daily memory remains historical and must not override fresh sources or the athlete's current report.

Missing overnight HRV is intentional and never a requirement to wear a device. RHR is optional too. Current subjective feedback is valid coaching evidence; absent wearables alone do not impose rest or prevent progression. Preserve every health stop/uncertainty and existing calendar-confirmation requirement.
'''


def memory_index(context_profile):
    return f'''# Durable cycling-coach context

This is a source index and stable preference note, not a current training snapshot.

- Stable goals, preferences and constraints: operator-selected `{context_profile['dossier']}`. Use the bounded reader to establish its current authority and relevant exact sections.
- Current readiness, training, wellness and calendar evidence: fresh section11_context task packet from `{context_profile['data_dir']}`. Never reuse old numbers or interpret publication as completion.
- Saved onboarding: fresh section11_coaching state or task packet athlete_intake; it persists independently of a plan. Preserve source dates, expiry and review flags; health observations never constitute current clearance.
- Plan continuity: current private managed-plan revision/review when available. An unavailable record is unknown; do not reconstruct or publish from a chat summary.
- Current stable communication/measurement preferences: `USER.md`, with observation date and active/superseded status. Current self-reported health/restedness remains useful evidence.

After reset/compaction, recover source facts before new prescriptions. Date and recheck temporary feedback/availability. Retain pending asks, corrections and confirmation/revision IDs; uncertainty requires clarification. Do not append packets, credentials, duplicated metrics or old schedules here. Daily memory notes are historical, never a fresh source of numbers.
'''


def user_preference_block():
    return '''## Coaching measurement preferences

- Active; observed 2026-10-22; source: athlete statement in implementation conversation. Treat Fitbit overnight HRV as intermittent by choice and RHR as available most days. Accept current self-reported health/restedness as useful evidence. Do not require sleep-device wear, HRV or RHR measurements, or restrict training merely because they are absent. Supersede this directive in place if the athlete changes the preference.
'''
