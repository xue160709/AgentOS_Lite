#!/usr/bin/env python3
"""Run code collection, scoring Skill, then writing Skill. --preview makes no requests."""
import argparse
from datetime import datetime
import os
from pathlib import Path
import shlex
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def build_plan(output, model=None, engine=None, home=None):
    output = Path(output).resolve()
    collect = [sys.executable, str(ROOT / 'scripts/collect.py'), '--home', str(home or ROOT / 'data/daily'),
               '--out', str(output / 'input.json')]
    generate = [sys.executable, str(ROOT / 'scripts/generate.py'), '--input', str(output / 'input.json'),
                '--selection', str(output / 'filter/model.json'),
                '--out', str(output / 'daily')]
    filtering = [sys.executable, str(ROOT / 'scripts/filter.py'), '--input', str(output / 'input.json'),
                 '--out', str(output / 'filter')]
    if engine:
        generate += ['--engine', engine]
        filtering += ['--engine', engine]
    if model:
        generate += ['--model', model]
        filtering += ['--model', model]
    return [collect, filtering, generate]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preview', action='store_true')
    parser.add_argument('--engine', choices=['claude','codex'])
    parser.add_argument('--model')
    parser.add_argument('--home', default=str(ROOT / 'data/daily'))
    args = parser.parse_args()
    output = ROOT / 'reports' / datetime.now().strftime('%Y-%m-%d_%H-%M-%S_%f')
    plan = build_plan(output,args.model,args.engine,args.home)
    if args.preview:
        for command in plan:
            print(subprocess.list2cmdline(command) if os.name == 'nt' else shlex.join(command))
        return 0
    output.mkdir(parents=True,exist_ok=False)
    with (output / 'job.log').open('w',encoding='utf-8') as log:
        collected = subprocess.run(plan[0],cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
        if collected.returncode not in (0,2):
            print(f'Collection failed; see {output / "job.log"}',file=sys.stderr)
            return collected.returncode
        filtered = subprocess.run(plan[1],cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
        if filtered.returncode:
            print(f'Scoring failed; see {output / "job.log"}',file=sys.stderr)
            return filtered.returncode
        generated = subprocess.run(plan[2],cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
        if generated.returncode:
            print(f'Generation failed; see {output / "job.log"}',file=sys.stderr)
            return generated.returncode
    print(f'Report: {output / "daily/daily.md"}')
    if collected.returncode == 2:
        print('Report generated with collection gaps; inspect input.json and report.',file=sys.stderr)
    return collected.returncode


if __name__ == '__main__':
    sys.exit(main())
