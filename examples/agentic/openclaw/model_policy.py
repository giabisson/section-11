"""Conservative report routing. Unreviewed experiments never select a model."""
import copy
from pathlib import Path
import re
import time


def routine(packet):
    """Routing eligibility only; never a diagnosis, readiness score or clearance."""
    snap=packet.get('snapshot',{});decision=snap.get('readiness_decision') or {};health=snap.get('health_context') or {}
    return (packet.get('task')=='morning' and snap.get('freshness')=='current'
            and snap.get('refresh_required_before_prescribing') is False
            and decision.get('recommendation')=='go' and decision.get('priority')==3
            and not decision.get('race_week_defers') and not decision.get('modification')
            and not decision.get('alarm_refs') and not snap.get('alerts') and not snap.get('athlete_notes')
            and health.get('source_status')=='ok' and health.get('marker_active') is False
            and health.get('recent_marker') is False and health.get('clarification_required') is False)


def selection(packet,config,path,load_private,assessor,now=None):
    baseline=config['agents']['entries']['main']['model']
    result={'route':'baseline','model':baseline,'thinking':config['agents']['defaults'].get('thinkingDefault','medium')}
    if not path.exists():return {**result,'reason':'no_approved_policy'}
    try:
        policy=load_private(path)
        if set(policy)!={'schema_version','enabled','benchmark_dir','manifest_sha256'} or policy['schema_version']!=1:
            raise ValueError('policy_schema')
        if policy['enabled'] is not True:return {**result,'reason':'candidate_not_enabled'}
        if not routine(packet):return {**result,'reason':'complex_or_uncertain_case'}
        directory=Path(policy['benchmark_dir'])
        if not directory.is_absolute():raise ValueError('absolute_benchmark_required')
        report=assessor(directory);manifest=load_private(directory/'manifest.json')
        current=int(time.time()*1000) if now is None else now
        if (report['manifest_sha256']!=policy['manifest_sha256'] or report['promotion_eligible'] is not True
                or not 0<=current-manifest['created_at_ms']<=30*86400000
                or manifest['arms']['baseline']!={'model':baseline.split('@',1)[0],'thinking':result['thinking']}):
            return {**result,'reason':'review_measurement_or_provenance_gate'}
        candidate=manifest['arms']['candidate']
        if not re.fullmatch(r'openai/[A-Za-z0-9_.-]+',candidate['model']) or candidate['thinking'] not in ('low','medium','high'):
            raise ValueError('invalid_candidate')
        suffix='@'+baseline.split('@',1)[1] if '@' in baseline else ''
        return {'route':'reviewed_routine_candidate','model':candidate['model']+suffix,'thinking':candidate['thinking'],'reason':'reviewed_measured_policy'}
    except Exception:return {**result,'reason':'invalid_or_unavailable_policy'}


def apply_selection(config,route):
    c=copy.deepcopy(config)
    if route['route']=='baseline':return c
    main=c['agents']['entries']['main'];main['model']=route['model']
    main.setdefault('models',{}).setdefault(route['model'].split('@',1)[0],{})['agentRuntime']={'id':'openclaw'}
    c['agents']['defaults']['thinkingDefault']=route['thinking']
    return c
