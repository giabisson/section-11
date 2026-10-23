"""Private, versioned athlete intake independent of a prescription or today's feedback.

Statements are caller-attested, not independently authenticated Telegram evidence.
No API, calendar, model, dossier write or memory-index operation occurs here.
"""
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import stat

KINDS = {'goal','availability','equipment','experience','preference','recovery_constraint','health_observation','follow_up'}
FIELDS = {'key','kind','text','observed_on','source','valid_from','valid_until','review_on'}
MAX_BYTES = 16000


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)


def day(value):
    if not isinstance(value,str) or date.fromisoformat(value).isoformat()!=value:
        raise ValueError('intake_date_required')
    return value


def text(value,limit=2000):
    if not isinstance(value,str) or not value.strip() or len(value)>limit:
        raise ValueError('bounded_intake_text_required')


def validate(payload,today):
    if not isinstance(payload,dict) or set(payload)!={'request_id','parent_revision','entries','open_questions'}:
        raise ValueError('invalid_intake_fields')
    if not isinstance(payload['request_id'],str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',payload['request_id']):
        raise ValueError('invalid_intake_request_id')
    parent=payload['parent_revision']
    if parent is not None and (not isinstance(parent,str) or not re.fullmatch(r'intake-[a-f0-9]{40}',parent)):
        raise ValueError('invalid_intake_parent')
    rows=payload['entries'];seen=set()
    if not isinstance(rows,list) or not 1<=len(rows)<=40:raise ValueError('intake_entries_required')
    for row in rows:
        if not isinstance(row,dict) or set(row)!=FIELDS:raise ValueError('invalid_intake_entry')
        key=row['key']
        if not isinstance(key,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',key) or key in seen:
            raise ValueError('unique_intake_key_required')
        seen.add(key)
        if row['kind'] not in KINDS:raise ValueError('invalid_intake_kind')
        text(row['text']);text(row['source'],500)
        observed=day(row['observed_on'])
        if observed>today:raise ValueError('future_intake_observation')
        for field in ('valid_from','valid_until','review_on'):
            if row[field] is not None:day(row[field])
        if row['valid_from'] and row['valid_until'] and row['valid_from']>row['valid_until']:
            raise ValueError('invalid_intake_period')
        if row['kind']=='health_observation' and row['valid_until']!=observed:
            raise ValueError('health_observation_must_expire_on_observation_date')
        if row['kind'] in {'goal','availability','recovery_constraint','follow_up'} and row['review_on'] is None:
            raise ValueError('dated_intake_requires_review_date')
    questions=payload['open_questions']
    if not isinstance(questions,list) or len(questions)>12:raise ValueError('bounded_intake_questions_required')
    for question in questions:text(question,500)
    if len(canonical(payload).encode())>MAX_BYTES:raise ValueError('intake_size_limit')


def connect(path,create=False):
    path=Path(path)
    if not path.is_absolute() or path.is_symlink():raise ValueError('ordinary_absolute_intake_path_required')
    parent=path.parent
    if parent.is_symlink() or parent.stat().st_uid!=os.getuid() or parent.stat().st_mode&0o077:
        raise ValueError('private_owned_intake_directory_required')
    if not path.exists():
        if not create:return None
        fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600);os.close(fd)
    info=path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode&0o077:
        raise ValueError('private_owned_intake_file_required')
    db=sqlite3.connect(path if create else path.as_uri()+'?mode=ro',uri=not create,timeout=2)
    if create:
        db.execute('PRAGMA journal_mode=DELETE')
        db.execute('CREATE TABLE IF NOT EXISTS intake_revisions (sequence INTEGER PRIMARY KEY AUTOINCREMENT, revision_id TEXT UNIQUE, request_id TEXT UNIQUE, athlete_id TEXT, request_sha256 TEXT, saved_on TEXT, body TEXT)')
        db.commit()
    return db


def read(path,athlete_id,today):
    day(today);db=connect(path)
    if db is None:return {'status':'unavailable','reason':'intake_not_saved','entries':[]}
    try:
        row=db.execute('SELECT revision_id,athlete_id,saved_on,body FROM intake_revisions ORDER BY sequence DESC LIMIT 1').fetchone()
        if row is None:return {'status':'unavailable','reason':'intake_not_saved','entries':[]}
        revision,owner,saved_on,raw=row
        if owner!=athlete_id:raise ValueError('intake_account_mismatch')
        value=json.loads(raw);entries=[]
        for item in value['entries']:
            status=('historical' if item['valid_until'] and today>item['valid_until'] else
                    'not_started' if item['valid_from'] and today<item['valid_from'] else 'current')
            entries.append({**item,'temporal_status':status,'review_due':bool(item['review_on'] and today>=item['review_on']),
                            'current_health_clearance':False})
        kinds={e['kind'] for e in entries if e['temporal_status']!='historical'}
        missing=sorted({'goal','availability','equipment','experience'}-kinds)
        return {'status':'available','revision_id':revision,'athlete_id':owner,'saved_on':saved_on,'as_of':today,
                'entries':entries,'open_questions':value['open_questions'],'missing_core_categories':missing,
                'scope':'Durable athlete-reported intake, not current readiness or medical clearance. Historical/review-due restrictions do not establish recovery. Recheck current health before training. No plan or calendar publication is implied.'}
    finally:db.close()


def save(path,athlete_id,payload,today):
    day(today);validate(payload,today)
    if not re.fullmatch(r'i?[0-9]+',athlete_id) or athlete_id in ('0','i0'):raise ValueError('explicit_intake_account_required')
    content=canonical(payload);fingerprint=hashlib.sha256(content.encode()).hexdigest()
    revision='intake-'+hashlib.sha256((athlete_id+'\n'+content).encode()).hexdigest()[:40]
    db=connect(path,create=True)
    try:
        db.execute('BEGIN IMMEDIATE')
        old=db.execute('SELECT athlete_id,request_sha256,revision_id FROM intake_revisions WHERE request_id=?',(payload['request_id'],)).fetchone()
        if old:
            if old[:2]!=(athlete_id,fingerprint):raise ValueError('intake_request_id_conflict')
            db.rollback();return {'success':True,'revision_id':old[2],'unchanged':True,'saved_entries':len(payload['entries']),'calendar_writes':0}
        current=db.execute('SELECT revision_id,athlete_id FROM intake_revisions ORDER BY sequence DESC LIMIT 1').fetchone()
        if current and current[1]!=athlete_id:raise ValueError('intake_account_mismatch')
        if payload['parent_revision']!=(current[0] if current else None):raise ValueError('intake_parent_changed_reload_state')
        db.execute('INSERT INTO intake_revisions (revision_id,request_id,athlete_id,request_sha256,saved_on,body) VALUES (?,?,?,?,?,?)',
                   (revision,payload['request_id'],athlete_id,fingerprint,today,content))
        db.commit()
    finally:db.close()
    # A successful acknowledgement requires recovery of the same committed revision.
    view=read(path,athlete_id,today)
    if view['revision_id']!=revision:raise ValueError('intake_changed_during_readback_recover_state')
    return {'success':True,'revision_id':revision,'unchanged':False,'saved_entries':len(payload['entries']),
            'missing_core_categories':view['missing_core_categories'],'calendar_writes':0,
            'scope':'Intake committed and read back. Training plan and calendar publication remain separate.'}
