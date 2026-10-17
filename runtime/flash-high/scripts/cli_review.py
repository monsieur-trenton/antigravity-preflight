"""Reusable bounded Flash review launcher. Live use needs explicit authorization.

prepare and check-citations are local operations; run is the only live command.
Offline qualification is not native containment or activation qualification.
"""
import argparse,hashlib,importlib.util,json,os,re,selectors,shutil,signal,subprocess,sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
PACKAGE=ROOT.parent
MODEL='gemini-3.8-flash-high'
CAP=2097152
HOST_SECONDS=600
INIT_SECONDS=45
def need(ok,code):
    if not ok: raise ValueError(code)
def sha(b): return hashlib.sha256(b).hexdigest()
def decode(b):
    def pairs(rows):
        result={}
        for key,value in rows:
            need(key not in result,'DUPLICATE_KEY');result[key]=value
        return result
    return json.loads(b,object_pairs_hook=pairs,parse_constant=lambda x:(_ for _ in ()).throw(ValueError('NONFINITE')))
def save(path,data):
    with Path(path).open('x',encoding='utf-8') as out:out.write(json.dumps(data,indent=2)+'\n')
class Stream:
    def __init__(self):self.init=None;self.result=None;self.steps={};self.events=0;self.ledger=[];self.ledger_omitted=0
    def line(self,raw):
        event=decode(raw);need(type(event) is dict,'EVENT_OBJECT');kind=event.get('event');need(self.result is None,'EVENT_AFTER_RESULT')
        row=dict(ordinal=self.events,kind=kind if kind in ('init','step_update','result') else 'OTHER',bytes=len(raw))
        if len(self.ledger)<256:self.ledger.append(row)
        else:self.ledger_omitted+=1
        if kind=='init':
            item=event.get('init');need(self.init is None and self.events==0 and type(item) is dict,'INIT_SEQUENCE')
            need(item.get('model')==MODEL and item.get('agent')=='preflight-inline' and item.get('cwd')=='/review' and item.get('permission_mode')=='request-review','INIT_BINDING')
            need(type(item.get('tools')) is list and bool(item['tools']) and all(type(x) is str for x in item['tools']),'INIT_CATALOG')
            self.init=item
        elif kind=='step_update':
            need(self.init is not None,'MISSING_INIT');item=event.get('step_update');need(type(item) is dict,'STEP_OBJECT')
            label=item.get('step_type');state=item.get('state');index=item.get('step_index')
            row.update(stepType=label if label in ('tool','user_input','agent_response','checkpoint','finish','error_message','subagent') else 'OTHER',state=state if state in ('ACTIVE','DONE','ERROR') else 'OTHER')
            need(type(index) is int and index>=0,'STEP_INDEX');need(state in ('ACTIVE','DONE'),'STEP_STATE')
            need(not item.get('subagent_info'),'DELEGATION_PAYLOAD')
            if label=='tool':
                name=item.get('tool_name');need(name=='finish' or name=='' and state=='ACTIVE','OPERATIONAL_TOOL');info=item.get('tool_info')
                need(info is None or type(info) is dict and info.get('name') in (None,'','finish') and not info.get('error'),'FINISH_PAYLOAD')
                need(name=='finish' or not info,'UNNAMED_TOOL_PAYLOAD')
            else:
                need(label in ('user_input','agent_response','checkpoint','finish'),'UNQUALIFIED_STEP')
                need(not item.get('tool_name') and not item.get('tool_info'),'EXECUTION_PAYLOAD')
                need(label!='finish' or state=='DONE','FINISH_STATE')
            previous=self.steps.get(index);need(previous is None or previous[1]!='DONE','STEP_AFTER_DONE')
            native_finish=previous==('tool','ACTIVE') and label=='finish' and state=='DONE'
            need(previous is None or previous[0]==label or native_finish,'STEP_TYPE_CHANGED')
            self.steps[index]=(label,state)
        elif kind=='result':
            need(self.init is not None,'MISSING_INIT');item=event.get('result');need(type(item) is dict,'RESULT_OBJECT')
            need(item.get('status')=='SUCCESS' and not item.get('error'),'RESULT_FAILURE')
            need(type(item.get('num_turns')) is int and item['num_turns']==1,'TURN_COUNT')
            need(self.steps and all(row[1]=='DONE' for row in self.steps.values()),'INCOMPLETE_STEPS')
            need(type(item.get('response')) is str and bool(item['response'].strip()) and len(item['response'].encode())<=32768,'REPORT_RESPONSE')
            self.result=item
        else:raise ValueError('UNQUALIFIED_EVENT')
        self.events+=1
