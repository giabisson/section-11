#!/usr/bin/env python3
"""Bounded, account-owned historical block analysis. GET only; private result cache.

No raw stream arrays, credential values, source prose or arbitrary model paths are
returned. Reuses sync's analyzer directly, outside its normal 14-day retention gate.
"""
import copy
from datetime import datetime, timezone
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import sys
import tempfile
import time

MAX_RESPONSE = 16_000_000
MAX_TOTAL = 32_000_000
MAX_RESULT = 7800
CACHE_SECONDS = 6*3600
MAX_CACHE_FILES = 64


class AnalysisError(ValueError):
    pass


def canonical(v):
    return json.dumps(v, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(v):
    return hashlib.sha256(canonical(v).encode()).hexdigest()


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec); sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


def private_json(path, maximum=65536):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd) as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_mode & 0o077 or info.st_size > maximum):
            raise AnalysisError('invalid_private_file')
        raw = stream.read(maximum+1)
        if len(raw.encode()) > maximum: raise AnalysisError('private_file_too_large')
        return json.loads(raw)


def load_profile(path):
    p = private_json(path)
    fields = {'schema_version','install_root','data_dir','state_dir','facts_store','athlete_id'}
    if not isinstance(p,dict) or set(p) != fields or p['schema_version'] != 1:
        raise AnalysisError('invalid_analysis_profile')
    for k in fields-{'schema_version','athlete_id'}:
        if not isinstance(p[k],str) or not Path(p[k]).is_absolute():
            raise AnalysisError('absolute_analysis_paths_required')
    if not isinstance(p['athlete_id'],str) or not re.fullmatch(r'i?[1-9][0-9]*',p['athlete_id']):
        raise AnalysisError('invalid_analysis_account')
    return p


def known_activity(p, aid):
    """Do not use arbitrary IDs to query other athletes' shared activities."""
    path = Path(p['facts_store'])
    if path.is_file() and not path.is_symlink():
        with sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True) as db:
            if db.execute('SELECT 1 FROM facts WHERE kind=? AND id=?',('activity',aid)).fetchone():
                return True
    latest = Path(p['data_dir'])/'latest.json'
    if latest.is_file() and latest.stat().st_size <= 8_000_000:
        value = json.loads(latest.read_text())
        return any(str(a.get('id')) == aid for a in value.get('recent_activities',[]))
    return False


class Fetch:
    """At most four GETs, fixed host/paths, no redirects, retries or provider text."""
    def __init__(self, auth):
        import requests
        self.requests = requests
        self.session = requests.Session(); self.session.auth = auth
        self.deadline = time.monotonic()+48
        self.calls = 0; self.bytes = 0

    def get(self, path, params=None):
        self.calls += 1
        remaining = self.deadline-time.monotonic()
        if self.calls > 4 or remaining <= 0: raise AnalysisError('fetch_budget_exceeded')
        try:
            with self.session.get('https://intervals.icu/api/v1'+path,params=params,
                    timeout=(2,min(8,remaining)),allow_redirects=False,stream=True) as response:
                status = response.status_code
                if status != 200:
                    code = {401:'authentication_failed',403:'access_denied',404:'not_found',
                            429:'rate_limited'}.get(status,'upstream_unavailable')
                    if 300 <= status < 400: code = 'redirect_rejected'
                    raise AnalysisError(code)
                chunks=[]; size=0
                for chunk in response.iter_content(65536):
                    size += len(chunk); self.bytes += len(chunk)
                    if size > MAX_RESPONSE or self.bytes > MAX_TOTAL:
                        raise AnalysisError('response_too_large')
                    if time.monotonic() > self.deadline: raise AnalysisError('fetch_budget_exceeded')
                    chunks.append(chunk)
                return json.loads(b''.join(chunks))
        except self.requests.exceptions.Timeout:
            raise AnalysisError('upstream_timeout') from None
        except self.requests.exceptions.RequestException:
            raise AnalysisError('network_unavailable') from None
        except (json.JSONDecodeError,UnicodeDecodeError):
            raise AnalysisError('invalid_upstream_json') from None


