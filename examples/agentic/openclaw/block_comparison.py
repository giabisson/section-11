"""Descriptive comparison of explicit, verified constant-target plan windows.

No physiological model, similarity tolerance, HR normalization, session-name
matching or medical inference. Numeric deltas are current minus reference.
"""
import json
import math
import re

ID = re.compile(r'i[1-9][0-9]{0,17}')
MIN_COVERAGE = 95  # Engineering data-quality gate, not a physiological threshold.
MAX_RESULT = 7800


def number(v):
    return type(v) in (int,float) and math.isfinite(v)


def eligible_step(packet, index):
    analysis=packet.get('analysis',{})
    if analysis.get('method')!='paired_plan_windows' or packet.get('paired_event_id') is None:
        return None,'verified_paired_windows_required'
    if any(x in analysis.get('issues',[]) for x in ('pairing_conflict','ambiguous_pairing','paired_event_unavailable')):
        return None,'verified_pairing_required'
    steps=analysis.get('steps',[])
    if type(index) is not int or not 0<=index<len(steps):return None,'invalid_step_selection'
    s=steps[index]
    if not number(s.get('target_w')) or s['target_w']<=0 or 'repeat' in s:
        return None,'constant_target_continuous_step_required'
    a=s.get('actual')
    if not isinstance(a,dict):return None,'measured_window_required'
    if not all(number(a.get(k)) for k in ('start_s','end_s','mean_power_w','power_coverage_pct')):
        return None,'measured_power_required'
    if a['end_s']<=a['start_s'] or a['mean_power_w']<=0 or not MIN_COVERAGE<=a['power_coverage_pct']<=100:
        return None,'insufficient_power_coverage_or_window'
    return s,None


def environment(activity):
    if activity.get('type')=='VirtualRide' or activity.get('trainer') is True:return 'indoor'
    if activity.get('trainer') is False:return 'outdoor'
    return None


def side(packet, step):
    a=step['actual'];act=packet['activity'];p=packet.get('provenance',{})
    return {'activity_id':act['id'],'date':act.get('start_date_local'),
            'step_index':step['step_index'],'planned_power_w':step['target_w'],
            'planned_duration_s':step.get('planned_duration_s'),
            'observed_window_s':a['end_s']-a['start_s'],
            'actual':a,'target_window_agreement':step.get('match'),
            'observed_window_fraction':step.get('observed_window_fraction'),
            'context':{'type':act.get('type'),'environment':environment(act),
                'recording_device':act.get('device_name'),'ftp_setting_w':act.get('icu_ftp'),
                'average_temperature':act.get('average_temp')},
            'whole_session_status':packet['analysis']['status'],
            'whole_session_issues':packet['analysis'].get('issues',[]),
            'provenance':{k:p.get(k) for k in ('computed_at','revalidated_at','streams_reused','source_fingerprint','analyzer_sha256')}}


