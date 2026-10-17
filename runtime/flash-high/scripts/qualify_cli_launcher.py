"""One fresh offline qualification of the reusable launcher; no real CLI calls."""
import hashlib,json,os,shutil,signal,subprocess,sys,time
from pathlib import Path

PACKAGE=Path(__file__).resolve().parent.parent
def pin(path):
    body=path.read_bytes();return dict(sha256=hashlib.sha256(body).hexdigest(),bytes=len(body))
def save(path,value):
    with path.open('x',encoding='utf-8') as out:out.write(json.dumps(value,indent=2)+'\n')
def inventory(root):
    return {str(p.relative_to(root)):pin(p) for p in sorted(root.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
def execute(command,root,label):
    process=None;failure=None;stdout=stderr=b'';start=time.monotonic()
    try:
        process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        stdout,stderr=process.communicate(timeout=90)
    except subprocess.TimeoutExpired:
        failure='OFFLINE_COMMAND_TIMEOUT';os.killpg(process.pid,signal.SIGKILL);stdout,stderr=process.communicate(timeout=5)
    finally:
        if process is not None and process.poll() is None:
            os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=5)
        (root/(label+'.stdout')).write_bytes(stdout);(root/(label+'.stderr')).write_bytes(stderr)
        save(root/(label+'.json'),dict(argv=command,exit=process.returncode if process else None,failure=failure,elapsedSeconds=round(time.monotonic()-start,3),directChildReaped=process is not None and process.poll() is not None))
    if failure or process is None or process.returncode!=0:raise ValueError('OFFLINE_COMMAND_FAILED:'+label)
def main(root):
    root.mkdir(parents=True,exist_ok=False);before=inventory(PACKAGE);save(root/'PACKAGE-BEFORE.json',before)
    subject=root/'subject';shutil.copytree(PACKAGE,subject);scripts=subject/'scripts';results=[]
    started=time.time_ns()
    try:
        rows={}
        for p in sorted(subject.rglob('*.py')):
            body=p.read_bytes();compile(body,str(p),'exec');rows[str(p.relative_to(scripts)) if p.is_relative_to(scripts) else str(p.relative_to(subject))]=dict(**pin(p),status='PASS',completeFinalBytes=True,beforeExecution=True)
        save(root/'FINAL-BYTE-SYNTAX.json',dict(status='PASS',files=rows))
        save(scripts/'CLI-SYNTAX.json',dict(status='PASS',files=rows))
        jobs=[('update',[str(scripts/'test_cli_capabilities.py'),str(root/'update-controls')],root/'update-controls/RESULT.json',48),
              ('parser',[str(scripts/'cli_review.py'),'controls',str(scripts/'CLI-OFFLINE-CONTROLS.json')],scripts/'CLI-OFFLINE-CONTROLS.json',24),
              ('overflow',[str(scripts/'test_ledger.py')],scripts/'POST-OVERFLOW-CONTROLS.json',42),
              ('completion',[str(scripts/'test_completion.py')],scripts/'COMPLETION-CONTROLS.json',76),
              ('entrypoint',[str(scripts/'test_cli_launcher.py'),str(root/'entrypoint-controls'),str(root/'update-controls')],root/'entrypoint-controls/RESULT.json',142)]
        for label,args,result_path,count in jobs:
            execute([sys.executable,'-B','-I',*args],root,label)
            data=json.loads(result_path.read_bytes())
            if data['status']!='PASS' or data['caseCount']!=count or data['families']!=2:raise ValueError('OFFLINE_RESULT:'+label)
            results.append(dict(suite=label,cases=count,result=str(result_path.relative_to(root)),**pin(result_path)))
        if inventory(PACKAGE)!=before:raise ValueError('SOURCE_PACKAGE_CUSTODY')
        for name,row in before.items():
            if pin(subject/name)!=row:raise ValueError('COPIED_SOURCE_CUSTODY')
        status='PASS';failure=None
    except Exception as error:
        status='STOPPED';failure=str(error) if type(error) is ValueError else type(error).__name__
    save(root/'PACKAGE-AFTER.json',inventory(PACKAGE))
    save(root/'RESULT.json',dict(status=status,failure=failure,scope='OFFLINE_ONLY',startedNs=started,completedNs=time.time_ns(),suites=results,totalCases=sum(x['cases'] for x in results),remainingSuites='NONE' if status=='PASS' else 'UNRUN',sourcePackageCustody='EXACT' if inventory(PACKAGE)==before else 'CHANGED',realNativeCalls=0,realProxyCalls=0,providerCalls=0,generativeCalls=0,qualificationCredit=0,limits='Source-free transport doubles; no native denial, provider, live or activation qualification'))
    print(json.dumps(dict(status=status,failure=failure,cases=sum(x['cases'] for x in results),realNativeCalls=0)))
    return 0 if status=='PASS' else 1
if __name__=='__main__':sys.exit(main(Path(sys.argv[1]).absolute()))
