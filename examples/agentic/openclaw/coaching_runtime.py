#!/usr/bin/env python3
"""Primary local plan/review bridge. Server-owned evidence; no calendar writes.

The coach supplies judgments, never its own readiness/API snapshot. Scheduled
reports use the same save function after validating their structured output.
Profiles, captured evidence, feedback and plan records remain private.
"""
import argparse
from datetime import date, datetime, timedelta, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
import time
from zoneinfo import ZoneInfo

MAX_INPUT = 2_000_000


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def module(path, name):
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec);sys.modules[name]=value;spec.loader.exec_module(value)
    return value


def private_json(path):
    path=Path(path);info=path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode&0o077 or info.st_size>MAX_INPUT:
        raise ValueError('private_bounded_file_required')
    return json.loads(path.read_text())


def write_json(path, value):
    path=Path(path);fd,name=tempfile.mkstemp(dir=path.parent,prefix='.'+path.name+'-');temporary=Path(name)
    try:
        with os.fdopen(fd,'w') as stream:
            stream.write(canonical(value)+'\n');stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,path)
    finally:
        if temporary.exists():temporary.unlink()


def load_profile(path):
    p=private_json(path)
    fields={'schema_version','install_root','data_dir','store_dir','state_dir','context_profile','timezone','scheduled_reviews_enabled'}
    if set(p)!=fields or p['schema_version']!=1 or type(p['scheduled_reviews_enabled']) is not bool:
        raise ValueError('invalid_coaching_profile')
    for key in fields-{'schema_version','timezone','scheduled_reviews_enabled'}:
        if not isinstance(p[key],str) or not Path(p[key]).is_absolute():raise ValueError('absolute_paths_required')
    ZoneInfo(p['timezone'])
    os.environ['TZ']=p['timezone'];time.tzset()
    return p


