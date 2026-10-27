#!/usr/bin/env python3
"""Prepare a macOS LaunchAgent. Install only when explicitly passed --install."""
import argparse
from datetime import datetime
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
LABEL = 'local.agentos-lite.daily'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--at', default='08:00', help='Daily local time, HH:MM')
    parser.add_argument('--install', action='store_true', help='Actually register the prepared task; no immediate run')
    args = parser.parse_args()
    try:
        when = datetime.strptime(args.at, '%H:%M')
    except ValueError:
        parser.error('--at must be a local time such as 08:00')
    output = ROOT / 'outputs/schedule' / (LABEL + '.plist')
    logs = ROOT / 'reports'
    output.parent.mkdir(parents=True, exist_ok=True)
    logs.mkdir(parents=True, exist_ok=True)
    config = {
        'Label': LABEL,
        'ProgramArguments': [sys.executable, str(ROOT / 'scripts/daily.py')],
        'WorkingDirectory': str(ROOT),
        'EnvironmentVariables': {'PATH': os.environ.get('PATH', '/usr/bin:/bin')},
        'StartCalendarInterval': {'Hour': when.hour, 'Minute': when.minute},
        'RunAtLoad': False,
        'StandardOutPath': str(logs / 'schedule.stdout.log'),
        'StandardErrorPath': str(logs / 'schedule.stderr.log'),
    }
    with output.open('wb') as stream:
        plistlib.dump(config, stream)
    print(f'Prepared: {output}')
    if args.install:
        target = Path.home() / 'Library/LaunchAgents' / output.name
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            raise FileExistsError(f'Task file already exists; inspect it before replacing: {target}')
        shutil.copyfile(output, target)
        subprocess.run(['launchctl', 'bootstrap', f'gui/{os.getuid()}', str(target)], check=True)
        print(f'Installed {LABEL}; next scheduled time {args.at}. No immediate run requested.')
    else:
        print('Not installed. Add --install only when you want to enable the task.')


if __name__ == '__main__':
    main()