def measurement(row):
    keys=('start_s','end_s','mean_power_w','work_kj','mean_hr_bpm','mean_cadence_rpm',
          'power_coverage_pct','hr_coverage_pct','cadence_coverage_pct','zero_power_pct')
    return dict(zip(keys,row)) if isinstance(row,list) and len(row)==10 else None


def compact(act, event, structure, planned_steps):
    steps=[]
    for i,s in enumerate(structure.get('steps',[])):
        step={k:s[k] for k in ('duration_s','target_w','repeat','match','observed_window_fraction','ramp_rmse_w') if k in s}
        # Successful analyzer rows compress duration into their measured windows.
        # Recover intended duration from normalized intent, never from execution.
        if i < len(planned_steps) and 'duration_s' in planned_steps[i]:
            step['planned_duration_s']=planned_steps[i]['duration_s']
        step.update(step_index=i,actual=measurement(s.get('actual')))
        steps.append(step)
    return {'activity':{k:act.get(k) for k in ('id','start_date_local','type','trainer',
                    'device_name','moving_time','elapsed_time','icu_ftp','average_temp')},
            'paired_event_id':event.get('id') if event else None,
            'analysis':{'version':structure['version'],'method':structure['method'],
                'status':structure['status'],'issues':structure.get('issues',[]),
                'offset_s':structure.get('offset_s',0),'steps':steps,
                'thirds':[measurement(x) for x in structure.get('thirds',[])],
                'efforts':structure.get('efforts',[]),
                'omitted_steps':structure.get('omitted_steps',0)},
            'interpretation_limits':[
                'Plan-window agreement is not formal adherence, goal attainment or health clearance.',
                'Step indices are prescription order, not inferred warm-up/main/recovery roles.',
                'Actual windows exclude transition samples; start/end are elapsed seconds, not stream indices.',
                'Missing HR/coverage remains unknown. Compare observed power, duration and context; no automatic fitness or surgery attribution.'
            ]}


def write_cache(path, value):
    fd,name=tempfile.mkstemp(prefix='.analysis-',dir=path.parent)
    try:
        with os.fdopen(fd,'w') as stream:
            stream.write(canonical(value)); stream.flush(); os.fsync(stream.fileno())
        os.replace(name,path)
    finally:
        if os.path.exists(name): os.unlink(name)
    files=sorted(path.parent.glob('*-i[0-9]*.json'),key=lambda x:x.stat().st_mtime,reverse=True)
    for old in files[MAX_CACHE_FILES:]:
        if old.is_file() and not old.is_symlink(): old.unlink()


