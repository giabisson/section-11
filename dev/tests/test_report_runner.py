"""Supervisor state machines with synthetic generation and Telegram receipts."""
import copy
import contextlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
from urllib.error import HTTPError
import io
from datetime import datetime,timezone
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from _harness import REPO_ROOT,load_module_by_path
r=load_module_by_path('s11_report_runner_tests',REPO_ROOT/'examples/agentic/openclaw/report_runner.py')


class ReportRunner(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.now=1792670400000
        self.p={'state_dir':str(Path(self.temp.name)/'state'),'target':'123456','bot_id':'777'}
        self.config={'channels':{'telegram':{'botToken':'synthetic-bot-token','allowFrom':['123456']}}}
        self.packet={'task':'morning','local_date':'2026-10-22','built_at':'volatile','sources':{'latest':{'sha256':'volatile'}},
                     'snapshot':{'metadata':{'last_updated':'volatile'},'age_seconds':1,'refresh_required_before_prescribing':False,
                                 'readiness_decision':{'recommendation':'go'},'derived_metrics':{'calculation_timestamp':'volatile'}},
                     'athlete_context':{'sections':[{'line':10,'text':'Stable constraints'}]}}
        self.gen=mock.Mock(return_value=('ready','Synthetic report',{'assistant_turns':1,'usage':{'input':100}}))
        self.send=mock.Mock(return_value={'status':'delivered','message_id':42})
        self.runner=r.Runner(self.p,clock=lambda:self.now,generator=self.gen,sender=self.send)
        self.addCleanup(self.runner.close)

    def run_report(self,packet=None,period='2026-10-22'):
        return self.runner.process(packet or self.packet,period,self.config,[])

    def test_confirmed_delivery_is_required_and_unchanged_evidence_skips_model(self):
        self.assertEqual(self.run_report()['status'],'delivered')
        self.assertEqual(self.run_report()['status'],'unchanged')
        self.assertEqual(self.gen.call_count,1);self.assertEqual(self.send.call_count,1)

    def test_generated_at_hash_line_and_age_noise_do_not_trigger_new_model_calls(self):
        self.run_report();p=copy.deepcopy(self.packet)
        p['built_at']='new';p['sources']['latest']['sha256']='new';p['snapshot']['age_seconds']=30;p['snapshot']['metadata']['last_updated']='new'
        p['snapshot']['derived_metrics']['calculation_timestamp']='new';p['athlete_context']['sections'][0]['line']=99
        self.assertEqual(self.run_report(p)['status'],'unchanged');self.assertEqual(self.gen.call_count,1)

    def test_material_fatigue_change_is_not_hidden_by_the_evidence_gate(self):
        self.run_report();p=copy.deepcopy(self.packet);p['snapshot']['readiness_decision']['recommendation']='modify'
        self.assertEqual(self.run_report(p)['status'],'delivered');self.assertEqual(self.gen.call_count,2)

    def test_known_failed_send_retries_cached_text_without_model_regeneration(self):
        self.send.side_effect=[{'status':'failed','retry_after':300},{'status':'delivered','message_id':43}]
        self.assertEqual(self.run_report()['status'],'failed')
        self.assertEqual(self.run_report()['status'],'backoff')
        self.now+=300001;self.assertEqual(self.run_report()['status'],'delivered')
        self.assertEqual(self.gen.call_count,1);self.assertEqual(self.send.call_count,2)
        self.assertEqual(self.send.call_args_list[0].args[2],self.send.call_args_list[1].args[2])

    def test_unknown_send_never_automatically_retries_even_after_inputs_change(self):
        self.send.return_value={'status':'unknown'}
        self.assertEqual(self.run_report()['status'],'unknown')
        self.now+=600000;p=copy.deepcopy(self.packet);p['snapshot']['new_health']='symptoms'
        self.assertEqual(self.run_report(p)['status'],'unknown')
        self.assertEqual(self.gen.call_count,1);self.assertEqual(self.send.call_count,1)

    def test_changed_evidence_invalidates_a_cached_undelivered_recommendation(self):
        self.send.side_effect=[{'status':'failed','retry_after':300},{'status':'delivered','message_id':43}]
        self.gen.side_effect=[('ready','Old recommendation',{}),('ready','New symptom-aware recommendation',{})]
        self.run_report();self.now+=300001;p=copy.deepcopy(self.packet);p['snapshot']['new_health']='symptoms'
        self.run_report(p)
        self.assertEqual(self.send.call_args.args[2],'New symptom-aware recommendation')
        self.assertEqual(self.gen.call_count,2)

    def test_generation_terminal_failures_have_two_attempt_cap_and_backoff(self):
        self.gen.return_value=('failed',None,{'error_code':'terminal'})
        self.assertEqual(self.run_report()['status'],'generation_failed')
        self.assertEqual(self.run_report()['status'],'backoff')
        self.now+=300001;self.run_report();self.now+=300001
        self.assertEqual(self.run_report()['status'],'generation_limit')
        self.assertEqual(self.gen.call_count,2);self.send.assert_not_called()

    def test_unknown_generation_never_retries(self):
        self.gen.return_value=('unknown',None,{})
        self.assertEqual(self.run_report()['status'],'generation_unknown')
        self.assertEqual(self.run_report()['status'],'unknown');self.assertEqual(self.gen.call_count,1)

    def test_delivery_attempt_cap_is_three(self):
        self.send.return_value={'status':'failed','retry_after':300}
        for _ in range(3):self.run_report();self.now+=300001
        self.assertEqual(self.run_report()['status'],'delivery_limit');self.assertEqual(self.send.call_count,3)

    def test_expired_undelivered_report_is_not_sent_late(self):
        self.send.return_value={'status':'failed','retry_after':300};self.run_report()
        self.now+=7200001
        self.assertEqual(self.run_report()['status'],'expired');self.assertEqual(self.send.call_count,1)

    def test_stale_current_source_does_not_generate_or_deliver_a_prescription(self):
        p=copy.deepcopy(self.packet);p['snapshot']['refresh_required_before_prescribing']=True
        self.assertEqual(self.run_report(p)['status'],'source_refresh_required')
        self.gen.assert_not_called();self.send.assert_not_called()

    def test_interrupted_inflight_send_becomes_unknown_not_a_new_send(self):
        self.run_report();rid=r.digest(['morning','2026-10-22']);self.runner.update(rid,state='sending')
        self.assertEqual(self.run_report()['status'],'unknown');self.assertEqual(self.send.call_count,1)

    def test_imported_reported_ids_do_not_create_new_notifications(self):
        self.runner.seed(['activity-one']);p=copy.deepcopy(self.packet);p['task']='post_workout'
        self.assertEqual(self.run_report(p,'activity-one')['status'],'already_reported')
        self.gen.assert_not_called();self.send.assert_not_called()

    def test_post_report_does_not_repeat_when_readiness_changes_on_later_days(self):
        p=copy.deepcopy(self.packet);p['task']='post_workout';self.run_report(p,'activity-new')
        p['local_date']='2026-10-23';p['snapshot']['readiness_decision']['recommendation']='modify'
        self.assertEqual(self.run_report(p,'activity-new')['status'],'unchanged');self.assertEqual(self.gen.call_count,1)

    def test_ledger_and_cache_are_private_and_lock_excludes_concurrent_generator(self):
        self.run_report();path=Path(self.p['state_dir'])/'reports.sqlite'
        self.assertEqual(path.stat().st_mode&0o777,0o600)
        with self.assertRaisesRegex(ValueError,'runner_busy'):r.Runner(self.p)

    def test_successful_cli_exit_without_a_valid_envelope_is_unknown(self):
        state,text,_=r.classify_generation({'returncode':0,'stdout':'not JSON'},1)
        self.assertEqual(state,'unknown');self.assertIsNone(text)

    def test_cleanup_warning_preserves_completed_text_without_duplicate_generation(self):
        envelope={'ok':False,'status':'error','final':'Completed report','error':{'kind':'cleanup'},'codeModeEngaged':False,'toolSummary':{'calls':0,'tools':[]}}
        state,text,metrics=r.classify_generation({'returncode':1,'stdout':json.dumps(envelope)},10)
        self.assertEqual((state,text),('ready','Completed report'));self.assertTrue(metrics['cleanup_warning'])

    def test_oversize_empty_timeout_and_killed_generation_are_not_success(self):
        for text in ['', 'x'*4001,'NO_REPLY']:
            state,_,_=r.classify_generation({'returncode':0,'stdout':json.dumps({'ok':True,'status':'ok','final':text,'codeModeEngaged':False,'toolSummary':{'calls':0,'tools':[]}})},10)
            self.assertEqual(state,'failed')
        self.assertEqual(r.classify_generation({'returncode':2,'stdout':json.dumps({'ok':False,'status':'timeout'})},10)[0],'failed')
        self.assertEqual(r.classify_generation({'supervisor_error':'timeout','stdout':''},10)[0],'unknown')

    def test_zero_cost_and_missing_usage_remain_unknown(self):
        m=r.generation_metrics({'costUsd':0},1)
        self.assertIsNone(m['reported_cost_usd']);self.assertEqual(m['usage'],{})

    def test_readonly_report_config_preserves_models_and_caps_every_agent_tool_surface(self):
        cfg={'tools':{'profile':'coding'},'models':{'provider':'unchanged'},'agents':{'entries':{'main':{'model':'same','tools':{'profile':'coding'}}}},'plugins':{'entries':{'section11-context':{'config':{}}}}}
        out=r.report_config(cfg)
        self.assertEqual(out['tools']['allow'],['section11_context']);self.assertNotIn('profile',out['tools'])
        self.assertIs(out['tools']['toolSearch'],False)
        self.assertEqual(out['agents']['entries']['main']['tools']['allow'],['section11_context'])
        self.assertEqual(out['models'],cfg['models']);self.assertEqual(out['agents']['entries']['main']['model'],'same')
        self.assertEqual(cfg['tools']['profile'],'coding')

    def test_send_receipt_must_match_the_pinned_target(self):
        identity={'ok':True,'result':{'id':777}}
        ack={'ok':True,'result':{'message_id':42,'chat':{'id':123456}}}
        with mock.patch.object(r,'telegram',side_effect=[(identity,200),(ack,200)]):
            self.assertEqual(r.deliver(self.p,self.config,'Report')['status'],'delivered')
        ack['result']['chat']['id']=999
        with mock.patch.object(r,'telegram',side_effect=[(identity,200),(ack,200)]):
            self.assertEqual(r.deliver(self.p,self.config,'Report')['status'],'unknown')

    def test_telegram_rejections_backoff_but_transport_and_server_failures_are_unknown(self):
        identity={'ok':True,'result':{'id':777}}
        for response,status,expected in [({'ok':False,'error_code':429,'parameters':{'retry_after':900}},429,'failed'),(None,None,'unknown'),({'ok':False,'error_code':500},500,'unknown')]:
            with self.subTest(status=status),mock.patch.object(r,'telegram',side_effect=[(identity,200),(response,status)]):
                outcome=r.deliver(self.p,self.config,'Report');self.assertEqual(outcome['status'],expected)
                if status==429:self.assertEqual(outcome['retry_after'],900)

    def test_unallowlisted_target_and_wrong_bot_are_rejected_before_send(self):
        config=copy.deepcopy(self.config);config['channels']['telegram']['allowFrom']=[]
        with mock.patch.object(r,'telegram') as call:
            self.assertEqual(r.deliver(self.p,config,'Report')['status'],'failed');call.assert_not_called()
        with mock.patch.object(r,'telegram',return_value=({'ok':True,'result':{'id':999}},200)) as call:
            self.assertEqual(r.deliver(self.p,self.config,'Report')['status'],'failed');self.assertEqual(call.call_count,1)

    def test_report_text_is_redacted_before_cache_and_delivery(self):
        self.gen.return_value=('ready','Report with synthetic-secret-123',{})
        self.runner.process(self.packet,'2026-10-22',self.config,['synthetic-secret-123'])
        self.assertNotIn('synthetic-secret-123',self.send.call_args.args[2])

    def test_bounded_process_timeout_and_output_limit(self):
        p=Path(self.temp.name)
        # Other HTTP-policy tests replace the process-wide time.monotonic.
        # These real subprocess deadlines need an independent real clock.
        with mock.patch.object(r,'time',SimpleNamespace(monotonic=__import__('time').perf_counter)):
            outcome=r.run_bounded([sys.executable,'-c','import time;time.sleep(3)'],0.05,p)
            self.assertEqual(outcome['supervisor_error'],'timeout')
            outcome=r.run_bounded([sys.executable,'-c','print("x"*1100000)'],3,p)
        self.assertEqual(outcome['supervisor_error'],'output_limit')
        self.assertLessEqual(len(outcome['stdout']),1000000)

    def test_placeholders_future_and_stale_activities_do_not_trigger_reports(self):
        context=r.sibling('context_packet');cp={'timezone':'Europe/Zurich','source_timezone':'Europe/Zurich'}
        now=datetime(2026,10,22,10,tzinfo=timezone.utc)
        for row in [{'id':'a','date':'2026-10-22','duration_hours':0},{'id':'a','date':'2026-10-19','duration_hours':1},{'id':'a','date':'2026-10-23T10:00:00+00:00','duration_hours':1},{'id':'a','date':'bad','duration_hours':1}]:
            self.assertFalse(r.eligible_activity(row,cp,now,context))
        self.assertTrue(r.eligible_activity({'id':'a','date':'2026-10-21T20:00:00+00:00','duration_hours':1},cp,now,context))
        self.assertTrue(r.eligible_activity({'id':'a','date':'2026-10-22','duration_hours':1},cp,now,context))

    def test_busy_queue_is_idempotent_and_contains_no_athlete_data(self):
        self.p['context_profile']='/private/context.json'
        fake=SimpleNamespace(load_profile=lambda _: {'timezone':'Europe/Zurich'},ZoneInfo=ZoneInfo)
        with mock.patch.object(r,'sibling',return_value=fake):
            r.queue_request(self.p,'morning');r.queue_request(self.p,'morning')
        files=list(Path(self.p['state_dir']).glob('queued-*.json'))
        self.assertEqual(len(files),1);self.assertEqual(files[0].stat().st_mode&0o777,0o600)
        self.assertEqual(set(json.loads(files[0].read_text())),{'task','period','at_ms'})

    def test_changed_evidence_cannot_bypass_telegram_retry_after(self):
        self.send.return_value={'status':'failed','retry_after':900};self.run_report()
        p=copy.deepcopy(self.packet);p['snapshot']['new_health']='fatigue';self.now+=300001
        self.assertEqual(self.run_report(p)['status'],'backoff');self.assertEqual(self.gen.call_count,1)

    def test_operator_resolution_is_explicit_and_sends_nothing(self):
        self.send.return_value={'status':'unknown'};self.run_report();rid=r.digest(['morning','2026-10-22'])
        self.runner.resolve(rid,'delivered','User verified original Telegram receipt')
        self.assertEqual(self.run_report()['status'],'unchanged');self.assertEqual(self.send.call_count,1)

    def test_unknown_generation_requires_confirmed_stop_before_operator_retry(self):
        self.gen.return_value=('unknown',None,{});self.run_report();rid=r.digest(['morning','2026-10-22'])
        with self.assertRaises(ValueError):self.runner.resolve(rid,'delivered','No report exists')
        with self.assertRaises(ValueError):self.runner.resolve(rid,'not_sent','No delivery seen')
        self.runner.resolve(rid,'not_sent','Generation process verified stopped',stopped=True)
        self.assertEqual(self.gen.call_count,1)

    def test_wrapped_unrestricted_or_failed_tool_runs_cannot_be_delivered(self):
        base={'ok':True,'status':'ok','final':'Misleading success','codeModeEngaged':False,'toolSummary':{'calls':1,'tools':['section11_context']}}
        for change in [{'codeModeEngaged':True},{'toolSummary':{'calls':1,'tools':['exec']}},{'toolSummary':{'calls':7,'tools':['section11_context']}},{'toolSummary':{'calls':1,'tools':['section11_context'],'unresolvedError':{'toolName':'section11_context'}}}]:
            body={**base,**change}
            self.assertNotEqual(r.classify_generation({'returncode':0,'stdout':json.dumps(body)},1)[0],'ready')
        self.assertEqual(r.classify_generation({'returncode':0,'stdout':json.dumps(base)},1)[0],'ready')

    def test_direct_answer_without_retrieval_uses_native_zero_tool_convention(self):
        body={'ok':True,'status':'ok','final':'Answer from supplied fresh packet','codeModeEngaged':False}
        self.assertEqual(r.classify_generation({'returncode':0,'stdout':json.dumps(body)},1)[0],'ready')

    def test_new_symptoms_during_generation_invalidate_advice_before_send(self):
        p=copy.deepcopy(self.packet);p['snapshot']['new_health']='new symptoms'
        self.runner.evidence_reader=lambda *_:p
        self.assertEqual(self.run_report()['status'],'evidence_changed_before_delivery')
        self.send.assert_not_called()

    def test_source_recheck_failure_never_sends_cached_advice(self):
        self.runner.evidence_reader=mock.Mock(side_effect=ValueError('source missing'))
        self.assertEqual(self.run_report()['status'],'source_recheck_failed')
        self.send.assert_not_called()

    def test_generation_crossing_expiry_cannot_send_late(self):
        def generation(*_):
            self.now+=7200001
            return 'ready','Late report',{}
        self.runner.generator=generation
        self.assertEqual(self.run_report()['status'],'expired');self.send.assert_not_called()

    def test_busy_queue_failure_is_sanitized(self):
        with mock.patch.object(sys,'argv',['runner','--profile','/private/profile.json','morning']),mock.patch.object(r,'load_profile',return_value=self.p),mock.patch.object(r,'Runner',side_effect=ValueError('runner_busy')),mock.patch.object(r,'queue_request',side_effect=ValueError('synthetic-private-content')),contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(r.main(),1)
        self.assertEqual(json.loads(output.getvalue())['error_code'],'report_queue_failed_no_private_details')
        self.assertNotIn('synthetic-private-content',output.getvalue())


if __name__=='__main__':unittest.main()