def compare_packets(current, reference, step_index=None, reference_step_index=None):
    for label,p in [('current',current),('reference',reference)]:
        if p.get('status')!='available':
            return {'status':'unavailable','error_code':'activity_analysis_unavailable','side':label,
                    'source_error':p.get('error_code'),'api_writes':0}
    version=current.get('analysis',{}).get('version')
    if type(version) is not int or version<=0 or version!=reference.get('analysis',{}).get('version'):
        return {'status':'unavailable','error_code':'analysis_versions_differ','api_writes':0}
    if current.get('provenance',{}).get('analyzer_sha256')!=reference.get('provenance',{}).get('analyzer_sha256'):
        return {'status':'unavailable','error_code':'analysis_methods_differ','api_writes':0}
    if step_index is None or reference_step_index is None:
        choices={}
        for label,p in [('current',current),('reference',reference)]:
            choices[label]=[{'step_index':i,'planned_power_w':s['target_w'],
                            'planned_duration_s':s.get('planned_duration_s'),
                            'mean_power_w':s['actual']['mean_power_w']}
                           for i in range(len(p['analysis'].get('steps',[])))
                           for s,error in [eligible_step(p,i)] if error is None]
            if not choices[label]:
                return {'status':'unavailable','error_code':'no_eligible_constant_target_windows','side':label,'api_writes':0}
        return {'status':'selection_required','candidates':choices,'api_writes':0,
                'scope':'Select an explicit step_index and reference_step_index from observed detail. Candidates are eligible constant-target windows, not inferred main-set roles or similarity rankings.'}
    selected=[]
    for label,p,i in [('current',current,step_index),('reference',reference,reference_step_index)]:
        s,error=eligible_step(p,i)
        if error:return {'status':'unavailable','error_code':error,'side':label,'api_writes':0}
        selected.append(side(p,s))
    c,r=selected;differences=[];missing=[]
    def delta(a,b):return round(a-b,2) if number(a) and number(b) else None
    values={'observed_power_w':delta(c['actual']['mean_power_w'],r['actual']['mean_power_w']),
            'observed_window_s':delta(c['observed_window_s'],r['observed_window_s']),
            'planned_power_w':delta(c['planned_power_w'],r['planned_power_w']),
            'planned_duration_s':delta(c['planned_duration_s'],r['planned_duration_s']),
            'window_start_s':delta(c['actual']['start_s'],r['actual']['start_s'])}
    for field in ('observed_power_w','observed_window_s','planned_power_w','planned_duration_s','window_start_s'):
        if values[field] not in (None,0):differences.append(field+'_differs')
    for field in ('environment','type','recording_device','ftp_setting_w','average_temperature'):
        a,b=c['context'][field],r['context'][field]
        if a is None or b is None:missing.append(field)
        elif a!=b:differences.append(field+'_differs')
    for label,s in [('current',c),('reference',r)]:
        if s['target_window_agreement'] is not True:differences.append(label+'_target_window_agreement_not_established')
        f=s['observed_window_fraction']
        if number(f) and f<1:differences.append(label+'_window_clipped')
    for metric,coverage in [('mean_hr_bpm','hr_coverage_pct'),('mean_cadence_rpm','cadence_coverage_pct')]:
        good=all(number(s['actual'].get(metric)) and s['actual'][metric]>0
                 and number(s['actual'].get(coverage)) and MIN_COVERAGE<=s['actual'][coverage]<=100 for s in (c,r))
        values[metric]=delta(c['actual'].get(metric),r['actual'].get(metric)) if good else None
        if not good:missing.append(metric+'_or_coverage')
    # Equality means only equality of stored rounded means and measured duration.
    # It never establishes equal power traces, hardware, conditions or response.
    same=values['observed_power_w']==0 and values['observed_window_s']==0
    return {'status':'available','comparison_kind':'descriptive_only',
            'workload_match':'same_at_reported_precision' if same else 'different',
            'current':c,'reference':r,'delta_current_minus_reference':values,
            'differences':differences,'unknown_context':missing,
            'data_quality_gate':{'minimum_power_hr_coverage_pct':MIN_COVERAGE,'basis':'engineering safeguard, not a physiological threshold'},
            'interpretation_limits':[
                'This is not an exact controlled comparison, even when workload_match is same_at_reported_precision.',
                'HR delta is observed at the stated workloads; never label it HR change at a common wattage when observed power differs.',
                'Do not normalize HR to another wattage, substitute whole-session HR, or infer fitness change, surgery effects or medical clearance.',
                'Unknown effort, symptoms, cooling, hydration, medication and sensor/calibration context remain unverified; optional HRV is not required.',
                'A shortened cooldown/whole-session warning is separate from the selected window; target-window agreement is not formal completion or positive tolerability.'
            ],'api_writes':0}


def compare(config, activity_id, reference_activity_id, analyze, step_index=None, reference_step_index=None):
    if (not isinstance(activity_id,str) or not ID.fullmatch(activity_id)
            or not isinstance(reference_activity_id,str) or not ID.fullmatch(reference_activity_id)
            or activity_id==reference_activity_id):
        return {'status':'unavailable','error_code':'two_distinct_valid_activity_ids_required','api_writes':0}
    current=analyze(config,activity_id)
    if current.get('status')!='available':return compare_packets(current,{},step_index,reference_step_index)
    reference=analyze(config,reference_activity_id)
    result=compare_packets(current,reference,step_index,reference_step_index)
    result['retrieval']={'api_gets':current.get('provenance',{}).get('api_gets',current.get('api_gets',0))+reference.get('provenance',{}).get('api_gets',reference.get('api_gets',0)),
                         'maximum_api_gets':8,'model_calls':0}
    if len(json.dumps(result,separators=(',',':'),allow_nan=False).encode())>MAX_RESULT:
        return {'status':'unavailable','error_code':'comparison_result_size_limit','api_writes':0}
    return result
