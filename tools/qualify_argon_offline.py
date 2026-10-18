"""Two fresh portable normal/profile suites. Synthetic children only; no vendor calls."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
ROOT = Path(__file__).resolve().parent.parent

def pin(p):
    b=p.read_bytes(); return dict(sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def save(p,v): p.write_text(json.dumps(v,indent=2)+"\n")
def require(v,reason):
    if not v: raise ValueError(reason)
def main(output):
    output=output.absolute()
    require(not output.resolve().is_relative_to(ROOT.resolve()),'OUTPUT_INSIDE_REPO')
    output.mkdir(parents=True,exist_ok=False)
    package=ROOT/'runtime/argon-high'
    pins=json.loads((ROOT/'qualification/argon-runtime-pins.json').read_bytes())['packageFiles']
    def custody(): return all(pin(package/n)==v for n,v in pins.items())
    require(custody(),'RUNTIME_PIN')
    runs=[]
    for number in (1,2):
        run=output/f'run-{number}';run.mkdir()
        subject=run/'subject';shutil.copytree(package,subject);scripts=subject/'scripts'
        syntax={}
        for p in subject.rglob('*.py'):
            compile(p.read_bytes(),str(p),'exec')
            key=str(p.relative_to(scripts)) if p.is_relative_to(scripts) else str(p.relative_to(subject))
            syntax[key]=dict(**pin(p),status='PASS',completeFinalBytes=True,beforeExecution=True)
        save(scripts/'CLI-SYNTAX.json',dict(status='PASS',files=syntax))
        jobs=[]
        def execute(name,args,document,count):
            process=subprocess.run([sys.executable,'-B','-I',*map(str,args)],capture_output=True,timeout=360)
            (run/(name+'.stdout')).write_bytes(process.stdout);(run/(name+'.stderr')).write_bytes(process.stderr)
            require(process.returncode==0,'SUITE_STOPPED:'+name)
            result=json.loads(document.read_bytes())
            require(result['status']=='PASS' and result['caseCount']==count,'SUITE_RESULT:'+name)
            jobs.append(dict(suite=name,cases=count,result=pin(document)))
        for profile in ('flash-high','argon-high'):
            caps=run/('capabilities-'+profile)
            execute('caps-'+profile,[scripts/'test_cli_capabilities.py',caps,profile],caps/'RESULT.json',48)
            launch=run/('launcher-'+profile)
            execute('launcher-'+profile,[scripts/'test_cli_launcher.py',launch,caps,profile],launch/'RESULT.json',142)
        for name,args,doc,count in (
            ('parser',[scripts/'cli_review.py','controls',scripts/'CLI-OFFLINE-CONTROLS.json'],scripts/'CLI-OFFLINE-CONTROLS.json',24),
            ('overflow',[scripts/'test_ledger.py'],scripts/'POST-OVERFLOW-CONTROLS.json',42),
            ('completion',[scripts/'test_completion.py'],scripts/'COMPLETION-CONTROLS.json',76),
            ('profiles',[scripts/'test_profiles.py',run/'profiles'],run/'profiles/RESULT.json',96)):
            execute(name,args,doc,count)
        require(sum(j['cases'] for j in jobs)==618 and custody(),'RUN_CUSTODY_OR_COUNT')
        save(run/'RESULT.json',dict(status='PASS',caseCount=618,jobs=jobs))
        runs.append(dict(id=f'run-{number}',status='PASS',cases=618,result=pin(run/'RESULT.json'),suites=jobs))
        print(json.dumps(dict(run=number,status='PASS',cases=618)),flush=True)
    spec=importlib.util.spec_from_file_location('published_argon',package/'scripts/cli_review.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    envelope=output/'DUAL-OFFLINE-QUALIFICATION.json'
    save(envelope,dict(status='PASS',scope='OFFLINE_ONLY',twoFreshRuns=True,packageFiles=pins,
        runtimeProfiles=module.profile_bindings(),casesPerRun=618,totalCases=1236,runs=runs,
        nativeCalls=0,proxyCalls=0,providerCalls=0,qualificationCredit=0,
        sharedImplementationAndHost=True,limits='Synthetic normal/profile subset; excludes historical denial drivers. No native qualification or owner authorization.'))
    gate=output/'actual-envelope-controls'
    process=subprocess.run([sys.executable,'-B','-I',str(package/'scripts/test_profiles.py'),str(gate),str(envelope)],capture_output=True,timeout=360)
    (output/'actual-envelope.stdout').write_bytes(process.stdout);(output/'actual-envelope.stderr').write_bytes(process.stderr)
    require(process.returncode==0,'ACTUAL_ENVELOPE_CONTROLS')
    result=json.loads((gate/'RESULT.json').read_bytes())
    require(result['status']=='PASS' and result['caseCount']==40 and custody(),'ACTUAL_ENVELOPE_RESULT')
    print(json.dumps(dict(status='PASS',totalCases=1236,actualEnvelopeControls=40,nativeCalls=0,providerCalls=0)))
if __name__=='__main__':
    if len(sys.argv)!=2: raise SystemExit('Usage: qualify_argon_offline.py <new-output-directory>')
    main(Path(sys.argv[1]))
