"""Durable intake recovery before a plan; synthetic facts only, no service calls."""
import copy
from datetime import datetime,timedelta,timezone
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from _harness import REPO_ROOT,load_module_by_path
import test_coaching_runtime as fixtures

PATH=REPO_ROOT/'examples/agentic/openclaw/athlete_intake.py'
i=load_module_by_path('s11_intake_tests',PATH)


def entry(key,kind,text,**changes):
    return {'key':key,'kind':kind,'text':text,'observed_on':'2026-10-29','source':'Synthetic athlete message; explicit source, not a medical assessment',
            'valid_from':None,'valid_until':None,'review_on':'2026-11-20' if kind in {'goal','availability','recovery_constraint','follow_up'} else None,**changes}


def payload():
    return {'request_id':'synthetic-intake','parent_revision':None,'entries':[
        entry('goal','goal','Enjoy a tolerable return to cycling; no performance deadline'),
        entry('time','availability','Two short weekday sessions and a flexible weekend'),
        entry('bike','equipment','Synthetic indoor ERG trainer'),entry('history','experience','Synthetic new cyclist'),
        entry('recovery','recovery_constraint','Reported conditional clearance only; recheck pain and response before training',review_on='2026-10-30'),
        entry('today','health_observation','Feels weak on the statement date',valid_until='2026-10-29')],
        'open_questions':['Confirm current symptoms before the next prescription']}


