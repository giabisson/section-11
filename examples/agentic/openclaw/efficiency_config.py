"""Pure primary-only configuration and durable source-pointer construction."""
import copy

RECOVERY_HEADING='Section 11 context recovery'


def configure(config):
    c=copy.deepcopy(config);defaults=c['agents']['defaults']
    defaults['contextPruning']={'mode':'cache-ttl','ttl':'30m','tools':{'allow':['section11_context']},
                               'hardClear':{'enabled':True,'placeholder':'[Historical coaching context removed. Read a fresh section11_context packet before using numbers or prescribing.]'}}
    compaction=defaults.setdefault('compaction',{})
    compaction.update(mode='safeguard',identifierPolicy='strict',recentTurnsPreserve=3,
                      qualityGuard={'enabled':True,'maxRetries':1},maxActiveTranscriptBytes=2097152)
    sections=compaction.setdefault('postCompactionSections',[])
    if RECOVERY_HEADING not in sections:sections.append(RECOVERY_HEADING)
    # This OAuth route supports its session cache key, not API lifetime fields.
    # "short" explicitly leaves lifetime selection to the provider.
    c['agents']['entries']['main'].setdefault('params',{})['cacheRetention']='short'
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

After compaction, reset, history omission or tool-result pruning, read a fresh section11_context task packet before quoting any current number or prescribing. Historical JSON fragments and memory notes are not valid current packets. Require valid whole JSON and packet_complete:true. A transport marker is not health clearance or complete history. Use exact source sections and date-filtered history for omitted dependencies.

The operator-selected stable athlete source is `{context_profile['dossier']}`; its authority/coverage is labelled by the fresh reader profile `{profile_path}`. Re-read its relevant goals, availability and constraints; do not copy an old calendar as current availability. Check the current private managed-plan revision/review if one exists; absent/unavailable records are unknown, never permission to reconstruct a plan from memory or change a calendar.

`MEMORY.md` is a small durable source index and stable preference note. Persist only explicit athlete-confirmed durable preferences/constraints with source/date; temporary symptoms, availability and feedback need an observation date and expiry/recheck, not promotion to timeless facts. Preserve unresolved asks, user corrections, decision/confirmation status and exact plan revision IDs across compaction. If those are unavailable, clarify before acting. Never save credentials, duplicate whole packets or keep dynamic training metrics in the always-loaded memory file. Existing daily memory remains historical and must not override fresh sources or the athlete's current report.

Missing overnight HRV is intentional and never a requirement to wear a device. RHR is optional too. Current subjective feedback is valid coaching evidence; absent wearables alone do not impose rest or prevent progression. Preserve every health stop/uncertainty and existing calendar-confirmation requirement.
'''


def memory_index(context_profile):
    return f'''# Durable cycling-coach context

This is a source index and stable preference note, not a current training snapshot.

- Stable goals, preferences and constraints: operator-selected `{context_profile['dossier']}`. Use the bounded reader to establish its current authority and relevant exact sections.
- Current readiness, training, wellness and calendar evidence: fresh section11_context task packet from `{context_profile['data_dir']}`. Never reuse old numbers or interpret publication as completion.
- Plan continuity: current private managed-plan revision/review when available. An unavailable record is unknown; do not reconstruct or publish from a chat summary.
- Current stable communication/measurement preferences: `USER.md`, with observation date and active/superseded status. Current self-reported health/restedness remains useful evidence.

After reset/compaction, recover source facts before new prescriptions. Date and recheck temporary feedback/availability. Retain pending asks, corrections and confirmation/revision IDs; uncertainty requires clarification. Do not append packets, credentials, duplicated metrics or old schedules here. Daily memory notes are historical, never a fresh source of numbers.
'''


def user_preference_block():
    return '''## Coaching measurement preferences

- Active; observed 2026-10-22; source: athlete statement in implementation conversation. Treat Fitbit overnight HRV as intermittent by choice and RHR as available most days. Accept current self-reported health/restedness as useful evidence. Do not require sleep-device wear, HRV or RHR measurements, or restrict training merely because they are absent. Supersede this directive in place if the athlete changes the preference.
'''
