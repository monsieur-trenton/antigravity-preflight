"""Exercise the saved launcher main with source-free process transport doubles.

No real agy, bwrap, Secret Service, provider or model is invoked. The doubles
inspect production argv and launch only syntax/hash-retained Python children.
This is not native tool-denial or containment qualification.
The synthetic proxy uses a plain readiness file; no Unix socket is opened.
"""
import contextlib,fcntl,hashlib,importlib.util,io,json,os,shutil,signal,subprocess,sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('subject_cli',HERE/'cli_review.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
REAL_POPEN=subprocess.Popen
REAL_RMTREE=shutil.rmtree
def require(ok,label):
    if not ok:raise AssertionError(label)
def save(path,data):
    with path.open('x',encoding='utf-8') as out:out.write(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
def invoke(args,log):
    out=io.StringIO();err=io.StringIO()
    with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):
        try:code=m.main(args)
        except SystemExit as error:code=error.code
    save(log,dict(argv=args,exit=code,stdout=out.getvalue(),stderr=err.getvalue()))
    return code,json.loads(out.getvalue()) if out.getvalue().strip() else None
def fixture(path,source):
    raw=source.encode();compile(raw,str(path),'exec');path.write_bytes(raw)
    save(path.with_suffix('.SYNTAX.json'),dict(status='PASS',sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),completeFinalBytes=True,beforeExecution=True))
def packet(case,family):
    root=case/'input';(root/'snapshots').mkdir(parents=True)
    ending='\n' if family=='ASCII_LF' else '\r\n'
    text='Valid record' if family=='ASCII_LF' else '条件 Valid record λ'
    source=(text+ending+'Sparse record'+ending+'Adversarial record'+ending).encode()
    prompt=('PLAN review of S01; answer Q01. Supplied snapshot:\n'+source.decode()).encode()
    (root/'snapshots/source.txt').write_bytes(source);(root/'PROMPT.txt').write_bytes(prompt)
    descriptor=dict(schemaVersion=1,mode='PLAN',prompt=dict(path='PROMPT.txt',sha256=m.sha(prompt),bytes=len(prompt)),
                    sources=[dict(id='S01',path='snapshots/source.txt',sha256=m.sha(source),bytes=len(source))],questions=['Q01'])
    save(root/'PACKET.json',descriptor)
    return root,descriptor
