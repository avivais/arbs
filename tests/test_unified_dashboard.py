"""Offline frontend contracts; synthetic fixtures do not attest live opportunities."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / 'docs/dashboard.html').read_text()
MODEL = re.search(r'<script id="dashboard-model">(.*?)</script>', HTML, re.S).group(1)
UI = re.search(r'<script id="dashboard-ui">(.*?)</script>', HTML, re.S).group(1)
FIXTURE = r"""
const assert=require('node:assert/strict'), M=DashboardModel;
const now=Date.parse('2026-09-17T10:00:00Z'), iso=ms=>new Date(ms).toISOString();
function book(){return {event_id:'event-1',participants:['A','B'],status:'OBSERVED_RAW_GAP',cross_leg_receipt_skew_ms:400,legs:[
 {venue:'kalshi',outcome:'A',instrument_id:'ticker-A',best_ask:'0.43',best_ask_quantity:'10',received_at:iso(now-1000),source_time_status:'not_exposed'},
 {venue:'polymarket',outcome:'B',instrument_id:'token-B',best_ask:'0.56',best_ask_quantity:'20',received_at:iso(now-600),source_time_status:'available',source_age_at_receipt_ms:'5000000'}]};}
const proposal={id:'proposal-1',category:'economics',status:'REVIEW',score:.3,left:{venue:'kalshi',id:'rate-1',title:'Interest rate decision',raw:{yes_ask_dollars:'0.01'}},right:{venue:'polymarket',id:'rate-2',title:'Different meeting',raw:{outcomePrices:'["0.01","0.99"]'}}};
const discovery={generated_at:iso(now),catalog_generated_at:iso(now),proposals:[proposal]}, books={generated_at:iso(now),records:[book()]};
const f={category:'all',status:'all',search:'',mode:'all',threshold:'99'};
"""

@unittest.skipUnless(shutil.which('node'), 'Node required for actual JS model tests')
class DashboardModelTests(unittest.TestCase):
    def js(self, code):
        run = subprocess.run(['node', '-e', MODEL + FIXTURE + code], text=True, capture_output=True)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)

    def test_unified_feed_and_status_filters(self):
        self.js("""const rows=M.normalize(discovery,books,now);assert.equal(rows.length,2);
        assert.deepEqual(M.stats(rows),{raw:1,fresh:1,proposals:1});
        assert.equal(M.filter(rows,{...f,category:'economics'})[0].kind,'proposal');
        assert.equal(M.filter(rows,{...f,status:'NO BOOK'}).length,1);
        assert.equal(M.filter(rows,{...f,status:'REVIEW'}).length,2);
        assert.equal(M.filter(rows,{...f,search:'different meeting'}).length,1);
        assert.equal(M.filter(rows,{...f,search:'token-b'}).length,1);""")

    def test_decimal_threshold_inclusive_exclusive(self):
        self.js("""const rows=M.normalize(discovery,books,now);
        assert.equal(M.filter(rows,{...f,mode:'lte'}).length,1);
        assert.equal(M.filter(rows,{...f,mode:'lt'}).length,0);
        assert.equal(M.filter(rows,{...f,mode:'lt',threshold:'99.00000001'}).length,1);
        assert.equal(M.filter(rows,{...f,mode:'lte',threshold:'98.99999999'}).length,0);
        for(const t of ['',null,'NaN','Infinity','0','201','-1'])assert.equal(M.filter(rows,{...f,mode:'lte',threshold:t}).length,0);
        for(const t of [null,'',true,'1e-2','NaN','Infinity','0.123456789'])assert.equal(M.fixed(t),null);""")

    def test_metadata_never_becomes_quote(self):
        self.js("""const rows=M.normalize(discovery,null,now);assert.equal(rows[0].quote.total,null);
        assert.equal(M.filter(rows,{...f,mode:'lte',threshold:'200'}).length,0);
        assert.equal(M.stats(rows).raw,0);""")

    def test_snapshot_expiry_and_future_fail_closed(self):
        self.js("""for(const t of [iso(now-90001),iso(now+1),'bad','2026-09-17T10:00:00',null]){
        const rows=M.normalize(discovery,{...books,generated_at:t},now);
        assert.equal(rows[0].status,'STALE');assert.equal(M.stats(rows).raw,0);}
        assert.equal(M.quote(book(),iso(now-90000),now).valid,true);""")

    def test_leg_expiry_even_when_artifact_fresh(self):
        self.js("""for(const t of [iso(now-90001),iso(now+1),'bad',null]){const r=book();r.legs[0].received_at=t;assert.equal(M.quote(r,iso(now),now).valid,false);}
        const rows=M.normalize(discovery,books,now+90001);assert.equal(M.stats(rows).raw,0);
        assert.equal(M.filter(rows,{...f,mode:'lte'}).length,0);""")

    def test_skew_boundary_and_source_age_semantics(self):
        self.js("""let r=book();r.legs[1].received_at=iso(now-200);r.cross_leg_receipt_skew_ms=800;
        assert.equal(M.quote(r,iso(now),now).valid,true);
        r.legs[1].received_at=iso(now-199);assert.equal(M.quote(r,iso(now),now).valid,false);
        for(const x of [801,null,'',-1]){r=book();r.cross_leg_receipt_skew_ms=x;assert.equal(M.quote(r,iso(now),now).valid,false);}
        assert.equal(M.quote(book(),iso(now),now).valid,true); // old source update is measurement only
        for(const status of ['invalid','future','unknown']){r=book();r.legs[1].source_time_status=status;assert.equal(M.quote(r,iso(now),now).valid,false);}
        for(const x of [null,'',-2001]){r=book();r.legs[1].source_age_at_receipt_ms=x;assert.equal(M.quote(r,iso(now),now).valid,false);}""")

    def test_bad_quotes_depth_and_source_status(self):
        self.js("""for(const x of [null,'',true,'NaN','Infinity','1.01','-0.1']){const r=book();r.legs[0].best_ask=x;assert.equal(M.quote(r,iso(now),now).valid,false);}
        for(const x of [null,'',0,-1]){const r=book();r.legs[0].best_ask_quantity=x;assert.equal(M.quote(r,iso(now),now).status,'NO BOOK');}
        for(const status of ['UNAVAILABLE_FRESHNESS','NO_DEPTH','unexpected']){const r=book();r.status=status;assert.equal(M.quote(r,iso(now),now).valid,false);}
        const r=book();r.legs[1].best_ask='0.57';assert.equal(M.quote(r,iso(now),now).status,'NO RAW GAP');
        r.legs=[null];assert.equal(M.quote(r,iso(now),now).status,'NO BOOK');""")

    def test_catalog_two_hour_freshness_is_not_execution(self):
        self.js("""let rows=M.normalize(discovery,books,now+7200000);assert.equal(rows[1].status,'REVIEW');assert.equal(rows[0].status,'STALE');
        rows=M.normalize(discovery,books,now+7200001);assert.equal(rows[1].status,'STALE');assert(rows[1].tags.includes('REVIEW'));
        const reject={...proposal,ai_review:{verdict:'REJECT',reason:'Different meetings'}};
        rows=M.normalize({...discovery,proposals:[reject]},null,now);assert.equal(rows[0].status,'REJECT');assert.equal(rows[0].quote.valid,false);""")

    def test_partial_failures_retain_but_invalidate(self):
        self.js("""const failed=M.settled({data:books},null,'HTTP 503');assert.equal(failed.data,books);assert(failed.error);
        const rows=M.normalize(discovery,failed.data,now,{books:true});assert.equal(rows.length,2);assert.equal(M.stats(rows).raw,0);assert.equal(rows[1].status,'REVIEW');
        const other=M.normalize(discovery,books,now,{discovery:true});assert.equal(M.stats(other).raw,1);assert.equal(other[1].status,'STALE');
        assert.equal(M.settled(failed,books,null).error,null);
        assert.throws(()=>M.validate({records:[{legs:[null]}]},'books'));
        assert.throws(()=>M.validate({proposals:{}},'discovery'));
        assert.throws(()=>M.validate(null,'books'));
        assert.equal(M.validate(books,'books'),books);""")

    def test_safe_https_links(self):
        self.js("""for(const x of ['javascript:alert(1)','data:text/html,bad','//evil.test','http://example.com','https://user:secret@example.com',null])assert.equal(M.safeURL(x),null);
        assert.equal(M.safeURL('https://kalshi.com/markets/example'),'https://kalshi.com/markets/example');""")

    def test_both_scripts_parse(self):
        self.js('new Function(' + json.dumps(UI) + ');')


class DashboardSourceTests(unittest.TestCase):
    def test_only_same_origin_read_endpoints(self):
        for path in ['../data/discovery/report-latest.json','../data/shadow/latest-indicators.json','../data/discovery/ai-worker-state.json']:
            self.assertIn(path, UI)
        self.assertIn('setInterval(load,30000)', UI)
        self.assertIn('setInterval(()=>render(),1000)', UI)
        self.assertIn('AbortController', UI)
        self.assertIn('Promise.allSettled', UI)
        self.assertNotRegex(UI, r"method\s*:\s*['\"](?:POST|PUT|DELETE)")

    def test_safe_render_and_navigation(self):
        self.assertNotIn('innerHTML', HTML)
        self.assertNotIn('insertAdjacentHTML', HTML)
        self.assertNotRegex(HTML, r'<script[^>]+src=')
        for target in ['discovery.html','rolling-plan.html','fee-aware-validation.html','reports.html']:
            self.assertIn(f'href="{target}"', HTML)
        for phrase in ['All categories','MLB only','net profit is not established','NO RAW GAP','NO BOOK','Unavailable','N/A','unverified discovery candidates']:
            self.assertIn(phrase, HTML)
        self.assertEqual(HTML.count('id="feed"'), 1)
        self.assertNotIn('Live sports arbitrage scanner', HTML)


if __name__ == '__main__':
    unittest.main()
