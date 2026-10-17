"""Exact completion-transition controls before/after ledger overflow; no native calls."""
import hashlib,importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def sha(body):return hashlib.sha256(body).hexdigest()
def need(ok,code):
    if not ok:raise AssertionError(code)
def main():
    body=(ROOT/'cli_review.py').read_bytes();syntax=json.loads((ROOT/'CLI-SYNTAX.json').read_bytes())
    need(sha(body)==syntax['files']['cli_review.py']['sha256'],'FINAL_SOURCE_PIN')
    spec=importlib.util.spec_from_file_location('r3_completion',ROOT/'cli_review.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    directory=ROOT/'fixtures_completion';directory.mkdir();cases=[]
    for family,text,ending in [('ASCII_LF','fixture\n',b'\n'),('UNICODE_CRLF','条件 λ\r\n',b'\r\n')]:
        def encode(event):return json.dumps(event,ensure_ascii=False,separators=(',',':')).encode()+ending
        init=dict(event='init',init=dict(model=m.MODEL,agent='preflight-inline',cwd='/review',permission_mode='request-review',tools=['finish']))
        def step(label,state,index,**fields):return dict(event='step_update',step_update=dict(step_type=label,state=state,step_index=index,**fields))
        def result(status='SUCCESS',turns=1,response=text):return dict(event='result',result=dict(status=status,num_turns=turns,response=response))
        active=step('tool','ACTIVE',2,tool_name='finish');done=step('finish','DONE',2)
        native=[active,done,result()]
        modes=[
            ('named_native_finish',native,None),
            ('pending_native_finish',[step('tool','ACTIVE',2,tool_name=''),done,result()],None),
            ('legacy_tool_completion',[active,step('tool','DONE',2,tool_name='finish'),result()],None),
            ('non_tool_predecessor',[step('checkpoint','ACTIVE',2),done],'STEP_TYPE_CHANGED'),
            ('completed_step_reuse',[active,step('tool','DONE',2,tool_name='finish'),done],'STEP_AFTER_DONE'),
            ('active_finish',[active,step('finish','ACTIVE',2)],'FINISH_STATE'),
            ('error_finish',[active,step('finish','ERROR',2)],'STEP_STATE'),
            ('other_type_change',[active,step('checkpoint','DONE',2)],'STEP_TYPE_CHANGED'),
            ('reverse_after_finish',[active,done,step('tool','ACTIVE',2,tool_name='finish')],'STEP_AFTER_DONE'),
            ('wrong_index',[active,step('finish','DONE',3),result()],'INCOMPLETE_STEPS'),
            ('typed_terminal_index',[active,step('finish','DONE',True)],'STEP_INDEX'),
            ('terminal_execution_payload',[active,step('finish','DONE',2,tool_info={'name':'run_command'})],'EXECUTION_PAYLOAD'),
            ('terminal_tool_name',[active,step('finish','DONE',2,tool_name='finish')],'EXECUTION_PAYLOAD'),
            ('operational_predecessor',[step('tool','ACTIVE',2,tool_name='run_command'),done],'OPERATIONAL_TOOL'),
            ('pending_with_payload',[step('tool','ACTIVE',2,tool_name='',tool_info={'name':'finish'}),done],'UNNAMED_TOOL_PAYLOAD'),
            ('result_failure',[active,done,result(status='ERROR')],'RESULT_FAILURE'),
            ('extra_turn',[active,done,result(turns=2)],'TURN_COUNT'),
            ('missing_response',[active,done,result(response=None)],'REPORT_RESPONSE'),
            ('event_after_result',native+[step('agent_response','ACTIVE',4)],'EVENT_AFTER_RESULT'),
        ]
        for phase,count in [('BEFORE_OVERFLOW',0),('AFTER_OVERFLOW',300)]:
            prefix=[encode(init),encode(step('user_input','DONE',0))]+[encode(step('agent_response','ACTIVE',1,text_delta=text)) for _ in range(count)]+[encode(step('agent_response','DONE',1))]
            for mode,events,expected in modes:
                s=m.Stream();tail=[encode(x) for x in events];wire=b''.join(prefix+tail)
                path=directory/(family+'-'+phase+'-'+mode+'.ndjson');path.write_bytes(wire)
                for raw in prefix:s.line(raw)
                need((s.ledger_omitted>0)==(phase=='AFTER_OVERFLOW'),'PHASE_PREREQUISITE')
                prefixpin=sha(json.dumps(s.ledger,sort_keys=True).encode())
                caught=None
                try:
                    for raw in tail:s.line(raw)
                except ValueError as error:caught=str(error);need(expected==caught,'WRONG_FIRST_FAILURE')
                if expected is None:need(caught is None and s.result['response']==text,'VALID_COMPLETION_REPORT')
                else:need(caught==expected,'EXPECTED_FAILURE_MISSED')
                if phase=='AFTER_OVERFLOW':need(len(s.ledger)==256 and sha(json.dumps(s.ledger,sort_keys=True).encode())==prefixpin,'OVERFLOW_PREFIX_MUTATED')
                need(len(s.ledger)<=256,'STORAGE_BOUND')
                cases.append(dict(family=family,phase=phase,case=mode,status='PASS',firstFailure=caught,completeReport=expected is None,fixturePath=str(path.relative_to(ROOT)),fixtureSha256=sha(wire),fixtureBytes=len(wire),acceptedEvents=s.events,storedRows=len(s.ledger),omittedRows=s.ledger_omitted))
    with (ROOT/'COMPLETION-CONTROLS.json').open('x',encoding='utf-8') as out:out.write(json.dumps(dict(status='PASS',families=2,phases=['BEFORE_OVERFLOW','AFTER_OVERFLOW'],caseCount=len(cases),cases=cases,nativeCalls=0,containmentQualification='NOT_CLAIMED'),indent=2)+'\n')
    print(json.dumps(dict(status='PASS',families=2,phases=2,caseCount=len(cases),nativeCalls=0)))
if __name__=='__main__':main()
