"""A weekly report is deliverable only after its structured review is persisted."""
import copy
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest import mock
import test_report_runner as fixtures
import test_context_packet as contexts

r=fixtures.r


class ManagedDelivery(unittest.TestCase):
    setUp=fixtures.ReportRunner.setUp
    run_report=fixtures.ReportRunner.run_report

    def managed(self,notify=True,valid=True):
        self.p['coaching_profile']='/private/coaching.json';self.packet['task']='weekly'
        self.receipt={'review_id':'review-one','revision_id':'revision-one','capture_id':'a'*64,'notify':notify}
        self.gen.return_value=('ready','Synthetic reviewed report',{'managed_review':self.receipt})
        runtime=mock.Mock();runtime.verify_receipt.return_value=valid
        bridge=SimpleNamespace(load_profile=lambda p:{},CoachingRuntime=lambda p:runtime)
        patch=mock.patch.object(r,'sibling',return_value=bridge);patch.start();self.addCleanup(patch.stop)
        return runtime

    def test_saved_review_receipt_is_verified_before_delivery(self):
        runtime=self.managed();self.assertEqual(self.run_report()['status'],'delivered')
        runtime.verify_receipt.assert_called_once_with(self.receipt);self.send.assert_called_once()

    def test_unchanged_maintain_review_stays_quiet_and_does_not_regenerate(self):
        self.managed(notify=False)
        self.assertEqual(self.run_report()['status'],'unchanged');self.assertEqual(self.run_report()['status'],'unchanged')
        self.send.assert_not_called();self.assertEqual(self.gen.call_count,1)
        self.assertEqual(self.runner.db.execute('SELECT state FROM reports').fetchone()[0],'quiet')

    def test_missing_receipt_blocks_delivery(self):
        self.managed();self.gen.return_value=('ready','Unsaved report',{})
        self.assertEqual(self.run_report()['status'],'weekly_review_receipt_missing');self.send.assert_not_called()

    def test_changed_plan_or_health_blocks_cached_review_delivery(self):
        self.managed(valid=False)
        self.assertEqual(self.run_report()['status'],'review_evidence_changed_before_delivery');self.send.assert_not_called()

    def test_onboarding_message_never_claims_a_saved_review(self):
        self.managed();self.gen.return_value=('ready','Describe current goals first',{'managed_review_state':'onboarding_required'})
        self.assertEqual(self.run_report()['status'],'delivered');self.send.assert_called_once()


class ManagedGeneration(unittest.TestCase):
    def setUp(self):
        self.fixture=contexts.ContextPacket();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.root=self.fixture.root;self.state=self.root/'report-state';self.state.mkdir(mode=0o700)
        (self.root/'WEEKLY_REPORT_TEMPLATE.md').write_text('Synthetic weekly template')
        self.profile={'state_dir':str(self.state),'context_profile':str(self.root/'profile.json'),'coaching_profile':'/private/coaching.json','openclaw_bin':'/private/openclaw'}
        self.packet={'task':'weekly','local_date':'2026-10-22'}
        self.runtime=mock.Mock();self.runtime.prepare_scheduled.return_value={'state':'prepared','capture_id':'a'*64,'snapshot':{},'plan':{}}
        self.runtime.save.return_value={'success':True,'review_id':'one','notify':True}
        original=r.sibling
        def sibling(name):
            if name=='coaching_runtime':return SimpleNamespace(load_profile=lambda p:{},CoachingRuntime=lambda p:self.runtime)
            return original(name)
        patch=mock.patch.object(r,'sibling',side_effect=sibling);patch.start();self.addCleanup(patch.stop)
        self.config={'plugins':{'entries':{'section11-context':{'config':{}}}},'agents':{'defaults':{},'entries':{}}}
        self.artifact={'report':'Synthetic report','review':{'observations':[],'decisions':[],'candidate_plan':None}}

    def generate(self,artifact=None):
        body={'ok':True,'status':'ok','codeModeEngaged':False,'final':json.dumps(artifact if artifact is not None else self.artifact)}
        with mock.patch.object(r,'run_bounded',return_value={'returncode':0,'stdout':json.dumps(body)}) as run:
            result=r.generate(self.profile,self.config,self.packet,[])
        return result,run

    def test_native_output_is_parsed_saved_then_only_report_text_returns(self):
        (status,text,metrics),_=self.generate()
        self.assertEqual((status,text),('ready','Synthetic report'))
        self.runtime.save.assert_called_once_with('a'*64,self.artifact['review'],trigger='scheduled')
        self.assertEqual(metrics['managed_review']['review_id'],'one')

    def test_invalid_or_rejected_reviews_never_become_deliverable(self):
        (status,text,_),_=self.generate({'report':'Unsaved report'})
        self.assertEqual(status,'failed');self.assertIsNone(text);self.runtime.save.assert_not_called()
        self.runtime.save.side_effect=ValueError('private-canary')
        (status,text,metrics),_=self.generate();self.assertEqual(status,'failed');self.assertIsNone(text)
        self.assertNotIn('private-canary',json.dumps(metrics))

    def test_prepare_failure_has_no_model_call_and_is_a_known_failure(self):
        self.runtime.prepare_scheduled.side_effect=TimeoutError('private-canary')
        (status,text,metrics),run=self.generate()
        self.assertEqual(status,'failed');self.assertIsNone(text);run.assert_not_called();self.assertEqual(metrics['model_calls'],0)

    def test_structured_bound_does_not_relax_normal_report_or_tool_limits(self):
        body={'ok':True,'status':'ok','codeModeEngaged':False,'final':'x'*5000}
        result={'returncode':0,'stdout':json.dumps(body)}
        self.assertEqual(r.classify_generation(result,1)[0],'failed')
        self.assertEqual(r.classify_generation(result,1,True)[0],'ready')
        body['toolSummary']={'calls':1,'tools':['section11_coaching']};result['stdout']=json.dumps(body)
        self.assertEqual(r.classify_generation(result,1,True)[0],'failed')
