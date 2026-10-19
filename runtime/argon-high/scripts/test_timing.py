import sys
sys.dont_write_bytecode=True
from pathlib import Path
import os,json,time,importlib.util
ROOT=Path(__file__).resolve().parents[1]
def need(ok,label):
    if not ok:raise AssertionError(label)
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def load(p,name):
    raw=p.read_bytes();compile(raw,str(p),'exec');spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def validate(record,settlement):
    need({'kind','pid','registeredPgid','startNewSession','observed','scope','registeredAtNs','registeredMonotonicNs','registrationCompletedMonotonicNs','clockBasis'}<=set(record),'REGISTRATION_TIMING_FIELDS')
    need(type(record['registeredAtNs']) is int and record['registeredAtNs']>0,'WALL_OBSERVATION')
    basis=dict(wall='unix_epoch_ns_observation_only',monotonic='host_monotonic_ns')
    need(record['clockBasis']==settlement['clockBasis']==basis,'CLOCK_BASIS')
    mono=[record['registeredMonotonicNs'],record['registrationCompletedMonotonicNs'],settlement['settlementStartedMonotonicNs']]
    observations=settlement['probeObservations']
    need(1<=len(observations)<=41 and [x['outcome'] for x in observations]==settlement['probes'],'PROBE_TIMING_COVERAGE')
    for x in observations:
        need(type(x['observedAtNs']) is int,'PROBE_WALL_TYPE');mono.append(x['observedMonotonicNs'])
    mono.append(settlement['settlementCompletedMonotonicNs'])
    need(all(type(x) is int and x>=0 for x in mono) and mono==sorted(mono),'MONOTONIC_ORDER')
    need(settlement['reaped'] and settlement['groupAbsent'] and settlement['probes'][-1]=='ABSENT_PROCESS_LOOKUP','SETTLEMENT_FACTS')

def main(output):
    output.mkdir(exist_ok=False);h=load(ROOT/'scripts/test_profiles.py','timing_profile_fixtures');m=load(ROOT/'scripts/cli_review.py','timing_runner');rows=[]
    def done(profile,family,case):rows.append(dict(profile=profile,family=family,case=case,status='PASS'))
    for profile in ('flash-high','argon-high'):
      for family in ('ASCII_LF','UNICODE_CRLF'):
        case=output/(profile+'-'+family+'-timing');case.mkdir();e,caps,packet=h.prepare(case,m,profile,family)
        q=case/'QUALIFICATION.json';save(q,dict(status='PASS',scope='OFFLINE_ONLY',twoFreshRuns=True,packageFiles=m.package_identity(),runtimeProfiles=m.profile_bindings(),fixture='LOCAL_SYNTHETIC_NO_NATIVE_AUTHORITY'))
        register=m.register_child;write=m.os.write;registered={};prompt_times=[]
        def capture(child,kind):
            value=register(child,kind);registered[kind]=value;return value
        def deliver(fd,data):
            at=time.monotonic_ns();need(set(registered)=={'proxy','native'},'REGISTERED_BEFORE_PROMPT')
            need(all(x['registrationCompletedMonotonicNs']<=at for x in registered.values()),'REGISTRATION_PRECEDES_DELIVERY');prompt_times.append(at);return write(fd,data)
        m.register_child=capture;m.os.write=deliver
        try:receipt=h.run_case(case,m,e,q,profile)
        finally:m.register_child=register;m.os.write=write
        need(prompt_times and receipt['promptSent'],'TIMED_PROMPT_DELIVERED')
        for kind in ('proxy','native'):
            validate(receipt['registeredChildren'][kind],receipt['registeredSettlement'][kind])
            need(receipt['registeredChildren'][kind]==registered[kind],'REGISTRATION_ARCHIVED')
        need(receipt['privateHomeAbsent'] and receipt['socketDirectoryAbsent'] and not (e/'private-home').exists(),'PHYSICAL_CLEANUP')
        save(case/'TIMING-CHECK.json',dict(status='PASS',receipt=m.pin(e/'CLI-RECEIPT.json'),promptWriteMonotonicNs=prompt_times,scope='Real local Python transport children and registered numeric groups; no agy/provider calls or universal containment claim'))
        done(profile,family,'registration_probe_timing')
    class Child:
        pid=912345
        def poll(self):return 0
    child=Child()
    original={name:getattr(m.os,name) for name in ['getpgid','getsid','killpg']}
    clocks={name:getattr(m.time,name) for name in ['time_ns','monotonic_ns','monotonic','sleep']}
    try:
        m.os.getpgid=lambda pid:pid;m.os.getsid=lambda pid:pid
        def absent(*args):raise ProcessLookupError()
        m.os.killpg=absent;counter=[0];wall=[1000000000000]
        def mono():counter[0]+=1000;return counter[0]
        def backwards():wall[0]-=1;return wall[0]
        m.time.monotonic_ns=mono;m.time.time_ns=backwards
        record=m.register_child(child,'clock_rollback');settlement=m.settle_registered(child,record);validate(record,settlement)
        need(record['registeredAtNs']>settlement['probeObservations'][0]['observedAtNs'],'ROLLBACK_EXERCISED')
        save(output/'clock-rollback.json',dict(identity=record,settlement=settlement,allOsQueriesMocked=True,physicalAbsenceClaim=False));done('both','local','wall_clock_rollback')
        def gone(*args):raise ProcessLookupError()
        m.os.getpgid=gone;m.os.getsid=gone
        record=m.register_child(child,'already_exited');settlement=m.settle_registered(child,record);validate(record,settlement)
        need(record['observed']==dict(pgid=None,sid=None),'EARLY_EXIT_OBSERVATIONS')
        save(output/'early-exit-observation.json',dict(identity=record,settlement=settlement,allOsQueriesMocked=True,physicalAbsenceClaim=False));done('both','local','early_exit_timestamp')
        m.os.getpgid=lambda pid:pid;m.os.getsid=lambda pid:pid;clock=[0.0];calls=[]
        m.time.monotonic=lambda:clock[0];m.time.monotonic_ns=lambda:int(clock[0]*1000000000)
        m.time.sleep=lambda seconds:clock.__setitem__(0,clock[0]+seconds)
        m.os.killpg=lambda *args:calls.append(args)
        record=m.register_child(child,'bound');failed=False
        try:m.settle_registered(child,record)
        except ValueError as error:need(str(error)=='REGISTERED_GROUP_REMAINS','BOUND_FAILURE');failed=True
        need(failed and 1<=len(calls)<=41 and clock[0]<=2.000001,'FIXED_SETTLEMENT_BOUND')
        save(output/'deadline-refusal.json',dict(status='PASS',probeCount=len(calls),elapsedSeconds=clock[0],expected='REGISTERED_GROUP_REMAINS',allOsQueriesMocked=True,physicalAbsenceClaim=False));done('both','local','settlement_deadline_refusal')
    finally:
        for name,value in original.items():setattr(m.os,name,value)
        for name,value in clocks.items():setattr(m.time,name,value)
    need(len(rows)==7,'TIMING_CONTROL_COUNT')
    save(output/'RESULT.json',dict(status='PASS',caseCount=len(rows),cases=rows,retries=0,realNativeCalls=0,realProxyCalls=0,providerModelCalls=0,scope='Four real local Python transport cases plus three explicitly mocked timing/error controls.'))
    print(json.dumps(dict(status='PASS_TIMING_CONTROLS',cases=len(rows))))
if __name__=='__main__':main(Path(sys.argv[1]))
