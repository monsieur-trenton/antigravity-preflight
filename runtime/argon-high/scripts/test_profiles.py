import sys, os, json, hashlib, pathlib, shutil, subprocess, time
"""Synthetic profile binding and actual saved-document controls; no real CLI."""
from pathlib import Path
import contextlib,copy,hashlib,importlib.util,io,json,shutil,subprocess,sys,time
ROOT=Path(__file__).resolve().parent.parent
NORMAL=ROOT
REAL_POPEN=subprocess.Popen
def pin(p):
 b=Path(p).read_bytes();return dict(sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def save(p,v):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n')
def need(ok,label):
 if not ok:raise AssertionError(label)
def load(p):
 raw=p.read_bytes();compile(raw,str(p),'exec');spec=importlib.util.spec_from_file_location('profile_test_subject',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def fixture(p,text):
 raw=text.encode();compile(raw,str(p),'exec');p.write_bytes(raw);save(p.with_suffix('.SYNTAX.json'),dict(**pin(p),completeFinalBytes=True,beforeExecution=True,status='PASS'))
def metadata(root,m,profile,family):
 root.mkdir();(root/'runtime').mkdir();(root/'runtime/agy').write_bytes(b'SYNTHETIC_NEVER_EXECUTE\n')
 selected=m.runtime_profile(profile);label={'flash-high':'Gemini 3.8 Flash (High)','argon-high':'Gemini 4 Argon (High)'}[profile];ending='\n' if family=='ASCII_LF' else '\r\n'
 cap=m.load_module('cli_capabilities');native=pin(root/'runtime/agy')
 for n in ['NATIVE-BEFORE.json','NATIVE-AFTER.json']:save(root/n,native)
 for name,args,text in [('VERSION',['--version'],'fixture-future-99'),('HELP',['--help'],' '.join(cap.FLAGS)),('MODELS',['models'],selected['model']+'\t'+label)]:
  (root/(name+'.stdout')).write_bytes((text+ending).encode());(root/(name+'.stderr')).write_bytes(b'')
  save(root/(name+'.json'),dict(args=args,returncode=0,failure=None,cleanupFailures=[],directChildReaped=True,streams={c:pin(root/(name+'.'+c)) for c in ['stdout','stderr']}))
 save(root/'RESULT.json',dict(status='PASS_METADATA_CAPABILITIES_ONLY',binaryStable=True,frozenBinary=native,**cap.interpret(root,profile),fixture='SYNTHETIC_NOT_NATIVE'))
def prepare(case,m,profile,family):
 packet=case/'input';(packet/'snapshots').mkdir(parents=True);ending=b'\n' if family=='ASCII_LF' else b'\r\n'
 (packet/'snapshots/source.txt').write_bytes(('Valid record' if family=='ASCII_LF' else 'Valid record λ').encode()+ending)
 (packet/'PROMPT.txt').write_bytes(b'PLAN review S01 Q01'+ending)
 save(packet/'PACKET.json',dict(schemaVersion=1,mode='PLAN',prompt=dict(path='PROMPT.txt',**pin(packet/'PROMPT.txt')),sources=[dict(id='S01',path='snapshots/source.txt',**pin(packet/'snapshots/source.txt'))],questions=['Q01']))
 caps=case/'metadata';metadata(caps,m,profile,family);e=case/'evidence'
 need(m.prepare(packet/'PACKET.json',caps,e,profile)==0,'PREPARE');return e,caps,packet
def run_case(case,m,e,q,profile,wrong_init=False):
 ending=b'\n' if 'ASCII_LF' in str(case) else b'\r\n'
 report='# 1. Configuration\n# 2. Sources\n# 3. Questions\nQ01 ANSWERED\n# 4. Findings\nNone\n# 5. Completeness\nCOMPLETE\n# 6. Assessment\nNO_BLOCKERS_FOUND\n# 7. Limits\nSynthetic only\n# 8. Actions\nNone\n'
 init=dict(event='init',init=dict(model=('gemini-3.8-flash-high' if profile=='argon-high' else 'gemini-4-argon-high') if wrong_init else m.runtime_profile(profile)['model'],agent='preflight-inline',cwd='/review',permission_mode='request-review',tools=['finish']))
 events=[dict(event='step_update',step_update=dict(step_type='agent_response',state='DONE',step_index=0)),dict(event='result',result=dict(status='SUCCESS',num_turns=1,response=report))]
 proxy=case/'proxy.py';native=case/'native.py'
 fixture(proxy,"import sys,time\nfrom pathlib import Path\nPath(sys.argv[1]).touch(exist_ok=False)\nwhile True:time.sleep(1)\n")
 fixture(native,"import json,sys\nfrom pathlib import Path\nsys.stdout.buffer.write("+repr(json.dumps(init).encode()+ending)+");sys.stdout.buffer.flush()\nprompt=sys.stdin.buffer.readline()\nPath("+repr(str(case/'PROMPT-RECEIVED.bin'))+").write_bytes(prompt)\nsys.stdout.buffer.write("+repr(b''.join(json.dumps(x).encode()+ending for x in events))+");sys.stdout.buffer.flush()\n")
 calls=[]
 def popen(argv,**kw):
  calls.append(argv)
  if argv[0]=='/usr/bin/xdg-dbus-proxy':return REAL_POPEN([sys.executable,'-B','-I',str(proxy),argv[2]],**kw)
  need(argv[0]=='/usr/bin/bwrap','UNEXPECTED_REAL_COMMAND');need(argv[argv.index('--model')+1]==m.runtime_profile(profile)['model'],'ARGV_MODEL');need(argv[argv.index('--effort')+1]=='high','ARGV_EFFORT')
  return REAL_POPEN([sys.executable,'-B','-I',str(native)],**kw)
 m.subprocess.Popen=popen
 try:code=m.run(e,q)
 finally:m.subprocess.Popen=REAL_POPEN
 r=json.loads((e/'CLI-RECEIPT.json').read_bytes())
 need(r['processes']['native']['reaped'] is True and r['processes']['proxy']['reaped'] is True,'REAPED');need(r['privateHomeAbsent'] and r['socketDirectoryAbsent'] and not r['closingFailures'],'CLEANUP')
 if wrong_init:need(code==1 and (r.get('failure') or {}).get('code')=='INIT_BINDING' and r['promptDelivery']['bytesWritten']==0,'INIT_BEFORE_PROMPT')
 else:need(code==0 and r['runtimeProfile']==m.runtime_profile(profile) and r['report']==pin(e/'GEMINI-REVIEW.md'),'PROFILE_REPORT_BINDING')
 save(case/'TRANSPORT.json',dict(calls=len(calls),actualPythonChildren=2,realNativeCalls=0,proxyCalls=0,syntaxRecords=2))
 return r
def main(output,actual=None):
 output.mkdir(parents=True,exist_ok=False);m=load(NORMAL/'scripts/cli_review.py');rows=[];before={n:pin(NORMAL/n) for n in m.CODE_FILES}
 for family in ['ASCII_LF','UNICODE_CRLF']:
  for profile in ['flash-high','argon-high']:
   modes=['valid','wrong_init','missing_profiles','cross_profile','registry_digest','wrong_effort','old_package','bad_status','bad_scope','two_runs_false']
   for mode in modes:
    case=output/(family+'-'+profile+'-'+mode);case.mkdir();e,caps,packet=prepare(case,m,profile,family)
    q=copy.deepcopy(json.loads(Path(actual).read_bytes())) if actual else dict(status='PASS',scope='OFFLINE_ONLY',twoFreshRuns=True,packageFiles=m.package_identity(),runtimeProfiles=m.profile_bindings(),fixture='SYNTHETIC_NOT_ACCEPTANCE')
    if mode=='missing_profiles':q.pop('runtimeProfiles',None)
    if mode=='cross_profile':q['runtimeProfiles']={profile:m.runtime_profile(profile)}
    if mode=='registry_digest':q['runtimeProfiles'][profile]['registry']['sha256']='0'*64
    if mode=='wrong_effort':q['runtimeProfiles'][profile]['effort']='low'
    if mode=='old_package':q['packageFiles'].pop('RUNTIME-PROFILES.json')
    if mode=='bad_status':q['status']='FAIL'
    if mode=='bad_scope':q['scope']='OTHER'
    if mode=='two_runs_false':q['twoFreshRuns']=False
    qpath=Path(actual) if actual and mode in ['valid','wrong_init'] else case/'QUALIFICATION.json'
    if qpath!=Path(actual or ''):save(qpath,q)
    qpin=pin(qpath);save(case/'QUALIFICATION-INPUT.json',dict(path=str(qpath),**qpin,actualSavedDocument=bool(actual and mode in ['valid','wrong_init'])))
    if mode in ['valid','wrong_init']:r=run_case(case,m,e,qpath,profile,mode=='wrong_init')
    else:
     def no_process(*a,**k):raise AssertionError('NO_SPAWN_BEFORE_GATE')
     m.subprocess.Popen=no_process
     try:code=m.run(e,qpath)
     finally:m.subprocess.Popen=REAL_POPEN
     r=json.loads((e/'CLI-RECEIPT.json').read_bytes());need(code==1 and r['invocations']==dict(proxy=0,native=0),'PRELAUNCH_ZERO_SPAWN')
     expected='OFFLINE_QUALIFICATION_REQUIRED' if mode in ['old_package','bad_status','bad_scope'] else 'DUAL_OFFLINE_REQUIRED' if mode=='two_runs_false' else 'PROFILE_QUALIFICATION'
     need((r.get('failure') or {}).get('code')==expected,(mode,r['failure']))
    need(pin(qpath)==qpin,'SAVED_DOCUMENT_CUSTODY');rows.append(dict(family=family,profile=profile,case=mode,status='PASS',receipt=pin(e/'CLI-RECEIPT.json')))
   if actual:continue
   for mode in ['unknown_profile','missing_profile','plan_profile','plan_model','plan_effort','plan_registry','catalogue_missing','catalogue_duplicate','catalogue_label','catalogue_alias','metadata_profile','registry_unknown_key','registry_duplicate_key','registry_wrong_effort']:
    case=output/(family+'-'+profile+'-'+mode);case.mkdir();local=NORMAL;subject=m
    if mode.startswith('registry_'):
     local=case/'subject';shutil.copytree(NORMAL,local);reg=local/'RUNTIME-PROFILES.json';v=json.loads(reg.read_bytes())
     if mode=='registry_unknown_key':v['extra']=True
     if mode=='registry_wrong_effort':v['profiles'][profile]['effort']='low'
     reg.write_text('{"schemaVersion":1,"schemaVersion":1}' if mode=='registry_duplicate_key' else json.dumps(v));subject=load(local/'scripts/cli_review.py')
     try:subject.runtime_profile(profile)
     except ValueError as error:need(str(error)==('PROFILE_DUPLICATE_KEY' if mode=='registry_duplicate_key' else 'PROFILE_REGISTRY'),'REGISTRY_REFUSAL')
     else:raise AssertionError('REGISTRY_ACCEPTED')
    else:
     e,caps,packet=prepare(case,subject,profile,family)
     if mode=='unknown_profile':
      try:subject.runtime_profile('other')
      except ValueError as error:need(str(error)=='RUNTIME_PROFILE_REQUIRED','UNKNOWN_PROFILE')
      else:raise AssertionError('PROFILE_ACCEPTED')
     elif mode=='missing_profile':
      with contextlib.redirect_stderr(io.StringIO()):
       try:subject.main(['prepare',str(packet/'PACKET.json'),str(caps),str(case/'absent')])
       except SystemExit as error:need(error.code==2,'MISSING_EXPLICIT_PROFILE')
       else:raise AssertionError('MISSING_PROFILE_ACCEPTED')
     elif mode.startswith('plan_'):
      p=json.loads((e/'CLI-PLAN.json').read_bytes())
      if mode=='plan_profile':p['runtimeProfile']['id']='other'
      if mode=='plan_model':p['model']='other'
      if mode=='plan_effort':p['effort']='low'
      if mode=='plan_registry':p['runtimeProfile']['registry']['sha256']='0'*64
      save(case/'PLAN-BEFORE.json',p);(e/'CLI-PLAN.json').write_text(json.dumps(p));v=json.loads((e/'PREPARE-RESULT.json').read_bytes());v['plan']=pin(e/'CLI-PLAN.json');(e/'PREPARE-RESULT.json').write_text(json.dumps(v))
      qpath=case/'QUALIFICATION.json';save(qpath,dict(status='PASS',scope='OFFLINE_ONLY',twoFreshRuns=True,packageFiles=m.package_identity(),runtimeProfiles=m.profile_bindings()))
      def no_process(*a,**k):raise AssertionError('TAMPER_SPAWN')
      m.subprocess.Popen=no_process
      try:code=m.run(e,qpath)
      finally:m.subprocess.Popen=REAL_POPEN
      r=json.loads((e/'CLI-RECEIPT.json').read_bytes());need(code==1 and r['invocations']==dict(proxy=0,native=0),'PLAN_REFUSAL')
      need((r.get('failure') or {}).get('code')==('RUNTIME_PROFILE_REQUIRED' if mode=='plan_profile' else 'PROFILE_PLAN_PIN' if mode=='plan_registry' else 'PLAN_LIMITS'),'PLAN_DIAGNOSTIC')
     else:
      if mode=='metadata_profile':v=json.loads((caps/'RESULT.json').read_bytes());v['runtimeProfile']['id']='other';(caps/'RESULT.json').write_text(json.dumps(v))
      else:
       p=caps/'MODELS.stdout';v=p.read_text()
       if mode=='catalogue_missing':v='other\tOther\n'
       if mode=='catalogue_duplicate':v+=v
       if mode=='catalogue_label':v=v.replace('(High)','(Low)')
       if mode=='catalogue_alias':v=v.replace(m.runtime_profile(profile)['model'],m.runtime_profile(profile)['model']+'-alias')
       p.write_text(v);record=json.loads((caps/'MODELS.json').read_bytes());record['streams']['stdout']=pin(p);(caps/'MODELS.json').write_text(json.dumps(record))
      try:subject.prepare(packet/'PACKET.json',caps,case/'rejected',profile)
      except ValueError as error:need(str(error)==('METADATA_INTERPRETATION' if mode=='metadata_profile' else 'PINNED_MODEL_UNAVAILABLE_OR_AMBIGUOUS'),'CATALOGUE_REFUSAL')
      else:raise AssertionError('METADATA_ACCEPTED')
    rows.append(dict(family=family,profile=profile,case=mode,status='PASS'))
 need(before=={n:pin(NORMAL/n) for n in m.CODE_FILES},'FROZEN_SOURCE_CUSTODY')
 result=dict(status='PASS',caseCount=len(rows),cases=rows,actualSavedDocument=bool(actual),scope='OFFLINE_ONLY',realNativeCalls=0,proxyCalls=0,providerCalls=0)
 save(output/'RESULT.json',result);print(json.dumps(dict(status='PASS',cases=len(rows),actual=bool(actual))))
if __name__=='__main__':main(Path(sys.argv[1]),sys.argv[2] if len(sys.argv)>2 else None)
