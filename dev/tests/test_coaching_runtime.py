"""Private coaching bridge: real store/review/reader, synthetic source evidence."""
import copy
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
from _harness import REPO_ROOT,RefuseEverything,load_module_by_path

b=load_module_by_path('s11_coaching_bridge_tests',REPO_ROOT/'examples/agentic/openclaw/coaching_runtime.py')
NOW=datetime(2026,10,29,12,tzinfo=timezone.utc)


class CoachingRuntime(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.now=NOW
        self.write('.sync_config.json',{'athlete_id':'i123456','intervals_key':'synthetic'})
        self.latest={'metadata':{'last_updated':NOW.isoformat()},'readiness_decision':{'priority':3,'recommendation':'go'},'health_context':{'clarification_required':False},'current_status':{}}
        self.write('latest.json',self.latest)
        context={'schema_version':1,'data_dir':str(self.root),'protocol':str(self.root/'p.md'),'workout_reference':str(self.root/'w.md'),'reports_dir':str(self.root),'dossier':str(self.root/'d.md'),'dossier_sections':{t:[] for t in ['morning','weekly','workout','plan','post_workout']},'timezone':'Europe/Zurich','source_timezone':'Europe/Zurich','review_store':str(self.root/'store/coaching_plan.sqlite3')}
        self.write('context.json',context)
        self.p={'schema_version':1,'install_root':str(REPO_ROOT),'data_dir':str(self.root),'store_dir':str(self.root/'store'),'state_dir':str(self.root/'bridge'),'context_profile':str(self.root/'context.json'),'timezone':'Europe/Zurich','scheduled_reviews_enabled':True}
        self.reader=mock.Mock(return_value=[])
        self.runtime=b.CoachingRuntime(self.p,clock=lambda:self.now,reader=self.reader)
        patch=mock.patch.object(self.runtime.api,'today',return_value='2026-10-29');patch.start();self.addCleanup(patch.stop)
        self.plan=json.loads((REPO_ROOT/'examples/json-examples/coaching_plan.example.json').read_text());self.plan['sessions']=[]

    def write(self,name,value):
        p=self.root/name;p.write_text(json.dumps(value));p.chmod(0o600)

    def propose(self):
        return self.runtime.propose({'plan':copy.deepcopy(self.plan),'current_athlete_context':{'date':'2026-10-29','source':'Synthetic athlete statement','goals_and_availability':'Synthetic sustainable endurance; four available hours, flexible days'}})

    def prepare(self):return self.runtime.prepare('2026-10-26','2026-10-29')

    def draft(self):return {'observations':[],'decisions':[{'action':'maintain','session_ids':[],'observation_ids':[],'reason':'No changed training or dose is prescribed','next_observation':'Ask current availability and response before adding exact sessions'}],'candidate_plan':None}

    def test_no_plan_requires_onboarding_without_creating_a_fake_plan(self):
        self.assertEqual(self.runtime.state_view()['state'],'onboarding_required')
        self.assertEqual(self.prepare()['state'],'onboarding_required');self.reader.assert_not_called()
        self.assertFalse((self.root/'store').exists())
        empty=self.runtime.store(create=True);empty.close()
        self.assertEqual(self.runtime.state_view()['athlete_id'],'i123456')
        self.assertEqual(self.runtime.state_view()['state'],'onboarding_required')

    def test_propose_creates_actual_store_and_binds_current_context_without_publication(self):
        result=self.propose();self.assertEqual(result['calendar_writes'],0)
        shown=self.runtime.state_view();self.assertEqual(shown['state'],'active')
        self.assertIn('caller-attested',shown['plan']['revision']['evidence'][-1]['source'])
        self.assertEqual(shown['publication']['state'],'proposed')

    def test_stale_context_other_account_or_data_cannot_seed_onboarding(self):
        value={'plan':copy.deepcopy(self.plan),'current_athlete_context':{'date':'2026-10-28','source':'old','goals_and_availability':'old'}}
        with self.assertRaises(ValueError):self.runtime.propose(value)
        value['current_athlete_context']['date']='2026-10-29';value['plan']['athlete_id']='i999'
        with self.assertRaises(ValueError):self.runtime.propose(value)
        self.latest['metadata']['last_updated']='2026-10-01T10:00:00+00:00';self.write('latest.json',self.latest)
        with self.assertRaises(ValueError):self.propose()

    def test_full_loop_save_reader_receipt_and_repeat_silence(self):
        self.propose();capture=self.prepare();draft=self.draft()
        first=self.runtime.save(capture['capture_id'],draft,trigger='scheduled')
        self.assertTrue(first['success']);self.assertFalse(first['notify']);self.assertTrue(self.runtime.verify_receipt(first))
        second=self.runtime.save(capture['capture_id'],draft,trigger='scheduled')
        self.assertTrue(second['unchanged']);self.assertEqual(first['review_id'],second['review_id'])
        rows=self.runtime.context.review_history(self.runtime.cp)['rows'];self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['objective'],self.plan['block']['objective']);self.assertEqual(rows[0]['decisions'],draft['decisions'])
        self.assertEqual(rows[0]['period'],{'start':'2026-10-26','end':'2026-10-29'})
        store=self.runtime.store()
        try:self.assertEqual(len([e for e in store._events() if e['kind']=='reviewed']),1)
        finally:store.close()

    def test_model_cannot_replace_snapshot_readiness_or_feedback(self):
        self.propose();capture=self.prepare()
        for key in ['snapshot','current_feedback','trigger','parent_revision']:
            value=self.draft();value[key]={}
            with self.assertRaises(ValueError):self.runtime.save(capture['capture_id'],value)

    def test_changed_health_or_feedback_and_expired_capture_refuse_saves(self):
        self.propose();capture=self.prepare();self.latest['health_context']['clarification_required']=True;self.write('latest.json',self.latest)
        with self.assertRaises(ValueError):self.runtime.save(capture['capture_id'],self.draft())
        capture=self.prepare();self.now+=timedelta(minutes=16)
        with self.assertRaises(ValueError):self.runtime.save(capture['capture_id'],self.draft())

    def test_optional_wearables_and_current_feedback_expiry(self):
        self.propose();self.runtime.record_feedback({'date':'2026-10-29','state':'normal','note':'Synthetic athlete reports rested without overnight measurement','health_clarification':None})
        prepared=self.prepare();self.assertEqual(prepared['current_feedback']['state'],'normal')
        self.assertEqual(prepared['snapshot']['readiness']['recommendation'],'go')
        self.now+=timedelta(days=1);self.assertIsNone(self.runtime.feedback())

    def test_feedback_cannot_erase_a_producer_stop(self):
        self.propose();self.latest['readiness_decision']={'priority':0,'recommendation':'skip'};self.write('latest.json',self.latest)
        self.runtime.record_feedback({'date':'2026-10-29','state':'rested','note':'Synthetic positive feedback','health_clarification':{'compatible':True,'reason':'Caller report'}})
        prepared=self.prepare();self.assertEqual(prepared['snapshot']['readiness']['priority'],0)
        self.assertEqual(prepared['snapshot']['readiness']['recommendation'],'skip')
        draft=self.draft();draft['decisions'][0]['action']='progress'
        with self.assertRaises(ValueError):self.runtime.save(prepared['capture_id'],draft)

    def test_schedule_opt_in_path_limits_duplicates_and_no_extra_reads_on_save(self):
        self.propose();capture=self.prepare();self.assertEqual(self.reader.call_count,2)
        self.runtime.p['scheduled_reviews_enabled']=False
        with self.assertRaises(ValueError):self.runtime.save(capture['capture_id'],self.draft(),trigger='scheduled')
        self.runtime.save(capture['capture_id'],self.draft());self.assertEqual(self.reader.call_count,2)
        with self.assertRaises(ValueError):self.runtime.prepare('2026-01-01','2026-10-29')
        with self.assertRaises(ValueError):self.runtime.save('../bad',self.draft())

    def test_saved_receipt_invalidates_when_plan_or_safety_changes(self):
        self.propose();capture=self.prepare();receipt=self.runtime.save(capture['capture_id'],self.draft())
        self.assertTrue(self.runtime.verify_receipt(receipt))
        self.latest['health_context']['clarification_required']=True;self.write('latest.json',self.latest)
        self.assertFalse(self.runtime.verify_receipt(receipt))

    def test_prepare_provider_failure_cannot_create_a_review(self):
        self.propose();self.reader.side_effect=RuntimeError('private-provider-canary')
        with self.assertRaises(RuntimeError):self.prepare()
        self.assertEqual(self.runtime.context.review_history(self.runtime.cp)['rows'],[])

    def test_duplicate_source_ids_are_rejected(self):
        self.propose();self.reader.return_value=[{'id':'duplicate'},{'id':'duplicate'}]
        with self.assertRaises(ValueError):self.prepare()

    def test_scheduled_review_uses_block_window_when_due(self):
        self.plan['block']['review_date']='2026-10-29';self.propose()
        prepared=self.runtime.prepare_scheduled('2026-10-29')
        self.assertEqual(prepared['review_scope'],'block');self.assertEqual(prepared['period']['start'],'2026-10-26')

    def test_published_snapshot_response_revision_and_reader_close_the_actual_loop(self):
        import test_coaching_review as fixtures
        fx=fixtures.CoachingReview();fx.setUp();self.addCleanup(fx.doCleanups)
        source=fx.ready();fx.candidate(source,minutes=100)
        self.runtime.p['store_dir']=str(fx.folder)
        self.runtime.cp['review_store']=str(fx.folder/'coaching_plan.sqlite3')
        self.reader.side_effect=lambda endpoint,start,end:source['snapshot'][endpoint]
        self.runtime.record_feedback({k:source['current_feedback'][k] for k in ['date','state','note','health_clarification']})
        capture=self.runtime.prepare('2026-10-26','2026-10-28')
        writes=len(fx.remote.writes)
        with mock.patch.object(self.runtime.api.push_module(),'_requests',RefuseEverything()):
            receipt=self.runtime.save(capture['capture_id'],{k:source[k] for k in ['observations','decisions','candidate_plan']})
        self.assertTrue(receipt['revision_created']);self.assertEqual(len(fx.remote.writes),writes)
        review=self.runtime.context.review_history(self.runtime.cp)['rows'][0]
        self.assertEqual(review['observations'][0]['completion_evidence'],'paired_activity')
        self.assertEqual(review['observations'][0]['response'],'tolerated')
        self.assertEqual(review['decisions'][0]['action'],'progress')
        self.assertEqual(review['parent_revision'],source['parent_revision'])
        self.assertEqual(review['result_revision'],receipt['revision_id'])


if __name__=='__main__':unittest.main()
