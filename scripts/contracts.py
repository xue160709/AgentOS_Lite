#!/usr/bin/env python3
"""Shared context hashes, output contracts and read-only Codex command construction."""
import json
from pathlib import Path
from lite import ROOT, digest


def context_hash(directory):
    files = sorted(Path(directory).glob('*.md'))
    if not files:
        raise ValueError('Context directory has no Markdown')
    hashes = {p.name: digest(p.read_bytes()) for p in files}
    return digest(json.dumps(hashes, sort_keys=True)), hashes


def schema_for(mode):
    def obj(props):
        return {'type': 'object', 'additionalProperties': False, 'properties': props, 'required': list(props)}
    string = {'type': 'string'}
    if mode == 'filter':
        row = obj({'id': string, 'decision': {'type': 'string', 'enum': ['keep', 'exclude', 'pending']},
                   'reason': string, 'evidence': string, 'limitations': string})
        return obj({'context_sha256': string, 'decisions': {'type': 'array', 'items': row}})
    return obj({'context_sha256': string, 'used_ids': {'type': 'array', 'items': string},
                'markdown': string, 'limitations': {'type': 'array', 'items': string}})


def validate_filter(result, snapshot, ctx):
    if result['context_sha256'] != ctx:
        raise ValueError('Context hash mismatch')
    expected = {x['id']: x for x in snapshot['materials']}
    ids = [x['id'] for x in result['decisions']]
    if len(ids) != len(set(ids)) or set(ids) != set(expected):
        raise ValueError('Decisions must cover each material exactly once')
    for row in result['decisions']:
        material = expected[row['id']]
        source = material['body'] or material['title']
        if not row['evidence'] or row['evidence'] not in source or len(row['evidence']) > 200:
            raise ValueError('Evidence must be a short exact source substring: ' + row['id'])
        if row['decision'] not in ('keep', 'exclude', 'pending') or not row['reason']:
            raise ValueError('Invalid decision')
        if not material['body'] and row['decision'] != 'pending':
            raise ValueError('No body: must remain pending in this teaching workflow')


def validate_daily(result, snapshot, selection, ctx):
    validate_filter(selection, snapshot, ctx)
    if result['context_sha256'] != ctx:
        raise ValueError('Context hash mismatch: rerun filter after changing context')
    keep = {x['id'] for x in selection['decisions'] if x['decision'] == 'keep'}
    used = result['used_ids']
    if len(used) != len(set(used)) or not set(used) <= keep:
        raise ValueError('Report can only use unique keep IDs')
    text = result['markdown']
    for m in snapshot['materials']:
        if m['id'] in used and (m['url'] not in text or m['id'] not in text):
            raise ValueError('Missing original link or material ID')
        if m['id'] not in used and m['id'] in text and m['id'] in keep:
            raise ValueError('Reported keep material missing from used_ids')
    if not text.strip():
        raise ValueError('Empty report')


def trace_reads(events_path, skill_path, context_dir):
    outputs = []
    commands = []
    for line in Path(events_path).read_text().splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        item = event.get('item', {})
        if event.get('type') == 'item.completed' and item.get('type') == 'command_execution':
            outputs.append(item.get('aggregated_output', ''))
            commands.append({'id': item.get('id'), 'command': item.get('command'), 'exit_code': item.get('exit_code')})
    observed = '\n'.join(outputs)
    if Path(skill_path).read_text().strip() not in observed:
        raise ValueError('Skill content not observed in completed CLI file-read output')
    files = sorted(Path(context_dir).glob('*.md'))
    missing = [f.name for f in files if f.read_text().strip() not in observed]
    if missing:
        raise ValueError('Context contents not observed in CLI output: ' + ', '.join(missing))
    return {'skill_content_observed': True, 'context_contents_observed': [f.name for f in files],
            'completed_read_commands': commands}


def validate_selection_binding(selection_path, input_path):
    selection_path, input_path = Path(selection_path), Path(input_path)
    receipt = json.loads((selection_path.parent / 'receipt.json').read_text())
    if receipt.get('status') != 'validated' or receipt.get('input_sha256') != digest(input_path.read_bytes()):
        raise ValueError('Selection receipt does not bind to this exact input snapshot')
    if not receipt.get('model_sha256') or receipt['model_sha256'] != digest(selection_path.read_bytes()):
        raise ValueError('Selection file changed after validation')


def build_codex_command(schema_path, final, prompt, model=None, reasoning_effort=None):
    command = ['codex', 'exec', '-C', str(ROOT), '--sandbox', 'read-only', '--json',
               '--output-schema', str(schema_path), '-o', str(final)]
    if model:
        command.extend(['--model', model])
    if reasoning_effort:
        command.extend(['-c', f'model_reasoning_effort="{reasoning_effort}"'])
    return command + [prompt]
