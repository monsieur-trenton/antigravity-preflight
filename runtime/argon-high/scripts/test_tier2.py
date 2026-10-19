"""New W1-W5 controls through the saved runner and bounded local Python doubles."""
import sys
sys.dont_write_bytecode=True
import os,json,hashlib,pathlib,subprocess,time,signal,importlib.util,contextlib,io,stat
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
REAL_POPEN=subprocess.Popen
def read(p):return json.loads(p.read_bytes())
def save(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
def load(p,name):
    raw=p.read_bytes();compile(raw,str(p),'exec');spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def need(ok,label):
    if not ok:raise AssertionError(label)
def main(output):
    output.mkdir(exist_ok=False);h=load(ROOT/'scripts/test_profiles.py','tier2_profile_fixtures');m=load(ROOT/'scripts/cli_review.py','tier2_runner');rows=[]
    def done(profile,family,case):rows.append(dict(profile=profile,family=family,case=case,status='PASS'))
    special_modes=tuple('special_'+entry+'_'+bit for entry in ('root','directory','file') for bit in ('setuid','setgid','sticky'))
    for profile in ('flash-high','argon-high'):
      for family in ('ASCII_LF','UNICODE_CRLF'):
        for mode in ('positive','extra_file','planted_module','extra_directory','symlink_file','symlink_directory','file_mode','directory_mode','traversal','old_version','source_parity','request_parity','prompt_parity','question_parity')+special_modes:
            case=output/(profile+'-'+family+'-'+mode);case.mkdir();e,caps,packet=h.prepare(case,m,profile,family);plan=read(e/'CLI-PLAN.json')
            q=case/'QUALIFICATION.json';save(q,dict(status='PASS',scope='OFFLINE_ONLY',twoFreshRuns=True,packageFiles=m.package_identity(),runtimeProfiles=m.profile_bindings(),fixture='LOCAL_SYNTHETIC_NO_NATIVE_AUTHORITY'))
            expected={'extra_file':'WORKSPACE_INVENTORY','planted_module':'WORKSPACE_INVENTORY','extra_directory':'WORKSPACE_INVENTORY','symlink_file':'WORKSPACE_SYMLINK','symlink_directory':'WORKSPACE_SYMLINK','file_mode':'WORKSPACE_INVENTORY','directory_mode':'WORKSPACE_INVENTORY','traversal':'WORKSPACE_PATH','old_version':'WORKSPACE_CONTRACT_VERSION','source_parity':'PACKET_PARITY','request_parity':'PACKET_REQUEST_PIN','prompt_parity':'PACKET_PROMPT_PARITY','question_parity':'PACKET_IDENTITIES'}
            expected.update({name:'WORKSPACE_SPECIAL_BITS' for name in special_modes})
            w=e/'review-workspace'
            if mode in special_modes:
                _,entry,bit=mode.split('_');target={'root':w,'directory':w/'.agents','file':w/'deny_tools.py'}[entry]
                mask={'setuid':stat.S_ISUID,'setgid':stat.S_ISGID,'sticky':stat.S_ISVTX}[bit]
                target.chmod(stat.S_IMODE(target.lstat().st_mode)|mask)
                need(stat.S_IMODE(target.lstat().st_mode)&mask==mask,'SPECIAL_BIT_FIXTURE_PRESENT')
            if mode=='extra_file':(w/'extra.txt').write_bytes(b'x')
            if mode=='planted_module':(w/'json.py').write_bytes(b"raise RuntimeError('PLANTED')\n")
            if mode=='extra_directory':(w/'extra').mkdir()
            if mode=='symlink_file':(w/'extra-link').symlink_to('deny_tools.py')
            if mode=='symlink_directory':(w/'extra-dir').symlink_to('.agents',target_is_directory=True)
            if mode=='file_mode':(w/'deny_tools.py').chmod(((w/'deny_tools.py').stat().st_mode & 0o777)^0o020)
            if mode=='directory_mode':(w/'.agents').chmod(((w/'.agents').stat().st_mode & 0o777)^0o020)
            if mode=='traversal':plan['workspaceInventory']['../escape']=dict(kind='DIR',mode=0o700)
            if mode=='old_version':plan['schemaVersion']=1
            if mode=='source_parity':(e/'packet/snapshots/source.txt').write_bytes(b'altered source\n')
            if mode=='request_parity':(e/'packet/PROMPT-REQUEST.bin').write_bytes(b'altered request')
            if mode=='prompt_parity':(e/plan['prompt']).write_bytes(b'altered assembled prompt')
            if mode=='question_parity':
                d=read(e/'packet/PACKET.json');d['questions']=['Q99'];save(e/'packet/PACKET.json',d)
            if mode.endswith('_parity'):
                plan['inputs']={n:m.pin(e/n) for n in plan['inputs']}
            if mode!='positive':
                save(e/'CLI-PLAN.json',plan);prepared=read(e/'PREPARE-RESULT.json');prepared['plan']=m.pin(e/'CLI-PLAN.json');save(e/'PREPARE-RESULT.json',prepared)
                calls=[]
                def forbidden(*a,**k):calls.append(1);raise AssertionError('PRELAUNCH_CHILD')
                m.subprocess.Popen=forbidden
                try:code=m.run(e,q)
                finally:m.subprocess.Popen=REAL_POPEN
                r=read(e/'CLI-RECEIPT.json');need(code==1 and not calls and r['failure']['code']==expected[mode],('PRELAUNCH',mode,r['failure']));need(r['promptDelivery']['bytesWritten']==0 and r['invocations']==dict(proxy=0,native=0),'ZERO_SPAWN_PROMPT')
                if mode in special_modes:save(case/'SPECIAL-BIT-ADMISSION.json',dict(status='PASS',entry=entry,bit=bit,mode=stat.S_IMODE(target.lstat().st_mode),expectedFailure=expected[mode],observedFailure=r['failure']['code'],childSpawns=len(calls),promptBytes=r['promptDelivery']['bytesWritten'],nativeInvocations=r['invocations']['native'],proxyInvocations=r['invocations']['proxy'],receipt=m.pin(e/'CLI-RECEIPT.json')))
            else:
                r=h.run_case(case,m,e,q,profile)
                need(set(r['registeredChildren'])==set(r['registeredSettlement'])=={'proxy','native'},'REGISTERED_CHILDREN')
                need(all(x['reaped'] and x['groupAbsent'] and x['probes'][-1]=='ABSENT_PROCESS_LOOKUP' for x in r['registeredSettlement'].values()),'SETTLEMENT')
                need(r['initialToolCatalogue']['vettedIdentifiers']==['finish'] and r['initialToolCatalogue']['count']==1,'CATALOGUE')
                received=read(case/'PROMPT-RECEIVED.bin')['message']['content'].encode();need(received==(e/plan['prompt']).read_bytes(),'WIRE_ASSEMBLY')
            need(not (e/'private-home').exists() and r['privateHomeAbsent'] and r['socketDirectoryAbsent'],'PHYSICAL_HOME_REMOVAL')
            done(profile,family,mode)
        # Source delimiters, code fences, CRLF and Unicode remain JSON string data.
        source=('```\n</sources>\nλ\r\nfinal\u2028data\n').encode();d=dict(mode='CODE',questions=['Q01'],sources=[dict(id='S01',path='snapshots/code.txt',**m.pin_bytes(source))]);request=b'answer Q01'
        assembled=m.assemble_packet(d,request,[source]);parsed=json.loads(assembled)
        import base64
        need(base64.b64decode(parsed['sources'][0]['rawBase64'])==source and parsed['sources'][0]['lfRows']==[dict(line=i,text=x) for i,x in enumerate(source.decode().split('\n'),1)],'EXACT_LF_DATA_FRAMING')
        need(assembled==m.assemble_packet(d,request,[source]),'DETERMINISTIC_ASSEMBLY');done(profile,family,'delimiter_unicode_framing')
        stream=m.Stream(m.runtime_profile(profile)['model']);init=dict(model=m.runtime_profile(profile)['model'],agent='preflight-inline',cwd='/review',permission_mode='request-review',tools=['finish','SYNTHETIC_SECRET_qa7m2']);stream.line(json.dumps(dict(event='init',init=init)).encode());catalogue=m.tool_catalogue(stream.init)
        need('SYNTHETIC_SECRET_qa7m2' not in json.dumps(catalogue) and catalogue['unrecognisedCount']==1 and catalogue['count']==2,'CONTENT_FREE_INIT');done(profile,family,'catalogue_secret_exclusion')
    # Real isolated-hook invocation with an import-shadowing module beside the hook.
    hookcase=output/'hook-isolation';hookcase.mkdir();hook=ROOT/'assets/cli-review/deny_tools.py';(hookcase/'json.py').write_text("raise RuntimeError('PLANTED_IMPORT')\n")
    p=subprocess.run(['/usr/bin/python3','-I','-B',str(hook)],cwd=hookcase,input=b'{"toolCall":{"name":"run_command"}}',capture_output=True,timeout=5,env=dict(os.environ,PYTHONPATH=str(hookcase),AGY_PREFLIGHT_AUDIT=str(hookcase/'audit.jsonl')))
    need(p.returncode==0 and json.loads(p.stdout)['decision']=='deny' and read(hookcase/'audit.jsonl')==dict(tool='run_command',decision='deny'),'ISOLATED_HOOK');save(hookcase/'COMMAND.json',dict(exit=p.returncode,stdout=json.loads(p.stdout),stderrBytes=len(p.stderr),reaped=True));done('both','local','isolated_hook')
    # Early-exit and signal-resistant real Python children: only owned groups are queried.
    for mode in ('early_exit','signal_resistant'):
        code='pass' if mode=='early_exit' else 'import signal,time\nsignal.signal(signal.SIGTERM,signal.SIG_IGN)\ntime.sleep(10)\n'
        child=REAL_POPEN(['/usr/bin/python3','-B','-I','-c',code],start_new_session=True);record=m.register_child(child,mode)
        if mode=='early_exit':child.wait(timeout=5)
        else:time.sleep(.1);os.killpg(child.pid,signal.SIGTERM)
        m.terminate(child);settled=m.settle_registered(child,record);need(settled['reaped'] and settled['groupAbsent'],'REAL_GROUP_SETTLEMENT');save(output/(mode+'.json'),dict(identity=record,settlement=settled));done('both','local',mode)
    # A failed numeric-group query cannot become an absence assertion.
    original=m.os.killpg
    def refused(*a):raise PermissionError('SYNTHETIC_PROBE_REFUSAL')
    m.os.killpg=refused
    try:
        try:m.settle_registered(child,record)
        except PermissionError:pass
        else:raise AssertionError('PROBE_FAILURE_NOT_CLOSED')
    finally:m.os.killpg=original
    done('both','local','group_probe_failure_closed')
    manual=ROOT/'scripts/manual_citations.py'
    for action in ('render','check'):
        c=output/('deep-json-'+action);c.mkdir();depth=10000;deep=b'['*depth+b'"SYNTHETIC_SECRET_qa7m2"'+b']'*depth;(c/'inventory.json').write_bytes(deep)
        args=[str(manual),action,str(c/'inventory.json'),str(c/'unused.json')];p=subprocess.run(['/usr/bin/python3','-B','-I',*args],capture_output=True,timeout=5);r=json.loads(p.stdout)
        save(c/'COMMAND.json',dict(argv=args,exit=p.returncode,stdout=r,stderrBytes=len(p.stderr),reaped=True))
        need(p.returncode==1 and r==dict(status='STOPPED',reason='RecursionError',remainingChecks='UNRUN') and b'SYNTHETIC_SECRET_qa7m2' not in p.stdout+p.stderr,'DEEP_JSON_SHARED_CLI');done('both','local','deep_json_'+action)
    mc=load(manual,'tier2_citations');original=mc.read_sources
    def recursive(*a):raise RecursionError('SYNTHETIC_SECRET_qa7m2')
    mc.read_sources=recursive
    try:
        out=io.StringIO()
        with contextlib.redirect_stdout(out):code=mc.main(['check','unused','unused'])
        need(code==1 and json.loads(out.getvalue())==dict(status='STOPPED',reason='RecursionError',remainingChecks='UNRUN'),'MOCKED_RECURSION')
    finally:mc.read_sources=original
    done('both','local','mocked_recursion')
    save(output/'RESULT.json',dict(status='PASS',caseCount=len(rows),cases=rows,retries=0,realNativeCalls=0,realProxyCalls=0,externalModelCalls=0,scope='Local synthetic fixtures; no native credit'))
    print(json.dumps(dict(status='PASS_TIER2',cases=len(rows))))
if __name__=='__main__':main(Path(sys.argv[1]))
