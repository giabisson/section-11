"""Account-bound settings and checked catalog projection for power prescriptions.

One fixed Intervals.icu GET; no calendar writes, model calls or raw credential/API
bodies in output. Configured FTP/zones are settings, not measured fitness/clearance.
"""
from datetime import datetime, timezone
from decimal import Decimal
import importlib.util
import json
import math
from pathlib import Path
import re
import sys
import time


def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec);sys.modules[name]=value;spec.loader.exec_module(value)
    return value


def positive(value):
    return type(value) in (int,float) and math.isfinite(value) and value>0


def project(settings,athlete,environment,templates,catalog,now):
    sport='VirtualRide' if environment=='indoor' else 'Ride'
    if (not isinstance(settings,dict) or type(settings.get('id')) is not int or settings['id']<=0 or sport not in (settings.get('types') or [])
            or str(settings.get('athlete_id','')).removeprefix('i')!=athlete.removeprefix('i')):
        raise ValueError('sport_settings_account_or_type_mismatch')
    field='indoor_ftp' if environment=='indoor' and positive(settings.get('indoor_ftp')) else 'ftp'
    ftp=settings.get(field);raw=settings.get('power_zones')
    if not positive(ftp) or not isinstance(raw,list) or not 1<=len(raw)<=7:
        raise ValueError('configured_ftp_and_zone_upper_bounds_required')
    if any(not positive(v) for v in raw) or any(a>=b for a,b in zip(raw,raw[1:])):
        raise ValueError('ordered_configured_zone_bounds_required')
    # Intervals power_zones are the configured upper limits in percent of FTP.
    # Retain exact limits; no default zone model or invented open-ended Z7 ceiling.
    bounds={};lower=0
    for i,percent in enumerate(raw,1):
        upper=float(Decimal(str(ftp))*Decimal(str(percent))/Decimal(100))
        if not math.isfinite(upper) or upper<=lower:raise ValueError('invalid_converted_zone_bounds')
        bounds[str(i)]=[lower,upper];lower=upper
    return {'status':'available','retrieved_at':now.isoformat(),'environment':environment,
            'settings_source':{'service':'Intervals.icu','sport':sport,'settings_id':settings.get('id'),
                'selected_ftp_field':field,'power_zone_units':'percent_upper_limits_of_selected_configured_ftp',
                'configured_power_zones_percent':raw,'setting_is_not_a_fitness_test':True},
            'fitness_reference':{'metric':'ftp','value_watts':ftp,'date':None,'method':None,
                'equipment':None,'environment':'unknown','status':'uncertain','zone_bounds_watts':bounds,
                'source':'Current Intervals.icu '+sport+' sport settings; '+field+'; assessment provenance unavailable'},
            'checked_templates':{key:{'template_version':catalog['library_version'],'constraints':catalog['templates'][key]} for key in templates},
            'catalog_provenance':{k:catalog[k] for k in ('library_version','library_sha256','constraints_sha256')},
            'prescription_contract':{'schema_version':1,
                'required':['session_template','template_version','available_minutes','fitness_reference','steps'],
                'step_required':['role','seconds','target'],
                'continuous_main_role':'work, even for steady Z1/Z2 endurance; endurance is background in complex templates',
                'labels':'Optional words only; no digits or executable ramp/freeride keywords',
                'power_target':{'basis':'watts','low':'actual prescribed watts','zones':'configured contiguous zone numbers'},
                'do_not_supply_native_description':'The compiler derives description/duration. If supplied they must agree exactly.'},
            'scope':'Arithmetic conversion of actual configured zone limits, not physiological threshold validation. Unknown assessment provenance remains unknown; indoor_ftp does not prove indoor testing. Recheck current health/readiness and actual availability before prescription. The normal compiler and calendar preview/approval gates remain required.',
            'calendar_writes':0,'model_calls':0}


def read(profile,environment,templates,now=None,fetcher=None):
    if environment not in ('indoor','outdoor') or not isinstance(templates,list) or not 1<=len(templates)<=6 or len(set(templates))!=len(templates):
        raise ValueError('explicit_environment_and_one_to_six_templates_required')
    if any(not isinstance(t,str) or not re.fullmatch(r'[A-Z0-9]+-[A-Z0-9]+',t) for t in templates):
        raise ValueError('invalid_template_identifier')
    helper=module(Path(__file__).with_name('activity_analysis.py'),'s11_workout_inputs_private')
    coaching=helper.private_json(profile['coaching_profile'])
    if Path(coaching['data_dir']).resolve()!=Path(profile['data_dir']).resolve():raise ValueError('source_profile_mismatch')
    config=helper.private_json(Path(profile['data_dir'])/'.sync_config.json')
    athlete=str(config.get('athlete_id',''))
    if not re.fullmatch(r'i?[1-9][0-9]*',athlete):raise ValueError('explicit_account_required')
    if profile.get('intake_athlete_id',athlete)!=athlete:raise ValueError('source_account_mismatch')
    compiler=module(Path(coaching['install_root'])/'examples/agentic/workout_validation.py','s11_workout_inputs_compiler')
    checked=compiler.catalog()
    if any(t not in checked['templates'] for t in templates):raise ValueError('unknown_checked_template')
    sport='VirtualRide' if environment=='indoor' else 'Ride'
    path='/athlete/'+athlete+'/sport-settings/'+sport
    if fetcher:settings=fetcher(path)
    else:
        client=helper.Fetch(('API_KEY',config['intervals_key']))
        client.deadline=time.monotonic()+11
        try:settings=client.get(path)
        finally:client.session.close()
    if len(json.dumps(settings).encode())>65536:raise ValueError('settings_response_too_large')
    return project(settings,athlete,environment,templates,checked,now or datetime.now(timezone.utc))
