"""Save-first replanning survives reference errors and wire limits."""
import copy
import json
import unittest
from unittest import mock
from datetime import timedelta
from _harness import REPO_ROOT,load_module_by_path
import test_coaching_runtime as runtime_fixtures
import test_context_packet as context_fixtures
from test_athlete_intake import payload

c=load_module_by_path('s11_planning_references_tests',REPO_ROOT/'examples/agentic/openclaw/context_packet.py')


class References(unittest.TestCase):
    def test_entry_skill_fits_native_whole_document_read_and_gives_broker_workflow(self):
        text=(REPO_ROOT/'SKILL.md').read_text()
        self.assertLessEqual(len(text.splitlines()),200)
        self.assertLessEqual(len(text.encode()),12000)
        for required in ('same model turn','tool_call','planning_setup','payload":null',
                         'propose','P0/P1','immutable','calendar','HRV','SKILL_REFERENCE.md'):
            self.assertIn(required,text)
        self.assertTrue((REPO_ROOT/'SKILL_REFERENCE.md').is_file())

    def setUp(self):
        self.fixture=context_fixtures.ContextPacket();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.p=self.fixture.profile

    def test_primary_profile_explicitly_exposes_persistence_without_model_or_report_changes(self):
        e=load_module_by_path('s11_planning_tool_access',REPO_ROOT/'examples/agentic/openclaw/efficiency_config.py')
        config={'tools':{'profile':'coding','alsoAllow':['section11_context']},'agents':{'defaults':{'model':'same'},'entries':{'main':{'model':'sol','thinkingDefault':'medium'},'utility':{'model':'luna'}}}}
        original=copy.deepcopy(config);out=e.enable_primary_coaching_tools(config)
        self.assertIn('section11_coaching',out['agents']['entries']['main']['tools']['alsoAllow'])
        self.assertEqual(config,original);self.assertEqual(out['agents']['entries']['utility'],original['agents']['entries']['utility'])
        self.assertEqual(out['tools'],original['tools'])
        self.assertEqual(out['agents']['entries']['main']['model'],'sol')
        self.assertEqual(e.enable_primary_coaching_tools(out),out)

    def test_exact_failed_request_identifiers_resolve_to_full_real_titles(self):
        p={**self.p,'protocol':str(REPO_ROOT/'SECTION_11.md'),'workout_reference':str(REPO_ROOT/'examples/workout-library/WORKOUT_REFERENCE.md')}
        result=c.reference_batch(p,[{'source':'protocol','heading':'B'},{'source':'workouts','heading':'AE-1'}])
        self.assertEqual([r['resolved_heading'] for r in result['references']],
                         ['11 B. AI Training Plan Protocol','AE-1: Steady-State Endurance (Short)'])
        self.assertIn('Athlete Context and Planning Intent',result['references'][0]['section']['text'])
        self.assertLess(len(json.dumps(result).encode()),30000)

    def test_exact_title_wins_and_ambiguous_identifiers_never_guess(self):
        sections=[{'heading':'B','text':'Exact title','line':1},{'heading':'11 B. AI Training Plan Protocol','text':'Alias','line':2}]
        self.assertEqual(c.reference_section('protocol',sections,'B')['text'],'Exact title')
        sections=[{'heading':'AE-1: First','text':'one','line':1},{'heading':'AE-1: Second','text':'two','line':3}]
        with self.assertRaises(c.PacketError) as err:c.reference_section('workouts',sections,'AE-1')
        self.assertEqual(len(err.exception.reference_errors[0]['candidates']),2)
        with self.assertRaises(c.PacketError):c.reference_section('dossier',sections,'AE-1')

    def test_missing_batch_returns_candidates_without_any_successful_bodies(self):
        with self.assertRaises(c.PacketError) as err:
            c.reference_batch(self.p,[{'source':'protocol','heading':'Safety'}, {'source':'workouts','heading':'Template'}])
        e=err.exception
        self.assertEqual(str(e),'reference_selection_required')
        self.assertIn('Template A',e.reference_errors[0]['candidates'])
        self.assertNotIn('Stop rule',json.dumps(e.reference_errors))

    def test_plan_packet_supplies_save_first_order_without_duplicating_long_term(self):
        with mock.patch.object(c,'long_term') as read:
            result=c.build(self.p,'plan',now=context_fixtures.NOW)
        read.assert_not_called()
        self.assertIn('planning_setup',result['planning_workflow']['first'])
        self.assertEqual(result['snapshot']['readiness_decision']['priority'],0)
        self.assertIn('athlete_intake',result)
        latest=self.fixture.latest
        latest['derived_metrics']['capability']={'bulky':'C'*16000}
        self.fixture.write('latest.json',latest)
        intake={'status':'available','revision_id':'intake-synthetic','entries':[{'key':'goal','kind':'goal','text':'Saved goal '+('G'*7000)}],'open_questions':[]}
        with mock.patch.object(c,'intake_context',return_value=intake):
            original=c.build(self.p,'plan',now=context_fixtures.NOW)
        frozen=json.dumps(original,sort_keys=True)
        wire=json.loads(c.encode_tool_packet(original,{'tool_packet_bytes':25000},'build'))
        self.assertEqual(wire['athlete_intake']['entries'],intake['entries'])
        self.assertEqual(wire['snapshot']['readiness_decision'],original['snapshot']['readiness_decision'])
        self.assertEqual(wire['snapshot']['health_context'],original['snapshot']['health_context'])
        self.assertIn('capability_deferred',wire['snapshot'])
        self.assertEqual(frozen,json.dumps(original,sort_keys=True))



