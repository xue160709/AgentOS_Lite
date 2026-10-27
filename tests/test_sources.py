import contextlib
import io
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest import mock
import subprocess

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from lite import Store, export, canonical, dump
from sources import source_configs, load_config, opencli_command, call_opencli, social_item, note_text
from storage import PlatformStore, analysis_connection, processed_ids
from skill_runner import run_stage, validate_scores
from contracts import context_hash
from collect import collect

RULES={'include':[],'exclude_hints':[]}


class SourceTests(unittest.TestCase):
    def test_shared_sources_and_option_injection(self):
        root=Path(__file__).resolve().parents[1]
        configs=list(source_configs(root/'config/sources'))
        self.assertEqual({k for k,s in configs},{'rss','url','opencli'})
        for kind,source in configs:
            if kind=='opencli': opencli_command(source)
        for value in [
            {'site':'twitter','command':'post','limit':2},
            {'site':'twitter','command':'search','query':'--execute','limit':2},
            {'site':'twitter','command':'search','query':'Python','options':{'execute':'true'}}]:
            with self.assertRaises(ValueError): opencli_command(value)

    def test_temporary_signatures_and_url_forms_share_one_note_identity(self):
        note='6adf6d35000000000d0382bb'
        a=f'https://www.xiaohongshu.com/search_result/{note}?xsec_token=one&xsec_source=search'
        b=f'https://www.xiaohongshu.com/explore/{note}?xsec_token=two&xsec_source=search'
        self.assertEqual(canonical(a),canonical(b))
        with self.assertRaises(ValueError): social_item('xiaohongshu',{'url':'https://example.org/note'})
        with tempfile.TemporaryDirectory() as t:
            store=PlatformStore(t,'xiaohongshu')
            try:
                ids=[]
                for url in [a,b]:
                    item=social_item('xiaohongshu',{'url':url,'title':'test'})
                    mid,fresh=store.item(item,'search',store.raw('test'),RULES); ids.append(mid)
                self.assertEqual(ids[0],ids[1])
                self.assertEqual(store.db.execute('SELECT COUNT(*) FROM materials').fetchone()[0],1)
            finally: store.db.close()

    def test_platform_databases_are_separate_and_no_model_columns(self):
        with tempfile.TemporaryDirectory() as t:
            stores=[PlatformStore(t,p) for p in ['xiaohongshu','twitter','tiktok']]
            try:
                self.assertEqual(len({s.db_path for s in stores}),3)
                for s in stores:
                    tables={r[0] for r in s.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                    self.assertNotIn('scores',tables);self.assertNotIn('decisions',tables)
                    self.assertEqual(s.db.execute('SELECT platform FROM source_meta').fetchone()[0],s.platform)
                item=social_item('tiktok',{'url':'https://www.tiktok.com/@sample/video/123','desc':'Python automation description, no video transcript.'})
                stores[2].item(item,'search',stores[2].raw('test'),RULES)
                self.assertEqual(stores[0].db.execute('SELECT COUNT(*) FROM materials').fetchone()[0],0)
            finally:
                for s in stores:s.db.close()

    def test_local_override_replaces_shared_without_editing_it(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'rss.json';p.write_text('{"sources":[]}')
            p.with_name('rss.local.json').write_text('{"sources":[1]}')
            self.assertEqual(load_config(p)['sources'],[1]);self.assertEqual(json.loads(p.read_text())['sources'],[])

    def test_adapter_errors_are_not_empty_success(self):
        with tempfile.TemporaryDirectory() as t:
            store=Store(t)
            try:
                with mock.patch('sources.subprocess.run',return_value=subprocess.CompletedProcess([],0,'{"ok":false,"error":{"code":"LOGIN"}}','')):
                    with self.assertRaises(RuntimeError):call_opencli(store,['opencli','twitter'])
            finally:store.db.close()

    def test_short_platform_text_is_preserved_and_metadata_is_not_body(self):
        with tempfile.TemporaryDirectory() as t:
            store=Store(t)
            try:
                item=social_item('twitter',{'url':'https://x.com/i/status/123','text':'Python RSS automation: a short public post with enough context.'})
                store.item(item,'twitter',store.raw('test'),RULES)
                self.assertEqual(export(store)['materials'][0]['body'],item['body'])
                self.assertEqual(note_text([{'field':'title','value':'only title'}]),'')
                self.assertEqual(note_text([{'field':'content','value':'actual note'}]),'actual note')
            finally:store.db.close()

    def test_opencli_empty_exit_is_distinct_from_infrastructure_failure(self):
        with tempfile.TemporaryDirectory() as t:
            store=Store(t)
            try:
                for code,empty in [(66,True),(69,False)]:
                    with mock.patch('sources.subprocess.run',return_value=subprocess.CompletedProcess([],code,'[]','')),mock.patch('sources.time.sleep'):
                        if empty:
                            rows,path=call_opencli(store,['opencli','twitter'])
                            self.assertEqual(rows,[])
                            self.assertTrue((store.home/path).exists())
                        else:
                            with self.assertRaises(RuntimeError):call_opencli(store,['opencli','twitter'])
            finally:store.db.close()

    def make_input(self,base):
        store=PlatformStore(base/'data','twitter')
        text='A short public platform post about Python automation and RSS.'
        mid,_=store.item({'url':'https://x.com/i/status/123','title':'test','body':text,'scope':'platform_text_unverified'},'twitter',store.raw('test'),RULES)
        snapshot=export(store);snapshot['data_home']=str(base/'data');snapshot['materials'][0]['platform']='twitter';store.db.close()
        inp=base/'input.json';dump(inp,snapshot)
        ctx=base/'context';ctx.mkdir()
        for name in ['profile','interests','disinterests','report']:(ctx/(name+'.md')).write_text('fictional')
        ctx_hash,_=context_hash(ctx)
        selection={'context_sha256':ctx_hash,'decisions':[{'id':mid,'score':4,'decision':'keep','reason':'automation','evidence':'Python automation','limitations':'platform text'}]}
        report={'context_sha256':ctx_hash,'used_ids':[mid],'markdown':f'fixture {mid} https://x.com/i/status/123','limitations':[]}
        return inp,ctx,ctx_hash,mid,selection,report

    def fake_reply(self,result):
        def reply(command,**kwargs):
            kwargs['stdout'].write(json.dumps({'structured_output':result,'is_error':False}))
            return subprocess.CompletedProcess(command,0)
        return reply

    def test_signed_snapshot_is_rejected_before_cli_call(self):
        with tempfile.TemporaryDirectory() as t:
            base=Path(t);inp,ctx,*_=self.make_input(base)
            inp.write_text('{"url":"https://www.xiaohongshu.com/explore/123?xsec_token=temporary"}')
            with mock.patch('skill_runner.subprocess.run') as run:
                with self.assertRaises(ValueError):run_stage('filter',inp,base/'out','claude',context_dir=ctx)
            run.assert_not_called()

    def test_two_stages_persist_scores_before_report_and_process_only_on_success(self):
        with tempfile.TemporaryDirectory() as t:
            base=Path(t);inp,ctx,ctx_hash,mid,selection,report=self.make_input(base)
            with mock.patch('skill_runner.subprocess.run',side_effect=self.fake_reply(selection)),contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(run_stage('filter',inp,base/'filter','claude',context_dir=ctx),0)
            self.assertEqual(processed_ids(base/'data',ctx_hash),set())
            with analysis_connection(base/'data') as db:
                self.assertEqual(db.execute('SELECT score FROM scores').fetchone()[0],4)
            report['markdown']='missing source link'
            with mock.patch('skill_runner.subprocess.run',side_effect=self.fake_reply(report)),contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(run_stage('daily',inp,base/'bad','claude',context_dir=ctx,selection_path=base/'filter/model.json'),1)
            self.assertEqual(processed_ids(base/'data',ctx_hash),set())
            report['markdown']=f'fixture {mid} https://x.com/i/status/123'
            with mock.patch('skill_runner.subprocess.run',side_effect=self.fake_reply(report)),contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(run_stage('daily',inp,base/'daily','claude',context_dir=ctx,selection_path=base/'filter/model.json'),0)
            self.assertEqual({m for m,h in processed_ids(base/'data',ctx_hash)},{mid})
            self.assertEqual(processed_ids(base/'data','different-context'),set())
            with sqlite3.connect(base/'data/sources/twitter/twitter.sqlite') as db:
                self.assertEqual(db.execute('SELECT COUNT(*) FROM materials').fetchone()[0],1)
            # Rewriting or swapping a scoring result is rejected before another model call.
            (base/'filter/model.json').write_text('{}')
            with mock.patch('skill_runner.subprocess.run') as run:
                with self.assertRaises(ValueError):run_stage('daily',inp,base/'swapped','claude',context_dir=ctx,selection_path=base/'filter/model.json')
            run.assert_not_called()

    def test_collection_deduplicates_snapshot_without_merging_source_databases(self):
        with tempfile.TemporaryDirectory() as t:
            base=Path(t);sources=base/'config';sources.mkdir()
            dump(sources/'rss.json',{'sources':[{'id':'feed','enabled':True,'url':'https://example.org/feed','limit':1}]})
            dump(sources/'urls.json',{'sources':[{'id':'page','enabled':True,'url':'https://example.org/article','title':'Reference'}]})
            body=json.loads((Path(__file__).resolve().parents[1]/'fixtures/materials.json').read_text())[0]['body']
            import html
            feed=('<rss xmlns:content="http://purl.org/rss/1.0/modules/content/"><channel><item><title>Reference</title><link>https://example.org/article</link><content:encoded>'+html.escape(body)+'</content:encoded></item></channel></rss>').encode()
            def fetch(url): return feed if url.endswith('/feed') else ('Markdown Content:\n'+body).encode()
            with mock.patch('collect.request',side_effect=fetch),contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(collect(base/'data',sources,base/'input.json'),0)
            snap=json.loads((base/'input.json').read_text())
            self.assertEqual(len(snap['materials']),1)
            self.assertEqual(len(snap['materials'][0]['source_databases']),2)
            for platform in ['rss','urls']:
                with sqlite3.connect(base/f'data/sources/{platform}/{platform}.sqlite') as db:
                    self.assertEqual(db.execute('SELECT COUNT(*) FROM materials').fetchone()[0],1)

    def test_score_threshold_and_pending_rules(self):
        with tempfile.TemporaryDirectory() as t:
            base=Path(t);inp,ctx,ctx_hash,mid,result,_=self.make_input(base);snap=json.loads(inp.read_text())
            result['decisions'][0]['score']=2
            with self.assertRaises(ValueError):validate_scores(result,snap,ctx_hash,3)
            result['decisions'][0].update(score=4,decision='pending')
            with self.assertRaises(ValueError):validate_scores(result,snap,ctx_hash,3)


if __name__=='__main__':unittest.main()
