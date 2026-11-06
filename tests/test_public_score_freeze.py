"""The actual browser adapter must preserve server-audited public scores."""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

class PublicScoreFreezeTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'),'Node is required only for this browser-adapter test')
    def test_browser_time_and_private_imports_do_not_change_public_scores(self):
        script=r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const base={as_of:'2020-01-02T00:00:00Z',evidence_total:600,
 themes:[{id:'ai',heat:41,consensus:null,evidence_count:3,source_count:2,terms:['gpu']}],
 evidence:[],sources:[],data_readiness:{status:'blocked'}};
const context={document:{documentElement:{dataset:{mode:'static'}},baseURI:'https://fixture.invalid/',addEventListener(){}},
 localStorage:{getItem(){return null},setItem(){}},window:{},structuredClone,
 fetch:async()=>({ok:true,json:async()=>structuredClone(base)}),URL,Date,JSON,Set,
 TextEncoder,Uint8Array,crypto:require('crypto').webcrypto,setTimeout,Blob};
vm.runInNewContext(fs.readFileSync('web/static-api.js','utf8'),context);
(async()=>{
 const api=context.window.radarStaticApi;
 const a=await api('/api/snapshot');assert.equal(a.themes[0].heat,41);
 await api('/api/import',{records:[{title:'GPU fixture',url:'https://fixture.invalid/import',published:'2020-01-01T12:00:00Z',theme:'ai',source:'fixture'}]});
 const b=await api('/api/snapshot');assert.equal(b.themes[0].heat,41);
 assert.equal(b.themes[0].source_count,2);assert.equal(b.evidence_total,601);
 assert.equal(b.score_scope,'public_snapshot');assert.equal(b.data_readiness.status,'blocked');
 console.log('PASS: frozen audited scores, complete public count, private data cannot cure public readiness');
})().catch(e=>{console.error(e);process.exit(1)});
'''
        root=Path(__file__).resolve().parent.parent
        result=subprocess.run(['node','-e',script],cwd=root,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

if __name__=='__main__':unittest.main()
