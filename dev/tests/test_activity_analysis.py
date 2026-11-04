"""Historical analysis is account-bound, compact, cached and failure-explicit."""
import copy
from datetime import datetime,timedelta,timezone
import fcntl
import json
import os
from pathlib import Path
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from _harness import REPO_ROOT,load_module_by_path
m=load_module_by_path('s11_activity_analysis_tests',REPO_ROOT/'examples/agentic/openclaw/activity_analysis.py')
c=load_module_by_path('s11_activity_analysis_context_tests',REPO_ROOT/'examples/agentic/openclaw/context_packet.py')


class Analysis(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.data=self.root/'data';self.data.mkdir(mode=0o700)
        p=self.data/'.sync_config.json';p.write_text(json.dumps({'athlete_id':'i99','intervals_key':'synthetic-private-key'}));p.chmod(0o600)
        self.facts=self.root/'facts.sqlite3'
        with sqlite3.connect(self.facts) as db:
            db.execute('CREATE TABLE facts (kind TEXT,id TEXT,body TEXT)')
            db.execute('INSERT INTO facts VALUES (?,?,?)',('activity','i123','{}'))
        self.p={'schema_version':1,'install_root':str(REPO_ROOT),'data_dir':str(self.data),
                'facts_store':str(self.facts),'state_dir':str(self.root/'cache'),'athlete_id':'i99'}
        self.now=datetime(2026,11,4,tzinfo=timezone.utc)
        self.act={'id':'i123','start_date_local':'2026-01-01T09:00:00','type':'VirtualRide',
                  'paired_event_id':123,'elapsed_time':120,'moving_time':120,'icu_ftp':250}
        self.event={'id':123,'workout_doc':{'duration':120,'steps':[{'duration':20,'ramp':True,'power':{'units':'w','start':100,'end':180}},
                {'duration':80,'power':{'units':'w','value':180}}, {'duration':20,'power':{'units':'w','value':100}}]}}
        self.intervals={'id':'i123','icu_intervals':[{'type':'RECOVERY','start_index':0,'end_index':121}]}
        self.streams=[{'type':'time','data':list(range(121))},
            {'type':'watts','data':[100+4*t if t<=20 else 180 if t<=100 else 100 for t in range(121)]},
            {'type':'heartrate','data':[130]*121}, {'type':'cadence','data':[85]*121}]
        self.calls=[];self.clients=[];outer=self
        class Fake:
            def __init__(self,auth):
                assert auth==('API_KEY','synthetic-private-key')
                self.calls=0;outer.clients.append(self)
            def get(self,path,params=None):
                self.calls+=1;outer.calls.append((path,params))
                if outer.failure and outer.failure[0] in path:raise m.AnalysisError(outer.failure[1])
                if path.endswith('/streams.json'):return copy.deepcopy(outer.streams)
                if path.endswith('/intervals'):return copy.deepcopy(outer.intervals)
                if '/events/' in path:return copy.deepcopy(outer.event)
                return copy.deepcopy(outer.act)
        self.factory=Fake;self.failure=None

    def run_analysis(self,now=None):return m.analyze(self.p,'i123',self.factory,now or self.now)

    def test_old_ride_uses_real_analyzer_without_retention_gate_or_raw_output(self):
        r=self.run_analysis();self.assertEqual(r['status'],'available')
        self.assertEqual(r['analysis']['method'],'paired_plan_windows')
        self.assertEqual(len(r['analysis']['steps']),3)
        self.assertEqual([s['planned_duration_s'] for s in r['analysis']['steps']],[20,80,20])
        actual=r['analysis']['steps'][1]['actual']
        self.assertEqual(actual['mean_hr_bpm'],130)
        self.assertGreater(actual['mean_power_w'],175)
        self.assertEqual(actual['hr_coverage_pct'],100)
        self.assertEqual(len(self.calls),4)
        self.assertLess(len(json.dumps(r).encode()),7800)
        self.assertNotIn('synthetic-private-key',json.dumps(r))
        self.assertNotIn('streams',r);self.assertNotIn('data',r)
        self.assertEqual(r['api_writes'],0)
        cached=list((self.root/'cache').glob('*.json'));self.assertEqual(len(cached),1)
        self.assertEqual(cached[0].stat().st_mode&0o777,0o600)
        self.assertNotIn('synthetic-private-key',cached[0].read_text())

    def test_cache_revalidates_metadata_but_skips_stream_download(self):
        self.run_analysis();self.calls=[]
        r=self.run_analysis(self.now+timedelta(minutes=5))
        self.assertTrue(r['provenance']['streams_reused'])
        self.assertEqual(len(self.calls),3)
        self.assertFalse(any('/streams.json' in path for path,_ in self.calls))
        self.assertEqual(r['provenance']['computed_at'],self.now.isoformat())
        self.assertNotEqual(r['provenance']['computed_at'],r['provenance']['revalidated_at'])

    def test_activity_prescription_interval_changes_and_ttl_invalidate_cache(self):
        self.run_analysis()
        for change in [lambda:self.act.update(icu_sync_date='changed'),
                       lambda:self.event['workout_doc']['steps'][1]['power'].update(value=185),
                       lambda:self.intervals['icu_intervals'][0].update(label='edited')]:
            change();self.calls=[];r=self.run_analysis(self.now+timedelta(minutes=10))
            self.assertFalse(r['provenance']['streams_reused']);self.assertEqual(len(self.calls),4)
        r=self.run_analysis(self.now+timedelta(hours=7));self.assertFalse(r['provenance']['streams_reused'])

    def test_missing_hr_remains_unknown_with_coverage(self):
        self.streams=[s for s in self.streams if s['type']!='heartrate']
        r=self.run_analysis();self.assertEqual(r['status'],'available')
        for step in r['analysis']['steps']:
            self.assertIsNone(step['actual']['mean_hr_bpm']);self.assertEqual(step['actual']['hr_coverage_pct'],0)

    def test_identity_and_account_guards_precede_api_access(self):
        self.p['athlete_id']='i88';r=self.run_analysis()
        self.assertEqual(r['error_code'],'credential_account_mismatch');self.assertFalse(self.calls)
        self.p['athlete_id']='i99'
        for aid in ['i999','../secrets','i123?other=1']:
            r=m.analyze(self.p,aid,self.factory,self.now)
            self.assertEqual(r['status'],'unavailable');self.assertFalse(self.calls)

    def test_mismatched_api_identity_or_event_cannot_establish_pairing(self):
        self.act['id']='i999';self.assertEqual(self.run_analysis()['error_code'],'activity_identity_mismatch')
        self.act['id']='i123';self.event['id']=999
        self.assertEqual(self.run_analysis()['error_code'],'paired_event_identity_mismatch')

    def test_failure_does_not_substitute_a_cached_success_or_expose_provider_text(self):
        self.run_analysis()
        for code in ['authentication_failed','access_denied','rate_limited','upstream_timeout','network_unavailable']:
            self.failure=('/activity/i123',code);r=self.run_analysis()
            self.assertEqual(r['error_code'],code);self.assertNotIn('analysis',r)
        self.failure=None;self.intervals={'provider_text':'synthetic-private-key'}
        r=self.run_analysis();self.assertEqual(r['error_code'],'invalid_intervals_response')
        self.assertNotIn('synthetic-private-key',json.dumps(r))

    def test_unpaired_and_missing_prescription_are_descriptive_not_adherence(self):
        self.act['paired_event_id']=None;r=self.run_analysis()
        self.assertNotEqual(r['analysis']['method'],'paired_plan_windows')
        self.assertNotEqual(r['analysis']['status'],'followed')
        self.act['paired_event_id']=123;self.failure=('/events/','not_found')
        r=self.run_analysis();self.assertIn('paired_event_unavailable',r['analysis']['issues'])

    def test_private_cache_and_lock_prevent_unsafe_access_or_stampede(self):
        folder=self.root/'cache';folder.mkdir(mode=0o700)
        folder.chmod(0o755)
        self.assertEqual(self.run_analysis()['error_code'],'invalid_private_cache_directory')
        folder.chmod(0o700)
        with (folder/'.lock').open('w') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            self.assertEqual(self.run_analysis()['error_code'],'analysis_busy_retry_later')
        self.assertFalse(self.calls)

    def test_profile_is_operator_owned_and_context_feature_is_opt_in(self):
        path=self.root/'profile.json';path.write_text(json.dumps(self.p));path.chmod(0o600)
        self.assertEqual(m.load_profile(path),self.p)
        path.chmod(0o644)
        with self.assertRaises(m.AnalysisError):m.load_profile(path)
        self.assertEqual(c.activity_analysis({},'i123')['error_code'],'activity_analysis_not_configured')
        path.chmod(0o600)
        profile={'data_dir':'/different','activity_analysis_profile':str(path)}
        with self.assertRaises(c.PacketError):c.activity_analysis(profile,'i123')
        wire=c.encode_tool_packet(self.run_analysis(),{},'activity_analysis')
        self.assertLessEqual(len(wire.encode()),8192);self.assertTrue(json.loads(wire)['packet_complete'])


class HttpBounds(unittest.TestCase):
    def client(self,status=200,chunks=None):
        client=m.Fetch(('API_KEY','synthetic-secret'))
        response=mock.MagicMock();response.status_code=status
        response.iter_content.return_value=iter(chunks if chunks is not None else [b'{}'])
        response.__enter__.return_value=response
        client.session=mock.Mock();client.session.get.return_value=response
        return client

    def test_http_errors_redirects_and_bodies_are_sanitized(self):
        for status,code in [(401,'authentication_failed'),(403,'access_denied'),(404,'not_found'),(429,'rate_limited'),(503,'upstream_unavailable'),(302,'redirect_rejected')]:
            client=self.client(status)
            with self.assertRaisesRegex(m.AnalysisError,code):client.get('/activity/i123')
            self.assertFalse(client.session.get.call_args.kwargs['allow_redirects'])

    def test_body_call_and_time_budgets_are_enforced_without_retry(self):
        client=self.client(chunks=[b'x'*(m.MAX_RESPONSE+1)])
        with self.assertRaisesRegex(m.AnalysisError,'response_too_large'):client.get('/activity/i123')
        self.assertEqual(client.session.get.call_count,1)
        client=self.client();client.calls=4
        with self.assertRaisesRegex(m.AnalysisError,'fetch_budget_exceeded'):client.get('/activity/i123')
        client.session.get.assert_not_called()
        client=self.client();client.deadline=0
        with self.assertRaisesRegex(m.AnalysisError,'fetch_budget_exceeded'):client.get('/activity/i123')
        client.session.get.assert_not_called()