def analyze(p, aid, fetch_factory=Fetch, now=None):
    now=now or datetime.now(timezone.utc)
    if not isinstance(aid,str) or not re.fullmatch(r'i[1-9][0-9]{0,17}',aid):
        return {'status':'unavailable','error_code':'invalid_activity_id'}
    client=None
    try:
        if not known_activity(p,aid): raise AnalysisError('activity_not_in_account_history')
        root=Path(p['install_root'])
        pull=module(root/'examples/agentic/pull.py','s11_analysis_pull')
        try: athlete,key=pull._load_credentials(type('Args',(),{'credentials_dir':p['data_dir']})())
        except ValueError: raise AnalysisError('credentials_unavailable') from None
        if athlete != p['athlete_id']: raise AnalysisError('credential_account_mismatch')
        folder=Path(p['state_dir']); folder.mkdir(parents=True,mode=0o700,exist_ok=True)
        info=folder.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode&0o077:
            raise AnalysisError('invalid_private_cache_directory')
        fd=os.open(folder/'.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW|os.O_NONBLOCK,0o600)
        with os.fdopen(fd,'w') as lock:
            try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError: raise AnalysisError('analysis_busy_retry_later') from None
            client=fetch_factory(('API_KEY',key))
            act=client.get('/activity/'+aid)
            if not isinstance(act,dict) or str(act.get('id'))!=aid: raise AnalysisError('activity_identity_mismatch')
            paired=act.get('paired_event_id'); event=None; reason=None
            if paired is not None:
                if not re.fullmatch(r'[0-9]{1,18}',str(paired)): raise AnalysisError('invalid_paired_event_id')
                try: event=client.get(f'/athlete/{athlete}/events/{paired}',{'resolve':'true'})
                except AnalysisError as exc:
                    if str(exc)!='not_found': raise
                    reason='paired_event_unavailable'
                if event is not None and (not isinstance(event,dict) or str(event.get('id'))!=str(paired)):
                    raise AnalysisError('paired_event_identity_mismatch')
            intervals=client.get('/activity/'+aid+'/intervals')
            if not isinstance(intervals,dict) or not isinstance(intervals.get('icu_intervals'),list):
                raise AnalysisError('invalid_intervals_response')
            analyzer_sha=hashlib.sha256((root/'examples/sync.py').read_bytes()).hexdigest()
            fingerprint=digest([act,event,intervals,analyzer_sha,hashlib.sha256(Path(__file__).read_bytes()).hexdigest()])
            path=folder/(athlete+'-'+aid+'.json'); cached=None
            if path.exists():
                cached=private_json(path,65536)
            if (isinstance(cached,dict) and cached.get('fingerprint')==fingerprint
                    and 0 <= now.timestamp()-cached.get('computed_epoch',0) < CACHE_SECONDS):
                result=copy.deepcopy(cached['result']); result['provenance'].update(
                    revalidated_at=now.isoformat(),streams_reused=True,api_gets=client.calls)
                return result
            payload=client.get('/activity/'+aid+'/streams.json',{'types':'time,watts,heartrate,cadence'})
            if not isinstance(payload,list): raise AnalysisError('invalid_streams_response')
            streams={}
            for s in payload:
                if not isinstance(s,dict) or s.get('type') not in ('time','watts','heartrate','cadence'):
                    raise AnalysisError('invalid_streams_response')
                kind=s['type']; values=s.get('data')
                if kind in streams or not isinstance(values,list) or len(values)>100000:
                    raise AnalysisError('invalid_streams_response')
                streams[kind]=values
            sync=module(root/'examples/sync.py','s11_historical_analysis_sync')
            engine=object.__new__(sync.IntervalsSync)
            structure=engine._build_session_structure(act,event,streams,intervals['icu_intervals'],reason)
            if structure is None: raise AnalysisError('activity_type_not_supported')
            planned_steps=engine._structure_plan(act,event).get('steps',[])
            result={'status':'available',**compact(act,event,structure,planned_steps),
                'provenance':{'computed_at':now.isoformat(),'revalidated_at':now.isoformat(),
                    'streams_reused':False,'api_gets':client.calls,'source_fingerprint':fingerprint,
                    'stream_fingerprint':digest(streams),'analyzer_sha256':analyzer_sha,
                    'stream_cache_max_age_s':CACHE_SECONDS,'cache_saved':True},'api_writes':0}
            if len(canonical(result).encode())>MAX_RESULT: raise AnalysisError('analysis_result_size_limit')
            write_cache(path,{'fingerprint':fingerprint,'computed_epoch':now.timestamp(),'result':result})
            return result
    except AnalysisError as exc:
        return {'status':'unavailable','activity_id':aid,'error_code':str(exc),
                'api_gets':client.calls if client else 0,'api_writes':0,
                'scope':'Retrieval/analysis failed; this does not establish missing workout data. Cached results were not substituted.'}
    except Exception:
        return {'status':'unavailable','activity_id':aid,'error_code':'analysis_source_unavailable_or_invalid','api_writes':0}
