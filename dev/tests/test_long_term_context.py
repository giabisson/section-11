"""Bounded typed retrieval against synthetic durable history and review records."""
from datetime import date, datetime, timezone
import json
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import unittest
from _harness import REPO_ROOT, load_module_by_path

h=load_module_by_path('s11_long_history_core',REPO_ROOT/'examples/training_history.py')
c=load_module_by_path('s11_long_history_context',REPO_ROOT/'examples/agentic/openclaw/context_packet.py')
NOW=datetime(2026,10,23,10,tzinfo=timezone.utc)


class LongTermContext(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.profile={'schema_version':1,'data_dir':str(self.root),'protocol':str(self.root/'p.md'),'workout_reference':str(self.root/'w.md'),'reports_dir':str(self.root),'dossier':str(self.root/'d.md'),'dossier_sections':{t:[] for t in c.TASKS},'timezone':'Europe/Zurich','source_timezone':'Europe/Zurich','long_term_source':str(self.root/'summary.json')}
        activities=[{'id':str(n),'start_date_local':f'2026-{n:02d}-08T10:00:00','type':'VirtualRide','moving_time':3600,'icu_training_load':40} for n in range(1,11)]
        self.a,self.w=h.facts(activities,[])
        self.value=h.summarize(self.a,self.w,'2023-10-24','2026-10-23',NOW.isoformat())
        self.value['generation']='synthetic-generation';h.atomic_json(self.root/'summary.json',self.value)
        (self.root/'profile.json').write_text(json.dumps(self.profile))

    def test_small_view_six_closed_plus_current_separately_labelled(self):
        value=c.long_term(self.profile,NOW)
        self.assertEqual([r['month'] for r in value['rows']],['2026-04','2026-05','2026-06','2026-07','2026-08','2026-09','2026-10'])
        self.assertEqual(value['omitted_older_months'],3)
        self.assertLessEqual(len(c.encode(value,8192).encode()),8192)
        self.assertTrue(value['rows'][-1]['coverage']['partial'])
        self.assertFalse(value['stale']);self.assertEqual(value['reviews']['status'],'unavailable')

    def test_monthly_whole_rows_and_boundaries(self):
        value=c.history_months(self.profile,date(2026,4,15),date(2026,5,10),NOW)
        self.assertEqual([r['month'] for r in value['rows']],['2026-04','2026-05'])
        self.assertEqual(value['rows'][0],self.value['monthly'][3])
        with self.assertRaises(c.PacketError):c.history_months(self.profile,date(2020,1,1),date(2026,1,1))

    def test_unavailable_is_not_zero(self):
        p=dict(self.profile);p.pop('long_term_source')
        self.assertEqual(c.long_term(p,NOW)['status'],'unavailable')

    def test_staleness_and_failure_preserve_provenance(self):
        self.value['generated_at']='2026-10-01T10:00:00+00:00';h.atomic_json(self.root/'summary.json',self.value)
        h.atomic_json(self.root/'status.json',{'success':False,'error':'refresh_failed_last_good_summary_retained'})
        value=c.long_term(self.profile,NOW)
        self.assertTrue(value['stale']);self.assertFalse(value['refresh_status']['success'])
        self.assertEqual(len(value['rows']),7)

    def test_duplicate_months_fail_closed(self):
        self.value['monthly'].append(self.value['monthly'][0]);h.atomic_json(self.root/'summary.json',self.value)
        with self.assertRaises(c.PacketError):c.long_term(self.profile,NOW)

    def test_no_clipping_on_oversize(self):
        self.value['policy']='synthetic '*2000;h.atomic_json(self.root/'summary.json',self.value)
        with self.assertRaises(c.PacketError):c.encode(c.long_term(self.profile,NOW),8192)

    def test_exact_activity_identity_and_generation_guard(self):
        db=sqlite3.connect(self.root/'facts.sqlite3')
        db.execute('CREATE TABLE metadata(key TEXT,value TEXT)');db.execute('INSERT INTO metadata VALUES(?,?)',('generation',json.dumps('synthetic-generation')))
        db.execute('CREATE TABLE facts(kind TEXT,id TEXT,body TEXT)');db.execute('INSERT INTO facts VALUES(?,?,?)',('activity','1',json.dumps(self.a[0])));db.commit();db.close()
        self.assertEqual(c.history_detail(self.profile,'1')['activity']['id'],'1')
        self.assertEqual(c.history_detail(self.profile,'missing')['status'],'not_found')
        self.value['generation']='other';h.atomic_json(self.root/'summary.json',self.value)
        with self.assertRaises(c.PacketError):c.history_detail(self.profile,'1')

    def reviews(self):
        path=self.root/'coaching_plan.sqlite3';self.profile['review_store']=str(path)
        db=sqlite3.connect(path);db.execute('PRAGMA user_version=1');db.execute('CREATE TABLE journal(seq INTEGER,kind TEXT,at TEXT,body TEXT)');db.execute('CREATE TABLE revisions(id TEXT,body TEXT)')
        db.execute('INSERT INTO revisions VALUES(?,?)',('parent',json.dumps({'plan':{'block':{'objective':'Sustainable endurance','starting_evidence':['activity-1']}}})))
        for n in range(1,5):
            event={'review_id':f'review-{n}','parent_revision':'parent','result_revision':'result','source':{'period':{'start':'2026-10-01','end':'2026-10-23'}},'result':{'report':{'observations':[{'activity_id':'activity-1','goal_attainment':'met','response':'tolerated'}],'decisions':[{'action':'maintain','reason':'tolerated','next_observation':'fatigue tomorrow'}],'unresolved_questions':[],'evidence_scope':'Sourced assessment'}}}
            db.execute('INSERT INTO journal VALUES(?,?,?,?)',(n,'reviewed',NOW.isoformat(),json.dumps(event)))
        db.commit();db.close()

    def test_reviews_keep_causal_record_and_exact_old_reference(self):
        self.reviews();reviews=c.review_history(self.profile)
        self.assertEqual([r['review_id'] for r in reviews['rows']],['review-3','review-4'])
        row=c.review_history(self.profile,'review-1')['rows'][0]
        self.assertEqual(row['objective'],'Sustainable endurance');self.assertEqual(row['decisions'][0]['next_observation'],'fatigue tomorrow')
        index=c.long_term(self.profile,NOW)['reviews']['rows'][0]
        self.assertNotIn('observations',index);self.assertEqual(index['review_id'],'review-3')

    def test_optional_paths_validated_without_breaking_old_profiles(self):
        self.assertEqual(c.load_profile(self.root/'profile.json'),self.profile)
        self.profile['long_term_source']='relative';(self.root/'profile.json').write_text(json.dumps(self.profile))
        with self.assertRaises(c.PacketError):c.load_profile(self.root/'profile.json')

    def test_real_cli_outputs_complete_json(self):
        result=subprocess.run(['python3',str(REPO_ROOT/'examples/agentic/openclaw/context_packet.py'),'--profile',str(self.root/'profile.json'),'long_term'],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout);self.assertTrue(json.loads(result.stdout)['packet_complete'])
        self.assertLessEqual(len(result.stdout.encode()),8193)


if __name__=='__main__':unittest.main()
