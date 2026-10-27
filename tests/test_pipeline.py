import json
from pathlib import Path
import sys
import tempfile
import subprocess
import unittest
from unittest import mock
import contextlib
import io

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import daily
from lite import ROOT, digest, Store, acquire, canonical, export, parse_feed, prefilter, quality
from run_skills import context_hash, validate_filter, validate_daily, validate_selection_binding, trace_reads, build_codex_command

RULES = {'include': ['sqlite'], 'exclude_hints': ['horoscope']}
BODY = json.loads((ROOT / 'fixtures/materials.json').read_text())[0]['body']


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(self.temp.name)

    def tearDown(self):
        self.store.db.close()
        self.temp.cleanup()

    def add(self, body='', scope='metadata_only', url='https://example.org/a'):
        item = {'url': url, 'title': 'A vague title', 'body': body, 'scope': scope}
        mid, fresh = self.store.item(item, 'fixture', self.store.raw(json.dumps(item)), RULES)
        return self.store.db.execute('SELECT * FROM materials WHERE id=?', (mid,)).fetchone(), fresh

    def test_incremental_dedup_and_provenance(self):
        row, fresh = self.add(BODY, 'fixture_full')
        _, fresh2 = self.add(BODY, 'fixture_full', 'https://example.org/a?utm_source=x#frag')
        self.assertTrue(fresh)
        self.assertFalse(fresh2)
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM materials').fetchone()[0], 1)
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM body_versions').fetchone()[0], 1)
        self.assertGreaterEqual(self.store.db.execute('SELECT COUNT(*) FROM observations').fetchone()[0], 1)
        self.assertTrue(self.store.cached(row))

    def test_reuse_never_calls_network(self):
        row, _ = self.add(BODY, 'fixture_full')
        def forbidden(url):
            self.fail('Network must not be called on valid cache')
        self.assertEqual(acquire(self.store, row, [('jina', forbidden), ('crawl4ai', forbidden)]), 'reused')

    def test_jina_success_stops_before_crawl(self):
        row, _ = self.add()
        called = []
        def jina(url):
            called.append('jina'); return 'Title: A\nMarkdown Content:\n' + BODY
        def browser(url):
            self.fail('Success must stop fallback')
        self.assertEqual(acquire(self.store, row, [('jina', jina), ('crawl4ai', browser)]), 'succeeded')
        self.assertEqual(called, ['jina'])

    def test_bad_jina_falls_back_and_keeps_rejected_original(self):
        row, _ = self.add()
        def jina(url): return 'verify you are human ' * 100
        self.assertEqual(acquire(self.store, row, [('jina', jina), ('crawl4ai', lambda u: BODY)]), 'succeeded')
        attempts = list(self.store.db.execute('SELECT * FROM attempts'))
        self.assertEqual([r['status'] for r in attempts], ['rejected', 'ok'])
        self.assertTrue((self.store.home / attempts[0]['raw_path']).exists())

    def test_failure_is_recoverable_and_not_zero_new(self):
        row, _ = self.add()
        def fail(url): raise TimeoutError('controlled fixture timeout')
        self.assertEqual(acquire(self.store, row, [('jina', fail), ('crawl4ai', fail)]), 'failed')
        row = self.store.db.execute('SELECT * FROM materials').fetchone()
        self.assertEqual(row['body_status'], 'failed')
        self.assertEqual(acquire(self.store, row, [('jina', lambda u: BODY)]), 'succeeded')
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM attempts').fetchone()[0], 3)

    def test_tampered_cache_not_reused(self):
        row, _ = self.add(BODY, 'fixture_full')
        (self.store.home / row['body_path']).write_text('tampered')
        self.assertFalse(self.store.cached(row))
        self.assertEqual(export(self.store)['materials'][0]['body'], '')

    def test_refresh_retains_previous_version_and_failure(self):
        row, _ = self.add(BODY, 'fixture_full')
        self.assertEqual(acquire(self.store, row, [('jina', lambda u: 'too short')], force=True), 'failed')
        row = self.store.db.execute('SELECT * FROM materials').fetchone()
        self.assertEqual(row['body_status'], 'refresh_failed')
        self.assertTrue((self.store.home / row['body_path']).exists())
        self.assertEqual(acquire(self.store, row, [('jina', lambda u: BODY + '\n\nA new version contains a documented extra paragraph for version preservation.')]), 'succeeded')
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM body_versions').fetchone()[0], 2)

    def test_keyword_hints_do_not_exclude_vague_titles(self):
        result = prefilter('Something changed', '', RULES)
        self.assertEqual(result['state'], 'needs_review')
        self.assertEqual(prefilter('horoscope', '', RULES)['state'], 'needs_review')

    def test_summary_is_not_full_body_and_atom_works(self):
        rss = '<rss><channel><item><title>x</title><link>https://example.org/x</link><description>' + BODY + '</description></item></channel></rss>'
        row = parse_feed(rss, 'https://example.org')[0]
        self.assertEqual(row['body'], '')
        atom = '<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>x</title><id>1</id><link href="https://example.org/x"/><content>First paragraph is deliberately long enough to count as actual prose in a minimal quality check.\n\nSecond paragraph contains more independent explanatory prose about deterministic testing and body scope.</content></entry></feed>'
        self.assertEqual(parse_feed(atom, 'https://example.org')[0]['source_item_id'], '1')
        self.assertFalse(quality('access denied ' * 100)[0])
        self.assertFalse(quality('brief description')[0])
        self.assertFalse(quality('<!DOCTYPE html><html><body>' + BODY + '</body></html>')[0])

    def test_markdown_html_examples_are_not_html_documents(self):
        tutorial = '# Write HTML safely\n\n' + BODY + '\n\nExample: `<html>` is a root tag.\n\n```html\n<!DOCTYPE html>\n<html><body>Example</body></html>\n```'
        self.assertTrue(quality(tutorial)[0])
        starts_with_code = '```html\n<!DOCTYPE html>\n<html><body>Example</body></html>\n```\n\n' + BODY
        self.assertTrue(quality(starts_with_code)[0])
        self.assertFalse(quality('  <!DOCTYPE html>\n<html><head></head><body>' + BODY + '</body></html>')[0])

    def test_context_change_invalidates_selection(self):
        row, _ = self.add(BODY, 'fixture_full')
        snapshot = export(self.store)
        ctxdir = Path(self.temp.name) / 'context'; ctxdir.mkdir()
        f = ctxdir / 'interests.md'; f.write_text('sqlite')
        ctx, _ = context_hash(ctxdir)
        selection = {'context_sha256': ctx, 'decisions': [{'id': row['id'], 'decision': 'keep', 'reason': 'sqlite workflow', 'evidence': 'SQLite lets a small application', 'limitations': 'fixture'}]}
        validate_filter(selection, snapshot, ctx)
        f.write_text('entertainment')
        changed, _ = context_hash(ctxdir)
        self.assertNotEqual(ctx, changed)
        with self.assertRaises(ValueError): validate_filter(selection, snapshot, changed)
        bad = {'context_sha256': ctx, 'used_ids': [row['id']], 'markdown': 'No source', 'limitations': []}
        with self.assertRaises(ValueError): validate_daily(bad, snapshot, selection, ctx)

    def test_fabricated_quote_and_missing_rows_rejected(self):
        row, _ = self.add(BODY, 'fixture_full')
        snapshot = export(self.store)
        with self.assertRaises(ValueError): validate_filter({'context_sha256': 'a', 'decisions': []}, snapshot, 'a')
        with self.assertRaises(ValueError): validate_filter({'context_sha256': 'a', 'decisions': [{'id': row['id'], 'decision': 'keep', 'reason': 'a', 'evidence': 'invented quote'}]}, snapshot, 'a')

    def test_snapshot_binding_rejects_changed_inputs(self):
        base = Path(self.temp.name)
        inp = base / 'input.json'; inp.write_text('{"a":1}')
        selected = base / 'model.json'; selected.write_text('{"decisions":[]}')
        receipt = {'status':'validated', 'input_sha256':digest(inp.read_bytes()), 'model_sha256':digest(selected.read_bytes())}
        (base / 'receipt.json').write_text(json.dumps(receipt))
        validate_selection_binding(selected, inp)
        inp.write_text('{"a":2}')
        with self.assertRaises(ValueError): validate_selection_binding(selected, inp)
        inp.write_text('{"a":1}'); selected.write_text('{"decisions":[{}]}')
        with self.assertRaises(ValueError): validate_selection_binding(selected, inp)

    def test_unknown_xml_not_treated_as_empty_feed(self):
        with self.assertRaises(ValueError): parse_feed('<html><body>error</body></html>', 'https://example.org')
        self.assertEqual(parse_feed('<rss><channel/></rss>', 'https://example.org'), [])

    def test_raw_integrity_does_not_overwrite_original(self):
        path = self.store.raw('original')
        (self.store.home / path).write_text('tampered')
        with self.assertRaises(ValueError): self.store.raw('original')
        self.assertEqual((self.store.home / path).read_text(), 'tampered')

    def test_trace_requires_actual_contents_not_model_claim(self):
        base=Path(self.temp.name);ctx=base/'ctx';ctx.mkdir()
        (ctx/'a.md').write_text('fictional preference')
        skill=base/'SKILL.md';skill.write_text('actual skill instructions')
        trace=base/'events.jsonl'
        trace.write_text(json.dumps({'type':'item.completed','item':{'type':'agent_message','text':'I read SKILL.md and context'}})+'\n')
        with self.assertRaises(ValueError): trace_reads(trace,skill,ctx)
        trace.write_text(json.dumps({'type':'item.completed','item':{'type':'command_execution','command':'cat SKILL.md ctx/a.md','aggregated_output':'actual skill instructions\nfictional preference','exit_code':0}})+'\n')
        self.assertTrue(trace_reads(trace,skill,ctx)['skill_content_observed'])

    def test_model_override_is_only_a_subprocess_argument(self):
        default=build_codex_command('schema.json','out.json','prompt')
        self.assertNotIn('--model',default)
        self.assertNotIn('-c',default)
        custom=build_codex_command('schema.json','out.json','prompt','ccs-deepseek/deepseek-flash','low')
        self.assertEqual(custom[custom.index('--model')+1],'ccs-deepseek/deepseek-flash')
        self.assertEqual(custom[custom.index('-c')+1],'model_reasoning_effort="low"')
        self.assertEqual(custom[-1],'prompt')

    def test_daily_preview_never_starts_collection_or_models(self):
        with mock.patch.object(daily, 'ROOT', Path(self.temp.name)), mock.patch.object(sys, 'argv', ['daily.py','--preview']), mock.patch('daily.subprocess.run') as run, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(daily.main(), 0)
        run.assert_not_called()
        self.assertFalse((Path(self.temp.name)/'reports').exists())

    def test_daily_collection_failure_stops_before_model_calls(self):
        with mock.patch.object(daily, 'ROOT', Path(self.temp.name)), mock.patch.object(sys, 'argv', ['daily.py']), mock.patch('daily.subprocess.run') as run, contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            run.return_value.returncode=1
            self.assertEqual(daily.main(), 1)
        self.assertEqual(run.call_count, 1)
        self.assertIn('collect.py', run.call_args.args[0][1])

    def test_daily_collects_then_generates_from_same_snapshot(self):
        with mock.patch.object(daily, 'ROOT', Path(self.temp.name)), mock.patch.object(sys, 'argv', ['daily.py']), mock.patch('daily.subprocess.run') as run, contextlib.redirect_stdout(io.StringIO()):
            run.return_value.returncode=0
            self.assertEqual(daily.main(), 0)
        commands=[call.args[0] for call in run.call_args_list]
        self.assertEqual(len(commands), 3)
        self.assertIn('collect.py', commands[0][1])
        self.assertIn('filter.py', commands[1][1])
        self.assertIn('generate.py', commands[2][1])
        self.assertEqual(commands[0][commands[0].index('--out')+1], commands[1][commands[1].index('--input')+1])
        self.assertEqual(commands[1][commands[1].index('--out')+1]+'/model.json', commands[2][commands[2].index('--selection')+1])

    def test_partial_collection_generates_report_but_keeps_partial_exit(self):
        def partial(command, **kwargs):
            return subprocess.CompletedProcess(command, 2 if 'collect.py' in command[1] else 0)
        with mock.patch.object(daily, 'ROOT', Path(self.temp.name)), mock.patch.object(sys, 'argv', ['daily.py']), mock.patch('daily.subprocess.run', side_effect=partial) as run, contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(daily.main(), 2)
        self.assertEqual(run.call_count, 3)

    def test_url_identity(self):
        self.assertEqual(canonical('https://EXAMPLE.org/a?x=2&utm_medium=rss#f'), 'https://example.org/a?x=2')
        with self.assertRaises(ValueError): canonical('https://example.org:80/a')
        with self.assertRaises(ValueError): canonical('file:///private/data')
        with self.assertRaises(ValueError): canonical('https://user:pass@example.org/a')


if __name__ == '__main__':
    unittest.main()
