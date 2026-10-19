import sys
sys.dont_write_bytecode = True
"""Source-free parser behavior after diagnostic storage fills; no native calls."""
import ast,hashlib,importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def sha(body):return hashlib.sha256(body).hexdigest()
def need(ok,code):
    if not ok:raise AssertionError(code)
def save(path,value):
    with path.open('x',encoding='utf-8') as out:out.write(json.dumps(value,indent=2,ensure_ascii=False)+'\n')
def main():
    body=(ROOT/'cli_review.py').read_bytes()
    syntax=json.loads((ROOT/'CLI-SYNTAX.json').read_bytes())
    need(sha(body)==syntax['files']['cli_review.py']['sha256'],'FINAL_SOURCE_PIN')
    spec=importlib.util.spec_from_file_location('successor_ledger',ROOT/'cli_review.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    directory=ROOT/'fixtures';directory.mkdir();cases=[]
    for family,text,ending in [('ASCII_LF','fixture\n',b'\n'),('UNICODE_CRLF','条件 λ\r\n',b'\r\n')]:
        def encode(event):return json.dumps(event,ensure_ascii=False,separators=(',',':')).encode()+ending
        init=dict(event='init',init=dict(model=m.MODEL,agent='preflight-inline',cwd='/review',permission_mode='request-review',tools=['finish']))
        def step(label,state,index,**fields):return dict(event='step_update',step_update=dict(step_type=label,state=state,step_index=index,**fields))
        def result(**fields):return dict(event='result',result=dict(status='SUCCESS',num_turns=1,response=text,**fields))
        def prefix(count):return [encode(init),encode(step('user_input','DONE',0))]+[encode(step('agent_response','ACTIVE',1,text_delta=text)) for _ in range(count)]
        normal=[encode(step('agent_response','DONE',1)),encode(step('tool','ACTIVE',2,tool_name='finish')),encode(step('tool','DONE',2,tool_name='finish')),encode(result())]
        for mode,count in [('exact_256',250),('one_over_257',251),('long_1030',1024)]:
            lines=prefix(count)+normal;s=m.Stream();wire=b''.join(lines)
            fixture=directory/(family+'-'+mode+'.ndjson');fixture.write_bytes(wire)
            for line in lines:s.line(line)
            need(s.events==count+6 and s.result['response']==text,'VALID_LONG_REPORT')
            need(len(s.ledger)==min(256,s.events) and s.ledger_omitted==max(0,s.events-256),'STORAGE_BOUNDARY')
            need([x['ordinal'] for x in s.ledger]==list(range(len(s.ledger))),'LEDGER_PREFIX')
            cases.append(dict(family=family,case=mode,status='PASS',fixtureSha256=sha(wire),fixtureBytes=len(wire),acceptedEvents=s.events,storedRows=len(s.ledger),omittedRows=s.ledger_omitted,completeReport=True))
        base=prefix(300);basewire=b''.join(base);(directory/(family+'-overflow-prefix.ndjson')).write_bytes(basewire)
        bad_result=dict(event='result',result=dict(status='ERROR',num_turns=1,response=text))
        two_turns=dict(event='result',result=dict(status='SUCCESS',num_turns=2,response=text))
        no_response=dict(event='result',result=dict(status='SUCCESS',num_turns=1))
        modes=[
            ('operational_tool',[encode(step('tool','ACTIVE',2,tool_name='run_command'))],'OPERATIONAL_TOOL',ValueError),
            ('delegation',[encode(step('agent_response','ACTIVE',1,subagent_info={'subagents':[{}]}))],'DELEGATION_PAYLOAD',ValueError),
            ('finish_error',[encode(step('tool','ERROR',2,tool_name='finish'))],'STEP_STATE',ValueError),
            ('passive_execution_payload',[encode(step('agent_response','ACTIVE',1,tool_info={'name':'run_command'}))],'EXECUTION_PAYLOAD',ValueError),
            ('unknown_step',[encode(step('subagent','ACTIVE',2))],'UNQUALIFIED_STEP',ValueError),
            ('typed_index',[encode(step('agent_response','ACTIVE',True))],'STEP_INDEX',ValueError),
            ('changed_step_type',[encode(step('checkpoint','ACTIVE',1))],'STEP_TYPE_CHANGED',ValueError),
            ('after_done',[encode(step('agent_response','DONE',1)),encode(step('agent_response','ACTIVE',1))],'STEP_AFTER_DONE',ValueError),
            ('active_finish',[encode(step('finish','ACTIVE',2))],'FINISH_STATE',ValueError),
            ('failed_result',[encode(bad_result)],'RESULT_FAILURE',ValueError),
            ('two_turn_result',[encode(two_turns)],'TURN_COUNT',ValueError),
            ('unfinished_steps',[encode(result())],'INCOMPLETE_STEPS',ValueError),
            ('missing_response',[encode(step('agent_response','DONE',1)),encode(no_response)],'REPORT_RESPONSE',ValueError),
            ('after_result',normal+[encode(step('agent_response','ACTIVE',3))],'EVENT_AFTER_RESULT',ValueError),
            ('duplicate_key',[b'{"event":"step_update","event":"result"}'+ending],'DUPLICATE_KEY',ValueError),
            ('malformed_json',[b'{'+ending],None,json.JSONDecodeError),
            ('non_utf8',[b'\xff'+ending],None,UnicodeDecodeError),
            ('nonfinite',[b'{"event":"step_update","step_update":{"step_index":NaN}}'+ending],'NONFINITE',ValueError),
        ]
        for mode,tail,expected,expected_type in modes:
            s=m.Stream()
            for line in base:s.line(line)
            need(len(s.ledger)==256 and s.ledger_omitted==46,'OVERFLOW_PREREQUISITE')
            ledgerpin=sha(json.dumps(s.ledger,sort_keys=True).encode());wire=basewire+b''.join(tail)
            (directory/(family+'-'+mode+'-tail.ndjson')).write_bytes(b''.join(tail))
            caught=None
            try:
                for line in tail:s.line(line)
            except Exception as error:
                caught=error;need(type(error) is expected_type,'POST_OVERFLOW_CLASS')
                if expected is not None:need(str(error)==expected,'POST_OVERFLOW_CODE')
            need(caught is not None,'POST_OVERFLOW_FAILURE_MISSED')
            need(len(s.ledger)==256 and sha(json.dumps(s.ledger,sort_keys=True).encode())==ledgerpin,'RETAINED_PREFIX_MUTATED')
            cases.append(dict(family=family,case=mode,status='PASS',prefixSha256=sha(basewire),tailSha256=sha(b''.join(tail)),fixtureSha256=sha(wire),fixtureBytes=len(wire),failureClass=expected_type.__name__,firstFailure=expected or expected_type.__name__,storedRows=len(s.ledger),omittedRows=s.ledger_omitted,acceptedEvents=s.events,retainedPrefix='EXACT'))
    save(ROOT/'POST-OVERFLOW-CONTROLS.json',dict(status='PASS',method='Actual successor Stream.line on saved source-free fixtures; no native or provider calls',families=2,caseCount=len(cases),cases=cases,nativeCalls=0,containmentQualification='NOT_CLAIMED'))
    print(json.dumps(dict(status='PASS',families=2,caseCount=len(cases),nativeCalls=0)))
if __name__=='__main__':main()
