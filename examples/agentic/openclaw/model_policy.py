"""Conservative report routing. Unreviewed experiments never select a model."""
import copy
from pathlib import Path
import re
import time


def fixed_sol_policy(config):
    """Recognize the explicit operator allowlist independent of order/scope."""
    agents=config['agents'];owners=[agents['defaults'],agents['entries']['main']]
    allowed={'openai/gpt-6.1-sol','openai/gpt-6-luna'}
    return any(set(owner.get('modelPolicy',{}).get('allow',[]))==allowed for owner in owners)


def effective_thinking(config):
    agents=config['agents']
    return agents['entries']['main'].get('thinkingDefault',agents['defaults'].get('thinkingDefault','medium'))


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
    result={'route':'baseline','model':baseline,'thinking':effective_thinking(config)}
    if fixed_sol_policy(config):
        if baseline.split('@',1)[0]!='openai/gpt-6.1-sol' or result['thinking']!='medium':raise ValueError('primary_model_policy_violation')
        return {**result,'reason':'operator_fixed_sol_medium_policy'}
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
    if fixed_sol_policy(config) and (route['model'].split('@',1)[0]!='openai/gpt-6.1-sol' or route['model']!=config['agents']['entries']['main']['model'] or route['thinking']!='medium' or effective_thinking(config)!='medium'):
        raise ValueError('operator_model_policy_forbids_route')
    c=copy.deepcopy(config)
    if route['route']=='baseline':return c
    main=c['agents']['entries']['main'];main['model']=route['model'];main['thinkingDefault']=route['thinking']
    main.setdefault('models',{}).setdefault(route['model'].split('@',1)[0],{})['agentRuntime']={'id':'openclaw'}
    c['agents']['defaults']['thinkingDefault']=route['thinking']
    return c
