"""Comparison must use selected block measurements and disclose mismatches."""
import copy
import json
import unittest
from unittest import mock
from _harness import REPO_ROOT,load_module_by_path
m=load_module_by_path('s11_block_comparison_tests',REPO_ROOT/'examples/agentic/openclaw/block_comparison.py')


def packet(aid='i123',power=180.2,hr=137.3,duration=2699):
    return {'status':'available','activity':{'id':aid,'start_date_local':'2026-11-04T17:00:00',
            'type':'VirtualRide','trainer':True,'device_name':'Synthetic device','icu_ftp':270,'average_temp':None,
            'average_heartrate':99}, # Deliberately wrong whole-ride HR must never be used.
            'paired_event_id':123,'analysis':{'version':4,'method':'paired_plan_windows','status':'followed','issues':[],
            'steps':[{'step_index':0,'target_w':{'ramp':[100,180]},'actual':None},
                     {'step_index':1,'target_w':180,'planned_duration_s':duration+1,'match':True,
                      'actual':{'start_s':602,'end_s':602+duration,'mean_power_w':power,'mean_hr_bpm':hr,
                                'power_coverage_pct':100,'hr_coverage_pct':100,'mean_cadence_rpm':85,'cadence_coverage_pct':100}},
                     {'step_index':2,'target_w':135,'planned_duration_s':300,'actual':None}]},
            'provenance':{'analyzer_sha256':'same-analyzer','computed_at':'2026-11-04T18:00:00+00:00','api_gets':4,'source_fingerprint':'synthetic'}}