class IntakeStore(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.root.chmod(0o700);self.db=self.root/'athlete_intake.sqlite3'

    def test_atomic_save_idempotency_and_missing_parent_or_account_never_overwrite(self):
        p=payload();saved=i.save(self.db,'i123',p,'2026-10-29');self.assertFalse(saved['unchanged'])
        self.assertTrue(i.save(self.db,'i123',p,'2026-10-30')['unchanged'])
        for actor,change in [('i123',{'request_id':'new'}),('i456',{'request_id':'other','parent_revision':saved['revision_id']}),('i123',{'open_questions':[]})]:
            with self.subTest(change=change),self.assertRaises(ValueError):i.save(self.db,actor,{**p,**change},'2026-10-29')
        self.assertEqual(i.read(self.db,'i123','2026-10-30')['revision_id'],saved['revision_id'])
        with sqlite3.connect(self.db) as db:self.assertEqual(db.execute('SELECT count(*) FROM intake_revisions').fetchone()[0],1)
        with self.assertRaises(ValueError):i.read(self.db,'i456','2026-10-30')

    def test_revision_history_retains_old_facts_and_explicit_replacement_has_readback(self):
        p=payload();old=i.save(self.db,'i123',p,'2026-10-29');p['request_id']='revised';p['parent_revision']=old['revision_id'];p['entries'][1]['text']='Reduced availability from explicit synthetic statement'
        new=i.save(self.db,'i123',p,'2026-10-30');self.assertNotEqual(new['revision_id'],old['revision_id'])
        self.assertEqual(i.read(self.db,'i123','2026-10-30')['entries'][1]['text'],p['entries'][1]['text'])
        with sqlite3.connect(self.db) as db:self.assertEqual(db.execute('SELECT count(*) FROM intake_revisions').fetchone()[0],2)

    def test_next_day_recovers_goals_without_reusing_old_health_as_clearance(self):
        i.save(self.db,'i123',payload(),'2026-10-29');view=i.read(self.db,'i123','2026-10-30')
        self.assertEqual(view['missing_core_categories'],[])
        self.assertEqual(next(x for x in view['entries'] if x['key']=='goal')['temporal_status'],'current')
        self.assertEqual(next(x for x in view['entries'] if x['key']=='today')['temporal_status'],'historical')
        self.assertTrue(next(x for x in view['entries'] if x['key']=='recovery')['review_due'])
        self.assertTrue(all(x['current_health_clearance'] is False for x in view['entries']))

    def test_rejects_undated_health_constraints_unknown_fields_duplicates_and_future_sources(self):
        variants=[]
        for key,value in [('valid_until',None),('observed_on','2026-11-01')]:
            p=payload();p['entries'][-1][key]=value;variants.append(p)
        for kind in ['goal','availability','recovery_constraint','follow_up']:
            p=payload();p['entries']=[entry('x',kind,'Synthetic',review_on=None)];variants.append(p)
        p=payload();p['entries'][0]['snapshot']={};variants.append(p)
        p=payload();p['entries'].append(copy.deepcopy(p['entries'][0]));variants.append(p)
        p=payload();p['entries'][0]['text']='x'*2001;variants.append(p)
        for p in variants:
            with self.subTest(p=p),self.assertRaises(ValueError):i.save(self.db,'i123',p,'2026-10-29')
        self.assertFalse(self.db.exists())

    def test_private_permissions_and_symlinks_are_rejected(self):
        i.save(self.db,'i123',payload(),'2026-10-29');self.assertEqual(self.db.stat().st_mode&0o777,0o600)
        self.db.chmod(0o644)
        with self.assertRaises(ValueError):i.read(self.db,'i123','2026-10-30')
        self.db.chmod(0o600);alias=self.root/'alias';alias.symlink_to(self.db)
        with self.assertRaises(ValueError):i.read(alias,'i123','2026-10-30')
        self.root.chmod(0o755)
        with self.assertRaises(ValueError):i.read(self.db,'i123','2026-10-30')


class IntakeWorkflow(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.CoachingRuntime();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups);self.f=self.fixture

    def test_save_before_plan_and_fresh_next_day_state_and_context_recover_same_revision(self):
        f=self.f;self.assertEqual(f.runtime.state_view()['onboarding_stage'],'intake_required')
        saved=f.runtime.save_intake(payload());self.assertEqual(saved['calendar_writes'],0);self.assertFalse((f.root/'store').exists())
        intake=f.root/'bridge/athlete_intake.sqlite3'
        f.runtime.cp.update(intake_store=str(intake),intake_athlete_id='i123456')
        f.write('context.json',f.runtime.cp)
        code='''import importlib.util,sys,json
from datetime import datetime,timezone
s=importlib.util.spec_from_file_location('fresh_bridge',sys.argv[1]);m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)
r=m.CoachingRuntime(m.load_profile(sys.argv[2]),clock=lambda:datetime(2026,10,30,12,tzinfo=timezone.utc))
print(json.dumps({'state':r.state_view(),'intake':r.context.intake_context(r.cp,r.now()),'feedback':r.feedback(),'packet':json.loads(r.context.encode(r.context.build(r.cp,'plan',now=r.now())))}))
'''
        f.write('coaching.json',f.p)
        proc=subprocess.run([sys.executable,'-c',code,str(REPO_ROOT/'examples/agentic/openclaw/coaching_runtime.py'),str(f.root/'coaching.json')],capture_output=True,text=True,timeout=15)
        self.assertEqual(proc.returncode,0,proc.stderr);result=json.loads(proc.stdout)
        self.assertEqual(result['state']['onboarding_stage'],'intake_saved_plan_pending');self.assertIsNone(result['state']['plan']);self.assertIsNone(result['feedback'])
        self.assertEqual(result['intake']['revision_id'],saved['revision_id']);self.assertEqual(len(result['intake']['entries']),6)
        self.assertEqual(result['state']['intake']['revision_id'],saved['revision_id'])
        self.assertTrue(result['packet']['packet_complete']);self.assertEqual(result['packet']['athlete_intake']['revision_id'],saved['revision_id'])

    def test_large_history_is_explicitly_deferred_without_losing_health_or_intake(self):
        f=self.f;f.runtime.save_intake(payload());cp={**f.runtime.cp,'intake_store':str(f.root/'bridge/athlete_intake.sqlite3'),'intake_athlete_id':'i123456'}
        f.latest['health_context']={'clarification_required':True,'reason':'Synthetic safety canary'};f.write('latest.json',f.latest)
        history={'daily_90d':[],'weekly_180d':[{'week_start':'2026-10-26','note':'x'*43000}]};f.write('history.json',history)
        ctx=f.runtime.context;p=ctx.build(cp,'plan',now=f.runtime.now());encoded=ctx.encode(p)
        self.assertLessEqual(len(encoded.encode()),49152)
        self.assertEqual(p['athlete_intake']['revision_id'],f.runtime.intake_view()['revision_id'])
        self.assertEqual(p['snapshot']['health_context'],f.latest['health_context'])
        self.assertEqual(p['history']['status'],'deferred');self.assertNotIn('rows',p['history']);self.assertNotIn('weekly_rows',p['history'])
        self.assertFalse(p['history']['coverage_complete']);self.assertEqual(p['history']['deferred_row_counts']['weekly_rows'],1)
        from datetime import date
        q=p['history']['required_retrieval'];read=ctx.history_window(cp,date.fromisoformat(q['start']),date.fromisoformat(q['end']))
        self.assertEqual(read['weekly_rows'][0]['row'],history['weekly_180d'][0]);ctx.encode(read)
        history['weekly_180d'][0]['note']='y'*43000;f.write('history.json',history)
        other=ctx.build(cp,'plan',now=f.runtime.now());self.assertNotEqual(p['history']['deferred_rows_sha256'],other['history']['deferred_rows_sha256'])

    def test_context_pair_and_runtime_store_binding_fail_closed(self):
        f=self.f
        for extra in [{'intake_store':str(f.root/'bridge/athlete_intake.sqlite3')},
                      {'intake_athlete_id':'i123456'},
                      {'intake_store':str(f.root/'wrong/athlete_intake.sqlite3'),'intake_athlete_id':'i123456'},
                      {'intake_store':str(f.root/'bridge/athlete_intake.sqlite3'),'intake_athlete_id':'i999'}]:
            f.write('context.json',{**f.runtime.cp,**extra})
            with self.subTest(extra=extra),self.assertRaises(ValueError):fixtures.b.CoachingRuntime(f.p,clock=f.runtime.clock)

    def test_changed_intake_invalidates_prepared_review_and_cached_receipt(self):
        f=self.f;f.propose();f.runtime.save_intake(payload());capture=f.prepare();saved=f.runtime.save(capture['capture_id'],f.draft());self.assertTrue(f.runtime.verify_receipt(saved))
        p=payload();p.update(request_id='changed',parent_revision=f.runtime.intake_view()['revision_id']);p['entries'][1]['text']='Changed explicit synthetic availability'
        f.runtime.save_intake(p)
        self.assertFalse(f.runtime.verify_receipt(saved))
        with self.assertRaisesRegex(ValueError,'review_evidence_changed'):f.runtime.save(capture['capture_id'],f.draft())