class PlanningSetup(unittest.TestCase):
    def setUp(self):
        self.f=runtime_fixtures.CoachingRuntime();self.f.setUp();self.addCleanup(self.f.doCleanups)
        (self.f.root/'p.md').write_text('# Protocol\n## 11 B. AI Training Plan Protocol\nValidated plan rules.\n')
        (self.f.root/'w.md').write_text('# Library\n#### AE-1: Steady-State Endurance (Short)\nReference only.\n')
        self.f.runtime.save_intake(payload());self.f.propose()
        self.before=self.f.runtime.state_view()

    def test_setup_saves_new_feedback_before_optional_reads_and_readback_survives(self):
        feedback={'date':'2026-10-29','state':'normal','note':'Synthetic shoulder felt fine the next morning; no new clearance','health_clarification':None}
        with mock.patch.object(self.f.runtime.context,'reference_batch',side_effect=ValueError('PRIVATE_CANARY')):
            result=self.f.runtime.planning_setup(None,[{'source':'workouts','heading':'AE-1'}],feedback)
        self.assertTrue(result['feedback_receipt']['success'])
        self.assertEqual(self.f.runtime.state_view()['current_feedback']['note'],feedback['note'])
        self.assertEqual(result['planning_references']['status'],'unavailable')
        self.assertNotIn('PRIVATE_CANARY',json.dumps(result))
        self.assertEqual(self.f.runtime.state_view()['plan'],self.before['plan'])

    def test_saved_feedback_receipt_survives_independent_intake_failure(self):
        feedback={'date':'2026-10-29','state':'normal','note':'Synthetic feedback','health_clarification':None}
        with mock.patch.object(self.f.runtime,'save_intake',side_effect=ValueError('stale parent')):
            result=self.f.runtime.planning_setup(self.changed(),[{'source':'workouts','heading':'AE-1'}],feedback)
        self.assertTrue(result['feedback_receipt']['success'])
        self.assertFalse(result['intake_receipt']['success'])
        self.assertEqual(result['planning_reads']['status'],'not_started')

    def test_invalid_continuous_role_returns_safe_code_rolls_back_and_allows_correction(self):
        plan=copy.deepcopy(self.f.plan)
        source=json.loads((REPO_ROOT/'examples/json-examples/coaching_plan.example.json').read_text())
        plan['sessions']=[source['sessions'][1]]
        plan['revision'].update(parent_revision=self.before['revision_id'],request_id='continuous-role-repair')
        steps=plan['sessions'][0]['workout']['coaching_prescription']['steps']
        for step in steps:
            if step.get('role')=='work':step['role']='endurance'
        context={'date':'2026-10-29','source':'Synthetic current statement','goals_and_availability':'Synthetic unchanged context'}
        from test_coaching_plan import Clock
        push=self.f.runtime.api.push_module()
        patch=mock.patch.object(push,'datetime',Clock);patch.start();self.addCleanup(patch.stop)
        patch=mock.patch.object(push._load_workout_validator(),'datetime',Clock);patch.start();self.addCleanup(patch.stop)
        with self.assertRaises(runtime_fixtures.b.PlanInputError) as error:
            self.f.runtime.propose({'plan':plan,'current_athlete_context':context})
        self.assertEqual(str(error.exception),'continuous_role_or_dose')
        self.assertEqual(self.f.runtime.state_view()['revision_id'],self.before['revision_id'])
        for step in steps:
            if step.get('role')=='endurance':step['role']='work'
        result=self.f.runtime.propose({'plan':plan,'current_athlete_context':context})
        self.assertTrue(result['success']);self.assertEqual(result['calendar_writes'],0)
        self.assertTrue(all(r['validation_status']=='checked' for r in self.f.runtime.state_view()['prescription_summaries'].values()))

    def test_large_plan_state_keeps_whole_plan_and_receipts_and_explicitly_defers_intake(self):
        state=copy.deepcopy(self.before)
        state['intake']['entries']=[{'key':'synthetic-'+str(i),'text':'Reported synthetic constraint '+('x'*900)} for i in range(22)]
        state['publication']={'state':'proposed','sessions':[{'session_id':str(i),'receipt':'protected'} for i in range(16)]}
        frozen=json.dumps(state,sort_keys=True)
        limit=len(json.dumps(state).encode())-4000
        raw=runtime_fixtures.b.encode_response(state,{'tool_packet_bytes':limit},'state')
        wire=json.loads(raw);self.assertTrue(wire['packet_complete'])
        self.assertEqual(wire['plan'],state['plan']);self.assertEqual(wire['publication'],state['publication'])
        self.assertTrue(wire['intake']['entries_deferred'])
        self.assertEqual(wire['intake']['required_retrieval'],{'tool':'section11_context','operation':'intake'})
        self.assertNotIn('entries',wire['intake']);self.assertLessEqual(len(raw.encode()),limit)
        self.assertEqual(json.dumps(state,sort_keys=True),frozen)

    def changed(self):
        p=payload();p.update(request_id='active-plan-update',parent_revision=self.f.runtime.intake_view()['revision_id'])
        p['entries'][0]['text']='Explicit updated six-week return objective'
        p['entries'][1]['text']='Explicit updated Mon/Wed one hour, Saturday one to two hours'
        return p

    def test_active_plan_update_commits_before_bad_reference_and_fresh_next_day_recovers(self):
        result=self.f.runtime.planning_setup(self.changed(),[{'source':'workouts','heading':'missing'}])
        self.assertTrue(result['intake_receipt']['success'])
        self.assertEqual(result['planning_references']['error_code'],'reference_selection_required')
        self.assertEqual(result['managed_plan']['plan']['sessions'],self.before['plan']['sessions'])
        self.assertTrue(result['managed_plan']['full_plan_deferred'])
        self.f.now+=timedelta(days=1)
        fresh=self.f.runtime.state_view()
        self.assertEqual(fresh['state'],'active')
        self.assertIn('active-plan',fresh['instruction'])
        self.assertEqual(fresh['intake']['revision_id'],result['intake_receipt']['revision_id'])
        self.assertEqual(fresh['intake']['entries'][0]['text'],'Explicit updated six-week return objective')
        self.assertEqual(fresh['plan'],self.before['plan'])

    def test_unchanged_setup_reads_plan_and_alias_references_without_new_revision(self):
        result=self.f.runtime.planning_setup(None,[{'source':'protocol','heading':'B'},{'source':'workouts','heading':'AE-1'}])
        self.assertTrue(result['intake_receipt']['unchanged'])
        self.assertEqual(result['intake_receipt']['revision_id'],self.before['intake']['revision_id'])
        self.assertEqual(result['planning_references']['status'],'available')
        self.assertNotIn('intake',result['managed_plan'])
        self.f.runtime.cp['long_term_source']='/private/summary.json'
        with mock.patch.object(self.f.runtime.context,'long_term',return_value={'status':'available','rows':[]}) as read:
            result=self.f.runtime.planning_setup(None,[{'source':'workouts','heading':'AE-1'}])
        read.assert_called_once();self.assertEqual(result['long_term']['status'],'available')

    def test_oversize_read_defers_reference_bodies_without_hiding_successful_save(self):
        self.f.runtime.cp['tool_packet_bytes']=8192
        (self.f.root/'p.md').write_text('# Protocol\n## Large\n'+'x'*20000)
        result=self.f.runtime.planning_setup(self.changed(),[{'source':'protocol','heading':'Large'}])
        self.assertTrue(result['intake_receipt']['success'])
        self.assertEqual(result['planning_references']['status'],'deferred')
        self.assertNotIn('x'*1000,json.dumps(result))
        self.assertLess(len(json.dumps(result,separators=(',',':')).encode()),8192)
        self.assertEqual(result['intake_receipt']['revision_id'],self.f.runtime.intake_view()['revision_id'])

    def test_failed_plan_state_read_cannot_erase_intake_receipt(self):
        with mock.patch.object(self.f.runtime,'state_view',side_effect=ValueError('PRIVATE_CANARY')):
            result=self.f.runtime.planning_setup(self.changed(),[{'source':'workouts','heading':'AE-1'}])
        self.assertTrue(result['intake_receipt']['success'])
        self.assertEqual(result['managed_plan']['state'],'unavailable')
        self.assertNotIn('PRIVATE_CANARY',json.dumps(result))
