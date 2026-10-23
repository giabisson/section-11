"""Synthetic model comparison provenance, guarded routing and context continuity."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from _harness import REPO_ROOT,load_module_by_path
BASE=REPO_ROOT/'examples/agentic/openclaw'
b=load_module_by_path('s11_model_bench_tests',BASE/'model_benchmark.py')
p=load_module_by_path('s11_model_policy_tests',BASE/'model_policy.py')
e=load_module_by_path('s11_efficiency_config_tests',BASE/'efficiency_config.py')
r=load_module_by_path('s11_efficiency_runner_tests',BASE/'report_runner.py')
ev=load_module_by_path('s11_efficiency_evals_tests',BASE/'coaching_evals.py')


class ModelEfficiency(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.root.chmod(0o700)
        for name in ('records','reviews','workspace'):(self.root/name).mkdir(mode=0o700)
        self.config={'agents':{'defaults':{'thinkingDefault':'medium','model':{'primary':'openai/gpt-6.1-sol'},'compaction':{'notifyUser':True}},'entries':{'main':{'model':'openai/gpt-6-astra@openai:synthetic-profile','utilityModel':'openai/gpt-6-luna'}}},
                     'tools':{'profile':'coding'},'plugins':{'entries':{'section11-context':{'config':{'reportMode':False}}}},'channels':{'telegram':{'botToken':'synthetic-secret'}}}
        self.packet={'task':'morning','built_at':'one','packet_complete':True,'policy':['Current data only'],
                     'athlete_context':{'sections':[{'text':'No compulsory HRV','line':2}]},
                     'snapshot':{'freshness':'current','refresh_required_before_prescribing':False,'readiness_decision':{'recommendation':'go','priority':3},
                                 'health_context':{'source_status':'ok','marker_active':False,'recent_marker':False,'clarification_required':False},'age_seconds':1}}
        self.cases=ev.load_cases();self.packets=ev.packets(self.cases)

    def fixture(self,repetitions=2,review=True,candidate_wall=1000):
        m={'schema_version':1,'created_at_ms':1000,'repetitions':repetitions,'cases_sha256':ev.fingerprint(self.cases),
           'evaluator_sha256':hashlib.sha256((BASE/'coaching_evals.py').read_bytes()).hexdigest(),
           'runner_sha256':hashlib.sha256((BASE/'model_benchmark.py').read_bytes()).hexdigest(),
           'arms':{'baseline':{'model':'openai/gpt-6-astra','thinking':'medium'},'candidate':{'model':'openai/gpt-6.1-sol','thinking':'low'}}}
        b.save(self.root/'manifest.json',m)
        for rep in range(1,repetitions+1):
            for arm in ('baseline','candidate'):
                for case,packet in zip(self.cases,self.packets):
                    response=copy.deepcopy(case['reference_response']);name=f"{arm}-r{rep}-{case['case_id']}.json"
                    row={'status':'completed','arm':arm,'repetition':rep,'case_id':case['case_id'],'input_sha256':packet['input_sha256'],**m['arms'][arm],
                         'response':response,'metrics':{'wall_ms':10000 if arm=='baseline' else candidate_wall,'reported_cost_usd':None,'usage':{'input':10,'output':20}}}
                    b.save(self.root/'records'/name,row)
                    if review:b.save(self.root/'reviews'/name,{'case_id':case['case_id'],'response_sha256':ev.fingerprint(response),'reviewer':'Synthetic human attestation fixture','scores':{k:2 for k in ev.RUBRIC}})
        return m

    def policy(self,enabled=True):
        report=b.assess(self.root);path=self.root/'policy.json'
        b.save(path,{'schema_version':1,'enabled':enabled,'benchmark_dir':str(self.root),'manifest_sha256':report['manifest_sha256']})
        return path

    def select(self,path=None,packet=None,now=2000):
        return p.selection(packet or self.packet,self.config,path or self.root/'absent.json',r.load_private,b.assess,now)

    def test_config_keeps_primary_model_identity_utility_reasoning_and_heartbeat(self):
        original=copy.deepcopy(self.config);cfg=e.configure(self.config)
        self.assertEqual(cfg['agents']['entries']['main']['model'],original['agents']['entries']['main']['model'])
        self.assertEqual(cfg['agents']['entries']['main']['utilityModel'],'openai/gpt-6-luna')
        self.assertEqual(cfg['agents']['defaults']['thinkingDefault'],'medium');self.assertEqual(self.config,original)
        self.assertEqual(cfg['channels'],self.config['channels']);self.assertNotIn('heartbeat',cfg['agents']['defaults'])

    def test_only_readonly_context_results_are_pruned_and_recent_turns_survive(self):
        cfg=e.configure(self.config)['agents']['defaults']
        self.assertEqual(cfg['contextPruning']['tools']['allow'],['section11_context'])
        self.assertEqual(cfg['compaction']['recentTurnsPreserve'],3)
        self.assertEqual(cfg['compaction']['qualityGuard'],{'enabled':True,'maxRetries':1})
        self.assertEqual(cfg['compaction']['identifierPolicy'],'strict')
        self.assertEqual(cfg['compaction']['maxActiveTranscriptBytes'],2097152)
        self.assertEqual(e.configure(e.configure(self.config)),e.configure(self.config))

    def test_keyword_memory_is_explicit_primary_only_and_preserves_other_settings(self):
        self.config['memory']={'search':{'provider':'openai','model':'synthetic-embedding-model'}}
        self.config['agents']['entries']['other']={'memory':{'search':{'provider':'local'}}}
        original=copy.deepcopy(self.config)
        cfg=e.configure_keyword_memory(self.config)
        self.assertEqual(cfg['agents']['entries']['main']['memory']['search'],
                         {'provider':'none','sources':['memory'],'rememberAcrossConversations':False})
        self.assertEqual(cfg['memory'],original['memory'])
        self.assertEqual(cfg['agents']['entries']['other'],original['agents']['entries']['other'])
        self.assertEqual(cfg['agents']['entries']['main']['model'],original['agents']['entries']['main']['model'])
        self.assertEqual(cfg['channels'],original['channels']);self.assertEqual(self.config,original)

    def test_keyword_memory_preserves_query_settings_and_is_idempotent(self):
        self.config['agents']['entries']['main']['memory']={'search':{'provider':'openai','query':{'maxResults':7},'sources':['sessions'],'rememberAcrossConversations':True}}
        cfg=e.configure_keyword_memory(self.config)
        search=cfg['agents']['entries']['main']['memory']['search']
        self.assertEqual(search['query'],{'maxResults':7});self.assertEqual(search['provider'],'none')
        self.assertEqual(search['sources'],['memory']);self.assertFalse(search['rememberAcrossConversations'])
        self.assertEqual(e.configure_keyword_memory(cfg),cfg)
        self.assertEqual(e.configure(cfg)['agents']['entries']['main']['memory'],cfg['agents']['entries']['main']['memory'])

    def test_memory_contains_source_pointers_not_metric_snapshots_or_expired_schedules(self):
        cp={'dossier':'/private/dossier.md','data_dir':'/private/data'}
        text=e.memory_index(cp)+e.recovery_block(cp,'/private/context.json')+e.user_preference_block()
        self.assertIn('intermittent by choice',text);self.assertIn('Current self-reported',text)
        self.assertIn('expiry/recheck',text);self.assertIn('/private/dossier.md',text)
        self.assertNotIn('CTL:',text);self.assertNotIn('3 to 4h',text)
        self.assertLess(len(e.memory_index(cp).encode()),4096)

    def test_packet_cache_order_is_lossless_and_keeps_transport_marker_last(self):
        text=r.cache_ordered_json(self.packet);self.assertEqual(json.loads(text),self.packet)
        self.assertTrue(text.endswith('"packet_complete":true}'))
        self.assertGreater(text.index('"built_at"'),text.index('"policy"'))
        self.assertGreater(text.index('"age_seconds"'),text.index('"readiness_decision"'))

    def test_volatile_timestamp_does_not_change_stable_prompt_prefix(self):
        changed=copy.deepcopy(self.packet);changed['built_at']='two'
        a=r.report_prompt(self.packet,'Stable report template',[]);z=r.report_prompt(changed,'Stable report template',[])
        self.assertEqual(a.split('"built_at"')[0],z.split('"built_at"')[0])
        self.assertNotEqual(a,z);self.assertIn('"built_at":"two"',z)

    def test_headless_report_flush_is_disabled_without_changing_live_config(self):
        cfg=r.report_config(self.config)
        self.assertFalse(cfg['agents']['defaults']['compaction']['memoryFlush']['enabled'])
        self.assertNotIn('memoryFlush',self.config['agents']['defaults']['compaction'])

    def test_benchmark_preserves_auth_pin_and_utility_but_denies_every_tool(self):
        cfg=b.benchmark_config(self.config,'openai/gpt-6.1-sol','low')
        main=cfg['agents']['entries']['main']
        self.assertEqual(main['model'],'openai/gpt-6.1-sol@openai:synthetic-profile')
        self.assertEqual(main['utilityModel'],'openai/gpt-6-luna');self.assertEqual(cfg['tools']['deny'],['*'])
        self.assertEqual(main['tools']['deny'],['*']);self.assertNotIn('allow',cfg['tools'])
        self.assertEqual(main['models']['openai/gpt-6.1-sol']['agentRuntime']['id'],'openclaw')

    def test_benchmark_rejects_other_providers_and_injected_model_arguments(self):
        for model in ['other/model','openai/model --tool exec','openai/model@foreign-profile']:
            with self.assertRaises(ValueError):b.benchmark_config(self.config,model,'low')

    def test_decoder_rejects_unexpected_model_tools_and_code_mode(self):
        base={'ok':True,'status':'ok','codeModeEngaged':False,'provider':'openai','model':'gpt-6.1-sol','final':json.dumps(self.cases[0]['reference_response'])}
        for change in [{'model':'another'},{'codeModeEngaged':True},{'toolSummary':{'calls':1,'tools':['section11_context']}}]:
            self.assertNotEqual(b.decode({'returncode':0,'stdout':json.dumps({**base,**change})},1,'openai/gpt-6.1-sol')['status'],'completed')
        self.assertEqual(b.decode({'returncode':0,'stdout':json.dumps(base)},1,'openai/gpt-6.1-sol')['status'],'completed')

    def test_unknown_existing_trial_is_never_invoked_again(self):
        f=self.root/'records'/f"baseline-r1-{self.packets[0]['case_id']}.json";b.save(f,{'status':'unknown'})
        invoke=mock.Mock()
        b.trial(self.root,{},self.config,self.packets[0],'baseline',{'model':'openai/gpt-6-astra','thinking':'medium'},1,invoke)
        invoke.assert_not_called()

    def test_automatic_success_without_reviews_never_promotes_a_candidate(self):
        self.fixture(review=False);out=b.assess(self.root)
        self.assertEqual(out['arms']['candidate']['automated_passes'],24)
        self.assertFalse(out['promotion_eligible'])
        self.assertEqual(self.select(self.policy())['route'],'baseline')

    def test_single_repeat_does_not_pass_even_with_reviews_and_faster_results(self):
        self.fixture(repetitions=1)
        self.assertFalse(b.assess(self.root)['promotion_eligible'])

    def test_reviewed_repeated_comparison_with_measured_benefit_is_eligible(self):
        self.fixture();out=b.assess(self.root)
        self.assertTrue(out['promotion_eligible']);self.assertIsNone(out['arms']['candidate']['reported_cost_usd'])
        self.assertTrue(out['measured_benefit']);self.assertEqual(out['arms']['baseline']['usage']['input'],240)

    def test_changed_answer_invalidates_the_original_human_review(self):
        self.fixture();name=f"candidate-r1-{self.cases[0]['case_id']}.json";path=self.root/'records'/name
        v=r.load_private(path);v['response']['answer']+=' A different recommendation.';b.save(path,v)
        self.assertFalse(b.assess(self.root)['promotion_eligible'])

    def test_changed_fixture_prompt_or_evaluator_invalidates_provenance(self):
        m=self.fixture();m['evaluator_sha256']='different';b.save(self.root/'manifest.json',m)
        self.assertFalse(b.assess(self.root)['provenance_valid'])

    def test_no_measured_benefit_prevents_promotion(self):
        self.fixture(candidate_wall=15000)
        self.assertFalse(b.assess(self.root)['promotion_eligible'])

    def test_missing_policy_and_disabled_policy_preserve_current_model(self):
        self.assertEqual(self.select()['route'],'baseline');self.fixture()
        self.assertEqual(self.select(self.policy(False))['route'],'baseline')

    def test_candidate_requires_explicit_policy_plus_bound_reviewed_experiment(self):
        self.fixture();route=self.select(self.policy())
        self.assertEqual(route['route'],'reviewed_routine_candidate')
        cfg=p.apply_selection(self.config,route)
        self.assertEqual(cfg['agents']['entries']['main']['model'],'openai/gpt-6.1-sol@openai:synthetic-profile')
        self.assertEqual(cfg['agents']['defaults']['thinkingDefault'],'low')
        self.assertEqual(self.config['agents']['defaults']['thinkingDefault'],'medium')

    def test_weekly_post_workout_health_markers_and_missing_coverage_keep_baseline(self):
        self.fixture();path=self.policy()
        variations=[]
        for task in ['weekly','post_workout','plan']:
            v=copy.deepcopy(self.packet);v['task']=task;variations.append(v)
        for key,value in [('marker_active',True),('recent_marker',True),('clarification_required',True),('source_status','partial')]:
            v=copy.deepcopy(self.packet);v['snapshot']['health_context'][key]=value;variations.append(v)
        v=copy.deepcopy(self.packet);v['snapshot']['health_context']=None;variations.append(v)
        for v in variations:self.assertEqual(self.select(path,v)['route'],'baseline')

    def test_missing_wearables_alone_never_change_routine_eligibility(self):
        self.packet['snapshot']['wellness_data']=[{'hrv_rmssd':None,'resting_hr':None}]
        self.assertTrue(p.routine(self.packet))

    def test_expired_review_or_changed_baseline_model_or_effort_never_routes(self):
        self.fixture();path=self.policy()
        self.assertEqual(self.select(path,now=32*86400000)['route'],'baseline')
        self.config['agents']['defaults']['thinkingDefault']='high'
        self.assertEqual(self.select(path)['route'],'baseline')

    def test_failed_model_trial_cannot_be_counted_as_quality_success(self):
        self.fixture();path=self.root/'records'/f"candidate-r1-{self.cases[0]['case_id']}.json"
        v=r.load_private(path);v['status']='failed';b.save(path,v)
        self.assertFalse(b.assess(self.root)['promotion_eligible'])

    def test_report_cwd_is_stable_while_private_prompts_are_ephemeral(self):
        seen=[];profile={'state_dir':str(self.root),'context_profile':'/private/profile','openclaw_bin':'/usr/bin/unused'}
        def invoke(argv,timeout,cwd):
            prompt=Path(argv[argv.index('--message-file')+1]);cfg=Path(argv[argv.index('--config')+1])
            seen.append((str(cwd),str(prompt)))
            self.assertEqual(prompt.stat().st_mode&0o777,0o600)
            self.assertEqual(cfg.stat().st_mode&0o777,0o600)
            self.assertNotIn('synthetic-credential',prompt.read_text())
            return {'returncode':0,'stdout':json.dumps({'ok':True,'status':'ok','codeModeEngaged':False,'final':'Test report'})}
        cp=SimpleNamespace(load_profile=lambda _: {})
        with mock.patch.object(r,'sibling',return_value=cp),mock.patch.object(r,'report_template',return_value=('Template synthetic-credential',{})),mock.patch.object(r,'run_bounded',side_effect=invoke):
            for _ in range(2):self.assertEqual(r.generate(profile,self.config,self.packet,['synthetic-credential'])[0],'ready')
        self.assertEqual(seen[0][0],seen[1][0]);self.assertNotEqual(seen[0][1],seen[1][1])
        self.assertFalse(Path(seen[0][1]).exists());self.assertEqual((self.root/'report-workspace').stat().st_mode&0o777,0o700)

    def test_report_workspace_symlink_is_rejected(self):
        (self.root/'report-workspace').symlink_to(self.root/'workspace')
        cp=SimpleNamespace(load_profile=lambda _: {})
        with mock.patch.object(r,'sibling',return_value=cp),mock.patch.object(r,'report_template',return_value=('Template',{})),mock.patch.object(r,'run_bounded') as invoke:
            with self.assertRaises(ValueError):r.generate({'state_dir':str(self.root),'context_profile':'/private/profile'},self.config,self.packet,[])
        invoke.assert_not_called()


if __name__=='__main__':unittest.main()