class CoachingRuntime:
    def __init__(self, profile, clock=None, reader=None):
        self.p=profile;self.clock=clock or (lambda:datetime.now(timezone.utc));self.reader=reader
        root=Path(profile['install_root'])
        self.api=module(root/'examples/agentic/coaching_plan.py','s11_coaching_runtime_plan')
        self.context=module(root/'examples/agentic/openclaw/context_packet.py','s11_coaching_runtime_context')
        self.history=module(root/'examples/training_history.py','s11_coaching_runtime_http')
        self.cp=self.context.load_profile(profile['context_profile'])
        if Path(self.cp['data_dir']).resolve()!=Path(profile['data_dir']).resolve():raise ValueError('source_profile_mismatch')
        self.config=private_json(Path(profile['data_dir'])/'.sync_config.json')
        self.athlete=str(self.config['athlete_id'])
        if not re.fullmatch(r'i?[0-9]+',self.athlete) or self.athlete in ('0','i0'):raise ValueError('explicit_account_required')
        self.state=Path(profile['state_dir'])
        if self.state.is_symlink() or self.state.resolve().is_relative_to(root.resolve()):raise ValueError('private_state_outside_source_required')
        self.state.mkdir(parents=True,exist_ok=True,mode=0o700)
        if self.state.stat().st_mode&0o077:raise ValueError('private_state_required')

    def now(self):
        value=self.clock()
        if value.tzinfo is None:raise ValueError('aware_clock_required')
        return value

    def today(self):
        return self.now().astimezone(ZoneInfo(self.p['timezone'])).date().isoformat()

    def store(self, create=False):
        return self.api.PlanStore(self.p['store_dir'],create=create)

    def state_view(self):
        if not (Path(self.p['store_dir'])/'coaching_plan.sqlite3').is_file():
            return {'success':True,'state':'onboarding_required','athlete_id':self.athlete,'plan':None,'instruction':'Ask for current goals, experience, recent training response, health and actual availability in Telegram before proposing a real plan. Old dossier dates and calendar publication are not current intent.','calendar_writes':0}
        store=self.store()
        try:
            if store.latest_id() is None:return {'success':True,'state':'onboarding_required','athlete_id':self.athlete,'plan':None,'calendar_writes':0}
            result=store.summary();result['state']='active';result['calendar_writes']=0
            if result['plan']['athlete_id']!=self.athlete:raise ValueError('plan_account_mismatch')
            return result
        finally:store.close()

    def latest(self):
        value,_=self.context.json_source(Path(self.p['data_dir'])/'latest.json',True)
        stamp=self.context.parse_stamp(value.get('metadata',{}).get('last_updated'),self.cp['source_timezone'])
        fresh=bool(stamp and -300<=(self.now()-stamp).total_seconds()<=86400 and stamp.astimezone(ZoneInfo(self.p['timezone'])).date().isoformat()==self.today())
        decision=value.get('readiness_decision') or {};health=value.get('health_context') or {}
        readiness={'date':stamp.astimezone(ZoneInfo(self.p['timezone'])).date().isoformat() if stamp else self.today(),
                   'recommendation':decision.get('recommendation','unknown'),'priority':decision.get('priority',3),
                   'health_clarification_required':health.get('clarification_required',True)}
        if not fresh:readiness['recommendation']='unknown';readiness['priority']=3
        def clean(v):
            if isinstance(v,dict):return {k:clean(x) for k,x in v.items() if k not in ('generated_at','calculation_timestamp','last_updated','evaluated_at')}
            if isinstance(v,list):return [clean(x) for x in v]
            return v
        safety=digest({'date':self.today(),'fresh':fresh,'readiness':clean(decision),'health':clean(health),'current_status':clean(value.get('current_status'))})
        return readiness,fresh,safety

    def feedback(self):
        try:value=private_json(self.state/'feedback.json')
        except FileNotFoundError:return None
        return value if value['date']==self.today() else None

    def record_feedback(self, value):
        if not isinstance(value,dict) or set(value)!={'date','state','note','health_clarification'} or value['date']!=self.today():raise ValueError('current_dated_feedback_required')
        if value['state'] not in ('rested','normal','fatigued','weak','symptoms','unknown'):raise ValueError('invalid_feedback_state')
        self.api.text(value['note'])
        health=value['health_clarification']
        if health is not None:
            self.api.obj(health,{'compatible','reason'})
            if type(health['compatible']) is not bool:raise ValueError('explicit_compatibility_required')
            self.api.text(health['reason'])
        saved={**value,'source':'Telegram athlete feedback, caller-attested; not independently authenticated'}
        write_json(self.state/'feedback.json',saved)
        return {'success':True,'recorded_date':value['date'],'state':value['state'],'scope':'Current-day report only; optional wearables are not required. Positive feedback never erases a producer health/readiness stop.','calendar_writes':0}

    def propose(self, payload):
        self.api.obj(payload,{'plan','current_athlete_context'})
        context=payload['current_athlete_context'];self.api.obj(context,{'date','source','goals_and_availability'})
        if context['date']!=self.today():raise ValueError('fresh_athlete_context_required')
        self.api.text(context['source']);self.api.text(context['goals_and_availability'])
        plan=payload['plan']
        if plan.get('athlete_id')!=self.athlete:raise ValueError('plan_account_mismatch')
        _,fresh,_=self.latest()
        if not fresh:raise ValueError('refresh_current_data_before_plan_proposal')
        plan=json.loads(canonical(plan))
        plan['revision']['evidence'].append({'source':'Current athlete goals/availability; caller-attested: '+context['source'],'as_of':context['date'],'summary':context['goals_and_availability']})
        store=self.store(create=True)
        try:return {**store.propose(plan),'calendar_writes':0,'publication':'not_requested'}
        finally:store.close()

    def prepare_scheduled(self, end):
        view=self.state_view()
        if view['state']=='onboarding_required':return view
        block=view['plan']['block'];right=date.fromisoformat(end)
        due=end>=block['review_date'] or end>=block['end_date']
        intended=min(right,date.fromisoformat(block['start_date'])) if due else right-timedelta(days=6)
        left=max(intended,right-timedelta(days=41))
        scope='block' if due else 'weekly'
        if left>intended:scope+='; partial last-42-day evidence, not a complete block assessment'
        return self.prepare(left.isoformat(),end,review_scope=scope,intended_start=intended.isoformat())

    def prepare(self, start, end, review_scope='manual', intended_start=None):
        left,right=date.fromisoformat(start),date.fromisoformat(end)
        if not left<=right<=date.fromisoformat(self.today()) or (right-left).days>=42:raise ValueError('review_window_must_be_past_1_to_42_days')
        view=self.state_view()
        if view['state']=='onboarding_required':return view
        readiness,fresh,safety=self.latest();feedback=self.feedback()
        rows={};coverage='partial'
        for endpoint in ('activities','events'):
            if self.reader:raw=self.reader(endpoint,start,end)
            else:raw=self.history.fetch(self.config,endpoint,start,end)
            if not isinstance(raw,list) or len(raw)>2000:raise ValueError('bounded_source_rows_required')
            if endpoint=='activities':
                records=[{k:r.get(k) for k in ('id','paired_event_id','start_date')} for r in raw]
            else:records=[{k:r.get(k) for k in ('id','paired_activity_id')} for r in raw]
            identities=[str(r['id']) for r in records]
            if len(identities)!=len(set(identities)):raise ValueError('duplicate_review_source_identity')
            rows[endpoint]=sorted(records,key=lambda r:str(r['id']))
        if not fresh:coverage='unavailable'
        snapshot={'athlete_id':self.athlete,'source':'Direct Intervals.icu GETs and current producer readiness; calendar coverage does not prove completion; scope='+review_scope+'; intended_start='+(intended_start or start),'as_of':self.today(),'coverage':coverage,**rows,'readiness':readiness}
        parent=view['revision_id']
        core={'parent_revision':parent,'period':{'start':start,'end':end},'snapshot':snapshot,'current_feedback':feedback,'safety':safety}
        capture=digest(core);path=self.state/('capture-'+capture+'.json')
        write_json(path,{**core,'captured_at':self.now().isoformat()})
        # Bound retained captures; no training record or journal is pruned here.
        for old in self.state.glob('capture-*.json'):
            saved=private_json(old)
            if (self.now()-datetime.fromisoformat(saved['captured_at'])).total_seconds()>86400:old.unlink()
        return {'success':True,'state':'prepared','capture_id':capture,'parent_revision':parent,'period':core['period'],'snapshot':snapshot,
                'review_scope':review_scope,'intended_start':intended_start or start,
                'current_feedback':feedback,'plan':view['plan'],'prescription_summaries':view['prescription_summaries'],
                'scope':'Source evidence is server-owned. Completion/goal/response remain distinct; unknown pairing or feedback cannot justify progression. Read exact prescriptions/execution details before judging attainment.','calendar_writes':0}

    def save(self, capture_id, draft, trigger='athlete'):
        if trigger not in ('athlete','scheduled') or trigger=='scheduled' and not self.p['scheduled_reviews_enabled']:raise ValueError('review_trigger_not_authorized')
        if not re.fullmatch(r'[a-f0-9]{64}',capture_id):raise ValueError('invalid_capture_identity')
        self.api.obj(draft,{'observations','decisions','candidate_plan'})
        capture=private_json(self.state/('capture-'+capture_id+'.json'))
        age=(self.now()-datetime.fromisoformat(capture['captured_at'])).total_seconds()
        if not 0<=age<=900:raise ValueError('review_capture_expired')
        _,_,safety=self.latest()
        if safety!=capture['safety'] or self.feedback()!=capture['current_feedback']:raise ValueError('review_evidence_changed_prepare_again')
        source={'schema_version':1,'review_id':'review-'+digest({k:v for k,v in capture.items() if k not in ('captured_at','safety') }|{'draft':draft})[:40],
                'parent_revision':capture['parent_revision'],'trigger':trigger,'schedule_opt_in':trigger=='scheduled',
                'assessed_date':self.today(),'period':capture['period'],'snapshot':capture['snapshot'],'current_feedback':capture['current_feedback'],**draft}
        store=self.store()
        try:
            result=store.review(source)
            return {**{k:result[k] for k in ('success','review_id','parent_revision','revision_id','revision_created','notify','calendar_writes')},
                    'unchanged':result.get('unchanged',False),'unresolved_questions':result['report']['unresolved_questions'],
                    'capture_id':capture_id,'scope':'Review and optional local revision saved. No calendar publication or message was sent.'}
        finally:store.close()

    def verify_receipt(self, receipt):
        """A cached report cannot outlive its review's plan/evidence binding."""
        if not isinstance(receipt,dict) or not re.fullmatch(r'[a-f0-9]{64}',receipt.get('capture_id','')):return False
        try:
            capture=private_json(self.state/('capture-'+receipt['capture_id']+'.json'))
            age=(self.now()-datetime.fromisoformat(capture['captured_at'])).total_seconds()
            if not 0<=age<=900 or self.latest()[2]!=capture['safety'] or self.feedback()!=capture['current_feedback']:return False
            store=self.store()
            try:
                return store.latest_id()==receipt.get('revision_id') and any(e['kind']=='reviewed' and e['body']['review_id']==receipt.get('review_id') and e['body']['result_revision']==receipt.get('revision_id') for e in store._events())
            finally:store.close()
        except (ValueError,OSError,KeyError):return False


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--profile',required=True,type=Path);args=parser.parse_args()
    try:
        raw=sys.stdin.buffer.read(MAX_INPUT+1)
        if len(raw)>MAX_INPUT:raise ValueError('input_size_limit')
        request=json.loads(raw);runtime=CoachingRuntime(load_profile(args.profile))
        if not isinstance(request,dict) or set(request)-{'operation','payload','start','end','capture_id','draft'}:raise ValueError('invalid_request')
        op=request['operation']
        allowed={'state':{'operation'},'feedback':{'operation','payload'},'propose':{'operation','payload'},'prepare':{'operation','start','end'},'save':{'operation','capture_id','draft'}}
        if op not in allowed or set(request)!=allowed[op]:raise ValueError('invalid_operation_fields')
        result=(runtime.state_view() if op=='state' else runtime.record_feedback(request['payload']) if op=='feedback' else runtime.propose(request['payload']) if op=='propose' else runtime.prepare(request['start'],request['end']) if op=='prepare' else runtime.save(request['capture_id'],request['draft']))
        text=canonical({**result,'packet_complete':True})
        if len(text.encode())>49152:raise ValueError('output_size_limit_use_narrower_review')
        print(text);return 0
    except Exception:
        # Provider/filesystem exceptions can contain credentials or athlete data.
        print('{"success":false,"error":"coaching_operation_failed_refresh_evidence_check_payload_or_private_configuration","packet_complete":false}');return 1


if __name__=='__main__':raise SystemExit(main())
