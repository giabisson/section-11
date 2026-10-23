#!/usr/bin/env python3
"""Compatibility entry point for the existing primary post-workout service."""
import argparse
from pathlib import Path
import sys
import os
import subprocess

runtime=Path(__file__).resolve().parent
sys.path.insert(0,str(runtime))
from report_runner import main

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--init',action='store_true');parser.add_argument('--dry-run',action='store_true')
    args=parser.parse_args()
    if not args.init and not args.dry_run:
        # Let the existing detector timer hand work to a unit with its own deadline.
        # This avoids the old service's possibly shorter TimeoutStartSec killing a model run.
        env=os.environ.copy();env.setdefault('XDG_RUNTIME_DIR','/run/user/'+str(os.getuid()))
        env.setdefault('DBUS_SESSION_BUS_ADDRESS','unix:path='+env['XDG_RUNTIME_DIR']+'/bus')
        result=subprocess.run(['systemctl','--user','start','--no-block','section11-post-primary.service'],env=env,capture_output=True,timeout=15)
        print('{"ok":'+('true' if result.returncode==0 else 'false')+',"status":"post_scan_handoff"}')
        sys.exit(result.returncode)
    sys.argv=['report_runner','--profile',str(runtime/'report-primary.json'),'initialize' if args.init else 'scan']+(['--dry-run'] if args.dry_run else [])
    sys.exit(main())