def qualify():
    cases=[]
    init=dict(event='init',init=dict(model=MODEL,agent='preflight-inline',cwd='/review',permission_mode='request-review',tools=['finish']))
    for family,text in [('ASCII_LF','fixture\n'),('UNICODE_CRLF','条件\r\n')]:
        for mode in ('positive','pending_finish','native_finish','pending_native_finish','wrong_model','operational','delegation','finish_error','missing_response','double_result','incomplete_step','duplicate_key'):
            s=Stream();items=[init,dict(event='step_update',step_update=dict(step_type='agent_response',state='DONE',step_index=0)),dict(event='result',result=dict(status='SUCCESS',num_turns=1,response=text))]
            items=json.loads(json.dumps(items));expected=None
            if mode in ('positive','pending_finish','native_finish','pending_native_finish'):
                start_name='' if mode in ('pending_finish','pending_native_finish') else 'finish'
                terminal=dict(step_type='finish',state='DONE',step_index=1) if mode in ('native_finish','pending_native_finish') else dict(step_type='tool',tool_name='finish',state='DONE',step_index=1)
                items[2:2]=[dict(event='step_update',step_update=dict(step_type='tool',tool_name=start_name,state='ACTIVE',step_index=1)),dict(event='step_update',step_update=terminal)]
            if mode=='wrong_model':items[0]['init']['model']='other';expected='INIT_BINDING'
            if mode=='operational':items[1]['step_update'].update(step_type='tool',tool_name='run_command');expected='OPERATIONAL_TOOL'
            if mode=='delegation':items[1]['step_update']['subagent_info']={'subagents':[{}]};expected='DELEGATION_PAYLOAD'
            if mode=='finish_error':items[1]['step_update'].update(step_type='tool',tool_name='finish',state='ERROR');expected='STEP_STATE'
            if mode=='missing_response':items[2]['result'].pop('response');expected='REPORT_RESPONSE'
            if mode=='double_result':items.append(items[2]);expected='EVENT_AFTER_RESULT'
            if mode=='incomplete_step':items[1]['step_update']['state']='ACTIVE';expected='INCOMPLETE_STEPS'
            if mode=='duplicate_key':expected='DUPLICATE_KEY'
            try:
                for item in items:s.line(b'{"event":"init","event":"result"}' if mode=='duplicate_key' else json.dumps(item,ensure_ascii=False).encode())
            except ValueError as error:need(str(error)==expected,'QUALIFICATION_REASON')
            else:need(expected is None and s.result['response']==text,'QUALIFICATION_ACCEPTANCE')
            cases.append(dict(family=family,case=mode,status='PASS'))
    return dict(status='PASS',families=2,caseCount=len(cases),cases=cases,nativeCalls=0,limits='Pure parser controls only; not native containment qualification')

CODE_FILES=('scripts/cli_review.py','scripts/cli_capabilities.py','scripts/manual_citations.py',
            'assets/cli-review/deny_tools.py','assets/cli-review/.agents/hooks.json',
            'assets/cli-review/.agents/agents/preflight-inline.md')
