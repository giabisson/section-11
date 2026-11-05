"""Configured power settings are delivered explicitly, not invented from FTP defaults."""
import copy
from datetime import datetime,timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
from _harness import REPO_ROOT,load_module_by_path

w=load_module_by_path('s11_workout_inputs_test',REPO_ROOT/'examples/agentic/openclaw/workout_inputs.py')
NOW=datetime(2026,11,5,9,tzinfo=timezone.utc)

class WorkoutInputs(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        for name,value in [('.sync_config.json',{'athlete_id':'i123','intervals_key':'PRIVATE_CANARY'}),
                           ('coaching.json',{'data_dir':str(self.root),'install_root':str(REPO_ROOT)})]:
            p=self.root/name;p.write_text(json.dumps(value));p.chmod(0o600)
        self.profile={'data_dir':str(self.root),'coaching_profile':str(self.root/'coaching.json'),'intake_athlete_id':'i123'}
        self.settings={'athlete_id':'i123','id':42,'types':['Ride','VirtualRide'],'ftp':300,'indoor_ftp':280,
                       'power_zones':[40,70,90,105,120,150,999],'private':'PRIVATE_CANARY'}
        self.fetch=mock.Mock(return_value=self.settings)

    def read(self,environment='indoor',templates=None):
        return w.read(self.profile,environment,templates or ['AE-1','AE-2'],NOW,self.fetch)

    def test_account_owned_custom_zone_conversion_and_checked_catalog_in_one_read(self):
        result=self.read();self.fetch.assert_called_once_with('/athlete/i123/sport-settings/VirtualRide')
        ref=result['fitness_reference'];self.assertEqual(ref['value_watts'],280)
        self.assertEqual(ref['zone_bounds_watts']['1'],[0,112])
        self.assertEqual(ref['zone_bounds_watts']['2'],[112,196])
        self.assertEqual(ref['zone_bounds_watts']['7'][1],2797.2)
        self.assertEqual(ref['environment'],'unknown');self.assertIsNone(ref['date']);self.assertIsNone(ref['method'])
        self.assertEqual(ref['status'],'uncertain');self.assertNotIn('PRIVATE_CANARY',json.dumps(result))
        self.assertEqual(result['checked_templates']['AE-1']['template_version'],'0.9.0')
        self.assertEqual(result['calendar_writes'],0);self.assertLess(len(json.dumps(result).encode()),8192)

    def test_outdoor_basis_and_absent_indoor_setting_are_explicit(self):
        result=self.read('outdoor');self.assertEqual(result['fitness_reference']['value_watts'],300)
        self.assertEqual(result['settings_source']['selected_ftp_field'],'ftp')
        self.settings['indoor_ftp']=0;self.assertEqual(self.read()['settings_source']['selected_ftp_field'],'ftp')

    def test_no_invented_seventh_zone_or_default_percentages(self):
        self.settings['power_zones']=[41,72,89,106,122,151]
        result=self.read();self.assertNotIn('7',result['fitness_reference']['zone_bounds_watts'])
        self.assertEqual(result['settings_source']['configured_power_zones_percent'],self.settings['power_zones'])

    def test_ambiguous_invalid_or_wrong_account_settings_fail_closed(self):
        original=copy.deepcopy(self.settings)
        for patch in [{'athlete_id':'i999'},{'types':['Run']},{'power_zones':None},
                      {'power_zones':[55,55,75]},{'power_zones':[True,75]},
                      {'ftp':0,'indoor_ftp':None},{'power_zones':[55,float('nan')]}]:
            with self.subTest(patch=patch),self.assertRaises(ValueError):
                self.settings.clear();self.settings.update(original);self.settings.update(patch);self.read()

    def test_input_fields_and_unknown_templates_fail_before_fetch(self):
        for env,templates in [('auto',['AE-1']),('indoor',[]),('indoor',['../key']),('indoor',['AE-1']*2),('indoor',['AE-999'])]:
            with self.subTest(env=env,templates=templates),self.assertRaises(ValueError):
                w.read(self.profile,env,templates,NOW,self.fetch)
        self.fetch.assert_not_called()

    def test_changed_account_profile_is_not_a_cross_account_read(self):
        self.profile['intake_athlete_id']='i999'
        with self.assertRaises(ValueError):self.read()
        self.fetch.assert_not_called()