def main(output,metadata_root):
    output.mkdir(parents=True,exist_ok=False);cases=[];package_before=m.package_identity()
    for family in ('ASCII_LF','UNICODE_CRLF'):
        metadata=metadata_root/(family+'-current')/'capture'
        prepare_modes={'valid':None,'prompt_hash':'INPUT_HASH','source_hash':'INPUT_HASH','path_escape':'PATH_ESCAPE',
                       'symlink':'SYMLINK_REFUSED','duplicate_source':'DUPLICATE_INPUT','duplicate_question':'QUESTION_IDENTITIES',
                       'duplicate_json':'DUPLICATE_KEY','prompt_cap':'INPUT_SIZE','boolean_version':'PACKET_CONTRACT',
                       'metadata_stream':'METADATA_STREAM_PIN','metadata_runtime':'NATIVE_PIN',
                       'metadata_model':'METADATA_INTERPRETATION','metadata_stop':'CAPABILITY_REQUIRED',
                       'existing_output':'FileExistsError','output_in_input':'EVIDENCE_INSIDE_INPUT'}
        for mode,expected in prepare_modes.items():
            case=output/(family+'-prepare-'+mode);case.mkdir();root,d=packet(case,family);caps=metadata
            if mode=='prompt_hash':(root/'PROMPT.txt').write_bytes(b'X'+(root/'PROMPT.txt').read_bytes()[1:])
            if mode=='source_hash':d['sources'][0]['sha256']='0'*64
            if mode=='path_escape':d['sources'][0]['path']='../elsewhere'
            if mode=='symlink':(root/'snapshots/source.txt').rename(root/'snapshots/real.txt');(root/'snapshots/source.txt').symlink_to('real.txt')
            if mode=='duplicate_source':d['sources'].append(d['sources'][0])
            if mode=='duplicate_question':d['questions'].append('Q01')
            if mode=='prompt_cap':d['prompt']['bytes']=131073
            if mode=='boolean_version':d['schemaVersion']=True
            (root/'PACKET.json').write_text(json.dumps(d))
            if mode=='duplicate_json':(root/'PACKET.json').write_bytes(b'{"schemaVersion":1,"schemaVersion":1}')
            if mode.startswith('metadata_'):
                caps=case/'metadata';shutil.copytree(metadata,caps)
                if mode=='metadata_stream':(caps/'HELP.stdout').write_bytes(b'changed')
                if mode=='metadata_runtime':(caps/'runtime/agy').chmod(0o755);(caps/'runtime/agy').write_bytes(b'changed')
                if mode in ('metadata_model','metadata_stop'):
                    v=json.loads((caps/'RESULT.json').read_bytes());v['model' if mode=='metadata_model' else 'status']='other' if mode=='metadata_model' else 'STOPPED';(caps/'RESULT.json').write_text(json.dumps(v))
            evidence=case/'evidence'
            if mode=='existing_output':evidence.mkdir();(evidence/'marker').write_bytes(b'untouched')
            if mode=='output_in_input':evidence=root/'evidence'
            def no_process(*a,**k):raise AssertionError('PREPARE_MUST_NOT_EXECUTE')
            m.subprocess.Popen=no_process
            try:code,result=invoke(['prepare',str(root/'PACKET.json'),str(caps),str(evidence)],case/'COMMAND.json')
            finally:m.subprocess.Popen=REAL_POPEN
            require(code==(0 if expected is None else 1),'PREPARE_EXIT')
            if expected:require(result['failure']==expected,('PREPARE_REASON',mode,result))
            else:
                plan=json.loads((evidence/'CLI-PLAN.json').read_bytes());require(plan['packageFiles']==package_before and plan['questions']==['Q01'],'PREPARE_BINDING')
                require((evidence/'packet/PROMPT.txt').read_bytes()==(root/'PROMPT.txt').read_bytes(),'PROMPT_EXACT')
                require(not (evidence/'private-home').exists() and not (evidence/'CLI-GATE.json').exists(),'PREPARE_NO_LAUNCH')
            if mode=='existing_output':require((evidence/'marker').read_bytes()==b'untouched','EXISTING_OUTPUT_PRESERVED')
            cases.append(dict(family=family,stage='prepare',case=mode,status='PASS'))

        run_modes={'valid':None,'wrong_init':'INIT_BINDING','operational':'OPERATIONAL_TOOL','delegation':'DELEGATION_PAYLOAD',
                   'error_step':'STEP_STATE','result_failure':'RESULT_FAILURE','malformed':'JSONDecodeError','duplicate':'DUPLICATE_KEY',
                   'truncated':'TRUNCATED_STREAM','incomplete':'INCOMPLETE_STEPS','missing_result':'MISSING_RESULT',
                   'exit_nonzero':'PROCESS_EXIT','stderr_overflow':'CAP_EXCEEDED','stdout_overflow':'CAP_EXCEEDED',
                   'timeout':'DEADLINE_EXCEEDED','no_init':'DEADLINE_EXCEEDED','after_result':'EVENT_AFTER_RESULT',
                   'report_cap':'REPORT_RESPONSE','custody':None,'primary_custody':'OPERATIONAL_TOOL',
                   'cleanup':None,'primary_cleanup':'OPERATIONAL_TOOL','audit':None,
                   'qualification':'OFFLINE_QUALIFICATION_REQUIRED','stale_input':'INPUT_PIN','stale_runtime':'NATIVE_PIN',
                   'stale_package':'PACKAGE_PIN','no_authorization':None,'one_shot':None,
                   'prompt_no_read':'DEADLINE_EXCEEDED','prompt_slow_read':None,
                   'prompt_stdout_backpressure':None,'prompt_stderr_backpressure':None,
                   'prompt_pipe_closed':'PROMPT_PIPE_CLOSED','prompt_partial_close':'PROMPT_PIPE_CLOSED',
                   'prompt_outputs_closed':'DEADLINE_EXCEEDED','prompt_slow_timeout':'DEADLINE_EXCEEDED',
                   'prompt_early_result':'RESULT_BEFORE_PROMPT_COMPLETE'}
        successful=None
        for mode,expected in run_modes.items():
            case=output/(family+'-run-'+mode);case.mkdir();root,d=packet(case,family);evidence=case/'evidence'
            if mode.startswith('prompt_'):
                ending=b'\n' if family=='ASCII_LF' else b'\r\n';unit=b'P' if family=='ASCII_LF' else '条件λ'.encode()
                size=131072-len(ending);prompt=unit*(size//len(unit))+b'x'*(size%len(unit))+ending
                require(len(prompt)==131072,'MAXIMUM_ALLOWED_PROMPT');prompt.decode('utf-8')
                (root/'PROMPT.txt').write_bytes(prompt);d['prompt'].update(sha256=m.sha(prompt),bytes=len(prompt));(root/'PACKET.json').write_text(json.dumps(d))
            require(invoke(['prepare',str(root/'PACKET.json'),str(metadata),str(evidence)],case/'PREPARE-COMMAND.json')[0]==0,'RUN_PREPARE')
            qualification=case/'MOCK-QUALIFICATION.json'
            save(qualification,dict(status='PASS' if mode!='qualification' else 'STOPPED',scope='OFFLINE_ONLY',twoFreshRuns=True,packageFiles=package_before,fixture='Synthetic qualification claim, not actual acceptance; process transport intercepted'))
            report='# 1. Configuration\n\n# 2. Sources\n\n# 3. Questions\n### Q01: Fixture\nANSWERED\n- `[S01:1]` `Valid record`\n\n# 4. Findings\nNone\n# 5. Completeness\nCOMPLETE\n# 6. Assessment\nNO_BLOCKERS_FOUND\n# 7. Limits\nSynthetic only\n# 8. Actions\nNo provider call\n'
            ending=b'\n' if family=='ASCII_LF' else b'\r\n'
            if family=='UNICODE_CRLF':report=report.replace('Configuration','Configuration 条件 λ').replace('\n','\r\n')
            init=dict(event='init',init=dict(model=m.MODEL if mode!='wrong_init' else 'other',agent='preflight-inline',cwd='/review',permission_mode='request-review',tools=['finish']))
            step=dict(event='step_update',step_update=dict(step_type='agent_response',state='ACTIVE' if mode=='incomplete' else 'DONE',step_index=0))
            if mode in ('operational','primary_custody','primary_cleanup'):step['step_update'].update(step_type='tool',tool_name='command')
            if mode=='delegation':step['step_update']['subagent_info']={'subagents':[{}]}
            if mode=='error_step':step['step_update'].update(step_type='error_message',state='ERROR')
            result=dict(event='result',result=dict(status='FAILED' if mode=='result_failure' else 'SUCCESS',num_turns=1,response=('X'*32769) if mode=='report_cap' else report))
            lines=[json.dumps(step,ensure_ascii=False).encode()+ending,json.dumps(result,ensure_ascii=False).encode()+ending]
            if mode=='malformed':lines=[b'not JSON\n']
            if mode=='duplicate':lines=[b'{"event":"result","event":"result"}\n']
            if mode=='truncated':lines=[b'{"event":']
            if mode=='missing_result':lines=lines[:1]
            if mode=='after_result':lines.append(lines[-1])
            proxy=case/'proxy.py';native=case/'native.py'
            fixture(proxy,"import sys,time\nfrom pathlib import Path\nPath(sys.argv[1]).touch(exist_ok=False)\nwhile True: time.sleep(1)\n")
            code=("import json,os,sys,time\nfrom pathlib import Path\nmode="+repr(mode)+"\nroot=Path("+repr(str(evidence))+")\n"
                  "if mode=='no_init': time.sleep(5)\n"
                  "if mode=='prompt_pipe_closed': os.close(0)\n"
                  "sys.stdout.buffer.write("+repr(json.dumps(init).encode()+ending)+");sys.stdout.buffer.flush()\n"
                  "if mode=='prompt_no_read': time.sleep(5)\n"
                  "if mode=='prompt_outputs_closed': os.close(1);os.close(2);time.sleep(5)\n"
                  "if mode=='prompt_partial_close':\n    (root/'PROMPT-PREFIX.bin').write_bytes(os.read(0,32));os.close(0);time.sleep(5)\n"
                  "if mode=='prompt_slow_timeout':\n    while True: os.read(0,1);time.sleep(.05)\n"
                  "if mode=='prompt_pipe_closed': time.sleep(5)\n"
                  "if mode=='prompt_early_result':\n    sys.stdout.buffer.write("+repr(b''.join(lines))+");sys.stdout.buffer.flush();time.sleep(5)\n"
                  "if mode=='prompt_stdout_backpressure':\n"
                  "    for index in range(1,9):\n"
                  "        event=dict(event='step_update',step_update=dict(step_type='agent_response',state='DONE',step_index=index,text_delta='X'*32768))\n"
                  "        sys.stdout.buffer.write(json.dumps(event).encode()+b'\\n');sys.stdout.buffer.flush()\n"
                  "if mode=='prompt_stderr_backpressure': sys.stderr.buffer.write(b'x'*262144);sys.stderr.buffer.flush()\n"
                  "prompt=b''\n"
                  "if mode=='prompt_slow_read':\n    while not prompt.endswith(b'\\n'):\n        part=sys.stdin.buffer.read(1024)\n        if not part: break\n        prompt+=part;time.sleep(.001)\n"
                  "else: prompt=sys.stdin.buffer.readline()\n"
                  "(root/'PROMPT-RECEIVED.bin').write_bytes(prompt)\n"
                  "if mode.startswith('prompt_'): assert sys.stdin.buffer.read(1)==b''\n"
                  "if mode=='timeout': time.sleep(5)\n"
                  "if mode in ('custody','primary_custody'): (root/'packet/PROMPT.txt').write_bytes(b'changed')\n"
                  "if mode=='audit': (root/'private-home/preflight-hook-events.jsonl').write_bytes(b'not JSON')\n"
                  "if mode=='stderr_overflow': sys.stderr.buffer.write(b'x'*2097153);sys.stderr.buffer.flush()\n"
                  "if mode=='stdout_overflow': sys.stdout.buffer.write(b'x'*2097153);sys.stdout.buffer.flush()\n"
                  "for line in "+repr(lines)+": sys.stdout.buffer.write(line);sys.stdout.buffer.flush()\n"
                  "sys.exit(3 if mode=='exit_nonzero' else 0)\n")
            fixture(native,code);calls=[];children=[]
            def popen(command,**kwargs):
                calls.append(command)
                if command[0]=='/usr/bin/xdg-dbus-proxy':
                    require(command[3:]==['--filter','--talk=org.freedesktop.secrets'],'PROXY_BOUNDARY')
                    child=REAL_POPEN([sys.executable,'-B','-I',str(proxy),command[2]],**kwargs);children.append(child);return child
                require(command[0]=='/usr/bin/bwrap','UNEXPECTED_EXECUTABLE')
                require(command[1:4]==['--die-with-parent','--unshare-all','--share-net'],'NAMESPACE_ARGS')
                for path,target in [('review-workspace','/review'),('runtime/agy','/runtime/agy')]:
                    require(['--ro-bind',str(evidence/path),target] in [command[i:i+3] for i in range(len(command)-2)],'READ_ONLY_BIND')
                native_args=command[command.index('/runtime/agy',command.index('--chdir'))+1:]
                require(native_args==['--input-format','stream-json','--output-format','stream-json','--agent','preflight-inline','--model',m.MODEL,'--effort','high','--disable-slash-commands','--print-timeout','10m','--new-project'],'EXACT_NATIVE_ARGS')
                require(kwargs['env']==dict(HOME='/home/john',PATH='/usr/bin:/bin',USER='john',LOGNAME='john',LANG='C.UTF-8'),'FILTERED_ENV')
                settings=json.loads((evidence/'private-home/.gemini/antigravity-cli/settings.json').read_bytes());require(settings['useG1Credits'] is False and settings['permissions']['deny'],'PRIVATE_SETTINGS')
                child=REAL_POPEN([sys.executable,'-B','-I',str(native)],**kwargs);children.append(child)
                if mode.startswith('prompt_'):
                    fcntl.fcntl(child.stdin.fileno(),fcntl.F_SETPIPE_SZ,4096)
                    capacity=fcntl.fcntl(child.stdin.fileno(),fcntl.F_GETPIPE_SZ)
                    save(case/'PIPE-CAPACITY.json',dict(stdinBytes=capacity,sourcePromptBytes=131072,watchdogSeconds=5))
                    require(capacity<131072,'PROMPT_LARGER_THAN_PIPE')
                return child
            if mode=='stale_input':(evidence/'packet/PROMPT.txt').write_bytes(b'changed')
            if mode=='stale_runtime':(evidence/'runtime/agy').chmod(0o755);(evidence/'runtime/agy').write_bytes(b'changed')
            if mode=='stale_package':
                p=json.loads((evidence/'CLI-PLAN.json').read_bytes());p['packageFiles']['scripts/cli_review.py']['sha256']='0'*64;(evidence/'CLI-PLAN.json').write_text(json.dumps(p));v=json.loads((evidence/'PREPARE-RESULT.json').read_bytes());v['plan']=m.pin(evidence/'CLI-PLAN.json');(evidence/'PREPARE-RESULT.json').write_text(json.dumps(v))
            def rmtree(path,*a,**kw):
                if mode in ('cleanup','primary_cleanup') and Path(path)==evidence/'private-home':raise OSError('synthetic cleanup failure')
                return REAL_RMTREE(path,*a,**kw)
            m.subprocess.Popen=popen;m.shutil.rmtree=rmtree;old_host=m.HOST_SECONDS;old_init=m.INIT_SECONDS
            if mode=='timeout':m.HOST_SECONDS=.35
            if mode=='no_init':m.INIT_SECONDS=.25
            if mode in ('prompt_no_read','prompt_outputs_closed','prompt_slow_timeout'):m.HOST_SECONDS=.5
            def watchdog(signum,frame):raise AssertionError('OFFLINE_PROMPT_WATCHDOG')
            old_alarm=signal.getsignal(signal.SIGALRM)
            if mode.startswith('prompt_'):signal.signal(signal.SIGALRM,watchdog);signal.setitimer(signal.ITIMER_REAL,5)
            args=['run',str(evidence),'--qualification',str(qualification)]
            if mode!='no_authorization':args.append('--authorize-live')
            try:code,result_value=invoke(args,case/'RUN-COMMAND.json')
            finally:
                if mode.startswith('prompt_'):signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,old_alarm)
                m.subprocess.Popen=REAL_POPEN;m.shutil.rmtree=REAL_RMTREE;m.HOST_SECONDS=old_host;m.INIT_SECONDS=old_init
            for child in children:
                require(child.poll() is not None,'FIXTURE_CHILD_REAPED')
                try:os.killpg(child.pid,0)
                except ProcessLookupError:pass
                else:raise AssertionError('FIXTURE_PROCESS_GROUP_REMAINS')
            save(case/'TRANSPORT-DOUBLE.json',dict(actualRequestedCommands=calls,realNativeCalls=0,realProxyCalls=0,generativeCalls=0,fixtureChildren=len(calls),fixtureGroupsAbsent=True))
            if mode=='no_authorization':
                require(code==2 and not calls and not (evidence/'CLI-GATE.json').exists(),'EXPLICIT_AUTHORIZATION_FLAG')
            else:
                receipt=json.loads((evidence/'CLI-RECEIPT.json').read_bytes());failure=receipt['failure']['code'] if receipt['failure'] else None
                require(failure==expected,('RUN_REASON',mode,receipt))
                is_closing=mode in ('custody','primary_custody','cleanup','primary_cleanup','audit','stale_input','stale_runtime','stale_package')
                require(code==(1 if expected or is_closing else 0),('RUN_EXIT',mode,receipt))
                require(bool(receipt['closingFailures'])==is_closing,('CLOSING_EXPECTATION',mode,receipt))
                require(all(not p['spawned'] or p['reaped'] for p in receipt['processes'].values()),'DIRECT_CHILD_REAPED')
                require(receipt['socketDirectoryAbsent'],'SOCKET_REMOVED')
                require(receipt['privateHomeAbsent']==(mode not in ('cleanup','primary_cleanup')),'HOME_REMOVED')
                require(receipt['retries']==0 and receipt['qualificationCredit']==0,'NO_RETRY_OR_CREDIT')
                if mode in ('wrong_init','no_init','qualification','stale_input','stale_runtime','stale_package'):
                    require(not receipt['promptSent'] and not (evidence/'PROMPT-RECEIVED.bin').exists(),'NO_PROMPT_BEFORE_BINDING')
                if not calls:require(receipt['invocations']==dict(proxy=0,native=0),'NO_PROCESS_BEFORE_PINS')
                if mode in ('valid','one_shot'):
                    require((evidence/'GEMINI-REVIEW.md').read_bytes()==report.encode(),'REPORT_EXACT')
                    require(receipt['report']==dict(sha256=hashlib.sha256(report.encode()).hexdigest(),bytes=len(report.encode())),'RECEIPT_BINDS_EXACT_REPORT_BYTES')
                    wire=json.loads((evidence/'PROMPT-RECEIVED.bin').read_bytes());require(wire['message']['content'].encode()==(root/'PROMPT.txt').read_bytes(),'EXACT_SINGLE_PROMPT')
                    successful=evidence
                if mode.startswith('prompt_'):
                    delivery=receipt['promptDelivery'];require(delivery['wireBytes']>131072,'FULL_JSON_FRAME_ACCOUNTED')
                    if expected is None:
                        require(receipt['promptSent'] and delivery['status']=='COMPLETE' and delivery['bytesWritten']==delivery['wireBytes'],'PROMPT_COMPLETE_ONCE')
                        wire=json.loads((evidence/'PROMPT-RECEIVED.bin').read_bytes());require(wire['message']['content'].encode()==(root/'PROMPT.txt').read_bytes(),'MAX_PROMPT_EXACT_DELIVERY')
                        require((evidence/'GEMINI-REVIEW.md').read_bytes()==report.encode(),'PROMPT_CONTROL_REPORT_EXACT')
                        if mode=='prompt_stdout_backpressure':require(receipt['transport']['stdout']['bytes']>262144,'STDOUT_DRAINED_DURING_WRITE')
                        if mode=='prompt_stderr_backpressure':require(receipt['transport']['stderr']['bytes']==262144,'STDERR_DRAINED_DURING_WRITE')
                    else:
                        require(not receipt['promptSent'] and delivery['bytesWritten']<delivery['wireBytes'] and not (evidence/'GEMINI-REVIEW.md').exists(),'INCOMPLETE_PROMPT_NOT_ADMITTED')
                        if mode in ('prompt_no_read','prompt_partial_close','prompt_outputs_closed','prompt_slow_timeout'):require(delivery['status']=='PARTIAL' and delivery['bytesWritten']>0,'PARTIAL_BYTES_ACCOUNTED')
                        if mode in ('prompt_no_read','prompt_outputs_closed','prompt_slow_timeout'):require(receipt['elapsedSeconds']<3,'DEADLINE_NOT_BLOCKED_BY_STDIN')
                if mode=='one_shot':
                    saved=m.pin(evidence/'CLI-RECEIPT.json');m.subprocess.Popen=lambda *a,**kw:(_ for _ in ()).throw(AssertionError('SECOND_INVOCATION'))
                    try:again,value=invoke(args,case/'SECOND-COMMAND.json')
                    finally:m.subprocess.Popen=REAL_POPEN
                    require(again==1 and value['failure']=='ATTEMPT_ALREADY_CONSUMED' and m.pin(evidence/'CLI-RECEIPT.json')==saved,'SINGLE_USE_GATE')
                if mode in ('cleanup','primary_cleanup'):REAL_RMTREE(evidence/'private-home')
            cases.append(dict(family=family,stage='run',case=mode,status='PASS',realNativeCalls=0,fixtureChildren=len(calls)))

        for mode,expected in {'valid':None,'coordinate':'QUOTE_MISMATCH','range':'LINE_OUT_OF_RANGE','report_hash':'REPORT_HASH','unknown_source':'UNKNOWN_SOURCE','duplicate_id':'DUPLICATE_CITATION_ID','malformed':'JSONDecodeError','source_pin':'INPUT_PIN','one_shot':None,
                              'report_rehashed':'REPORT_CUSTODY','report_resized_rehashed':'REPORT_CUSTODY',
                              'report_missing':'REGULAR_FILE_REQUIRED','report_pin_missing':'REPORT_PIN_REQUIRED',
                              'report_pin_hash':'REPORT_PIN_REQUIRED','report_pin_bytes':'REPORT_PIN_REQUIRED',
                              'report_pin_boolean_bytes':'REPORT_PIN_REQUIRED','report_pin_wrong_bytes':'REPORT_CUSTODY'}.items():
            case=output/(family+'-citation-'+mode);case.mkdir();evidence=case/'evidence';shutil.copytree(successful,evidence)
            ledger=dict(reportSha256=m.pin(evidence/'GEMINI-REVIEW.md')['sha256'],citations=[dict(id='Q01-P1',source='S01',line=1,quote='Valid record')])
            if mode=='coordinate':ledger['citations'][0]['line']=2
            if mode=='range':ledger['citations'][0]['line']=100
            if mode=='report_hash':ledger['reportSha256']='0'*64
            if mode=='unknown_source':ledger['citations'][0]['source']='S99'
            if mode=='duplicate_id':ledger['citations'].append(ledger['citations'][0])
            if mode=='source_pin':(evidence/'packet/snapshots/source.txt').write_bytes(b'changed')
            if mode in ('report_rehashed','report_resized_rehashed'):
                path=evidence/'GEMINI-REVIEW.md';before=path.read_bytes()
                changed=(b'!'+before[1:]) if mode=='report_rehashed' else before+b'changed'
                require(changed!=before,'REPORT_MUTATION_OCCURRED');path.write_bytes(changed)
                ledger['reportSha256']=hashlib.sha256(changed).hexdigest()
                require(ledger['reportSha256']!=json.loads((evidence/'CLI-RECEIPT.json').read_bytes())['report']['sha256'],'LEDGER_REHASHED_MUTATED_REPORT')
            if mode=='report_missing':(evidence/'GEMINI-REVIEW.md').unlink()
            if mode.startswith('report_pin_'):
                path=evidence/'CLI-RECEIPT.json';receipt=json.loads(path.read_bytes())
                if mode=='report_pin_missing':receipt.pop('report')
                if mode=='report_pin_hash':receipt['report']['sha256']='invalid'
                if mode=='report_pin_bytes':receipt['report']['bytes']=-1
                if mode=='report_pin_boolean_bytes':receipt['report']['bytes']=True
                if mode=='report_pin_wrong_bytes':receipt['report']['bytes']+=1
                path.write_text(json.dumps(receipt))
            receipt_before=m.pin(evidence/'CLI-RECEIPT.json')
            report_before=(evidence/'GEMINI-REVIEW.md').read_bytes() if (evidence/'GEMINI-REVIEW.md').exists() else None
            save(case/'ledger.json',ledger)
            if mode=='malformed':(case/'ledger.json').write_bytes(b'not JSON')
            m.subprocess.Popen=lambda *a,**kw:(_ for _ in ()).throw(AssertionError('CITATION_CHECK_MUST_NOT_EXECUTE'))
            try:code,value=invoke(['check-citations',str(evidence),str(case/'ledger.json')],case/'COMMAND.json')
            finally:m.subprocess.Popen=REAL_POPEN
            require(code==(0 if expected is None else 1),'CITATION_EXIT')
            require(m.pin(evidence/'CLI-RECEIPT.json')==receipt_before,'CITATION_PRESERVES_RECEIPT')
            require(((evidence/'GEMINI-REVIEW.md').read_bytes() if (evidence/'GEMINI-REVIEW.md').exists() else None)==report_before,'CITATION_PRESERVES_REPORT')
            if expected:require(not (evidence/'CITATION-LEDGER.json').exists(),'FAILED_LEDGER_NOT_ADMITTED')
            if expected:require(value['failure']==expected,('CITATION_REASON',mode,value))
            else:require(json.loads((evidence/'CITATION-RESULT.json').read_bytes())['citations']==1,'CITATION_COUNT')
            if mode=='one_shot':
                before=m.pin(evidence/'CITATION-RESULT.json');again,value=invoke(['check-citations',str(evidence),str(case/'ledger.json')],case/'SECOND-COMMAND.json');require(again==1 and value['failure']=='CITATION_CHECK_ALREADY_RECORDED' and m.pin(evidence/'CITATION-RESULT.json')==before,'CITATION_RESULT_PRESERVED')
            cases.append(dict(family=family,stage='citation',case=mode,status='PASS'))
    require(m.package_identity()==package_before,'FINAL_PACKAGE_CUSTODY')
    require(len({(row['family'],row['stage'],row['case']) for row in cases})==len(cases),'DISTINCT_CASE_IDENTITIES')
    save(output/'RESULT.json',dict(status='PASS',caseCount=len(cases),families=2,cases=cases,realNativeCalls=0,realProxyCalls=0,generativeCalls=0,method='Actual saved main entrypoint; only Popen process transport and injected cleanup faults replaced; real generated-child pipes',limits='Not native containment, tool-denial, provider or activation qualification'))
    print(json.dumps(dict(status='PASS',caseCount=len(cases),families=2,realNativeCalls=0)))
if __name__=='__main__':main(Path(sys.argv[1]).absolute(),Path(sys.argv[2]).absolute())
