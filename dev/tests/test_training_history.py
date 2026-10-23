"""Synthetic source reconciliation, coverage and null semantics; no network."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest import mock
from _harness import REPO_ROOT, load_module_by_path

h = load_module_by_path("s11_training_history_tests", REPO_ROOT/"examples/training_history.py")
NOW = datetime(2026, 10, 23, 10, tzinfo=timezone.utc)


def ride(identity="a", day="2026-06-08", **fields):
    return {"id": identity, "start_date_local": day+"T12:00:00", "type": "VirtualRide", "moving_time": 3600, "icu_training_load": 40, **fields}


class HistoryFacts(unittest.TestCase):
    def summary(self, rows, wellness=None, attestation=None):
        a,w = h.facts(rows, wellness or [])
        return h.summarize(a,w,"2023-10-24","2026-10-23",NOW.isoformat(),attestation)

    def test_short_history_has_all_months_no_padded_pretraining(self):
        result = self.summary([ride()])
        self.assertEqual([m['month'] for m in result['monthly']], ['2026-06','2026-07','2026-08','2026-09','2026-10'])
        self.assertTrue(result['monthly'][0]['coverage']['partial'])
        self.assertTrue(result['monthly'][-1]['coverage']['partial'])
        self.assertFalse(result['monthly'][1]['coverage']['partial'])
        self.assertEqual(result['monthly'][1]['coverage']['empty_meaning'], 'no_recorded_activity')

    def test_user_attestation_is_dated_not_inferred_or_extended(self):
        att = {'source':'athlete_statement','confirmed_at':NOW.isoformat(),'first_training_date':'2026-06-08','complete_through':'2026-10-23'}
        result = self.summary([ride()],attestation=att)
        self.assertEqual(result['coverage']['athlete_attestation'],att)
        self.assertEqual(result['monthly'][1]['coverage']['empty_meaning'],'confirmed_no_training')
        with self.assertRaises(ValueError):self.summary([ride(day='2026-06-07')],attestation=att)

    def test_missing_metrics_are_not_zero(self):
        row = self.summary([ride(),ride('b',icu_training_load=None,moving_time=None)])['monthly'][0]['cycling']
        self.assertIsNone(row['load']['value']);self.assertEqual(row['load']['known_sum'],40)
        self.assertEqual(row['hours']['missing'],1);self.assertIsNone(row['longest_hours'])

    def test_zero_is_observed_and_invalid_numbers_unknown(self):
        a,_=h.facts([ride(moving_time=0,icu_training_load=0)],[])
        self.assertEqual(a[0]['seconds'],0)
        for value in [True,float('nan'),float('inf'),-1,'3']:
            self.assertIsNone(h.number(value))

    def test_deduplication_and_conflicts(self):
        a,_=h.facts([ride(),ride()],[]);self.assertEqual(len(a),1)
        with self.assertRaises(ValueError):h.facts([ride(),ride(moving_time=4000)],[])
        with self.assertRaises(ValueError):h.facts([ride(day='bad')],[])

    def test_cycling_is_separate_and_zones_never_pool(self):
        row=self.summary([ride(icu_zone_times=[{'id':'Z1','secs':400}],icu_hr_zone_times=[600,0]),ride('run',type='Run')])['monthly'][0]
        self.assertEqual(row['cycling']['activities'],1);self.assertEqual(row['all_sports']['activities'],2)
        self.assertEqual(row['cycling']['zones']['power']['seconds']['Z1'],400)
        self.assertEqual(row['cycling']['zones']['hr']['seconds']['Z1'],600)

    def test_optional_wearables_and_setting_not_test(self):
        row=self.summary([ride(icu_ftp=200)],[{'id':'2026-06-08','hrv':None,'restingHR':50}])['monthly'][0]
        self.assertEqual(row['optional_measurements']['hrv']['observations'],0)
        self.assertEqual(row['optional_measurements']['rhr']['observations'],1)
        self.assertFalse(row['cycling']['ftp_reference']['comparable_test'])

    def test_determinism_and_empty_history(self):
        self.assertEqual(h.dumps(self.summary([ride('b'),ride('a')])),h.dumps(self.summary([ride('a'),ride('b')])))
        result=self.summary([]);self.assertIsNone(result['coverage']['first_activity'])
        self.assertEqual(result['monthly'][0]['coverage']['empty_meaning'],'no_recorded_activity')

    def test_actual_sync_generation_no_longer_gates_short_history(self):
        import test_history_refresh as fixtures
        with tempfile.TemporaryDirectory() as directory:
            result=fixtures.generate(directory,NOW,fixtures.Api(activities=[ride(icu_training_load=None)]))
        for tier in ('monthly_1y','monthly_2y','monthly_3y'):
            self.assertEqual([m['month'] for m in result[tier]],['2026-06','2026-07','2026-08','2026-09','2026-10'])
            self.assertIsNone(result[tier][0]['total_tss'])
            self.assertEqual(result[tier][0]['metric_coverage']['load']['missing'],1)


class HistoryRefresh(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);(self.root/'credentials.json').write_text(json.dumps({'athlete_id':'123','intervals_key':'synthetic'}))
        self.profile={'state_dir':str(self.root/'state'),'credentials_file':str(self.root/'credentials.json'),'timezone':'Europe/Zurich'}
        self.activities=[ride()];self.wellness=[];self.calls=[]

    def fetch(self,config,endpoint,start,end):
        self.calls.append((endpoint,start,end))
        return [r for r in self.activities if start<=r['start_date_local'][:10]<=end] if endpoint=='activities' else self.wellness

    def refresh(self,now=NOW):
        return h.refresh(self.profile,now,self.fetch)

    def snapshot(self):
        return json.loads((self.root/'state/summary.json').read_text())

    def test_incremental_then_full_catches_old_edits_and_deletion(self):
        self.refresh();self.assertEqual(self.snapshot()['monthly'][0]['cycling']['hours']['value'],1)
        self.activities=[ride(moving_time=7200)]
        self.refresh(NOW+timedelta(hours=1));self.assertEqual(self.snapshot()['monthly'][0]['cycling']['hours']['value'],1)
        self.refresh(NOW+timedelta(days=1));self.assertEqual(self.snapshot()['monthly'][0]['cycling']['hours']['value'],2)
        self.activities=[];self.refresh(NOW+timedelta(days=2));self.assertEqual(self.snapshot()['coverage']['activity_count'],0)

    def test_source_totals_unique_and_two_reads_per_refresh(self):
        self.activities=[ride(),ride()];result=self.refresh()
        self.assertEqual(result['activities'],1);self.assertEqual(len(self.calls),2)
        self.assertEqual(self.snapshot()['reconciliation']['source_activity_rows'],2)

    def test_failure_preserves_last_good_and_sets_status(self):
        self.refresh();old=(self.root/'state/summary.json').read_bytes()
        def fail(*args):raise RuntimeError('private-canary')
        with self.assertRaises(RuntimeError):h.refresh(self.profile,NOW+timedelta(hours=1),fail)
        self.assertEqual((self.root/'state/summary.json').read_bytes(),old)
        self.assertNotIn('private-canary',(self.root/'state/status.json').read_text())

    def test_invalid_source_rolls_back_before_deletions(self):
        self.refresh();generation=self.snapshot()['generation'];self.activities=[ride(),ride(moving_time=9)]
        with self.assertRaises(ValueError):self.refresh(NOW+timedelta(days=1))
        self.assertEqual(self.snapshot()['generation'],generation)
        db=sqlite3.connect(self.root/'state/facts.sqlite3')
        self.addCleanup(db.close);self.assertEqual(db.execute('SELECT count(*) FROM facts').fetchone()[0],1)

    def test_account_change_rejected_and_private_modes(self):
        self.refresh();(self.root/'credentials.json').write_text(json.dumps({'athlete_id':'456','intervals_key':'synthetic'}))
        with self.assertRaises(ValueError):self.refresh()
        self.assertEqual((self.root/'state').stat().st_mode&0o777,0o700)
        for name in ['facts.sqlite3','summary.json','status.json']:
            self.assertEqual((self.root/'state'/name).stat().st_mode&0o777,0o600)

    def test_out_of_range_response_rejected(self):
        self.refresh()
        with self.assertRaises(ValueError):h.refresh(self.profile,NOW+timedelta(hours=1),lambda c,e,s,t:[ride()] if e=='activities' else [])

    def test_no_redirect_with_credentials(self):
        with self.assertRaises(ValueError):h.NoRedirect().redirect_request(None,None,302,'',{},'https://other.invalid')

    def test_deleted_training_invalidates_prior_completeness_confirmation(self):
        self.profile['athlete_attestation']={'source':'athlete_statement','confirmed_at':'2026-10-23','first_training_date':'2026-06-08','complete_through':'2026-10-23'}
        self.refresh()
        self.assertEqual(self.snapshot()['coverage']['attestation_source_status'],'matches_confirmed_activity_identities')
        self.activities=[];self.refresh(NOW+timedelta(days=1))
        result=self.snapshot()
        self.assertEqual(result['coverage']['attestation_source_status'],'source_changed_reconfirm_completeness')
        self.assertEqual(result['monthly'][0]['coverage']['empty_meaning'],'no_recorded_activity')


if __name__=='__main__':unittest.main()