def pin(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as source:
        for chunk in iter(lambda:source.read(1048576),b''):h.update(chunk)
    return dict(sha256=h.hexdigest(),bytes=Path(path).stat().st_size)
def package_identity():return {name:pin(PACKAGE/name) for name in CODE_FILES}
def load_module(name):
    spec=importlib.util.spec_from_file_location('preflight_'+name,ROOT/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
def local_file(root,name):
    need(type(name) is str and bool(name),'PATH_REQUIRED');relative=Path(name)
    need(not relative.is_absolute() and '..' not in relative.parts and relative.as_posix()==name,'PATH_ESCAPE')
    result=Path(root)
    for part in relative.parts:
        result=result/part;need(not result.is_symlink(),'SYMLINK_REFUSED')
    need(result.is_file(),'REGULAR_FILE_REQUIRED');return result
def row_bytes(root,row,limit):
    need(type(row) is dict and type(row.get('bytes')) is int and 0<=row['bytes']<=limit,'INPUT_SIZE')
    need(type(row.get('sha256')) is str and re.fullmatch('[0-9a-f]{64}',row['sha256']),'INPUT_HASH_SHAPE')
    path=local_file(root,row.get('path'));need(path.stat().st_size==row['bytes'],'INPUT_BYTES')
    body=path.read_bytes();need(sha(body)==row['sha256'],'INPUT_HASH');body.decode('utf-8');return body
def prepare(packet_path,capability,root):
    packet_path=Path(packet_path).absolute();capability=Path(capability).absolute();root=Path(root).absolute()
    need(not packet_path.is_symlink(),'SYMLINK_REFUSED')
    for source in (packet_path.parent.resolve(),capability.resolve(),PACKAGE.resolve()):
        need(root.resolve()!=source and source not in root.resolve().parents,'EVIDENCE_INSIDE_INPUT')
    root.mkdir(parents=True,exist_ok=False)
    try:
        need(packet_path.stat().st_size<=131072,'PACKET_DESCRIPTOR_CAP')
        descriptor=decode(packet_path.read_bytes())
        need(type(descriptor) is dict and type(descriptor.get('schemaVersion')) is int and descriptor.get('schemaVersion')==1 and descriptor.get('mode') in ('PLAN','DIFF'),'PACKET_CONTRACT')
        questions=descriptor.get('questions');rows=descriptor.get('sources')
        need(type(questions) is list and 0<len(questions)<=99 and all(type(x) is str and re.fullmatch('Q[0-9]{2}',x) for x in questions) and len(set(questions))==len(questions),'QUESTION_IDENTITIES')
        need(type(rows) is list and 0<len(rows)<=99,'SOURCE_INVENTORY')
        prompt=row_bytes(packet_path.parent,descriptor.get('prompt'),131072);need(bool(prompt.strip()),'EMPTY_PROMPT')
        names=[descriptor['prompt']['path']];source_ids=[];bodies=[]
        for row in rows:
            need(type(row) is dict and type(row.get('id')) is str and re.fullmatch('S[0-9]{2}',row['id']),'SOURCE_ID')
            source_ids.append(row['id']);names.append(row['path']);bodies.append(row_bytes(packet_path.parent,row,131072))
        need(len(set(source_ids))==len(source_ids) and len(set(names))==len(names),'DUPLICATE_INPUT')
        need('PACKET.json' not in names and sum(map(len,bodies))<=131072,'PACKET_SOURCE_CAP')
        # Revalidate captured metadata, without running agy or querying a provider.
        meta=decode(local_file(capability,'RESULT.json').read_bytes())
        need(meta.get('status')=='PASS_METADATA_CAPABILITIES_ONLY' and meta.get('binaryStable') is True,'CAPABILITY_REQUIRED')
        runtime=local_file(capability,'runtime/agy');native=pin(runtime)
        need(native==meta.get('frozenBinary'),'NATIVE_PIN')
        before=decode(local_file(capability,'NATIVE-BEFORE.json').read_bytes());after=decode(local_file(capability,'NATIVE-AFTER.json').read_bytes())
        need(all({k:item.get(k) for k in ('sha256','bytes')}==native for item in (before,after)),'METADATA_NATIVE_BINDING')
        metadata_names=['RESULT.json','NATIVE-BEFORE.json','NATIVE-AFTER.json']
        for name in ('VERSION','HELP','MODELS'):
            record=decode(local_file(capability,name+'.json').read_bytes())
            need(record.get('args')=={'VERSION':['--version'],'HELP':['--help'],'MODELS':['models']}[name] and record.get('returncode')==0 and record.get('failure') is None and record.get('cleanupFailures')==[] and record.get('directChildReaped') is True,'METADATA_OUTCOME')
            for channel in ('stdout','stderr'):
                path=local_file(capability,name+'.'+channel);need(path.stat().st_size<=1048576 and pin(path)==record.get('streams',{}).get(channel),'METADATA_STREAM_PIN')
                metadata_names.append(name+'.'+channel)
            metadata_names.append(name+'.json')
        observed=load_module('cli_capabilities').interpret(capability)
        need(all(meta.get(k)==v for k,v in observed.items()),'METADATA_INTERPRETATION')
        packet=root/'packet';packet.mkdir();(packet/'PACKET.json').write_bytes(packet_path.read_bytes())
        for name,body in zip(names,[prompt,*bodies]):
            target=packet/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(body)
        (root/'metadata').mkdir()
        for name in metadata_names:shutil.copyfile(capability/name,root/'metadata'/name)
        (root/'runtime').mkdir();shutil.copyfile(runtime,root/'runtime/agy');(root/'runtime/agy').chmod(0o555)
        shutil.copytree(PACKAGE/'assets/cli-review',root/'review-workspace')
        save(root/'CITATION-INVENTORY.json',{'sources':[dict(id=row['id'],path='packet/'+row['path'],sha256=row['sha256']) for row in rows]})
        inputs={str(p.relative_to(root)):pin(p) for p in sorted(root.rglob('*')) if p.is_file() and p!=root/'runtime/agy'}
        plan=dict(schemaVersion=1,mode=descriptor['mode'],prompt='packet/'+descriptor['prompt']['path'],questions=questions,
                  sources=source_ids,inputs=inputs,native=native,packageFiles=package_identity(),model=MODEL,effort='high',
                  observedVersion=observed['observedVersion'],nativeInvocations=1,proxyInvocations=1,turns=1,hostRetries=0,
                  hostDeadlineSeconds=HOST_SECONDS,initDeadlineSeconds=INIT_SECONDS,perStreamCapBytes=CAP,
                  promptCapBytes=131072,reportCapBytes=32768,qualificationCredit=0)
        save(root/'CLI-PLAN.json',plan);save(root/'PREPARE-RESULT.json',dict(status='PREPARED_NOT_LAUNCHED',generativeCalls=0,plan=pin(root/'CLI-PLAN.json')))
        return 0
    except Exception as error:
        save(root/'PREPARE-RESULT.json',dict(status='STOPPED',failure=failure_code(error),remainingChecks='UNRUN',generativeCalls=0));raise
def failure_code(error):return str(error) if type(error) is ValueError else type(error).__name__
def terminate(process):
    # A direct child that already exited may still have group descendants.
    try:os.killpg(process.pid,signal.SIGKILL)
    except ProcessLookupError:pass
    process.wait(timeout=5)
def run(root,qualification):
    root=Path(root).absolute();need(root.is_dir() and not root.is_symlink(),'EVIDENCE_REQUIRED')
    need(not (root/'CLI-GATE.json').exists(),'ATTEMPT_ALREADY_CONSUMED')
    save(root/'CLI-GATE.json',dict(status='CONSUMED',nativeInvocationLimit=1,proxyInvocationLimit=1,turnLimit=1,retries=0,qualificationCredit=0))
    started=time.monotonic();process=proxy=None;selector=None;s=Stream();outputs={'stdout':bytearray(),'stderr':bytearray()};buffer=bytearray()
    failure=None;closing=[];counts={'proxy':0,'native':0};sent=False;socketroot=None;plan=None;plan_pin=None;qualification_pin=None;report_pin=None;prompt_frame=None;prompt_offset=0
    try:
        prepared=decode((root/'PREPARE-RESULT.json').read_bytes());need(prepared.get('status')=='PREPARED_NOT_LAUNCHED','PREPARATION_REQUIRED')
        plan_pin=pin(root/'CLI-PLAN.json');need(plan_pin==prepared.get('plan'),'PLAN_PIN');plan=decode((root/'CLI-PLAN.json').read_bytes())
        need(plan['model']==MODEL and plan['effort']=='high' and plan['nativeInvocations']==plan['proxyInvocations']==plan['turns']==1 and plan['hostRetries']==0,'PLAN_LIMITS')
        need(plan['packageFiles']==package_identity(),'PACKAGE_PIN')
        for name,row in plan['inputs'].items():need(pin(local_file(root,name))==row,'INPUT_PIN')
        need(pin(local_file(root,'runtime/agy'))==plan['native'],'NATIVE_PIN')
        qualification=Path(qualification);qualification_pin=pin(qualification);q=decode(qualification.read_bytes())
        need(q.get('status')=='PASS' and q.get('scope')=='OFFLINE_ONLY' and q.get('packageFiles')==plan['packageFiles'],'OFFLINE_QUALIFICATION_REQUIRED')
        need(q.get('twoFreshRuns') is True,'DUAL_OFFLINE_REQUIRED')
        # The flag/record bind a requested operation; they are not proof of owner authority.
        home=root/'private-home';home.mkdir(mode=0o700);settings=home/'.gemini/antigravity-cli';settings.mkdir(parents=True)
        save(settings/'settings.json',dict(enableTelemetry=False,useG1Credits=False,allowNonWorkspaceAccess=False,permissions={'deny':['read_file(*)','write_file(*)','command(*)','read_url(*)','execute_url(*)','mcp(*)']}))
        config=home/'.gemini/config';config.mkdir(parents=True);shutil.copyfile(root/'review-workspace/.agents/hooks.json',config/'hooks.json')
        socketroot=Path(tempfile.mkdtemp(prefix='agy-preflight-',dir='/tmp'));bus=socketroot/'bus'
        address=os.environ.get('DBUS_SESSION_BUS_ADDRESS',f'unix:path=/run/user/{os.getuid()}/bus')
        proxy=subprocess.Popen(['/usr/bin/xdg-dbus-proxy',address,str(bus),'--filter','--talk=org.freedesktop.secrets'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True);counts['proxy']+=1
        while not bus.exists() and time.monotonic()-started<3:time.sleep(.02)
        need(bus.exists() and proxy.poll() is None,'AUTH_PROXY_START')
        args=['--input-format','stream-json','--output-format','stream-json','--agent','preflight-inline','--model',MODEL,'--effort','high','--disable-slash-commands','--print-timeout','10m','--new-project']
        command=['/usr/bin/bwrap','--die-with-parent','--unshare-all','--share-net']
        for path in ('/usr','/lib','/lib64','/etc'):
            if Path(path).exists():command+=['--ro-bind',path,path]
        resolver=Path('/etc/resolv.conf').resolve(strict=True)
        if not str(resolver).startswith('/etc/'):command+=['--ro-bind',str(resolver),str(resolver)]
        command+=['--proc','/proc','--dev','/dev','--tmpfs','/tmp','--bind',str(home),'/home/john','--ro-bind',str(root/'review-workspace'),'/review','--ro-bind',str(root/'runtime/agy'),'/runtime/agy','--ro-bind',str(bus),'/runtime/secret-service','--setenv','DBUS_SESSION_BUS_ADDRESS','unix:path=/runtime/secret-service','--setenv','AGY_PREFLIGHT_AUDIT','/home/john/preflight-hook-events.jsonl','--setenv','AGY_CLI_DISABLE_AUTO_UPDATE','true','--setenv','HOME','/home/john','--setenv','PATH','/usr/bin:/bin','--chdir','/review','/runtime/agy',*args]
        env=dict(HOME='/home/john',PATH='/usr/bin:/bin',USER='john',LOGNAME='john',LANG='C.UTF-8')
        process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env,start_new_session=True,bufsize=0);counts['native']+=1
        os.set_blocking(process.stdin.fileno(),False)
        selector=selectors.DefaultSelector()
        for name,pipe in [('stdout',process.stdout),('stderr',process.stderr)]:os.set_blocking(pipe.fileno(),False);selector.register(pipe,selectors.EVENT_READ,name)
        while selector.get_map():
            need(time.monotonic()-started<HOST_SECONDS and (s.init is not None or time.monotonic()-started<INIT_SECONDS),'DEADLINE_EXCEEDED')
            for key,_ in selector.select(.05):
                need(time.monotonic()-started<HOST_SECONDS,'DEADLINE_EXCEEDED')
                if key.data=='stdin':
                    try:written=os.write(key.fileobj.fileno(),memoryview(prompt_frame)[prompt_offset:prompt_offset+65536])
                    except BlockingIOError:continue
                    except BrokenPipeError:raise ValueError('PROMPT_PIPE_CLOSED') from None
                    need(written>0,'PROMPT_WRITE_ZERO');prompt_offset+=written
                    if prompt_offset==len(prompt_frame):
                        selector.unregister(key.fileobj);key.fileobj.close();sent=True
                    continue
                chunk=os.read(key.fileobj.fileno(),65536)
                if not chunk:selector.unregister(key.fileobj);continue
                name=key.data;need(len(outputs[name])+len(chunk)<=CAP,'CAP_EXCEEDED');outputs[name].extend(chunk)
                if name=='stdout':
                    buffer.extend(chunk)
                    while b'\n' in buffer:
                        raw,_,tail=buffer.partition(b'\n');buffer=bytearray(tail);need(bool(raw.strip()),'EMPTY_STREAM_LINE');s.line(bytes(raw))
                        need(s.result is None or sent,'RESULT_BEFORE_PROMPT_COMPLETE')
                        if s.init is not None and prompt_frame is None:
                            save(root/'CLI-INIT.json',{k:s.init.get(k) for k in ('model','agent','cwd','permission_mode')})
                            prompt_frame=json.dumps(dict(event='user',message=dict(content=(root/plan['prompt']).read_bytes().decode('utf-8')))).encode()+b'\n'
                            selector.register(process.stdin,selectors.EVENT_WRITE,'stdin')
        need(not buffer,'TRUNCATED_STREAM');need(sent,'PROMPT_NOT_DELIVERED')
        try:process.wait(timeout=min(5,max(0,HOST_SECONDS-(time.monotonic()-started))))
        except subprocess.TimeoutExpired:raise ValueError('DEADLINE_EXCEEDED') from None
        need(process.returncode==0,'PROCESS_EXIT');need(s.result is not None,'MISSING_RESULT')
        report_bytes=s.result['response'].encode('utf-8')
        report_pin=dict(sha256=sha(report_bytes),bytes=len(report_bytes))
        with (root/'GEMINI-REVIEW.md').open('xb') as report:report.write(report_bytes)
        need(pin(local_file(root,'GEMINI-REVIEW.md'))==report_pin,'REPORT_WRITE_CUSTODY')
    except Exception as error:failure=dict(code=failure_code(error),failureClass=type(error).__name__)
    finally:
        def close(phase,action):
            try:action()
            except Exception as error:closing.append(dict(phase=phase,failureClass=type(error).__name__,code=failure_code(error)))
        for kind,p in [('native',process),('proxy',proxy)]:
            if p is not None:
                close(kind+'_terminate',lambda p=p:terminate(p))
                for pipe in (p.stdin,p.stdout,p.stderr):
                    if pipe is not None:close(kind+'_pipe',pipe.close)
        if selector is not None:close('selector',selector.close)
        audit=root/'private-home/preflight-hook-events.jsonl'
        if audit.exists():
            def read_audit():
                rows=[decode(line) for line in audit.read_bytes().splitlines()];need(all(x==dict(tool='finish',decision='allow') for x in rows),'HOOK_OPERATION_ATTEMPT');save(root/'CLI-HOOK-AUDIT.json',rows)
            close('hook_audit',read_audit)
        if (root/'private-home').exists():close('home_remove',lambda:shutil.rmtree(root/'private-home'))
        if socketroot is not None:close('socket_remove',lambda:shutil.rmtree(socketroot))
        if plan is not None:
            def custody():
                need(pin(root/'CLI-PLAN.json')==plan_pin and package_identity()==plan['packageFiles'],'FINAL_PLAN_OR_PACKAGE_CUSTODY')
                need(all(pin(local_file(root,name))==row for name,row in plan['inputs'].items()) and pin(root/'runtime/agy')==plan['native'],'FINAL_CUSTODY')
                if qualification_pin is not None:need(pin(qualification)==qualification_pin,'FINAL_QUALIFICATION_CUSTODY')
                if report_pin is not None:need(pin(local_file(root,'GEMINI-REVIEW.md'))==report_pin,'FINAL_REPORT_CUSTODY')
            close('input_custody',custody)
        receipt=dict(status='STOPPED' if failure or closing else 'REPORT_RECEIVED_PENDING_ADJUDICATION',failure=failure,closingFailures=closing,
                     model=MODEL,effort='high',effortEvidence='launcher_configuration',servedAttestation='UNAVAILABLE',promptSent=sent,
                     elapsedSeconds=round(time.monotonic()-started,3),invocations=counts,retries=0,providerRequestCount='UNAVAILABLE',events=s.events,
                     promptDelivery=dict(status='COMPLETE' if sent else 'PARTIAL' if prompt_offset else 'NOT_STARTED',wireBytes=len(prompt_frame) if prompt_frame is not None else 0,bytesWritten=prompt_offset,meaning='Bytes accepted by host pipe; not proof of native consumption'),
                     eventLedger=s.ledger,eventLedgerStorage=dict(entryCap=256,storedRows=len(s.ledger),omittedRows=s.ledger_omitted,scope='Storage only; every event is validated'),
                     transport={k:dict(bytes=len(v),sha256=sha(v)) for k,v in outputs.items()},
                     processes={kind:dict(spawned=p is not None,reaped=p.poll() is not None if p is not None else None) for kind,p in [('native',process),('proxy',proxy)]},
                     report=report_pin,privateHomeAbsent=not (root/'private-home').exists(),socketDirectoryAbsent=socketroot is None or not socketroot.exists(),qualificationCredit=0)
        if plan is not None:receipt['native']=plan['native']
        save(root/'CLI-RECEIPT.json',receipt)
    return 1 if failure or closing else 0
def check_citations(root,ledger_path):
    root=Path(root).absolute();need(not (root/'CITATION-RESULT.json').exists(),'CITATION_CHECK_ALREADY_RECORDED')
    try:
        receipt=decode((root/'CLI-RECEIPT.json').read_bytes());need(receipt.get('status')=='REPORT_RECEIVED_PENDING_ADJUDICATION','ADMISSIBLE_TRANSPORT_REQUIRED')
        plan=decode((root/'CLI-PLAN.json').read_bytes());need(plan['packageFiles']==package_identity(),'PACKAGE_PIN')
        for name,row in plan['inputs'].items():need(pin(local_file(root,name))==row,'INPUT_PIN')
        report_pin=receipt.get('report')
        need(type(report_pin) is dict and set(report_pin)=={'sha256','bytes'} and type(report_pin.get('sha256')) is str and re.fullmatch('[0-9a-f]{64}',report_pin['sha256']) and type(report_pin.get('bytes')) is int and 0<report_pin['bytes']<=32768,'REPORT_PIN_REQUIRED')
        need(pin(local_file(root,'GEMINI-REVIEW.md'))==report_pin,'REPORT_CUSTODY')
        ledger=decode(Path(ledger_path).read_bytes());need(ledger.get('reportSha256')==report_pin['sha256'],'REPORT_HASH')
        checker=load_module('manual_citations')
        try:count=checker.check(checker.read_sources(root/'CITATION-INVENTORY.json'),ledger)
        except checker.Invalid as error:raise ValueError(str(error)) from error
        save(root/'CITATION-LEDGER.json',ledger);save(root/'CITATION-RESULT.json',dict(status='CITATIONS_MATCHED',citations=count,scope='SUPPLIED_LEDGER_ONLY_NOT_REVIEW_ADMISSION',remaining='Codex must check complete extraction, coverage and substantive premises'))
        return 0
    except Exception as error:
        save(root/'CITATION-RESULT.json',dict(status='STOPPED',failure=failure_code(error),remainingChecks='UNRUN'));raise
def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);commands=parser.add_subparsers(dest='command',required=True)
    p=commands.add_parser('prepare');p.add_argument('packet');p.add_argument('capabilities');p.add_argument('evidence')
    p=commands.add_parser('run');p.add_argument('evidence');p.add_argument('--qualification',required=True);p.add_argument('--authorize-live',required=True,action='store_true')
    p=commands.add_parser('check-citations');p.add_argument('evidence');p.add_argument('ledger')
    p=commands.add_parser('controls');p.add_argument('output')
    args=parser.parse_args(argv)
    try:
        if args.command=='prepare':code=prepare(args.packet,args.capabilities,args.evidence)
        elif args.command=='run':code=run(args.evidence,args.qualification)
        elif args.command=='check-citations':code=check_citations(args.evidence,args.ledger)
        else:save(args.output,qualify());code=0
        print(json.dumps(dict(status='COMMAND_COMPLETE' if code==0 else 'STOPPED',command=args.command)));return code
    except Exception as error:
        print(json.dumps(dict(status='STOPPED',command=args.command,failure=failure_code(error),remainingChecks='UNRUN')));return 1
if __name__=='__main__':sys.exit(main())