class Comparison(unittest.TestCase):
    def setUp(self):
        self.current=packet();self.old=packet('i456',185.2,127.8,2819)
        self.old['activity'].update(start_date_local='2026-10-05T07:50:07',device_name='Other recorder')
        self.old['analysis'].update(status='partly_followed',issues=['shortened_or_extended'])
        self.old['analysis']['steps'][1].update(target_w=185,planned_duration_s=2820)
        self.old['analysis']['steps'][1]['actual'].update(start_s=484,end_s=3303)

    def compare(self):return m.compare_packets(self.current,self.old,1,1)

    def test_october_november_regression_is_observed_not_exact_or_normalized(self):
        r=self.compare();self.assertEqual(r['status'],'available')
        self.assertEqual(r['comparison_kind'],'descriptive_only');self.assertEqual(r['workload_match'],'different')
        delta=r['delta_current_minus_reference']
        self.assertEqual(delta['observed_power_w'],-5)
        self.assertEqual(delta['observed_window_s'],-120)
        self.assertEqual(delta['mean_hr_bpm'],9.5)
        self.assertEqual(r['current']['actual']['mean_hr_bpm'],137.3)
        self.assertEqual(r['reference']['actual']['mean_hr_bpm'],127.8)
        self.assertIn('recording_device_differs',r['differences'])
        self.assertIn('window_start_s_differs',r['differences'])
        self.assertNotIn('average_heartrate',json.dumps(r))
        self.assertIn('never label it HR change at a common wattage',' '.join(r['interpretation_limits']))

    def test_same_recorded_workload_is_still_not_a_controlled_or_fitness_comparison(self):
        self.old=packet('i456')
        r=self.compare();self.assertEqual(r['workload_match'],'same_at_reported_precision')
        self.assertEqual(r['comparison_kind'],'descriptive_only')
        self.assertIn('not an exact controlled comparison',' '.join(r['interpretation_limits']))

    def test_shortened_cooldown_does_not_reject_the_valid_main_window(self):
        r=self.compare();self.assertEqual(r['status'],'available')
        self.assertEqual(r['reference']['whole_session_status'],'partly_followed')
        self.assertEqual(r['reference']['target_window_agreement'],True)

    def test_omitted_selectors_request_explicit_choices_without_inferred_main_roles(self):
        r=m.compare_packets(self.current,self.old)
        self.assertEqual(r['status'],'selection_required')
        self.assertEqual([s['step_index'] for s in r['candidates']['current']],[1])
        self.assertIn('not inferred main-set roles',r['scope'])
        self.assertNotIn('delta_current_minus_reference',r)

    def test_invalid_ramp_repeat_and_unmeasured_steps_cannot_be_compared_as_steady(self):
        for index in (-1,True,99,0,2):
            self.assertEqual(m.compare_packets(self.current,self.old,index,1)['status'],'unavailable')
        self.current['analysis']['steps'][1]['repeat']=[4,60,60]
        self.assertEqual(self.compare()['error_code'],'constant_target_continuous_step_required')

    def test_unpaired_thirds_unknown_pairing_and_version_changes_block_comparison(self):
        for change in [lambda p:p['analysis'].update(method='fixed_elapsed_thirds'),
                       lambda p:p.update(paired_event_id=None),
                       lambda p:p['analysis'].update(issues=['pairing_conflict']),
                       lambda p:p['analysis'].update(version=3),
                       lambda p:p['provenance'].update(analyzer_sha256='other')]:
            self.current=packet();change(self.current)
            self.assertEqual(self.compare()['status'],'unavailable')
        self.current['analysis']['method']='fixed_elapsed_thirds'
        self.assertEqual(m.compare_packets(self.current,self.old)['status'],'unavailable')

    def test_missing_or_sparse_hr_does_not_create_hr_delta_or_fallback(self):
        for value,coverage in [(None,100),(0,100),(137.3,94),(137.3,None)]:
            self.current['analysis']['steps'][1]['actual'].update(mean_hr_bpm=value,hr_coverage_pct=coverage)
            r=self.compare();self.assertEqual(r['status'],'available')
            self.assertIsNone(r['delta_current_minus_reference']['mean_hr_bpm'])
            self.assertIn('mean_hr_bpm_or_coverage',r['unknown_context'])

    def test_sparse_power_and_invalid_timing_block_numeric_comparison(self):
        for change in [{'power_coverage_pct':94},{'end_s':0},{'mean_power_w':None}]:
            self.current=packet();self.current['analysis']['steps'][1]['actual'].update(change)
            self.assertEqual(self.compare()['status'],'unavailable')

    def test_environment_and_unknown_device_are_distinct_from_known_mismatch(self):
        self.old['activity'].update(device_name=None,type='Ride',trainer=False)
        r=self.compare();self.assertIn('environment_differs',r['differences'])
        self.assertIn('recording_device',r['unknown_context'])
        self.assertNotIn('recording_device_differs',r['differences'])

    def test_off_target_and_clipped_window_limits_are_explicit(self):
        self.current['analysis']['steps'][1].update(match=False,observed_window_fraction=.5)
        r=self.compare();self.assertEqual(r['status'],'available')
        self.assertIn('current_target_window_agreement_not_established',r['differences'])
        self.assertIn('current_window_clipped',r['differences'])

    def test_retrieval_is_bounded_and_failure_never_substitutes_another_ride(self):
        fetch=mock.Mock(side_effect=[self.current,self.old])
        r=m.compare({},'i123','i456',fetch,1,1)
        self.assertEqual(fetch.call_count,2);self.assertEqual(r['retrieval']['api_gets'],8)
        self.assertLess(len(json.dumps(r).encode()),7800)
        fetch=mock.Mock(return_value={'status':'unavailable','error_code':'authentication_failed'})
        r=m.compare({},'i123','i456',fetch,1,1)
        self.assertEqual(fetch.call_count,1);self.assertEqual(r['source_error'],'authentication_failed')
        for ids in [('i123','i123'),('i123','../secret'),('i123',None)]:
            fetch.reset_mock();r=m.compare({},*ids,fetch,1,1)
            self.assertEqual(r['status'],'unavailable');fetch.assert_not_called()
